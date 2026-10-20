"""
Seed the Zinvest Daily question bank (idempotent).

    python manage.py seed_daily

Each question is one situation with four options, and an explanation written in
the bear's voice: what the answer means and why, never a textbook paragraph.
The bank is deliberately short questions a learner can read on a phone while
the kettle boils. Five a day means this starter bank lasts about three days
before it starts repeating, so it is meant to keep growing.
"""
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from learning.content import bank_budgeting, bank_credit, bank_investing, bank_risk, bank_startup
from learning.models import DailyQuestion

T = DailyQuestion.Topic

# slug, topic, correct index, {lang: (question, [options], explain)}
BANK = [
    (
        "bonds-rates", T.INVESTING, 1,
        {
            "ru": ("Ставки выросли. Что происходит с ценой облигаций, купленных раньше?",
                   ["Растёт", "Падает", "Не меняется", "Зависит от эмитента"],
                   "Падает. Новые облигации теперь дают больший процент, поэтому старые, с маленьким купоном, соглашаются покупать только дешевле."),
            "en": ("Rates went up. What happens to the price of bonds bought earlier?",
                   ["It rises", "It falls", "Nothing changes", "Depends on the issuer"],
                   "It falls. New bonds pay more, so nobody wants the old low-coupon ones at the old price."),
            "uz": ("Stavkalar oshdi. Ilgari sotib olingan obligatsiya narxi nima bo‘ladi?",
                   ["Oshadi", "Tushadi", "O‘zgarmaydi", "Emitentga bog‘liq"],
                   "Tushadi. Yangi obligatsiyalar ko‘proq foiz beradi, shuning uchun eskisini faqat arzonroqqa oladilar."),
        },
    ),
    (
        "emergency-size", T.BUDGETING, 2,
        {
            "ru": ("Сколько обычно держат в подушке безопасности?",
                   ["Одну зарплату", "Годовой доход", "3–6 месяцев расходов", "Столько, сколько получится"],
                   "3–6 месяцев расходов. Считают именно расходы, а не доход: подушка нужна, чтобы прожить без поступлений, а не чтобы повторить зарплату."),
            "en": ("How big is an emergency fund usually?",
                   ["One paycheck", "A year of income", "3 to 6 months of expenses", "Whatever is left over"],
                   "3 to 6 months of expenses. It is measured in spending, not income: the fund has to cover life without a paycheck, not copy one."),
            "uz": ("Xavfsizlik yostig‘i odatda qancha bo‘ladi?",
                   ["Bir oylik maosh", "Yillik daromad", "3–6 oylik xarajat", "Qancha qolsa"],
                   "3–6 oylik xarajat. Aynan xarajat hisoblanadi: yostiq daromadsiz yashash uchun kerak, maoshni takrorlash uchun emas."),
        },
    ),
    (
        "diversify-why", T.RISK, 0,
        {
            "ru": ("Зачем распределять деньги между разными активами?",
                   ["Чтобы одна ошибка не стоила всего", "Чтобы доход был выше", "Чтобы платить меньше налогов", "Чтобы реже смотреть в приложение"],
                   "Чтобы одна ошибка не стоила всего. Диверсификация почти не повышает доходность — она снижает цену ошибки."),
            "en": ("Why spread money across different assets?",
                   ["So one mistake does not cost everything", "To earn more", "To pay less tax", "To check the app less often"],
                   "So one mistake does not cost everything. Diversification rarely raises returns, it lowers the price of being wrong."),
            "uz": ("Nega pulni turli aktivlarga bo‘lish kerak?",
                   ["Bitta xato hammasini olib ketmasligi uchun", "Daromad ko‘proq bo‘lishi uchun", "Soliq kamayishi uchun", "Ilovaga kamroq qarash uchun"],
                   "Bitta xato hammasini olib ketmasligi uchun. Diversifikatsiya daromadni emas, xato narxini kamaytiradi."),
        },
    ),
    (
        "inflation-cash", T.BUDGETING, 1,
        {
            "ru": ("Инфляция 10% в год. Деньги лежат дома наличными. Что с ними происходит?",
                   ["Ничего, сумма та же", "Покупательная способность падает", "Они растут вместе с ценами", "Зависит от валюты"],
                   "Сумма та же, а купить на неё можно меньше. Наличные не падают в цифрах — они падают в том, что на них дают."),
            "en": ("Inflation is 10% a year and your money sits at home in cash. What happens?",
                   ["Nothing, the amount is the same", "It buys less each year", "It grows with prices", "Depends on the currency"],
                   "The number stays, the shopping basket shrinks. Cash does not fall on paper, it falls in what it gets you."),
            "uz": ("Inflyatsiya yiliga 10%. Pul uyda naqd turibdi. Nima bo‘ladi?",
                   ["Hech nima, summa o‘sha", "Xarid qobiliyati tushadi", "Narx bilan birga o‘sadi", "Valyutaga bog‘liq"],
                   "Summa o‘sha, lekin unga kamroq narsa olinadi. Naqd raqamda emas, imkoniyatda tushadi."),
        },
    ),
    (
        "credit-minimum", T.CREDIT, 2,
        {
            "ru": ("Вы платите по кредитной карте только минимальный платёж. Что это значит?",
                   ["Долг закроется в срок", "Банк не берёт процент", "Долг тянется дольше и стоит дороже", "Кредитная история улучшается быстрее"],
                   "Минимальный платёж гасит в основном проценты. Основной долг почти не двигается, поэтому карта обходится дороже и дольше."),
            "en": ("You pay only the minimum on a credit card. What does that mean?",
                   ["The debt clears on time", "The bank charges no interest", "The debt lasts longer and costs more", "Your credit history improves faster"],
                   "The minimum mostly pays interest. The balance barely moves, so the card ends up costing more and staying longer."),
            "uz": ("Kredit karta bo‘yicha faqat minimal to‘lov qilyapsiz. Bu nima degani?",
                   ["Qarz o‘z vaqtida yopiladi", "Bank foiz olmaydi", "Qarz uzoqroq cho‘ziladi va qimmatroq tushadi", "Kredit tarixi tezroq yaxshilanadi"],
                   "Minimal to‘lov asosan foizni yopadi. Asosiy qarz deyarli qimirlamaydi, shuning uchun karta qimmatga tushadi."),
        },
    ),
    (
        "runway", T.STARTUP, 1,
        {
            "ru": ("На счету 60 000. Тратите 12 000 в месяц, доходов нет. Какой runway?",
                   ["3 месяца", "5 месяцев", "12 месяцев", "Нельзя посчитать"],
                   "Пять месяцев: 60 000 ÷ 12 000. Runway — это сколько вы проживёте при текущем расходе, и он сокращается каждый раз, когда растут траты."),
            "en": ("You have 60,000 in the bank, spend 12,000 a month, and earn nothing. What is the runway?",
                   ["3 months", "5 months", "12 months", "Cannot be calculated"],
                   "Five months: 60,000 ÷ 12,000. Runway is how long you last at today's burn, and it shortens every time spending grows."),
            "uz": ("Hisobda 60 000, oyiga 12 000 sarflaysiz, daromad yo‘q. Runway qancha?",
                   ["3 oy", "5 oy", "12 oy", "Hisoblab bo‘lmaydi"],
                   "Besh oy: 60 000 ÷ 12 000. Runway — hozirgi sarf bilan qancha yashashingiz, va xarajat oshgani sayin qisqaradi."),
        },
    ),
    (
        "etf-what", T.INVESTING, 0,
        {
            "ru": ("Что вы покупаете, покупая ETF на индекс?",
                   ["Долю сразу в сотнях компаний", "Одну компанию из индекса", "Обещание банка", "Валюту"],
                   "Долю сразу в сотнях компаний. Один тикер — весь набор, поэтому банкротство одной компании внутри почти не заметно."),
            "en": ("What do you buy when you buy an index ETF?",
                   ["A slice of hundreds of companies at once", "One company from the index", "A promise from a bank", "Currency"],
                   "A slice of hundreds of companies at once. One ticker holds the whole basket, so one company failing inside barely shows."),
            "uz": ("Indeks ETF sotib olganda nima olasiz?",
                   ["Bir vaqtning o‘zida yuzlab kompaniya ulushini", "Indeksdagi bitta kompaniyani", "Bank va'dasini", "Valyutani"],
                   "Bir vaqtda yuzlab kompaniya ulushini. Bitta ticker butun savatni tutadi, shuning uchun bittasining yiqilishi sezilmaydi."),
        },
    ),
    (
        "compound-time", T.INVESTING, 2,
        {
            "ru": ("Что сильнее всего влияет на сложный процент?",
                   ["Размер первого взноса", "Выбор брокера", "Время", "Новости рынка"],
                   "Время. Десять лет по чуть-чуть обгоняют один крупный взнос, сделанный поздно: проценты успевают начислиться на проценты."),
            "en": ("What matters most for compound interest?",
                   ["The size of the first deposit", "Which broker you pick", "Time", "Market news"],
                   "Time. Ten years of small amounts beats one large deposit made late, because interest gets long enough to earn interest."),
            "uz": ("Murakkab foizga eng ko‘p nima ta'sir qiladi?",
                   ["Birinchi to‘lov hajmi", "Broker tanlovi", "Vaqt", "Bozor yangiliklari"],
                   "Vaqt. O‘n yil ozdan qo‘yish kech qilingan katta to‘lovdan ustun: foiz foizga ulgurib qo‘shiladi."),
        },
    ),
    (
        "fixed-variable", T.STARTUP, 1,
        {
            "ru": ("Аренда помещения для пекарни — это какие расходы?",
                   ["Переменные", "Постоянные", "Разовые", "Зависит от выручки"],
                   "Постоянные: платите одинаково и в удачный месяц, и в пустой. Именно поэтому постоянные расходы опаснее переменных."),
            "en": ("Rent for a bakery is which kind of cost?",
                   ["Variable", "Fixed", "One-off", "Depends on revenue"],
                   "Fixed: you pay the same in a good month and an empty one. That is exactly why fixed costs bite harder than variable ones."),
            "uz": ("Nonvoyxona uchun ijara — qanday xarajat?",
                   ["O‘zgaruvchan", "Doimiy", "Bir martalik", "Tushumga bog‘liq"],
                   "Doimiy: yaxshi oyda ham, bo‘sh oyda ham bir xil to‘laysiz. Shuning uchun doimiy xarajat xavfliroq."),
        },
    ),
    (
        "risk-return", T.RISK, 3,
        {
            "ru": ("Вам обещают 30% в месяц без риска. Что это?",
                   ["Удачная находка", "Нормальная доходность для акций", "Государственная программа", "Повод уйти"],
                   "Повод уйти. Доходность без риска не бывает: если риск не назван, его несёте вы, просто пока об этом не знаете."),
            "en": ("Someone promises 30% a month with no risk. What is it?",
                   ["A lucky find", "A normal return for stocks", "A government scheme", "A reason to walk away"],
                   "A reason to walk away. Return without risk does not exist: if nobody names the risk, you are carrying it unknowingly."),
            "uz": ("Sizga xavfsiz oyiga 30% va'da qilishyapti. Bu nima?",
                   ["Omadli topilma", "Aksiyalar uchun oddiy daromad", "Davlat dasturi", "Ketish uchun sabab"],
                   "Ketish uchun sabab. Xavfsiz daromad bo‘lmaydi: xavf aytilmasa, uni siz ko‘tarasiz, shunchaki bilmaysiz."),
        },
    ),
    (
        "budget-order", T.BUDGETING, 0,
        {
            "ru": ("Зарплата пришла. Что разумно сделать первым?",
                   ["Отложить заранее решённую сумму", "Закрыть все желания, остальное отложить", "Подождать конца месяца", "Купить то, что давно хотели"],
                   "Отложить сначала. Если откладывать то, что осталось, не остаётся почти никогда — это и называют «заплати сначала себе»."),
            "en": ("Your salary lands. What is the sensible first move?",
                   ["Set aside the amount you decided in advance", "Spend first, save what is left", "Wait until the end of the month", "Buy the thing you have wanted"],
                   "Set it aside first. Saving what is left almost never leaves anything, which is why the rule is to pay yourself first."),
            "uz": ("Maosh tushdi. Birinchi navbatda nima qilgan ma'qul?",
                   ["Oldindan belgilangan summani ajratish", "Avval sarflab, qolganini yig‘ish", "Oy oxirini kutish", "Ko‘pdan beri xohlagan narsani olish"],
                   "Avval ajratish. Qolganini yig‘sangiz, deyarli hech narsa qolmaydi — shuning uchun «avval o‘zingga to‘la» deyishadi."),
        },
    ),
    (
        "unit-economics", T.STARTUP, 1,
        {
            "ru": ("Кофе продаёте за 20 000, себестоимость 14 000. Сколько приносит одна чашка?",
                   ["20 000", "6 000", "14 000", "Зависит от количества"],
                   "6 000 — это маржа с чашки. Из неё потом платится аренда и зарплаты, поэтому «прибыль с продажи» и «прибыль бизнеса» — разные вещи."),
            "en": ("You sell coffee for 20,000 and it costs 14,000 to make. What does one cup bring?",
                   ["20,000", "6,000", "14,000", "Depends on volume"],
                   "6,000, the margin per cup. Rent and wages come out of that, which is why profit per sale and profit of the business are different numbers."),
            "uz": ("Qahvani 20 000 ga sotasiz, tannarxi 14 000. Bitta finjon qancha keltiradi?",
                   ["20 000", "6 000", "14 000", "Miqdorga bog‘liq"],
                   "6 000 — finjondan marja. Ijara va maosh shundan to‘lanadi, shuning uchun sotuv foydasi va biznes foydasi boshqa narsa."),
        },
    ),
    (
        "loan-term", T.CREDIT, 1,
        {
            "ru": ("Тот же кредит, но срок вдвое длиннее. Что меняется?",
                   ["Платёж и переплата падают", "Платёж падает, переплата растёт", "Ничего не меняется", "Банк снижает ставку"],
                   "Платёж в месяц легче, а отдадите в сумме больше: проценты капают дольше. Длинный срок покупает комфорт за деньги."),
            "en": ("Same loan, twice the term. What changes?",
                   ["Both the payment and the total drop", "The payment drops, the total rises", "Nothing changes", "The bank lowers the rate"],
                   "The monthly payment gets lighter and the total gets heavier: interest runs for longer. A long term buys comfort with money."),
            "uz": ("Xuddi shu kredit, lekin muddati ikki barobar uzun. Nima o‘zgaradi?",
                   ["To‘lov ham, umumiy summa ham kamayadi", "To‘lov kamayadi, umumiy summa oshadi", "Hech nima", "Bank stavkani tushiradi"],
                   "Oylik to‘lov yengillashadi, umumiy summa og‘irlashadi: foiz uzoqroq ishlaydi. Uzun muddat qulaylikni pulga sotib oladi."),
        },
    ),
    (
        "market-drop", T.RISK, 2,
        {
            "ru": ("Рынок упал на 20%, деньги нужны через 15 лет. Разумный шаг?",
                   ["Продать всё", "Переложиться в одну «надёжную» акцию", "Продолжать по плану", "Удвоить вложения в кредит"],
                   "Продолжать по плану. Падение — это цена доходности, а не сигнал. Опасно не падение, а продажа на дне и кредит."),
            "en": ("The market drops 20% and you need the money in 15 years. Sensible move?",
                   ["Sell everything", "Move it all into one safe stock", "Carry on with the plan", "Double down with borrowed money"],
                   "Carry on with the plan. A drop is the price of the return, not a signal. What hurts is selling at the bottom, and borrowing."),
            "uz": ("Bozor 20% tushdi, pul 15 yildan keyin kerak. To‘g‘ri qadam?",
                   ["Hammasini sotish", "Bitta «ishonchli» aksiyaga o‘tish", "Rejani davom ettirish", "Kredit olib ikki barobar qo‘yish"],
                   "Rejani davom ettirish. Tushish — daromad narxi, signal emas. Zarar tubida sotish va kreditdan keladi."),
        },
    ),
    (
        "cashflow-vs-profit", T.STARTUP, 0,
        {
            "ru": ("Прибыль есть, а денег на счету нет. Как так?",
                   ["Клиенты ещё не заплатили", "Прибыль считается неправильно", "Так не бывает", "Банк удержал деньги"],
                   "Обычно так: продажа записана, а деньги придут позже. Прибыль — про сделки, поток — про то, что реально лежит на счету."),
            "en": ("There is profit but no money in the account. How?",
                   ["Customers have not paid yet", "The profit is miscalculated", "That cannot happen", "The bank is holding it"],
                   "Usually this: the sale is booked, the money arrives later. Profit is about deals, cash flow is about what is actually in the account."),
            "uz": ("Foyda bor, lekin hisobda pul yo‘q. Qanday?",
                   ["Mijozlar hali to‘lamagan", "Foyda noto‘g‘ri hisoblangan", "Bunday bo‘lmaydi", "Bank ushlab qolgan"],
                   "Odatda shunday: savdo yozilgan, pul keyin keladi. Foyda — bitimlar haqida, oqim — hisobdagi real pul haqida."),
        },
    ),
]


class Command(BaseCommand):
    help = "Seed the Zinvest Daily question bank."

    @transaction.atomic
    def handle(self, *args, **options):
        made = updated = 0
        # The starter bank keeps its authored order (Daily runs already
        # played store the chosen index); the content banks are shuffled.
        entries = [(slug, topic, answer, body) for slug, topic, answer, body in BANK]
        entries += [(slug, topic, *_shuffled(slug, answer, body)) for slug, topic, answer, body in CONTENT]
        slugs = [slug for slug, *_ in entries]
        if len(slugs) != len(set(slugs)):
            raise CommandError("duplicate slugs in the question bank")
        for slug, topic, answer, body in entries:
            _check(slug, answer, body)
            payload = {
                lang: {"question": q, "options": list(opts), "explain": ex}
                for lang, (q, opts, ex) in body.items()
            }
            _, created = DailyQuestion.objects.update_or_create(
                slug=slug,
                defaults={"topic": topic, "answer": answer, "body": payload, "active": True},
            )
            made += created
            updated += not created
        total = DailyQuestion.objects.filter(active=True).count()
        self.stdout.write(self.style.SUCCESS(f"daily bank: +{made} new, {updated} refreshed, {total} active"))


# Everything written in learning/content: 100 questions across the five topics.
CONTENT = [
    *bank_budgeting.BANK,
    *bank_investing.BANK,
    *bank_risk.BANK,
    *bank_credit.BANK,
    *bank_startup.BANK,
]

# Telegram quiz polls refuse longer ones; the site has no limit, the bot does.
MAX_QUESTION, MAX_OPTION = 300, 100


def _shuffled(slug, answer, body):
    """
    Mix the options so the right one is not always the second.

    One permutation per question, the same in every language and fixed by the
    slug, so a reseed never moves an answer under someone mid-question.
    """
    count = len(next(iter(body.values()))[1])
    order = list(range(count))
    random.Random(slug).shuffle(order)
    mixed = {lang: (q, [opts[i] for i in order], ex) for lang, (q, opts, ex) in body.items()}
    return order.index(answer), mixed


def _check(slug, answer, body):
    counts = {len(opts) for _q, opts, _ex in body.values()}
    if len(counts) != 1 or not 0 <= answer < counts.pop():
        raise CommandError(f"{slug}: options do not line up across languages")
    for lang, (q, opts, _ex) in body.items():
        if len(q) > MAX_QUESTION or any(len(o) > MAX_OPTION for o in opts):
            raise CommandError(f"{slug} [{lang}]: too long for a Telegram quiz")
