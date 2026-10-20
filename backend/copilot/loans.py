"""
Bank loans for small businesses in Uzbekistan, and how one is matched.

The catalogue holds the terms the banks advertise on their own pages (checked
in October 2026, links below). Banks change rates often, so every match says
the terms are indicative and must be confirmed with the bank. All in UZS.

Matching is arithmetic, not AI: a product qualifies when the amount, the term
and the business's legal form fit; the monthly payment is computed at the
product's highest advertised rate (the safe side); and the ranking rewards a
lower cost and a payment the business can carry from its monthly profit.
The AI only explains the result.
"""
from decimal import Decimal

from . import finance

CHECKED = "2026-10"

# form: who can borrow — "business" (registered company or individual
# entrepreneur), "person" (an individual, including the self-employed).
CATALOG = [
    {
        "id": "hamkor-small-business",
        "bank": "Hamkorbank",
        "product": "Kichik biznesga yordam (small business support)",
        "rate": (18, 21), "max_amount": 300_000_000, "months": (6, 84),
        "forms": {"business"}, "purposes": {"working_capital", "equipment", "any"},
        "collateral": "Required (property, vehicle or guarantee)",
        "url": "https://hamkorbank.uz/business/credits-for-business/for-any-purpose/",
    },
    {
        "id": "kapital-small-business",
        "bank": "Kapitalbank",
        "product": "Small business loan",
        "rate": (24, 24), "max_amount": 300_000_000, "months": (6, 120),
        "forms": {"business"}, "purposes": {"working_capital", "equipment", "any"},
        "collateral": "Required; grace period on the principal up to 6 months; early repayment without penalties",
        "url": "https://www.kapitalbank.uz/ru/corporate/crediting/loans-for-small-business/",
    },
    {
        "id": "ipakyuli-self-employed",
        "bank": "Ipak Yuli Bank",
        "product": "Microloan for the self-employed",
        "rate": (21, 24), "max_amount": 300_000_000, "months": (6, 60),
        "forms": {"person"}, "purposes": {"working_capital", "equipment", "any"},
        "collateral": "Depends on the amount",
        "url": "https://en.ipakyulibank.uz/physical/loans",
    },
    {
        "id": "aloqa-biznesga-madad",
        "bank": "Aloqabank",
        "product": "Biznesga Madad microloan",
        "rate": (26, 26), "max_amount": 100_000_000, "months": (6, 60),
        "forms": {"person", "business"}, "purposes": {"any", "working_capital", "equipment"},
        "collateral": "Liquid property",
        "url": "https://aloqabank.uz/en/private/crediting/microloan-biznesga-madad/",
    },
    {
        "id": "nbu-microloan",
        "bank": "National Bank of Uzbekistan (NBU)",
        "product": "Microloan",
        "rate": (24, 28), "max_amount": 100_000_000, "months": (6, 60),
        "forms": {"person"}, "purposes": {"any", "working_capital"},
        "collateral": "For borrowers with official income",
        "url": "https://nbu.uz/en/for-individuals-loans/microloan",
    },
    {
        "id": "mkbank-mahalla-business",
        "bank": "Mikrokreditbank (MKBank)",
        "product": "Mahalla-Business microloan",
        "rate": (25, 29), "max_amount": 30_000_000, "months": (6, 48),
        "forms": {"person"}, "purposes": {"any", "working_capital", "equipment"},
        "collateral": "For the self-employed in their mahalla; up to 17 mln UZS for 24 months, up to 30 mln for 48",
        "url": "https://mkbank.uz/en/private/crediting/mahalla-business-microloan-product/",
    },
]

FORMS = ("business", "person")
PURPOSES = ("working_capital", "equipment", "any")


def match(amount, months, form, purpose, monthly_net):
    """
    Rank the catalogue for a loan of `amount` over `months`. Returns every
    product with `eligible`, the reasons when it is not, and for eligible ones
    the payment, the total interest and whether the monthly profit covers it.
    """
    amount, monthly_net = Decimal(amount), Decimal(monthly_net or 0)
    out = []
    for p in CATALOG:
        reasons = []
        if amount > p["max_amount"]:
            reasons.append("amount_too_high")
        if not p["months"][0] <= months <= p["months"][1]:
            reasons.append("term_out_of_range")
        if form not in p["forms"]:
            reasons.append("wrong_borrower")
        if purpose not in p["purposes"] and "any" not in p["purposes"]:
            reasons.append("wrong_purpose")
        payment = finance.annuity(amount, p["rate"][1], months)
        share = float(payment / monthly_net * 100) if monthly_net > 0 else None
        out.append({
            "id": p["id"],
            "bank": p["bank"],
            "product": p["product"],
            "rate_min": p["rate"][0],
            "rate_max": p["rate"][1],
            "max_amount": finance.money(p["max_amount"]),
            "months_range": list(p["months"]),
            "collateral": p["collateral"],
            "url": p["url"],
            "eligible": not reasons,
            "reasons": reasons,
            "payment": finance.money(payment),
            "total_interest": finance.money(payment * months - amount),
            "payment_share": round(share, 1) if share is not None else None,
            "affordable": share is not None and share <= 50,
        })
    # Eligible first; then the ones the profit can carry; then the cheapest.
    out.sort(key=lambda o: (not o["eligible"], not o["affordable"], Decimal(o["total_interest"])))
    return out
