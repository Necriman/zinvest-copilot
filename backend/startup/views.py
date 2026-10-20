"""
Startup endpoints (native JsonResponse — no DRF). All @require_auth.

  GET        /api/startup/summary               revenue / spending / net (aggregated)
  GET · PUT  /api/startup/profile
  POST       /api/startup/onboarding            AI: nine answers → market check with search → blocks
  GET · POST /api/startup/cashflow
  DELETE     /api/startup/cashflow/<uuid>
  GET · POST /api/startup/employees             (+ total_salary aggregate)
  POST       /api/startup/employees/import      bulk rows parsed client-side from CSV/JSON
  PUT·DELETE /api/startup/employees/<uuid>
  POST       /api/startup/employees/<uuid>/photo   (multipart)
  GET · POST /api/startup/products
  POST       /api/startup/products/import       bulk rows parsed client-side from CSV/JSON
  PUT·DELETE /api/startup/products/<uuid>
  POST       /api/startup/products/<uuid>/image    (multipart)
  GET · POST /api/startup/assignments
  PATCH·DEL  /api/startup/assignments/<uuid>
  GET · POST /api/startup/todos
  PATCH·DEL  /api/startup/todos/<uuid>
  GET · POST /api/startup/roadmap               AI: where the startup stands → the road to a full startup
  POST       /api/startup/roadmap/questions     AI: what it needs to ask before building
  PATCH      /api/startup/roadmap/items/<id>    finish the next step or milestone / reopen the latest

Revenue/spending/net are computed with a DB aggregate; amounts are Decimal,
serialized as strings.
"""
import json
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import models, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from accounts.auth import require_auth
from ai_engine import gemini
from ai_engine.quota import check_ai_quota, consume_and_log, quota_dict

from . import research, roadmap as roadmaps
from .models import Assignment, CashFlowEntry, Employee, Product, StartupProfile, StartupTodo

ZERO = Decimal("0.00")

# Magic bytes → extension. The client's filename and Content-Type are attacker-
# controlled, so the stored extension is derived from the actual bytes instead.
_IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
)


def _sniff_image(header):
    for signature, ext in _IMAGE_SIGNATURES:
        if header.startswith(signature):
            return ext
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def _json_body(request):
    try:
        data = json.loads(request.body or b"{}")
        if not isinstance(data, dict):
            raise ValueError()
        return data, None
    except (ValueError, UnicodeDecodeError):
        return None, JsonResponse({"detail": "Malformed JSON body."}, status=400)


def _money(value):
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value or 0))
        except (InvalidOperation, TypeError):
            value = ZERO
    return str(value.quantize(ZERO))


def _decimal(value):
    """Parse a money value; None on failure/negative."""
    try:
        amount = Decimal(str(value)).quantize(ZERO)
    except (InvalidOperation, TypeError):
        return None
    return amount if amount.is_finite() and ZERO <= amount < Decimal('1000000000000') else None


def _get_profile(user):
    profile, _ = StartupProfile.objects.get_or_create(user=user)
    return profile


def _workspace_fields(p):
    return {k: getattr(p, k) for k in ('operating_mode', 'locations', 'demand', 'public_visible', 'public_summary')}


def _update_workspace(p, data):
    if 'operating_mode' in data:
        if data['operating_mode'] not in ('online', 'offline', 'hybrid'):
            return 'Invalid operating mode.'
        p.operating_mode = data['operating_mode']
    if 'locations' in data:
        rows = data['locations']
        if not isinstance(rows, list) or len(rows) > 100:
            return 'Locations must be a list of up to 100 entries.'
        cleaned = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('country'), str) or not row['country'].strip():
                return 'Every location needs a country.'
            clean = {k: str(row.get(k) or '').strip()[:240] for k in ('country', 'region', 'address')}
            if p.operating_mode in ('offline', 'hybrid') and not clean['address']:
                return 'Offline locations need a street address.'
            cleaned.append(clean)
        p.locations = cleaned
    if 'demand' in data:
        d = data['demand']
        if not isinstance(d, dict) or d.get('level') not in ('none', 'low', 'moderate', 'high', 'excess'):
            return 'Choose a demand level.'
        if not isinstance(d.get('evidence'), str) or not d['evidence'].strip():
            return 'Describe the evidence behind your demand assessment.'
        try:
            observed = date.fromisoformat(d.get('observed_on', ''))
        except (TypeError, ValueError):
            return 'Use a valid observation date.'
        if observed > timezone.localdate():
            return 'Observation date cannot be in the future.'
        counts = [d.get(k, 0) for k in ('inquiries', 'orders')]
        if any(type(n) is not int or not 0 <= n <= 100000000 for n in counts):
            return 'Inquiries and orders must be non-negative whole numbers.'
        p.demand = {'level':d['level'], 'evidence':d['evidence'].strip()[:5000], 'observed_on':observed.isoformat(), 'inquiries':counts[0], 'orders':counts[1], 'source':'founder'}
    if 'public_visible' in data:
        if type(data['public_visible']) is not bool:
            return 'Public visibility must be a boolean.'
        p.public_visible = data['public_visible']
    if 'public_summary' in data:
        p.public_summary = str(data['public_summary'] or '')[:3000]
    if 'blocks' in data:
        enabled = data['blocks']
        if not isinstance(enabled, list) or any(k not in MUST_BE_BLOCKS + ['tasks'] for k in enabled):
            return 'Unknown workspace block.'
        p.blocks = {**(p.blocks or {}), 'enabled':list(dict.fromkeys(enabled))}
    return None


def _file_url(request, field):
    return request.build_absolute_uri(field.url) if field else None


def _totals(user, period=None):
    qs = CashFlowEntry.objects.filter(user=user)
    if period:
        qs = qs.filter(occurred_on__year=period[0], occurred_on__month=period[1])
    agg = qs.aggregate(
        revenue=models.Sum("amount", filter=models.Q(entry_type=CashFlowEntry.Type.REVENUE)),
        spending=models.Sum("amount", filter=models.Q(entry_type=CashFlowEntry.Type.SPENDING)),
    )
    revenue = agg["revenue"] or ZERO
    spending = agg["spending"] or ZERO
    return {
        "revenue": _money(revenue),
        "spending": _money(spending),
        "net": _money(revenue - spending),
    }


def _parse_period(request):
    raw = request.GET.get("period")
    if not raw:
        return None
    try:
        year, month = raw.split("-")
        date(int(year), int(month), 1)
        return int(year), int(month)
    except (ValueError, AttributeError):
        return None


def _entry_dict(e):
    return {
        "id": str(e.id),
        "entry_type": e.entry_type,
        "category": e.category,
        "amount": _money(e.amount),
        "description": e.description,
        "cost_type": e.cost_type,
        "occurred_on": e.occurred_on.isoformat(),
    }


# --------------------------------------------------------------------------- #
@require_GET
@require_auth
def summary(request):
    profile = _get_profile(request.auth_user)
    period = _parse_period(request)
    if request.GET.get('period') and not period:
        return JsonResponse({'detail':'Use a valid month (YYYY-MM).'},status=400)
    return JsonResponse(
        {
            "name": profile.name,
            "currency": profile.currency,
            "period": request.GET.get("period"),
            **_totals(request.auth_user, period),
        }
    )


@csrf_exempt
@require_auth
def profile(request):
    if request.method == "GET":
        p = _get_profile(request.auth_user)
        _offer_new_blocks(p)
        return JsonResponse(
            {
                "name": p.name,
                "industry": p.industry,
                "currency": p.currency,
                **_workspace_fields(p),
                "onboarding": p.onboarding,
                "blocks": p.blocks,
                "onboarding_completed": p.onboarding_completed,
            }
        )
    if request.method == "PUT":
        data, err = _json_body(request)
        if err:
            return err
        p = _get_profile(request.auth_user)
        error = _update_workspace(p, data)
        if error:
            return JsonResponse({"detail": error}, status=400)
        if "name" in data:
            p.name = str(data.get("name") or "")[:120]
        if "industry" in data:
            p.industry = str(data.get("industry") or "")[:80]
        if "currency" in data:
            p.currency = str(data.get("currency") or "USD")[:8]
        if "onboarding" in data:
            p.onboarding = data.get("onboarding")
        p.save()
        return JsonResponse(
            {
                "name": p.name,
                "industry": p.industry,
                "currency": p.currency,
                **_workspace_fields(p),
                "onboarding": p.onboarding,
                "blocks": p.blocks,
                "onboarding_completed": p.onboarding_completed,
            }
        )
    return JsonResponse({"detail": "Method not allowed."}, status=405)


# --------------------------------------------------------------------------- #
# Onboarding: analyse the five answers, recommend which blocks to surface.
# The five MUST_BE blocks are always on; the AI only decides the optional
# "tasks" (Task-Dashboard) block and writes a short assessment.
MUST_BE_BLOCKS = ["employees", "products", "advisor", "roadmap", "matches", "finance", "todo", "demand", "locations"]
# Blocks added after launch. Workspaces saved before a block existed get it
# switched on once (recorded in blocks.offered), so a founder who later hides
# it keeps it hidden.
NEW_BLOCKS = ["matches", "roadmap"]


def _offer_new_blocks(p):
    blocks = p.blocks
    if not p.onboarding_completed or not isinstance(blocks, dict) or not isinstance(blocks.get("enabled"), list):
        return
    offered = blocks.get("offered") or []
    missing = [k for k in NEW_BLOCKS if k not in offered]
    if not missing:
        return
    enabled = list(blocks["enabled"])
    for key in missing:
        if key not in enabled:
            anchor = enabled.index("advisor") + 1 if "advisor" in enabled else len(enabled)
            enabled.insert(anchor, key)
    p.blocks = {**blocks, "enabled": enabled, "offered": offered + missing}
    p.save(update_fields=["blocks", "updated_at"])

def _recommended_blocks(analysis_text, enable_tasks):
    enabled = list(MUST_BE_BLOCKS)
    if enable_tasks:
        enabled.insert(1, "tasks")  # sits right after employees
    return {"analysis": analysis_text, "enabled": enabled}


NO_AI = {
    "ru": "ИИ пока не подключён. Мы открыли базовый набор блоков: заполните данные бизнеса и настройте видимость блоков под свои задачи.",
    "uz": "AI hali ulanmagan. Asosiy bloklar ochildi: biznes ma’lumotlarini kiriting va kerakli bloklarni sozlang.",
    "en": "AI is not connected yet. We opened a default workspace: add your business data and choose the blocks you need.",
}
NO_ANSWER = {
    "ru": "Сейчас не получилось проверить рынок. Мы открыли базовый набор блоков; анализ можно повторить позже из рабочего пространства.",
    "uz": "Hozir bozorni tekshirib bo‘lmadi. Asosiy bloklar ochildi; tahlilni keyinroq ish maydonidan qayta boshlash mumkin.",
    "en": "We couldn't check the market just now. A default workspace is open; you can run the analysis again later from the workspace.",
}


@csrf_exempt
@require_auth
@check_ai_quota
def onboarding(request):
    """
    The founder intake: nine questions, then a market check (startup.research)
    with Google Search: demand in the founder's country and city, who already
    serves it, the gap, risks and next steps, with the pages it drew on.
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    data, err = _json_body(request)
    if err:
        return err

    raw = data.get("answers") or {}
    problem = research.validate(raw)
    if problem:
        return JsonResponse({"detail": problem}, status=400)
    answers = research.clean(raw)
    language = data.get("language", "en")
    if language not in ("en", "ru", "uz"):
        language = "en"

    p = _get_profile(request.auth_user)
    p.onboarding = answers
    p.name = answers["name"][:120]

    findings, selection, enable_tasks, result = research.analyse(answers, language)
    quota = consume_and_log(request.auth_user, gemini.FEATURE_ONBOARDING_PARSE, result) if result else None

    if findings:
        p.blocks = _recommended_blocks(findings["summary"], enable_tasks)
        p.blocks["research"] = findings
        p.blocks["source"] = "ai"
    else:
        p.blocks = _recommended_blocks((NO_AI if result and result.is_stub else NO_ANSWER)[language], True)
        p.blocks["source"] = "default"
    if selection:
        p.blocks["enabled"] = list(dict.fromkeys(selection + ["advisor", "roadmap", "finance"]))
    p.blocks["offered"] = list(NEW_BLOCKS)
    p.onboarding_completed = True
    p.save()

    return JsonResponse(
        {
            "blocks": p.blocks,
            "is_stub": bool(result and result.is_stub),
            "quota": quota_dict(quota) if quota else None,
        }
    )


# --------------------------------------------------------------------------- #
@csrf_exempt
@require_auth
def cashflow(request):
    user = request.auth_user
    if request.method == "GET":
        period = _parse_period(request)
        if request.GET.get('period') and not period:
            return JsonResponse({'detail':'Use a valid month (YYYY-MM).'},status=400)
        qs = CashFlowEntry.objects.filter(user=user)
        if period:
            qs = qs.filter(occurred_on__year=period[0], occurred_on__month=period[1])
        etype = request.GET.get("type")
        if etype in (CashFlowEntry.Type.REVENUE, CashFlowEntry.Type.SPENDING):
            qs = qs.filter(entry_type=etype)
        return JsonResponse(
            {"entries": [_entry_dict(e) for e in qs], "totals": _totals(user, period)}
        )

    if request.method == "POST":
        data, err = _json_body(request)
        if err:
            return err
        etype = data.get("entry_type")
        if etype not in (CashFlowEntry.Type.REVENUE, CashFlowEntry.Type.SPENDING):
            return JsonResponse({"detail": "entry_type must be 'revenue' or 'spending'."}, status=400)
        amount = _decimal(data.get("amount"))
        if amount is None:
            return JsonResponse({"detail": "amount must be a non-negative number."}, status=400)

        occurred_on = data.get("occurred_on")
        try:
            occurred_on = date.fromisoformat(occurred_on) if occurred_on else timezone.localdate()
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Use a valid date (YYYY-MM-DD)."}, status=400)
        if data.get('cost_type', 'variable') not in ('fixed', 'variable'):
            return JsonResponse({"detail": "Invalid cost type."}, status=400)
        entry = CashFlowEntry.objects.create(
            user=user,
            entry_type=etype,
            category=str(data.get("category") or "General")[:80],
            amount=amount,
            description=str(data.get("description") or "")[:200],
            cost_type=data.get('cost_type', 'variable'),
            occurred_on=occurred_on or timezone.localdate(),
        )
        return JsonResponse({"entry": _entry_dict(entry), "totals": _totals(user)}, status=201)

    return JsonResponse({"detail": "Method not allowed."}, status=405)


@csrf_exempt
@require_auth
def cashflow_detail(request, entry_id):
    if request.method != "DELETE":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    entry = get_object_or_404(CashFlowEntry, pk=entry_id, user=request.auth_user)
    entry.delete()
    return JsonResponse({"deleted": True, "totals": _totals(request.auth_user)})


# --------------------------------------------------------------------------- #
# Employees
def _employee_dict(request, e):
    return {
        "id": str(e.id),
        "full_name": e.full_name,
        "position": e.position,
        "role": e.role,
        "team": e.team,
        "salary": _money(e.salary),
        "photo_url": _file_url(request, e.photo),
    }


def _employees_payload(request, user):
    qs = Employee.objects.filter(user=user)
    total = qs.aggregate(total=models.Sum("salary"))["total"] or ZERO
    return {
        "employees": [_employee_dict(request, e) for e in qs],
        "total_salary": _money(total),
    }


@csrf_exempt
@require_auth
def employees(request):
    user = request.auth_user
    if request.method == "GET":
        return JsonResponse(_employees_payload(request, user))

    if request.method == "POST":
        data, err = _json_body(request)
        if err:
            return err
        name = str(data.get("full_name") or "").strip()[:120]
        if not name:
            return JsonResponse({"detail": "full_name is required."}, status=400)
        salary = _decimal(data.get("salary")) if data.get("salary") not in (None, "") else ZERO
        if salary is None:
            return JsonResponse({"detail": "salary must be a non-negative number."}, status=400)
        emp = Employee.objects.create(
            user=user,
            full_name=name,
            position=str(data.get("position") or "").strip()[:80],
            role=str(data.get("role") or "")[:2000],
            team=str(data.get("team") or "").strip()[:80],
            salary=salary,
        )
        return JsonResponse(
            {"employee": _employee_dict(request, emp), **_employees_payload(request, user)}, status=201
        )

    return JsonResponse({"detail": "Method not allowed."}, status=405)


IMPORT_MAX_ROWS = 1000


def _import_rows(request):
    """Validate the {rows: [...]} envelope shared by the bulk import endpoints."""
    if request.method != "POST":
        return None, JsonResponse({"detail": "Method not allowed."}, status=405)
    data, err = _json_body(request)
    if err:
        return None, err
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        return None, JsonResponse({"detail": "The file has no rows to import."}, status=400)
    if len(rows) > IMPORT_MAX_ROWS:
        return None, JsonResponse({"detail": f"Import up to {IMPORT_MAX_ROWS} rows at a time."}, status=400)
    if any(not isinstance(row, dict) for row in rows):
        return None, JsonResponse({"detail": "Every row must be an object."}, status=400)
    return rows, None


def _import_errors(errors):
    # Row numbers are 1-based data rows, matching what the founder sees in a spreadsheet under the header.
    return JsonResponse({"detail": "Nothing was imported. Fix these rows and try again.", "errors": errors[:50]}, status=400)


@csrf_exempt
@require_auth
def employees_import(request):
    """All-or-nothing: one bad row rejects the file, so a retry never duplicates people."""
    rows, err = _import_rows(request)
    if err:
        return err
    user = request.auth_user
    staged, errors = [], []
    for n, row in enumerate(rows, start=1):
        name = str(row.get("full_name") or "").strip()[:120]
        raw_salary = row.get("salary")
        salary = ZERO if raw_salary in (None, "") else _decimal(raw_salary)
        if not name:
            errors.append({"row": n, "detail": "full_name is required."})
        elif salary is None:
            errors.append({"row": n, "detail": "salary must be a non-negative number."})
        else:
            staged.append(Employee(
                user=user, full_name=name, salary=salary,
                position=str(row.get("position") or "").strip()[:80],
                role=str(row.get("role") or "")[:2000],
                team=str(row.get("team") or "").strip()[:80],
            ))
    if errors:
        return _import_errors(errors)
    with transaction.atomic():
        Employee.objects.bulk_create(staged)
    return JsonResponse({"imported": len(staged), **_employees_payload(request, user)}, status=201)


@csrf_exempt
@require_auth
def employee_detail(request, employee_id):
    user = request.auth_user
    emp = get_object_or_404(Employee, pk=employee_id, user=user)

    if request.method == "PUT":
        data, err = _json_body(request)
        if err:
            return err
        if "full_name" in data:
            name = str(data.get("full_name") or "").strip()[:120]
            if not name:
                return JsonResponse({"detail": "full_name cannot be empty."}, status=400)
            emp.full_name = name
        if "position" in data:
            emp.position = str(data.get("position") or "").strip()[:80]
        if "role" in data:
            emp.role = str(data.get("role") or "")[:2000]
        if "team" in data:
            emp.team = str(data.get("team") or "").strip()[:80]
        if "salary" in data:
            salary = _decimal(data.get("salary"))
            if salary is None:
                return JsonResponse({"detail": "salary must be a non-negative number."}, status=400)
            emp.salary = salary
        emp.save()
        return JsonResponse({"employee": _employee_dict(request, emp), **_employees_payload(request, user)})

    if request.method == "DELETE":
        emp.delete()
        return JsonResponse({"deleted": True, **_employees_payload(request, user)})

    return JsonResponse({"detail": "Method not allowed."}, status=405)


@csrf_exempt
@require_auth
def employee_photo(request, employee_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    emp = get_object_or_404(Employee, pk=employee_id, user=request.auth_user)

    upload = request.FILES.get("photo")
    if not upload:
        return JsonResponse({"detail": "No file uploaded."}, status=400)
    if upload.size > settings.AVATAR_MAX_BYTES:
        limit = settings.AVATAR_MAX_BYTES // (1024 * 1024)
        return JsonResponse({"detail": f"Image must be under {limit}MB."}, status=400)

    ext = _sniff_image(upload.read(16))
    upload.seek(0)
    if not ext:
        return JsonResponse({"detail": "Upload a PNG, JPEG, GIF or WebP image."}, status=400)

    old_name = emp.photo.name if emp.photo else None
    emp.photo.save(f"photo.{ext}", upload, save=False)
    emp.save(update_fields=["photo"])
    if old_name and old_name != emp.photo.name:
        emp.photo.storage.delete(old_name)
    return JsonResponse({"employee": _employee_dict(request, emp)})


# --------------------------------------------------------------------------- #
# Products
def _product_dict(request, p):
    return {
        "id": str(p.id),
        "name": p.name,
        "kind": p.kind,
        "price": _money(p.price),
        "image_url": _file_url(request, p.image),
    }


@csrf_exempt
@require_auth
def products(request):
    user = request.auth_user
    if request.method == "GET":
        qs = Product.objects.filter(user=user)
        return JsonResponse({"products": [_product_dict(request, p) for p in qs]})

    if request.method == "POST":
        data, err = _json_body(request)
        if err:
            return err
        name = str(data.get("name") or "").strip()[:120]
        if not name:
            return JsonResponse({"detail": "name is required."}, status=400)
        price = _decimal(data.get("price")) if data.get("price") not in (None, "") else ZERO
        if price is None:
            return JsonResponse({"detail": "price must be a non-negative number."}, status=400)
        kind = data.get('kind', 'product')
        if kind not in ('product', 'service', 'subscription'):
            return JsonResponse({"detail": "Invalid product kind."}, status=400)
        prod = Product.objects.create(user=user, name=name, price=price, kind=kind)
        return JsonResponse({"product": _product_dict(request, prod)}, status=201)

    return JsonResponse({"detail": "Method not allowed."}, status=405)


@csrf_exempt
@require_auth
def products_import(request):
    rows, err = _import_rows(request)
    if err:
        return err
    user = request.auth_user
    staged, errors = [], []
    for n, row in enumerate(rows, start=1):
        name = str(row.get("name") or "").strip()[:120]
        raw_price = row.get("price")
        price = ZERO if raw_price in (None, "") else _decimal(raw_price)
        kind = row.get("kind") or "product"
        if not name:
            errors.append({"row": n, "detail": "name is required."})
        elif price is None:
            errors.append({"row": n, "detail": "price must be a non-negative number."})
        elif kind not in ("product", "service", "subscription"):
            errors.append({"row": n, "detail": "kind must be product, service or subscription."})
        else:
            staged.append(Product(user=user, name=name, price=price, kind=kind))
    if errors:
        return _import_errors(errors)
    with transaction.atomic():
        Product.objects.bulk_create(staged)
    qs = Product.objects.filter(user=user)
    return JsonResponse({"imported": len(staged), "products": [_product_dict(request, p) for p in qs]}, status=201)


@csrf_exempt
@require_auth
def product_detail(request, product_id):
    user = request.auth_user
    prod = get_object_or_404(Product, pk=product_id, user=user)

    if request.method == "PUT":
        data, err = _json_body(request)
        if err:
            return err
        if 'kind' in data:
            if data['kind'] not in ('product', 'service', 'subscription'):
                return JsonResponse({"detail": "Invalid product kind."}, status=400)
            prod.kind = data['kind']
        if "name" in data:
            name = str(data.get("name") or "").strip()[:120]
            if not name:
                return JsonResponse({"detail": "name cannot be empty."}, status=400)
            prod.name = name
        if "price" in data:
            price = _decimal(data.get("price"))
            if price is None:
                return JsonResponse({"detail": "price must be a non-negative number."}, status=400)
            prod.price = price
        prod.save()
        return JsonResponse({"product": _product_dict(request, prod)})

    if request.method == "DELETE":
        prod.delete()
        return JsonResponse({"deleted": True})

    return JsonResponse({"detail": "Method not allowed."}, status=405)


@csrf_exempt
@require_auth
def product_image(request, product_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    prod = get_object_or_404(Product, pk=product_id, user=request.auth_user)

    upload = request.FILES.get("image")
    if not upload:
        return JsonResponse({"detail": "No file uploaded."}, status=400)
    if upload.size > settings.AVATAR_MAX_BYTES:
        limit = settings.AVATAR_MAX_BYTES // (1024 * 1024)
        return JsonResponse({"detail": f"Image must be under {limit}MB."}, status=400)

    ext = _sniff_image(upload.read(16))
    upload.seek(0)
    if not ext:
        return JsonResponse({"detail": "Upload a PNG, JPEG, GIF or WebP image."}, status=400)

    old_name = prod.image.name if prod.image else None
    prod.image.save(f"image.{ext}", upload, save=False)
    prod.save(update_fields=["image"])
    if old_name and old_name != prod.image.name:
        prod.image.storage.delete(old_name)
    return JsonResponse({"product": _product_dict(request, prod)})


# --------------------------------------------------------------------------- #
# Assignments (Task-Dashboard block)
def _date_iso(value):
    # Freshly-created instances keep the raw string until reloaded, so accept
    # both a date object and an already-ISO string.
    if not value:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _assignment_dict(a):
    return {
        "id": str(a.id),
        "employee": str(a.employee_id),
        "employee_name": a.employee.full_name,
        "title": a.title,
        "start_date": _date_iso(a.start_date),
        "end_date": _date_iso(a.end_date),
        "done": a.done,
    }


def _assignment_dates(data, previous=None):
    dates=[]
    for field in ('start_date','end_date'):
        raw=data.get(field,getattr(previous,field,None))
        if raw and not isinstance(raw,date):
            try:
                raw=date.fromisoformat(raw)
            except (ValueError,TypeError):
                return None, 'Use valid dates (YYYY-MM-DD).'
        dates.append(raw or None)
    if all(dates) and dates[1]<dates[0]:
        return None,'End date must be on or after start date.'
    return dates,None


@csrf_exempt
@require_auth
def assignments(request):
    user = request.auth_user
    if request.method == "GET":
        qs = Assignment.objects.filter(employee__user=user).select_related("employee")
        return JsonResponse({"assignments": [_assignment_dict(a) for a in qs]})

    if request.method == "POST":
        data, err = _json_body(request)
        if err:
            return err
        try:
            employee_id=uuid.UUID(str(data.get('employee')))
        except ValueError:
            return JsonResponse({'detail':'Choose an employee.'},status=400)
        emp = get_object_or_404(Employee, pk=employee_id, user=user)
        title = str(data.get("title") or "").strip()[:200]
        if not title:
            return JsonResponse({"detail": "title is required."}, status=400)
        dates,date_error=_assignment_dates(data)
        if date_error:
            return JsonResponse({'detail':date_error},status=400)
        a = Assignment.objects.create(
            employee=emp,
            title=title,
            start_date=dates[0],
            end_date=dates[1],
        )
        return JsonResponse({"assignment": _assignment_dict(a)}, status=201)

    return JsonResponse({"detail": "Method not allowed."}, status=405)


@csrf_exempt
@require_auth
def assignment_detail(request, assignment_id):
    a = get_object_or_404(
        Assignment.objects.select_related("employee"),
        pk=assignment_id,
        employee__user=request.auth_user,
    )

    if request.method == "PATCH":
        data, err = _json_body(request)
        if err:
            return err
        dates,date_error=_assignment_dates(data,a)
        if date_error:
            return JsonResponse({'detail':date_error},status=400)
        if "done" in data:
            a.done = bool(data.get("done"))
        if "title" in data:
            title = str(data.get("title") or "").strip()[:200]
            if title:
                a.title = title
        if "start_date" in data:
            a.start_date = dates[0]
        if "end_date" in data:
            a.end_date = dates[1]
        a.save()
        return JsonResponse({"assignment": _assignment_dict(a)})

    if request.method == "DELETE":
        a.delete()
        return JsonResponse({"deleted": True})

    return JsonResponse({"detail": "Method not allowed."}, status=405)


# --------------------------------------------------------------------------- #
# Startup to-dos
def _todo_dict(t):
    return {"id": str(t.id), "title": t.title, "done": t.done}


@csrf_exempt
@require_auth
def todos(request):
    user = request.auth_user
    if request.method == "GET":
        qs = StartupTodo.objects.filter(user=user)
        return JsonResponse({"todos": [_todo_dict(t) for t in qs]})

    if request.method == "POST":
        data, err = _json_body(request)
        if err:
            return err
        title = str(data.get("title") or "").strip()[:200]
        if not title:
            return JsonResponse({"detail": "title is required."}, status=400)
        t = StartupTodo.objects.create(user=user, title=title)
        return JsonResponse(_todo_dict(t), status=201)

    return JsonResponse({"detail": "Method not allowed."}, status=405)


@csrf_exempt
@require_auth
def todo_detail(request, todo_id):
    t = get_object_or_404(StartupTodo, pk=todo_id, user=request.auth_user)

    if request.method == "PATCH":
        data, err = _json_body(request)
        if err:
            return err
        if "done" in data:
            t.done = bool(data.get("done"))
        if "title" in data:
            title = str(data.get("title") or "").strip()[:200]
            if title:
                t.title = title
        t.save()
        return JsonResponse(_todo_dict(t))

    if request.method == "DELETE":
        t.delete()
        return JsonResponse({"deleted": True})

    return JsonResponse({"detail": "Method not allowed."}, status=405)


# --------------------------------------------------------------------------- #
# Roadmap (startup.roadmap): the road from where the startup stands to a full
# startup. Asking the questions and building the roadmap spend AI quota;
# reading it and ticking items off do not.
def _language(data):
    return data.get("language") if data.get("language") in ("en", "ru", "uz") else "en"


def _ai_failure(result):
    if result and result.is_stub:
        return JsonResponse({"detail": "AI is not connected yet.", "code": "ai_unavailable"}, status=503)
    return JsonResponse({"detail": "The roadmap could not be built just now. Try again in a minute."}, status=502)


@csrf_exempt
@require_auth
def roadmap(request):
    p = _get_profile(request.auth_user)
    if request.method == "GET":
        # A roadmap from before milestones existed reads as none: building a new
        # one keeps its finished steps (matched by title).
        return JsonResponse({"roadmap": p.roadmap if roadmaps.is_current(p.roadmap) else None})
    if request.method == "POST":
        return _build_roadmap(request, p)
    return JsonResponse({"detail": "Method not allowed."}, status=405)


@check_ai_quota
def _build_roadmap(request, p):
    data, err = _json_body(request)
    if err:
        return err
    if not p.onboarding_completed:
        return JsonResponse({"detail": "Finish the startup questions first."}, status=400)
    answers = roadmaps.clean_answers(data["answers"]) if "answers" in data else None
    plan, result = roadmaps.build(p, _language(data), answers)
    quota = consume_and_log(request.auth_user, gemini.FEATURE_ROADMAP, result) if result and not result.is_stub else None
    if plan is None:
        return _ai_failure(result)
    p.roadmap = plan
    p.save(update_fields=["roadmap", "updated_at"])
    return JsonResponse({"roadmap": plan, "quota": quota_dict(quota) if quota else None})


@csrf_exempt
@require_auth
def roadmap_questions(request):
    """POST {language, answers?} → the questions the AI wants answered before building."""
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    return _ask_roadmap_questions(request, _get_profile(request.auth_user))


@check_ai_quota
def _ask_roadmap_questions(request, p):
    data, err = _json_body(request)
    if err:
        return err
    if not p.onboarding_completed:
        return JsonResponse({"detail": "Finish the startup questions first."}, status=400)
    answers = roadmaps.clean_answers(data["answers"]) if "answers" in data else None
    questions, result = roadmaps.ask(p, _language(data), answers)
    quota = consume_and_log(request.auth_user, gemini.FEATURE_ROADMAP, result) if result and not result.is_stub else None
    if questions is None:
        return _ai_failure(result)
    return JsonResponse({"questions": questions, "quota": quota_dict(quota) if quota else None})


@csrf_exempt
@require_auth
def roadmap_item(request, item_id):
    """PATCH {done, note?}: finish the next step or milestone, or reopen the latest one."""
    if request.method != "PATCH":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    data, err = _json_body(request)
    if err:
        return err
    if type(data.get("done")) is not bool:
        return JsonResponse({"detail": "done must be true or false."}, status=400)
    note = str(data["note"]).strip()[:1000] if isinstance(data.get("note"), str) else None
    with transaction.atomic():
        p = StartupProfile.objects.select_for_update().get(pk=_get_profile(request.auth_user).pk)
        try:
            roadmaps.set_done(p.roadmap, item_id, data["done"], note)
        except KeyError:
            return JsonResponse({"detail": "This step is no longer in the roadmap."}, status=404)
        except roadmaps.OutOfOrder as exc:
            return JsonResponse({"detail": str(exc)}, status=409)
        p.save(update_fields=["roadmap", "updated_at"])
    return JsonResponse({"roadmap": p.roadmap})
