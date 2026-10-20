"""
Copilot endpoints (all @require_auth; the AI ones also spend AI quota).

  GET        /api/copilot/state                 figures, cash, settings, approved results, pending proposals
  PUT        /api/copilot/settings              {cash, business_form} — the owner's own numbers
  POST       /api/copilot/entries               AI: owner's text → proposed income and expense records
  POST       /api/copilot/analysis              AI: health check of the monthly figures
  POST       /api/copilot/runway                AI: when the money runs out, and what to do
  POST       /api/copilot/loan                  {amount, months, purpose} → best bank loan, explained
  POST       /api/copilot/plan                  AI: business plan with a 12-month forecast
  POST       /api/copilot/actions/<id>/decide   {decision: approve|reject}
  GET        /api/copilot/history[?format=csv]  everything the AI did, with the decisions

Every AI call returns a proposal (status "pending") listing the changes an
approval would make; nothing in the business's data changes until the owner
approves it.
"""
import csv
import io
import json
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from accounts.auth import require_auth
from ai_engine import gemini
from ai_engine.quota import check_ai_quota, consume_and_log, quota_dict
from startup.models import CashFlowEntry, Employee, Product, StartupProfile, StartupTodo

from . import ai, finance, loans
from .models import CopilotAction

Kind, Status = CopilotAction.Kind, CopilotAction.Status
FORMS = ("business", "person")
GROWTH, COST_GROWTH = 3.0, 2.0  # forecast assumptions, % a month


def _json(request):
    try:
        data = json.loads(request.body or b"{}")
        return (data, None) if isinstance(data, dict) else (None, JsonResponse({"detail": "Malformed JSON body."}, status=400))
    except (ValueError, UnicodeDecodeError):
        return None, JsonResponse({"detail": "Malformed JSON body."}, status=400)


def _language(data):
    return data.get("language") if data.get("language") in ("en", "ru", "uz") else "en"


def _profile(user):
    profile, _ = StartupProfile.objects.get_or_create(user=user)
    return profile


def _copilot(profile):
    return profile.copilot if isinstance(profile.copilot, dict) else {}


def _context(profile):
    """What the model is told about the business (no people's names)."""
    o = profile.onboarding or {}
    team = Employee.objects.filter(user=profile.user)
    return {
        "name": profile.name,
        "industry": profile.industry,
        "city": o.get("location", ""),
        "description": o.get("description", ""),
        "customers": o.get("market", ""),
        "stage": o.get("stage", ""),
        "team_size": team.count(),
        "team": [e.position or e.role[:60] for e in team[:15]],
        "products": [{"name": p.name, "price": finance.money(p.price)} for p in Product.objects.filter(user=profile.user)[:15]],
        "legal_form": _copilot(profile).get("business_form", ""),
    }


def action_dict(a):
    return {
        "id": str(a.id),
        "kind": a.kind,
        "status": a.status,
        "title": a.title,
        "summary": a.summary,
        "payload": a.payload,
        "effects": a.effects,
        "outcome": a.outcome,
        "created_at": a.created_at.isoformat(),
        "decided_at": a.decided_at.isoformat() if a.decided_at else None,
    }


def _propose(request, kind, title, summary, payload, effects, language, result):
    action = CopilotAction.objects.create(
        user=request.auth_user, kind=kind, title=title[:200], summary=summary, payload=payload,
        effects=effects, language=language, model_version=getattr(result, "model_version", "") or "",
    )
    quota = consume_and_log(request.auth_user, gemini.FEATURE_COPILOT, result) if result and not result.is_stub else None
    return JsonResponse({"action": action_dict(action), "quota": quota_dict(quota) if quota else None}, status=201)


def _ai_failed(result):
    if result and result.is_stub:
        return JsonResponse({"detail": "AI is not connected yet.", "code": "ai_unavailable"}, status=503)
    return JsonResponse({"detail": "The AI could not finish this just now. Try again in a minute."}, status=502)


def _need_figures(summary):
    if not summary["has_data"]:
        return JsonResponse({"detail": "Add your income and expenses first.", "code": "no_figures"}, status=400)
    return None


# --------------------------------------------------------------------------- #
@require_GET
@require_auth
def state(request):
    profile = _profile(request.auth_user)
    summary = finance.summary(request.auth_user)
    cp = _copilot(profile)
    pending = CopilotAction.objects.filter(user=request.auth_user, status=Status.PENDING)[:10]
    return JsonResponse({
        "currency": profile.currency,
        "summary": summary,
        "cash": cp.get("cash"),
        "business_form": cp.get("business_form", ""),
        "runway": finance.runway(cp["cash"], summary) if cp.get("cash") is not None and summary["has_data"] else None,
        "approved": {k: cp.get(k) for k in ("analysis", "runway", "loan", "plan")},
        "pending": [action_dict(a) for a in pending],
        "loan_catalog_checked": loans.CHECKED,
    })


@csrf_exempt
@require_auth
def settings_view(request):
    if request.method != "PUT":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    data, err = _json(request)
    if err:
        return err
    profile = _profile(request.auth_user)
    cp = dict(_copilot(profile))
    if "cash" in data:
        try:
            cash = Decimal(str(data["cash"]))
        except (InvalidOperation, TypeError):
            return JsonResponse({"detail": "Enter the cash you have as a number."}, status=400)
        if not cash.is_finite() or not Decimal(0) <= cash < Decimal("1e12"):
            return JsonResponse({"detail": "Enter the cash you have as a number."}, status=400)
        cp["cash"] = finance.money(cash)
    if "business_form" in data:
        if data["business_form"] not in FORMS:
            return JsonResponse({"detail": "Choose how the business is registered."}, status=400)
        cp["business_form"] = data["business_form"]
    profile.copilot = cp
    profile.save(update_fields=["copilot", "updated_at"])
    return JsonResponse({"cash": cp.get("cash"), "business_form": cp.get("business_form", "")})


# --------------------------------------------------------------------------- #
# The AI's work: each returns a proposal.
def _post_only(view):
    def wrapper(request, *args, **kwargs):
        if request.method != "POST":
            return JsonResponse({"detail": "Method not allowed."}, status=405)
        return view(request, *args, **kwargs)

    wrapper.__name__ = view.__name__
    return wrapper


@csrf_exempt
@require_auth
@_post_only
@check_ai_quota
def entries(request):
    data, err = _json(request)
    if err:
        return err
    raw = str(data.get("text") or "").strip()
    if not raw:
        return JsonResponse({"detail": "Describe your income and expenses first."}, status=400)
    language = _language(data)
    profile = _profile(request.auth_user)
    parsed, result = ai.parse_entries(raw, language, profile.currency)
    if parsed is None:
        return _ai_failed(result)
    if not parsed["entries"]:
        return JsonResponse({"detail": "No amounts were found in the text. Write them with numbers.", "unclear": parsed["unclear"]}, status=400)
    revenue = sum(Decimal(e["amount"]) for e in parsed["entries"] if e["type"] == "revenue")
    spending = sum(Decimal(e["amount"]) for e in parsed["entries"] if e["type"] == "spending")
    parsed["source"] = raw[:2000]
    return _propose(
        request, Kind.ENTRIES, "Read income and expenses",
        f"{len(parsed['entries'])} · +{finance.grouped(revenue)} / -{finance.grouped(spending)} {profile.currency}",
        parsed, [{"type": "add_entries", "count": len(parsed["entries"])}], language, result,
    )


@csrf_exempt
@require_auth
@_post_only
@check_ai_quota
def analysis(request):
    data, err = _json(request)
    if err:
        return err
    language = _language(data)
    profile = _profile(request.auth_user)
    summary = finance.summary(request.auth_user)
    missing = _need_figures(summary)
    if missing:
        return missing
    report, result = ai.analyze(_context(profile), summary, language, profile.currency)
    if report is None:
        return _ai_failed(result)
    report["summary"] = summary
    effects = [{"type": "save_report"}] + ([{"type": "add_tasks", "count": len(report["actions"])}] if report["actions"] else [])
    return _propose(request, Kind.ANALYSIS, "Financial analysis", report["headline"], report, effects, language, result)


@csrf_exempt
@require_auth
@_post_only
@check_ai_quota
def runway(request):
    data, err = _json(request)
    if err:
        return err
    language = _language(data)
    profile = _profile(request.auth_user)
    summary = finance.summary(request.auth_user)
    missing = _need_figures(summary)
    if missing:
        return missing
    cash = _copilot(profile).get("cash")
    if cash is None:
        return JsonResponse({"detail": "Enter how much cash the business has now.", "code": "no_cash"}, status=400)
    forecast = finance.runway(cash, summary)
    advice, result = ai.runway_advice(_context(profile), summary, forecast, language, profile.currency)
    if advice is None:
        return _ai_failed(result)
    payload = {"forecast": forecast, **advice}
    effects = [{"type": "save_forecast"}] + ([{"type": "add_tasks", "count": len(advice["actions"])}] if advice["actions"] else [])
    return _propose(request, Kind.RUNWAY, "Cash runway warning", advice["message"], payload, effects, language, result)


@csrf_exempt
@require_auth
@_post_only
@check_ai_quota
def loan(request):
    data, err = _json(request)
    if err:
        return err
    language = _language(data)
    profile = _profile(request.auth_user)
    try:
        amount = Decimal(str(data.get("amount")))
        months = int(data.get("months"))
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({"detail": "Enter the loan amount and the term in months."}, status=400)
    if not amount.is_finite() or not Decimal("1000000") <= amount <= Decimal("10000000000") or not 3 <= months <= 120:
        return JsonResponse({"detail": "Enter the loan amount and the term in months."}, status=400)
    purpose = data.get("purpose") if data.get("purpose") in loans.PURPOSES else "any"
    form = _copilot(profile).get("business_form") or "business"
    summary = finance.summary(request.auth_user)
    ranked = loans.match(amount, months, form, purpose, summary["net"])
    eligible = [p for p in ranked if p["eligible"]]
    if not eligible:
        return JsonResponse({"detail": "None of the banks' products fits this amount and term. Try a smaller amount or another term.", "code": "no_loan", "products": ranked}, status=400)
    need = {"amount": finance.money(amount), "months": months, "purpose": purpose, "borrower": form}
    explained, result = ai.explain_loan(_context(profile), summary, need, eligible[:3], language, profile.currency)
    if explained is None:
        return _ai_failed(result)
    chosen = next(p for p in eligible if p["id"] == explained["choice"])
    payload = {"need": need, "chosen": chosen, "options": ranked, "checked": loans.CHECKED, **explained}
    effects = [{"type": "save_loan"}, {"type": "add_tasks", "count": 1}]
    return _propose(request, Kind.LOAN, "Bank loan match", f"{chosen['bank']} — {chosen['product']}", payload, effects, language, result)


@csrf_exempt
@require_auth
@_post_only
@check_ai_quota
def plan(request):
    data, err = _json(request)
    if err:
        return err
    language = _language(data)
    profile = _profile(request.auth_user)
    summary = finance.summary(request.auth_user)
    missing = _need_figures(summary)
    if missing:
        return missing
    approved_loan = _copilot(profile).get("loan")
    loan_terms = None
    if approved_loan:
        chosen = approved_loan.get("chosen", {})
        loan_terms = {"amount": approved_loan.get("need", {}).get("amount", "0"), "payment": chosen.get("payment", "0"),
                      "bank": chosen.get("bank"), "product": chosen.get("product")}
    assumptions = {"revenue_growth_per_month": f"{GROWTH}%", "variable_cost_growth_per_month": f"{COST_GROWTH}%", "fixed_costs": "flat"}
    forecast = finance.projection(summary, GROWTH, COST_GROWTH, 12, loan_terms)
    written, result = ai.business_plan(_context(profile), summary, assumptions, forecast, loan_terms, language, profile.currency)
    if written is None:
        return _ai_failed(result)
    payload = {**written, "forecast": forecast, "assumptions": assumptions, "summary": summary, "loan": loan_terms}
    return _propose(request, Kind.PLAN, "Business plan", written["title"] or written["executive_summary"][:160], payload,
                    [{"type": "save_plan"}], language, result)


# --------------------------------------------------------------------------- #
# The owner's decision.
def _apply(action, profile):
    """Make the changes an approved proposal listed. Returns what was done."""
    p, user = action.payload, action.user
    cp = dict(_copilot(profile))
    done = []
    if action.kind == Kind.ENTRIES:
        today = timezone.localdate()
        rows = []
        for e in p.get("entries", []):
            year, month = int(e["month"][:4]), int(e["month"][5:7])
            day = today if (year, month) == (today.year, today.month) else today.replace(year=year, month=month, day=1)
            rows.append(CashFlowEntry(
                user=user, entry_type=e["type"], category=e["category"][:80], amount=Decimal(e["amount"]),
                description=(e.get("note") or "Zinvest AI Accountant")[:200], cost_type=e.get("cost_type", "variable"), occurred_on=day,
            ))
        CashFlowEntry.objects.bulk_create(rows)
        done.append({"type": "added_entries", "count": len(rows)})
    else:
        cp[action.kind] = {**p, "approved_at": timezone.now().isoformat()}
        done.append({"type": "saved", "what": action.kind})
        if action.kind in (Kind.ANALYSIS, Kind.RUNWAY):
            done += _tasks(user, [a["title"] for a in p.get("actions", [])])
        elif action.kind == Kind.LOAN:
            done += _tasks(user, [p.get("todo") or f"{p['chosen']['product']} — {p['chosen']['bank']}"])
    profile.copilot = cp
    profile.save(update_fields=["copilot", "updated_at"])
    return done


def _tasks(user, titles):
    titles = [t[:200] for t in titles if t]
    StartupTodo.objects.bulk_create([StartupTodo(user=user, title=t) for t in titles])
    return [{"type": "created_tasks", "count": len(titles)}] if titles else []


OUTCOME_TEXT = {
    "added_entries": "Added {count} income and expense records",
    "saved": "Saved the {what}",
    "created_tasks": "Created {count} tasks in the to-do list",
    "nothing_changed": "Nothing was changed",
}


def outcome_text(outcome):
    """The outcome in English, for the CSV."""
    return "; ".join(OUTCOME_TEXT.get(o.get("type"), o.get("type", "")).format(**{"count": "", "what": "", **o}) for o in outcome or [])


@csrf_exempt
@require_auth
def decide(request, action_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    data, err = _json(request)
    if err:
        return err
    decision = data.get("decision")
    if decision not in ("approve", "reject"):
        return JsonResponse({"detail": "Choose approve or reject."}, status=400)
    with transaction.atomic():
        action = get_object_or_404(CopilotAction.objects.select_for_update(), pk=action_id, user=request.auth_user)
        if action.status != Status.PENDING:
            return JsonResponse({"detail": "This proposal was already decided.", "action": action_dict(action)}, status=409)
        if decision == "approve":
            profile = StartupProfile.objects.select_for_update().get(pk=_profile(request.auth_user).pk)
            action.outcome = _apply(action, profile)
            action.status = Status.APPROVED
        else:
            action.outcome = [{"type": "nothing_changed"}]
            action.status = Status.REJECTED
        action.decided_at = timezone.now()
        action.save(update_fields=["status", "outcome", "decided_at"])
    return JsonResponse({"action": action_dict(action)})


# --------------------------------------------------------------------------- #
@require_GET
@require_auth
def history(request):
    qs = CopilotAction.objects.filter(user=request.auth_user)[:500]
    if request.GET.get("format") == "csv":
        out = io.StringIO()
        out.write("﻿")  # so Excel reads the Cyrillic right
        w = csv.writer(out)
        w.writerow(["time", "action", "status", "summary", "changes made", "decided at"])
        for a in qs:
            w.writerow([
                timezone.localtime(a.created_at).strftime("%Y-%m-%d %H:%M"), a.title, a.status, a.summary, outcome_text(a.outcome),
                timezone.localtime(a.decided_at).strftime("%Y-%m-%d %H:%M") if a.decided_at else "",
            ])
        response = HttpResponse(out.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="zinvest-copilot-history.csv"'
        return response
    return JsonResponse({"actions": [action_dict(a) for a in qs]})
