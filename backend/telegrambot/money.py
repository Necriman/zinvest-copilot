"""
Reading money out of a typed message, without asking the model.

Three ways a person writes an entry, all of them accepted:

    -50000 мука          a sign says which way the money went — saved at once
    доход 300 тысяч      a word says it instead ("потратил", "выручка", …)
    50000 мука           neither: the chat asks "расход или доход?"

Everything else — a question, a greeting, a sentence with a number in it — has
to come back as None, or the bear would book "у меня 3 сотрудника" as 3 sum.
The guards for that are in `read`: a question mark, more words than a short
note needs, or a number too small to be money without a word backing it up.
"""
import re
from decimal import Decimal, InvalidOperation

# A single letter only counts as "thousand" when it stands alone, or "5 кг"
# would be read as five thousand.
SCALE_WORDS = {"к": 1000, "k": 1000, "тыс": 1000, "млн": 1_000_000, "mln": 1_000_000, "kk": 1_000_000}
SCALE_PREFIXES = (("тыс", 1000), ("ming", 1000), ("thousand", 1000), ("миллион", 1_000_000), ("million", 1_000_000))

# Matched as prefixes against each word, so "потратил", "потратила" and
# "потратили" all land. Written without "ё" — the text is normalised first.
INCOME_WORDS = ("доход", "выручк", "прибыл", "заработ", "получил", "продал", "продаж", "поступлен",
                "приход", "income", "revenue", "earn", "sold", "sale", "daromad", "tushum", "sotdim")
SPENDING_WORDS = ("расход", "трат", "потрат", "купил", "куплен", "заплат", "оплат", "закуп", "счет",
                  "spent", "paid", "bought", "expense", "cost", "xarajat", "sotib", "to'lad", "toladim")
# Left over once the direction word is gone: "потратил на муку" → "мука".
FILLER = ("на", "за", "для", "от", "по", "в", "и", "с", "the", "on", "for", "of", "to", "uchun", "ga")

SIGN = re.compile(r"^\s*([+\-−])\s*")
NUMBER = re.compile(r"\d[\d\s .,]*")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

MAX_WORDS_WITHOUT_A_WORD_FOR_IT = 4
MIN_BARE_AMOUNT = Decimal("100")


def _normalise(text):
    return text.lower().replace("ё", "е")


def _amount_of(raw):
    """"50 000,50" → Decimal("50000.50"). None when it is not a number."""
    body = re.sub(r"[\s ]", "", raw).strip(".,")
    if not body:
        return None
    # A trailing ",50" or ".5" is a fraction; every other dot and comma is a
    # thousands separator, the way "1.000.000" is written.
    fraction = re.search(r"[.,](\d{1,2})$", body)
    if fraction:
        body = re.sub(r"[.,]", "", body[: fraction.start()]) + "." + fraction.group(1)
    else:
        body = re.sub(r"[.,]", "", body)
    try:
        return Decimal(body)
    except InvalidOperation:
        return None


def _scale_after(text, position):
    """The multiplier written right after the number, and where it ends."""
    after = text[position:]
    match = WORD.match(text, position + len(after) - len(after.lstrip()))
    if not match:
        return 1, position
    word = _normalise(match.group(0))
    if word in SCALE_WORDS:
        return SCALE_WORDS[word], match.end()
    for prefix, factor in SCALE_PREFIXES:
        if word.startswith(prefix):
            return factor, match.end()
    return 1, position


def _starts_with_any(word, options):
    return any(word.startswith(option) for option in options)


def _direction(words):
    """revenue / spending / None, from the words around the number."""
    income = any(_starts_with_any(word, INCOME_WORDS) for word in words)
    spending = any(_starts_with_any(word, SPENDING_WORDS) for word in words)
    if income == spending:  # neither, or a message claiming both
        return None
    return "revenue" if income else "spending"


def _label(words):
    """What is left once the direction words and the filler are dropped."""
    kept = [
        word for word in words
        if not _starts_with_any(_normalise(word), INCOME_WORDS + SPENDING_WORDS)
        and _normalise(word) not in FILLER
    ]
    label = " ".join(kept).strip(" .,;:!-–—")
    return label[:80]


def read(text):
    """
    A message that books money → {"kind", "amount", "category"}, else None.

    ``kind`` is None when nothing in the message says which way the money went;
    the caller asks before writing anything down.
    """
    text = (text or "").strip()
    if not text:
        return None

    sign_match = SIGN.match(text)
    sign = (sign_match.group(1) if sign_match else "")
    rest = text[sign_match.end():] if sign_match else text

    number_match = NUMBER.search(rest)
    if not number_match:
        return None
    amount = _amount_of(number_match.group(0))
    if amount is None or amount <= 0:
        return None
    factor, scale_end = _scale_after(rest, number_match.end())
    amount *= factor

    leftover = (rest[: number_match.start()] + " " + rest[scale_end:]).strip()
    words = WORD.findall(leftover)
    kind = "revenue" if sign == "+" else "spending" if sign else _direction([_normalise(w) for w in words])

    if not sign:
        # Without a sign the message has to look like a note, not a sentence.
        if "?" in text:
            return None
        if kind is None and (len(words) > MAX_WORDS_WITHOUT_A_WORD_FOR_IT or amount < MIN_BARE_AMOUNT):
            return None
        if kind is not None and len(words) > 8:
            return None

    return {"kind": kind, "amount": float(amount), "category": _label(words)}
