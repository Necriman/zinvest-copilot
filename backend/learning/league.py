"""
The weekly league: a small group of learners racing on points they earned this
week, with the top few moving up a division and the bottom few moving down.

Points are *derived* from what actually happened (lessons finished, unit tests
passed, days shown up), not from a counter someone could top up. Coins granted
by support therefore never buy a place on the board, and there is no weekly
"reset job" that could leave the numbers wrong if it failed to run.

A group is capped at GROUP_SIZE so the board always looks winnable: being 7th
of 25 is motivating, 7000th of a million is not.
"""
import uuid
from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone

from .models import DailyActivity, LessonProgress, UnitTestResult, UserStats

DIVISIONS = ("bronze", "silver", "gold", "platinum", "diamond")
GROUP_SIZE = 25
PROMOTE = 5   # top five move up
DEMOTE = 5    # bottom five move down (never out of bronze)

POINTS_PER_LESSON = 10
POINTS_PER_TEST = 40
POINTS_PER_ACTIVE_DAY = 5

# What the winners of a group get when the week closes.
PRIZE_COINS = (60, 40, 25)


def week_start(day=None):
    """Monday of the given day, in the server's local calendar."""
    day = day or timezone.localdate()
    return day - timedelta(days=day.weekday())


def week_end(start):
    return start + timedelta(days=7)


def _as_datetime(day):
    return timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))


def points_for(user_ids, start):
    """{user_id: points} earned between Monday and now (or the week's end)."""
    begin, end = _as_datetime(start), _as_datetime(week_end(start))
    totals = {uid: 0 for uid in user_ids}

    lessons = (
        LessonProgress.objects.filter(
            user_id__in=user_ids, status=LessonProgress.Status.COMPLETED,
            completed_at__gte=begin, completed_at__lt=end,
        )
        .values("user_id").annotate(n=models.Count("pk"))
    )
    for row in lessons:
        totals[row["user_id"]] += row["n"] * POINTS_PER_LESSON

    tests = (
        UnitTestResult.objects.filter(user_id__in=user_ids, passed=True, created_at__gte=begin, created_at__lt=end)
        .values("user_id", "unit_id").distinct()
    )
    for row in tests:  # one reward per unit, not per retake
        totals[row["user_id"]] += POINTS_PER_TEST

    days = (
        DailyActivity.objects.filter(user_id__in=user_ids, date__gte=start, date__lt=week_end(start))
        .values("user_id").annotate(n=models.Count("pk"))
    )
    for row in days:
        totals[row["user_id"]] += row["n"] * POINTS_PER_ACTIVE_DAY

    return totals


def snapshot(user, start=None):
    """
    The learner's league at a glance, for the dashboard — read-only.

    ``join`` hands out a seat on first look, which is right for the league
    page and wrong everywhere else: calling it from the dashboard would seat
    every learner who merely opened the app, and fill groups with people who
    never chose to compete. So this only reads. Without a seat this week it
    reports the division the learner would join, and no rank.
    """
    from .models import LeagueMembership

    start = start or week_start()
    seat = LeagueMembership.objects.filter(user=user, week_start=start).first()
    if seat is None:
        last = (
            LeagueMembership.objects.filter(user=user, closed=True)
            .order_by("-week_start").first()
        )
        division = next_division(last.division, last.result) if last else DIVISIONS[0]
        return {"division": division, "rank": None, "points": 0, "seated": False}

    seats = list(
        LeagueMembership.objects.filter(week_start=start, group_id=seat.group_id).order_by("created_at")
    )
    scores = points_for([s.user_id for s in seats], start)
    ordered = sorted(seats, key=lambda s: (-scores.get(s.user_id, 0), s.created_at))
    rank = next(i for i, s in enumerate(ordered, 1) if s.user_id == user.pk)
    return {"division": seat.division, "rank": rank, "points": scores.get(user.pk, 0), "seated": True}


def next_division(division, result):
    index = DIVISIONS.index(division) if division in DIVISIONS else 0
    if result == "promoted":
        return DIVISIONS[min(index + 1, len(DIVISIONS) - 1)]
    if result == "demoted":
        return DIVISIONS[max(index - 1, 0)]
    return DIVISIONS[index]


@transaction.atomic
def join(user, start=None):
    """
    This week's seat for one learner, created on first look.

    The division follows last week's result; the group is whichever one in that
    division still has room. Seats are handed out under a row lock so two tabs
    opening the page at once cannot land in two different groups.
    """
    from .models import LeagueMembership

    start = start or week_start()
    seat = LeagueMembership.objects.filter(user=user, week_start=start).first()
    if seat is not None:
        return seat

    last = (
        LeagueMembership.objects.filter(user=user, closed=True)
        .order_by("-week_start").first()
    )
    division = next_division(last.division, last.result) if last else DIVISIONS[0]

    # An open group in this division, or a fresh one.
    open_group = (
        LeagueMembership.objects.filter(week_start=start, division=division)
        .values("group_id").annotate(n=models.Count("pk")).filter(n__lt=GROUP_SIZE)
        .order_by("-n").first()  # fill a group before starting another
    )
    group_id = open_group["group_id"] if open_group else uuid.uuid4()
    return LeagueMembership.objects.create(user=user, week_start=start, division=division, group_id=group_id)


def standings(user, start=None):
    """The board as the learner sees it: their group, sorted, with their seat."""
    from .models import LeagueMembership

    start = start or week_start()
    seat = join(user, start)
    seats = list(
        LeagueMembership.objects.filter(week_start=start, group_id=seat.group_id)
        .select_related("user").order_by("created_at")
    )
    scores = points_for([s.user_id for s in seats], start)
    rows = sorted(
        ({"seat": s, "points": scores.get(s.user_id, 0)} for s in seats),
        key=lambda r: (-r["points"], r["seat"].created_at),
    )
    for place, row in enumerate(rows, 1):
        row["rank"] = place
    return seat, rows


def display_name(user):
    """A name for the board. Never an email — this list is public to the group."""
    return user.full_name or f"#{str(user.pk)[-4:]}"


@transaction.atomic
def close_week(start):
    """
    Settle one finished week: freeze the points, rank each group, mark who goes
    up and down, and pay the podium. Safe to run twice — closed seats are left
    alone, so a retry after a failed cron does not pay twice.
    """
    from .models import LeagueMembership

    seats = list(LeagueMembership.objects.filter(week_start=start, closed=False).select_for_update())
    if not seats:
        return {"groups": 0, "learners": 0}
    scores = points_for([s.user_id for s in seats], start)

    groups = {}
    for seat in seats:
        groups.setdefault(seat.group_id, []).append(seat)

    paid = 0
    for group in groups.values():
        ordered = sorted(group, key=lambda s: (-scores.get(s.user_id, 0), s.created_at))
        for place, seat in enumerate(ordered, 1):
            seat.points = scores.get(seat.user_id, 0)
            seat.rank = place
            # No points, no movement: an empty week should not push anyone down
            # a division just for being away.
            if seat.points == 0:
                seat.result = "stayed" if seat.division == DIVISIONS[0] else "demoted"
            elif place <= PROMOTE:
                seat.result = "promoted"
            elif place > len(ordered) - DEMOTE and len(ordered) > PROMOTE:
                seat.result = "demoted"
            else:
                seat.result = "stayed"
            seat.closed = True
            seat.save(update_fields=["points", "rank", "result", "closed"])
            if place <= len(PRIZE_COINS) and seat.points:
                stats, _ = UserStats.objects.select_for_update().get_or_create(user_id=seat.user_id)
                stats.add_coins(PRIZE_COINS[place - 1])
                stats.save(update_fields=["coins", "weekly_xp", "updated_at"])
                paid += 1

    return {"groups": len(groups), "learners": len(seats), "prizes": paid}
