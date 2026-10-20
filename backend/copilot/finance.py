"""
The arithmetic behind the Copilot. Numbers are computed here, never by the
model: the AI explains and advises on top of figures it cannot get wrong.

- `summary`: monthly income and expenses from the business's cash-flow
  records (the last three months that have any), split into fixed and
  variable costs, with the biggest categories.
- `runway`: how many months the cash lasts at the current monthly loss.
- `annuity` / `projection`: loan payments and a 12-month forecast.
"""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from startup.models import CashFlowEntry

ZERO = Decimal("0")
MONTHS_USED = 3


def money(value):
    return str(Decimal(value or 0).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def grouped(value):
    """45000000 → '45 000 000', for text people read."""
    return f"{int(Decimal(value or 0).quantize(Decimal('1'), rounding=ROUND_HALF_UP)):,}".replace(",", " ")


def add_months(day, n):
    month = day.month - 1 + n
    return date(day.year + month // 12, month % 12 + 1, 1)


def summary(user):
    """Average monthly figures over the latest months with records."""
    entries = CashFlowEntry.objects.filter(user=user)
    by_month = (
        entries.annotate(month=TruncMonth("occurred_on"))
        .values("month", "entry_type", "cost_type")
        .annotate(total=Sum("amount"))
    )
    months = {}
    for row in by_month:
        m = months.setdefault(row["month"], {"revenue": ZERO, "fixed": ZERO, "variable": ZERO})
        if row["entry_type"] == CashFlowEntry.Type.REVENUE:
            m["revenue"] += row["total"]
        else:
            m["fixed" if row["cost_type"] == "fixed" else "variable"] += row["total"]
    recent = sorted(months)[-MONTHS_USED:]
    n = len(recent) or 1
    revenue = sum((months[m]["revenue"] for m in recent), ZERO) / n
    fixed = sum((months[m]["fixed"] for m in recent), ZERO) / n
    variable = sum((months[m]["variable"] for m in recent), ZERO) / n
    expenses = fixed + variable

    since = recent[0] if recent else None
    categories = (
        entries.filter(occurred_on__gte=since) if since else entries.none()
    ).values("entry_type", "category").annotate(total=Sum("amount")).order_by("-total")
    top = {"revenue": [], "spending": []}
    for row in categories:
        bucket = top["revenue" if row["entry_type"] == CashFlowEntry.Type.REVENUE else "spending"]
        if len(bucket) < 6:
            bucket.append({"category": row["category"], "monthly": money(row["total"] / n)})

    net = revenue - expenses
    return {
        "months": [m.strftime("%Y-%m") for m in recent],
        "revenue": money(revenue),
        "expenses": money(expenses),
        "fixed": money(fixed),
        "variable": money(variable),
        "net": money(net),
        "margin": round(float(net / revenue * 100), 1) if revenue else None,
        "top": top,
        "has_data": bool(recent),
    }


def runway(cash, summary_):
    """
    Months until the cash runs out at the current monthly loss. A business
    that makes money each month has no end date; it gets status "ok".
    """
    cash = Decimal(cash or 0)
    burn = Decimal(summary_["expenses"]) - Decimal(summary_["revenue"])
    today = timezone.localdate()
    if burn <= 0:
        return {"cash": money(cash), "burn": money(burn), "months": None, "runs_out": None, "status": "ok"}
    months = cash / burn
    whole = int(months)
    status = "critical" if months < 3 else "warning" if months < 6 else "ok"
    return {
        "cash": money(cash),
        "burn": money(burn),
        "months": round(float(months), 1),
        "runs_out": add_months(today, whole).strftime("%Y-%m") if cash > 0 else today.strftime("%Y-%m"),
        "status": status,
    }


def annuity(principal, annual_rate, months):
    """Equal monthly payment for a loan."""
    principal, months = Decimal(principal), int(months)
    if months <= 0:
        return ZERO
    r = Decimal(str(annual_rate)) / 100 / 12
    if r == 0:
        return principal / months
    factor = (1 + r) ** months
    return principal * r * factor / (factor - 1)


def projection(summary_, growth=0.0, cost_growth=0.0, months=12, loan=None):
    """
    A month-by-month forecast from today's averages: revenue grows by `growth`
    a month, variable costs by `cost_growth`, fixed costs stay; a loan adds its
    cash in month one and its payment every month after.
    """
    revenue = Decimal(summary_["revenue"])
    fixed = Decimal(summary_["fixed"])
    variable = Decimal(summary_["variable"])
    payment = Decimal(loan["payment"]) if loan else ZERO
    start = add_months(timezone.localdate(), 1)
    rows, cumulative = [], ZERO
    g, cg = Decimal(str(growth)) / 100, Decimal(str(cost_growth)) / 100
    for i in range(months):
        rev = revenue * (1 + g) ** i
        var = variable * (1 + cg) ** i
        out = fixed + var + payment
        inflow = Decimal(loan["amount"]) if loan and i == 0 else ZERO
        profit = rev - out
        cumulative += profit + inflow
        rows.append({
            "month": add_months(start, i).strftime("%Y-%m"),
            "revenue": money(rev),
            "expenses": money(out),
            "profit": money(profit),
            "cumulative": money(cumulative),
        })
    return rows
