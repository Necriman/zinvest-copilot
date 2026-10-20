"""
Learning endpoints (native JsonResponse — no DRF). All @require_auth.

  GET   /api/learning/stats
  PATCH /api/learning/stats/goal
  GET   /api/learning/units
  GET   /api/learning/units/<uuid>/study-plan
  GET   /api/learning/lessons/<uuid>
  POST  /api/learning/lessons/<uuid>/complete
  POST  /api/learning/units/<uuid>/test/start
  POST  /api/learning/units/<uuid>/test/submit
  GET   /api/learning/league

Write endpoints lock the UserStats row (select_for_update) so coin/streak updates
are race-safe, exactly as the refresh view locks its token row.
"""
import json

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from django.conf import settings

from accounts import security
from accounts.auth import require_auth
from ai_engine.quota import add_bonus as add_ai_bonus
from config import languages

from . import daily as daily_service
from . import practice as practice_service
from . import predict as predict_service
from . import onboarding as onboarding_service
from . import services
from .models import (
    LeagueMembership,
    Lesson,
    LessonProgress,
    OnboardingAssessment,
    StudyPlan,
    Task,
    Unit,
    UnitProgress,
    UnitTestResult,
    UserStats,
)

TEST_PASS_COINS = 50  # bonus for passing a unit test the first time


def _json_body(request):
    try:
        return json.loads(request.body or b"{}"), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"detail": "Malformed JSON body."}, status=400)


def _require_method(request, method):
    if request.method != method:
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    return None


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #
@require_GET
@require_auth
def stats(request):
    return JsonResponse(services.stats_payload(request.auth_user, timezone.localdate()))


@csrf_exempt
@require_auth
def stats_goal(request):
    err = _require_method(request, "PATCH")
    if err:
        return err
    data, jerr = _json_body(request)
    if jerr:
        return jerr

    st = services.get_or_create_stats(request.auth_user)
    fields = []
    if "financial_goal" in data:
        st.financial_goal = str(data.get("financial_goal") or "")[:120]
        fields.append("financial_goal")
    if "target_score" in data:
        try:
            st.target_score = max(0, int(data.get("target_score") or 0))
            fields.append("target_score")
        except (TypeError, ValueError):
            return JsonResponse({"detail": "target_score must be an integer."}, status=400)
    if fields:
        st.save(update_fields=fields + ["updated_at"])
    return JsonResponse(services.stats_payload(request.auth_user, timezone.localdate()))


# --------------------------------------------------------------------------- #
# Today's tasks
# --------------------------------------------------------------------------- #
@csrf_exempt
@require_auth
def tasks(request):
    """GET → today's open + just-completed tasks · POST {"title"} → create one."""
    user = request.auth_user
    today = timezone.localdate()

    if request.method == "GET":
        return JsonResponse({"tasks": services.tasks_payload(user, today)})
    err = _require_method(request, "POST")
    if err:
        return err

    data, jerr = _json_body(request)
    if jerr:
        return jerr
    title = str(data.get("title") or "").strip()[:200]
    if not title:
        return JsonResponse({"detail": "title is required."}, status=400)

    last = (
        Task.objects.filter(user=user).order_by("-order").values_list("order", flat=True).first()
    )
    task = Task.objects.create(user=user, title=title, order=(last or 0) + 1)
    return JsonResponse(services.task_payload(task), status=201)


@csrf_exempt
@require_auth
def task_detail(request, task_id):
    """PATCH → tick / rename / reorder · DELETE → remove. Scoped to the owner."""
    task = get_object_or_404(Task, pk=task_id, user=request.auth_user)

    if request.method == "DELETE":
        task.delete()
        return JsonResponse({"status": "deleted"})
    err = _require_method(request, "PATCH")
    if err:
        return err

    data, jerr = _json_body(request)
    if jerr:
        return jerr

    fields = []
    if "title" in data:
        title = str(data.get("title") or "").strip()[:200]
        if not title:
            return JsonResponse({"detail": "title cannot be empty."}, status=400)
        task.title = title
        fields.append("title")
    if "done" in data and task.set_done(data.get("done"), timezone.now()):
        fields += ["done", "completed_at"]
    if "order" in data:
        try:
            task.order = max(0, int(data.get("order")))
            fields.append("order")
        except (TypeError, ValueError):
            return JsonResponse({"detail": "order must be an integer."}, status=400)
    if fields:
        task.save(update_fields=fields)
    return JsonResponse(services.task_payload(task))


# --------------------------------------------------------------------------- #
# Units / study plan / lessons
# --------------------------------------------------------------------------- #
@require_GET
@require_auth
def units(request):
    return JsonResponse({"units": services.units_payload(request.auth_user)})


@require_GET
@require_auth
def unit_study_plan(request, unit_id):
    unit = get_object_or_404(Unit, pk=unit_id)
    return JsonResponse(services.study_plan_payload(request.auth_user, unit))


@require_GET
@require_auth
def study_plan(request):
    """The whole plan — every unit's nodes — so the map can scroll end to end."""
    return JsonResponse(services.full_study_plan_payload(request.auth_user))


@require_GET
@require_auth
def today_plan(request):
    """The dashboard deck: next study step, an AI question, a startup entry."""
    return JsonResponse(services.today_plan_payload(request.auth_user, timezone.localdate()))


@require_GET
@require_auth
def next_step(request):
    """What the dashboard's "continue" button opens: the map's current node."""
    return JsonResponse(services.next_step_payload(request.auth_user))


# --------------------------------------------------------------------------- #
# Onboarding assessment → personalised plan
# --------------------------------------------------------------------------- #
def _onboarding_state(user):
    """Current assessment/plan state. Keys must not collide with the question
    bank's `profile`/`quiz` — hence `answers` for what the user previously chose."""
    assessment = OnboardingAssessment.objects.filter(user=user).first()
    plan = StudyPlan.objects.filter(user=user).first()
    return {
        "completed": bool(assessment and assessment.completed_at),
        "level": assessment.level if assessment else "",
        "quiz_score": round(assessment.quiz_score * 100) if assessment else 0,
        "answers": (assessment.answers or {}).get("profile", {}) if assessment else {},
        "plan": {
            "source": plan.source if plan else "default",
            "rationale": plan.rationale if plan else "",
            "lesson_count": plan.items.count() if plan else 0,
            "generated_at": plan.generated_at.isoformat() if plan else None,
        },
    }


@csrf_exempt
@require_auth
def onboarding(request):
    """GET → the questionnaire (quiz answers stripped) + current state.
    POST → submit answers, grade, and build the personalised plan."""
    user = request.auth_user

    if request.method == "GET":
        return JsonResponse({**onboarding_service.public_questions(), **_onboarding_state(user)})
    err = _require_method(request, "POST")
    if err:
        return err

    data, jerr = _json_body(request)
    if jerr:
        return jerr

    profile = data.get("profile")
    if not isinstance(profile, dict):
        return JsonResponse({"detail": "profile must be an object."}, status=400)
    quiz = data.get("quiz")
    if not isinstance(quiz, list):
        return JsonResponse({"detail": "quiz must be a list."}, status=400)

    onboarding_service.submit(user, profile, quiz)
    return JsonResponse(_onboarding_state(user))


@csrf_exempt
@require_POST
@require_auth
def regenerate_study_plan(request):
    """Rebuild the plan from the stored assessment — the "update plan" action."""
    user = request.auth_user
    assessment = OnboardingAssessment.objects.filter(user=user).first()
    if not assessment or not assessment.completed_at:
        return JsonResponse(
            {"detail": "Complete the onboarding assessment first."}, status=409
        )
    if not security.hit("plan-regenerate", user.pk, 5, 3600):
        return JsonResponse({"detail": "You are doing that too often. Please wait a little.", "code": "rate_limited"}, status=429)
    onboarding_service.build_plan(user, assessment)
    return JsonResponse(_onboarding_state(user))


@require_GET
@require_auth
def lessons_catalog(request):
    """Free-browse catalogue: every lesson, grouped by unit, nothing gated."""
    return JsonResponse({"units": services.lessons_catalog_payload(request.auth_user)})


@require_GET
@require_auth
def lesson_detail(request, lesson_id):
    """Any lesson is readable. `locked` in the payload is advisory — it tells the
    study plan this lesson is off the recommended route, nothing more."""
    lesson = get_object_or_404(Lesson.objects.select_related("unit"), pk=lesson_id)
    return JsonResponse(services.lesson_payload(request.auth_user, lesson))


@csrf_exempt
@require_auth
def lesson_practice(request, lesson_id):
    """Optional unit practice during a lesson; never awards coins or unlocks units."""
    lesson=get_object_or_404(Lesson.objects.select_related('unit'),pk=lesson_id)
    questions=lesson.unit.questions()
    if request.method=='GET':
        return JsonResponse({'questions':[{'id':q['id'],'prompt':q['prompt'],'choices':q['choices']} for q in questions]})
    if request.method=='POST':
        data,err=_json_body(request)
        if err:
            return err
        if not isinstance(data,dict):
            return JsonResponse({'detail':'Expected an object.'},status=400)
        q=next((q for q in questions if q['id']==data.get('question_id')),None)
        choice=data.get('choice_index')
        if not q or type(choice) is not int or not 0<=choice<len(q['choices']):
            return JsonResponse({'detail':'Choose a valid answer.'},status=400)
        return JsonResponse({'correct':choice==q['answer_index'],'explanation':q.get('explanation',''),'answer_index':q['answer_index']})
    return JsonResponse({'detail':'Method not allowed.'},status=405)


@csrf_exempt
@require_POST
@require_auth
def lesson_save(request, lesson_id):
    """Persist the user's edited lesson HTML (document editor "Save")."""
    lesson = get_object_or_404(Lesson.objects.select_related("unit"), pk=lesson_id)
    user = request.auth_user

    data, jerr = _json_body(request)
    if jerr:
        return jerr
    content = data.get("content")
    if not isinstance(content, str):
        return JsonResponse({"detail": "content must be a string."}, status=400)

    with transaction.atomic():
        lp, _ = LessonProgress.objects.select_for_update().get_or_create(user=user, lesson=lesson)
        lp.edited_content = content
        lp.save(update_fields=["edited_content"])

    return JsonResponse({"status": "saved", "saved_at": timezone.now().isoformat()})


@csrf_exempt
@require_POST
@require_auth
def lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related("unit"), pk=lesson_id)
    user = request.auth_user

    data, _ = _json_body(request)
    data = data or {}
    today = timezone.localdate()
    now = timezone.now()

    UserStats.objects.get_or_create(user=user)
    with transaction.atomic():
        st = UserStats.objects.select_for_update().get(user=user)

        lp = LessonProgress.objects.filter(user=user, lesson=lesson).first()
        already_done = bool(lp and lp.status == LessonProgress.Status.COMPLETED)
        if lp is None:
            lp = LessonProgress(user=user, lesson=lesson)
        lp.status = LessonProgress.Status.COMPLETED
        lp.completed_at = lp.completed_at or now
        if data.get("worksheet_answers") is not None:
            lp.worksheet_answers = data.get("worksheet_answers")
        lp.save()

        awarded = 0
        if not already_done:
            awarded = lesson.coin_reward
            st.add_coins(awarded)
            services.record_activity(user, st, today)
            st.save()
            add_ai_bonus(user, settings.AI_BONUS_PER_LESSON)  # a new lesson earns AI tokens for this month

        # Mark the unit in progress (cached; test pass flips it to completed).
        up, _ = UnitProgress.objects.get_or_create(user=user, unit=lesson.unit)
        if not up.test_passed and up.status != UnitProgress.Status.COMPLETED:
            up.status = UnitProgress.Status.IN_PROGRESS
            up.save(update_fields=["status"])

    nxt = lesson.unit.lessons.filter(order__gt=lesson.order).order_by("order").first()
    return JsonResponse(
        {
            "status": "completed",
            "coins_awarded": awarded,
            "new_coin_total": st.coins,
            "day_streak": st.day_streak,
            "unlocked_next": {
                "lesson_id": str(nxt.id) if nxt else None,
                "unit_test_available": nxt is None,
            },
        }
    )


# --------------------------------------------------------------------------- #
# Unit tests
# --------------------------------------------------------------------------- #
@csrf_exempt
@require_POST
@require_auth
def test_start(request, unit_id):
    unit = get_object_or_404(Unit, pk=unit_id)
    if services._unit_locked_for(request.auth_user, unit):
        return JsonResponse({"detail": "This unit is locked."}, status=403)
    # Never leak answer_index / explanation.
    questions = [
        {"id": q.get("id"), "prompt": q.get("prompt"), "choices": q.get("choices", [])}
        for q in unit.questions()
    ]
    already_passed = UnitProgress.objects.filter(user=request.auth_user, unit=unit, test_passed=True).exists()
    return JsonResponse(
        {
            "unit_id": str(unit.id),
            "unit_title": unit.tr("title"),
            "pass_threshold": unit.test_pass_threshold,
            "coin_reward": 0 if already_passed else TEST_PASS_COINS,
            "questions": questions,
        }
    )


@csrf_exempt
@require_POST
@require_auth
def test_submit(request, unit_id):
    unit = get_object_or_404(Unit, pk=unit_id)
    user = request.auth_user
    if services._unit_locked_for(user, unit):
        return JsonResponse({"detail": "This unit is locked."}, status=403)

    data, jerr = _json_body(request)
    if jerr:
        return jerr
    submitted = data.get("answers") or []
    answer_map = {a.get("question_id"): a.get("choice_index") for a in submitted}

    # Graded in the language the test is shown in: a translated version can
    # have its own right answers (see Unit.questions).
    questions = unit.questions()
    total = len(questions)
    correct = sum(1 for q in questions if answer_map.get(q.get("id")) == q.get("answer_index"))
    score = (correct / total) if total else 0.0
    passed = score >= unit.test_pass_threshold

    today = timezone.localdate()
    now = timezone.now()
    UserStats.objects.get_or_create(user=user)
    with transaction.atomic():
        st = UserStats.objects.select_for_update().get(user=user)
        UnitTestResult.objects.create(
            user=user, unit=unit, score=score, correct_count=correct,
            total_count=total, passed=passed, answers=submitted,
        )
        up, _ = UnitProgress.objects.get_or_create(user=user, unit=unit)
        if score > up.best_test_score:
            up.best_test_score = score

        coins_awarded = 0
        if passed and not up.test_passed:
            up.test_passed = True
            up.status = UnitProgress.Status.COMPLETED
            up.completed_at = now
            coins_awarded = TEST_PASS_COINS
            st.add_coins(coins_awarded)
        up.save()
        services.record_activity(user, st, today)
        st.save()

    return JsonResponse(
        {
            "score": round(score * 100),
            "passed": passed,
            "correct_count": correct,
            "total_count": total,
            "best_score": round(up.best_test_score * 100),
            "coins_awarded": coins_awarded,
            "day_streak": st.day_streak,
            # The answers are only revealed once the test is submitted.
            "review": [
                {
                    "question_id": q.get("id"),
                    "chosen_index": answer_map.get(q.get("id")),
                    "answer_index": q.get("answer_index"),
                    "correct": answer_map.get(q.get("id")) == q.get("answer_index"),
                    "explanation": q.get("explanation", ""),
                }
                for q in questions
            ],
        }
    )


@require_GET
@require_auth
def league(request):
    """
    GET /api/learning/league — this week's group standings for the learner.

    Names only (never emails): everyone in the group sees this list.
    """
    from . import league as league_service

    start = league_service.week_start()
    seat, rows = league_service.standings(request.auth_user, start)
    me = request.auth_user

    last = (
        LeagueMembership.objects.filter(user=me, closed=True).order_by("-week_start").first()
    )
    return JsonResponse({
        "division": seat.division,
        "divisions": list(league_service.DIVISIONS),
        "week_start": start.isoformat(),
        "ends_at": league_service._as_datetime(league_service.week_end(start)).isoformat(),
        "promote": league_service.PROMOTE,
        "demote": league_service.DEMOTE if len(rows) > league_service.PROMOTE else 0,
        "prizes": list(league_service.PRIZE_COINS),
        "points": {
            "lesson": league_service.POINTS_PER_LESSON,
            "test": league_service.POINTS_PER_TEST,
            "day": league_service.POINTS_PER_ACTIVE_DAY,
        },
        "me": {
            "rank": next((r["rank"] for r in rows if r["seat"].user_id == me.pk), None),
            "points": next((r["points"] for r in rows if r["seat"].user_id == me.pk), 0),
        },
        "members": [
            {
                "id": str(r["seat"].user_id),
                "name": league_service.display_name(r["seat"].user),
                "avatar_url": r["seat"].user.avatar.url if r["seat"].user.avatar else None,
                "points": r["points"],
                "rank": r["rank"],
                "is_me": r["seat"].user_id == me.pk,
            }
            for r in rows
        ],
        "last_week": {
            "division": last.division,
            "rank": last.rank,
            "points": last.points,
            "result": last.result,
        } if last else None,
    })


# --------------------------------------------------------------------------- #
# Zinvest Daily
# --------------------------------------------------------------------------- #
def _lang(request):
    """The interface language, sent per request — the client has no account
    setting for it, it is whatever the learner picked in the switcher."""
    return languages.from_request(request, default="ru")


@require_GET
@require_auth
def daily(request):
    """Today's five, with the answers filled in for the ones already played."""
    return JsonResponse(daily_service.state(request.auth_user, _lang(request)))


@csrf_exempt
@require_POST
@require_auth
def daily_answer(request):
    """Grade the next unanswered question. The index comes from the run, not
    the client, so a replayed request cannot pay twice."""
    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"detail": "Malformed JSON."}, status=400)
    result = daily_service.answer(request.auth_user, payload.get("choice"), _lang(request))
    if result is None:
        return JsonResponse({"detail": "No question to answer."}, status=400)
    return JsonResponse(result)


# --------------------------------------------------------------------------- #
# Practice trainer
# --------------------------------------------------------------------------- #
def _body(request):
    try:
        return json.loads(request.body or b"{}"), None
    except ValueError:
        return None, JsonResponse({"detail": "Malformed JSON."}, status=400)


@require_GET
@require_auth
def practice_next(request):
    """One question from the bank (without its answer), plus the topics and today's count."""
    question = practice_service.next_question(
        request.auth_user, _lang(request), request.GET.get("topic"), request.GET.get("after")
    )
    return JsonResponse({
        "question": question,
        "topics": practice_service.topics(),
        "stats": practice_service.stats(request.auth_user),
    })


@csrf_exempt
@require_POST
@require_auth
def practice_answer(request):
    data, err = _body(request)
    if err:
        return err
    result = practice_service.answer(
        request.auth_user, data.get("id"), data.get("choice"), _lang(request), reveal=data.get("reveal") is True
    )
    if result is None:
        return JsonResponse({"detail": "No such question or option."}, status=400)
    return JsonResponse(result)


# --------------------------------------------------------------------------- #
# "Up or down?"
# --------------------------------------------------------------------------- #
@require_GET
@require_auth
def predict(request):
    return JsonResponse(predict_service.state(request.auth_user, _lang(request)))


@csrf_exempt
@require_POST
@require_auth
def predict_answer(request):
    data, err = _body(request)
    if err:
        return err
    result, error = predict_service.answer(request.auth_user, data.get("id"), data.get("choice"), _lang(request))
    if error == "played":
        return JsonResponse({"detail": "Already played.", "code": "played"}, status=409)
    if error == "limit":
        return JsonResponse({"detail": "No rounds left today.", "code": "limit"}, status=429)
    if error:
        return JsonResponse({"detail": "No such round or choice."}, status=400)
    return JsonResponse(result)
