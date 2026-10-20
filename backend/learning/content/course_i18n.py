"""
The course in Russian and Uzbek.

English lives in seed_learning.UNITS; this file carries the same words keyed by
unit code and lesson slug, and the seed writes them into Unit.i18n and
Lesson.i18n (see learning.models.Translated). Test questions are matched by id
and only their words are translated — the answers stay with the English, so a
test is graded the same in every language. Tables keep the English shape, so a
lesson reads the same in all three.
"""

# The heading over the bullet points of every lesson.
KEY_POINTS = {"en": "Key points", "ru": "Главное", "uz": "Asosiy fikrlar"}

UNITS = {
    "01": {
        "ru": {
            "title": "Основы финансов",
            "subtitle": "Язык денег: главное",
            "test_questions": [
                {"id": "u1q1", "prompt": "Чему равен чистый капитал?",
                 "choices": ["Активы + пассивы", "Активы − пассивы", "Доходы − расходы", "Выручка − затраты"],
                 "explanation": "Чистый капитал — то, чем вы владеете, минус то, что вы должны."},
                {"id": "u1q2", "prompt": "Резервный фонд обычно покрывает…",
                 "choices": ["Расходы на 1 день", "Расходы на 3–6 месяцев", "Расходы на 10 лет", "Только аренду"]},
                {"id": "u1q3", "prompt": "Сложный процент — это когда проценты начисляются на…",
                 "choices": ["Только исходную сумму", "Исходную сумму и накопленные проценты", "Налоги", "Ни на что"]},
            ],
        },
        "uz": {
            "title": "Moliya asoslari",
            "subtitle": "Pul tilining asosi",
            "test_questions": [
                {"id": "u1q1", "prompt": "Sof boylik nimaga teng?",
                 "choices": ["Aktivlar + majburiyatlar", "Aktivlar − majburiyatlar", "Daromad − xarajat", "Tushum − xarajatlar"],
                 "explanation": "Sof boylik — egalik qilayotgan narsangiz minus qarzingiz."},
                {"id": "u1q2", "prompt": "Favqulodda jamg‘arma odatda nimani qoplaydi?",
                 "choices": ["1 kunlik xarajatni", "3–6 oylik xarajatni", "10 yillik xarajatni", "Faqat ijarani"]},
                {"id": "u1q3", "prompt": "Murakkab foizda foiz nimaga hisoblanadi?",
                 "choices": ["Faqat asosiy summaga", "Asosiy summa va yig‘ilgan foizlarga", "Soliqlarga", "Hech narsaga"]},
            ],
        },
    },
    "02": {
        "ru": {
            "title": "Основы инвестиций",
            "subtitle": "Пусть деньги работают",
            "test_questions": [
                {"id": "u2q1", "prompt": "Диверсификация прежде всего снижает…",
                 "choices": ["Доходность", "Риск", "Налоги", "Комиссии"]},
                {"id": "u2q2", "prompt": "Акция — это…",
                 "choices": ["Заём компании", "Доля владения в компании", "Государственная облигация", "Наличные"]},
                {"id": "u2q3", "prompt": "Индексные фонды популярны, потому что они…",
                 "choices": ["Активно торгуются", "Дешёвые и диверсифицированные", "Гарантированные", "Без налогов"]},
            ],
        },
        "uz": {
            "title": "Investitsiya asoslari",
            "subtitle": "Pulingiz siz uchun ishlasin",
            "test_questions": [
                {"id": "u2q1", "prompt": "Diversifikatsiya birinchi navbatda nimani kamaytiradi?",
                 "choices": ["Daromadni", "Riskni", "Soliqlarni", "Komissiyalarni"]},
                {"id": "u2q2", "prompt": "Aksiya — bu…",
                 "choices": ["Kompaniyaga berilgan qarz", "Kompaniyadagi egalik ulushi", "Davlat obligatsiyasi", "Naqd pul"]},
                {"id": "u2q3", "prompt": "Indeks fondlari mashhur, chunki ular…",
                 "choices": ["Faol savdo qilinadi", "Arzon va diversifikatsiyalangan", "Kafolatlangan", "Soliqsiz"]},
            ],
        },
    },
    "03": {
        "ru": {
            "title": "Финансовый анализ",
            "subtitle": "Читаем цифры",
            "test_questions": [
                {"id": "u3q1", "prompt": "Отчёт о прибылях и убытках показывает…",
                 "choices": ["Активы и пассивы", "Доходы и расходы за период", "Только деньги", "Имена владельцев"]},
                {"id": "u3q2", "prompt": "Валовая маржа равна…",
                 "choices": ["(Выручка − себестоимость) ÷ выручка", "Выручка + себестоимость", "Чистая прибыль × 2", "Деньги ÷ долг"]},
                {"id": "u3q3", "prompt": "Runway показывает…",
                 "choices": ["Общую выручку", "На сколько месяцев хватит денег", "Число сотрудников", "Маржу прибыли"]},
            ],
        },
        "uz": {
            "title": "Moliyaviy tahlil",
            "subtitle": "Raqamlarni o‘qiymiz",
            "test_questions": [
                {"id": "u3q1", "prompt": "Foyda va zararlar hisoboti nimani ko‘rsatadi?",
                 "choices": ["Aktivlar va majburiyatlarni", "Davr ichidagi daromad va xarajatlarni", "Faqat pulni", "Egalarning ismlarini"]},
                {"id": "u3q2", "prompt": "Yalpi marja nimaga teng?",
                 "choices": ["(Tushum − tannarx) ÷ tushum", "Tushum + tannarx", "Sof foyda × 2", "Pul ÷ qarz"]},
                {"id": "u3q3", "prompt": "Runway nimani o‘lchaydi?",
                 "choices": ["Umumiy tushumni", "Pul necha oyga yetishini", "Xodimlar sonini", "Foyda marjasini"]},
            ],
        },
    },
    "04": {
        "ru": {
            "title": "Личные финансы и капитал",
            "subtitle": "Капитал на годы вперёд",
            "test_questions": [
                {"id": "u4q1", "prompt": "«Сначала заплатить себе» — это…",
                 "choices": ["Сначала тратить, потом копить", "Откладывать до того, как тратить", "Никогда не копить", "Только оплачивать счета"]},
                {"id": "u4q2", "prompt": "Более высокий кредитный рейтинг обычно даёт…",
                 "choices": ["Более высокие ставки", "Более низкие ставки", "Никакого эффекта", "Больше долгов"]},
                {"id": "u4q3", "prompt": "Главное преимущество раннего старта в инвестициях…",
                 "choices": ["Удача", "Больше времени для сложного процента", "Гарантированный доход", "Только меньше налогов"]},
            ],
        },
        "uz": {
            "title": "Shaxsiy moliya va boylik",
            "subtitle": "Yillar davomida boylik",
            "test_questions": [
                {"id": "u4q1", "prompt": "«Avval o‘zingizga to‘lang» — bu…",
                 "choices": ["Avval sarflab, keyin jamg‘arish", "Sarflashdan oldin jamg‘arish", "Hech qachon jamg‘armaslik", "Faqat hisoblarni to‘lash"]},
                {"id": "u4q2", "prompt": "Yuqoriroq kredit reytingi odatda nimaga olib keladi?",
                 "choices": ["Yuqoriroq foiz stavkalariga", "Pastroq foiz stavkalariga", "Hech qanday ta’sir yo‘q", "Ko‘proq qarzga"]},
                {"id": "u4q3", "prompt": "Investitsiyani erta boshlashning asosiy afzalligi…",
                 "choices": ["Omad", "Murakkab foiz uchun ko‘proq vaqt", "Kafolatlangan daromad", "Faqat kamroq soliq"]},
            ],
        },
    },
}

LESSONS = {
    # ---- 01 · Finance Fundamentals ---------------------------------------
    "what-is-money": {
        "ru": {
            "title": "Что такое деньги?",
            "intro": "Деньги — инструмент, чтобы хранить ценность и обмениваться ею. Понять их роли — первый шаг к тому, чтобы уверенно с ними обращаться.",
            "bullets": ["Средство обмена", "Мера стоимости", "Средство сбережения"],
            "table": {"title": "Роли денег коротко",
                      "rows": [["Роль", "Пример"], ["Обмен", "Покупка продуктов"], ["Мера", "Цена товара"], ["Сбережение", "Сберегательный счёт"]]},
        },
        "uz": {
            "title": "Pul nima?",
            "intro": "Pul — qiymatni saqlash va almashish vositasi. Uning vazifalarini tushunish — puldan ongli foydalanishning birinchi qadami.",
            "bullets": ["Ayirboshlash vositasi", "Qiymat o‘lchovi", "Jamg‘arma vositasi"],
            "table": {"title": "Vazifalar qisqacha",
                      "rows": [["Vazifa", "Misol"], ["Ayirboshlash", "Oziq-ovqat xaridi"], ["O‘lchov", "Mahsulot narxi"], ["Jamg‘arma", "Jamg‘arma hisobi"]]},
        },
    },
    "assets-liabilities": {
        "ru": {
            "title": "Активы и пассивы",
            "intro": "Активы приносят деньги в карман, пассивы — забирают. Чистый капитал — разница между ними.",
            "bullets": ["Активы: наличные, инвестиции, недвижимость", "Пассивы: кредиты, долг по карте", "Чистый капитал = активы − пассивы"],
            "table": {"title": "Пример баланса",
                      "rows": [["Активы", "Пассивы"], ["Наличные $2 000", "Карта $500"], ["Инвестиции $3 000", "Кредит $1 500"]]},
        },
        "uz": {
            "title": "Aktivlar va majburiyatlar",
            "intro": "Aktivlar cho‘ntagingizga pul keltiradi, majburiyatlar esa olib ketadi. Sof boylik — ularning farqi.",
            "bullets": ["Aktivlar: naqd pul, investitsiyalar, mulk", "Majburiyatlar: kreditlar, karta qarzi", "Sof boylik = aktivlar − majburiyatlar"],
            "table": {"title": "Balans misoli",
                      "rows": [["Aktivlar", "Majburiyatlar"], ["Naqd pul $2 000", "Karta $500"], ["Investitsiyalar $3 000", "Kredit $1 500"]]},
        },
    },
    "budgeting-basics": {
        "ru": {
            "title": "Основы бюджета",
            "intro": "Бюджет — это план для каждого доллара. Правило 50/30/20 — простая схема для старта.",
            "bullets": ["50% — необходимое", "30% — желания", "20% — сбережения и погашение долгов"],
            "table": {"title": "50 / 30 / 20 при доходе $3 000",
                      "rows": [["Необходимое", "Желания", "Сбережения"], ["$1 500", "$900", "$600"]]},
        },
        "uz": {
            "title": "Byudjet asoslari",
            "intro": "Byudjet — har bir dollar uchun reja. 50/30/20 qoidasi — boshlash uchun oddiy tizim.",
            "bullets": ["50% — zarur xarajatlar", "30% — xohishlar", "20% — jamg‘arma va qarzni to‘lash"],
            "table": {"title": "$3 000 daromadda 50 / 30 / 20",
                      "rows": [["Zarur", "Xohishlar", "Jamg‘arma"], ["$1 500", "$900", "$600"]]},
        },
    },
    # ---- 02 · Investing Basics -------------------------------------------
    "stocks-and-bonds": {
        "ru": {
            "title": "Акции и облигации",
            "intro": "Акция — это доля в компании, облигация — заём. Вместе они составляют основу большинства портфелей.",
            "bullets": ["Акции: выше риск и потенциальная доходность", "Облигации: ниже риск, стабильнее доход", "Пропорция зависит от ваших целей"],
            "table": {"title": "Риск и доходность",
                      "rows": [["Актив", "Профиль"], ["Акции", "Рост"], ["Облигации", "Стабильность"]]},
        },
        "uz": {
            "title": "Aksiyalar va obligatsiyalar",
            "intro": "Aksiya — kompaniyadagi ulush, obligatsiya — qarz. Birgalikda ular ko‘pchilik portfellarning asosini tashkil qiladi.",
            "bullets": ["Aksiyalar: yuqori risk va yuqori daromad imkoniyati", "Obligatsiyalar: past risk, barqarorroq daromad", "Nisbat maqsadlaringizga bog‘liq"],
            "table": {"title": "Risk va daromad",
                      "rows": [["Aktiv", "Tavsif"], ["Aksiyalar", "O‘sish"], ["Obligatsiyalar", "Barqarorlik"]]},
        },
    },
    "diversification": {
        "ru": {
            "title": "Диверсификация",
            "intro": "Не кладите все яйца в одну корзину. Распределение вложений снижает общий риск.",
            "bullets": ["По классам активов", "По отраслям", "По странам и регионам"],
        },
        "uz": {
            "title": "Diversifikatsiya",
            "intro": "Barcha tuxumni bitta savatga solmang. Investitsiyalarni taqsimlash umumiy riskni kamaytiradi.",
            "bullets": ["Aktiv turlari bo‘yicha", "Tarmoqlar bo‘yicha", "Mamlakat va mintaqalar bo‘yicha"],
        },
    },
    "index-funds": {
        "ru": {
            "title": "Индексные фонды и ETF",
            "intro": "Индексные фонды повторяют рынок и берут низкие комиссии — любимый инструмент долгосрочных инвесторов.",
            "bullets": ["Широкая диверсификация сразу", "Низкие комиссии со временем экономят много", "Пассивный подход без суеты"],
        },
        "uz": {
            "title": "Indeks fondlari va ETF",
            "intro": "Indeks fondlari bozorni takrorlaydi va xarajatlarni past ushlaydi — uzoq muddatli investorlarning sevimli vositasi.",
            "bullets": ["Darhol keng diversifikatsiya", "Past komissiyalar vaqt o‘tib ko‘p tejaydi", "Passiv, ortiqcha tashvishsiz yondashuv"],
        },
    },
    "risk-and-return": {
        "ru": {
            "title": "Риск и доходность",
            "intro": "Более высокая ожидаемая доходность приходит вместе с сильными колебаниями. Цель — не избегать риска, а брать только тот риск, за который платят.",
            "bullets": ["Волатильность — цена более высокой доходности", "За риск, который убирается диверсификацией, не доплачивают", "Подбирайте риск под свой горизонт"],
            "table": {"title": "Долгосрочные средние (США)",
                      "rows": [["Актив", "Доходность", "Волатильность"], ["Наличные", "~3% в год", "Очень низкая"],
                               ["Облигации", "~5% в год", "Низкая"], ["Акции", "~10% в год", "Высокая"]]},
        },
        "uz": {
            "title": "Risk va daromad",
            "intro": "Yuqoriroq kutilgan daromad yo‘lda kuchliroq tebranishlar bilan keladi. Maqsad — riskdan qochish emas, balki faqat haq to‘lanadigan riskni olish.",
            "bullets": ["Tebranish — yuqori daromadning bahosi", "Diversifikatsiya bilan yo‘qotsa bo‘ladigan risk uchun qo‘shimcha haq to‘lanmaydi", "Riskni investitsiya muddatiga moslang"],
            "table": {"title": "Uzoq muddatli o‘rtacha ko‘rsatkichlar (AQSh)",
                      "rows": [["Aktiv", "Daromad", "Tebranish"], ["Naqd pul", "~3% yiliga", "Juda past"],
                               ["Obligatsiyalar", "~5% yiliga", "Past"], ["Aksiyalar", "~10% yiliga", "Yuqori"]]},
        },
    },
    "power-of-compounding": {
        "ru": {
            "title": "Сила сложного процента",
            "intro": "Сложный процент — это когда доход начинает приносить доход. С годами он даёт больше, чем вы вложили сами.",
            "bullets": ["Чем дольше вы вложены, тем быстрее рост", "Правило 72: 72 ÷ ставка ≈ лет до удвоения", "Реинвестируйте дивиденды и проценты автоматически"],
        },
        "uz": {
            "title": "Murakkab foiz kuchi",
            "intro": "Murakkab foiz — daromadingiz ham daromad keltira boshlaganda. Yillar o‘tib u siz qo‘ygan puldan ham ko‘proq hissa qo‘shadi.",
            "bullets": ["Qancha uzoq investitsiya qilsangiz, o‘sish shuncha tezlashadi", "72 qoidasi: 72 ÷ stavka ≈ ikki barobar bo‘lish yillari", "Dividend va foizlarni avtomatik qayta investitsiya qiling"],
        },
    },
    # ---- 03 · Financial Analysis -----------------------------------------
    "the-three-statements": {
        "ru": {
            "title": "Три финансовых отчёта",
            "intro": "Отчёт о прибылях и убытках, баланс и отчёт о движении денег вместе рассказывают историю компании.",
            "bullets": ["Прибыли и убытки: прибыльность", "Баланс: финансовое положение", "Движение денег: ликвидность"],
            "table": {"title": "На что отвечает каждый",
                      "rows": [["Отчёт", "Вопрос"], ["Прибыли и убытки", "Мы прибыльны?"],
                               ["Баланс", "Чем владеем и сколько должны?"], ["Движение денег", "Хватает ли денег?"]]},
        },
        "uz": {
            "title": "Uchta moliyaviy hisobot",
            "intro": "Foyda va zararlar hisoboti, balans va pul oqimi hisoboti birgalikda kompaniya tarixini aytib beradi.",
            "bullets": ["Foyda va zararlar: rentabellik", "Balans: moliyaviy holat", "Pul oqimi: likvidlik"],
            "table": {"title": "Har biri nimaga javob beradi",
                      "rows": [["Hisobot", "Savol"], ["Foyda va zararlar", "Biz foydadamizmi?"],
                               ["Balans", "Nimaga egamiz va qancha qarzmiz?"], ["Pul oqimi", "Pul yetarlimi?"]]},
        },
    },
    "key-ratios": {
        "ru": {
            "title": "Ключевые коэффициенты",
            "intro": "Коэффициенты превращают сухие цифры в понимание. Несколько главных быстро показывают здоровье бизнеса.",
            "bullets": ["Валовая маржа", "Коэффициент текущей ликвидности", "Долг к собственному капиталу"],
        },
        "uz": {
            "title": "Asosiy koeffitsiyentlar",
            "intro": "Koeffitsiyentlar quruq raqamlarni tushunchaga aylantiradi. Bir nechta asosiylari biznes holatini tez ko‘rsatadi.",
            "bullets": ["Yalpi marja", "Joriy likvidlik koeffitsiyenti", "Qarzning o‘z kapitalga nisbati"],
        },
    },
    "runway-and-burn": {
        "ru": {
            "title": "Скорость трат и запас денег",
            "intro": "Burn — с какой скоростью вы тратите деньги; runway — на сколько месяцев их хватит.",
            "bullets": ["Burn = чистый отток денег за месяц", "Runway = деньги на счёте ÷ burn", "Продлить runway: сократить траты или поднять выручку"],
            "table": {"title": "Пример",
                      "rows": [["Показатель", "Значение"], ["Деньги", "$60 000"], ["Burn в месяц", "$10 000"], ["Runway", "6 месяцев"]]},
        },
        "uz": {
            "title": "Sarf tezligi va pul zaxirasi",
            "intro": "Burn — pulni qanchalik tez sarflashingiz; runway — pul necha oyga yetishi.",
            "bullets": ["Burn = oylik sof pul chiqimi", "Runway = hisobdagi pul ÷ burn", "Runway’ni uzaytirish: sarfni qisqartiring yoki tushumni oshiring"],
            "table": {"title": "Misol",
                      "rows": [["Ko‘rsatkich", "Qiymat"], ["Pul", "$60 000"], ["Oylik burn", "$10 000"], ["Runway", "6 oy"]]},
        },
    },
    "unit-economics": {
        "ru": {
            "title": "Юнит-экономика",
            "intro": "Юнит-экономика смотрит на одного клиента или один товар и отвечает: рост создаёт ценность или просто быстрее сжигает деньги?",
            "bullets": ["Маржинальный доход = цена − переменные затраты", "CAC — сколько стоит привлечь одного клиента", "Цель — LTV:CAC 3:1 или лучше"],
            "table": {"title": "Пример на одного клиента",
                      "rows": [["Показатель", "Значение"], ["Цена в месяц", "$50"], ["Переменные затраты в месяц", "$15"],
                               ["CAC", "$210"], ["Окупаемость", "6 месяцев"]]},
        },
        "uz": {
            "title": "Unit-iqtisodiyot",
            "intro": "Unit-iqtisodiyot bitta mijoz yoki bitta mahsulotga qaraydi va javob beradi: o‘sish qiymat yaratyaptimi yoki shunchaki pulni tezroq yoqyaptimi?",
            "bullets": ["Marjinal daromad = narx − o‘zgaruvchan xarajat", "CAC — bitta mijozni jalb qilish narxi", "Maqsad — LTV:CAC 3:1 yoki undan yaxshi"],
            "table": {"title": "Bitta mijoz misolida",
                      "rows": [["Ko‘rsatkich", "Qiymat"], ["Oylik narx", "$50"], ["Oylik o‘zgaruvchan xarajat", "$15"],
                               ["CAC", "$210"], ["Qoplanish muddati", "6 oy"]]},
        },
    },
    # ---- 04 · Personal Finance & Wealth ----------------------------------
    "pay-yourself-first": {
        "ru": {
            "title": "Сначала заплатите себе",
            "intro": "Откладывайте автоматически — до того, как начнёте тратить. Чего не видите, того не хватитесь.",
            "bullets": ["Настройте автоперевод в день зарплаты", "Относитесь к сбережениям как к обязательному платежу", "Постепенно повышайте процент"],
        },
        "uz": {
            "title": "Avval o‘zingizga to‘lang",
            "intro": "Sarflashdan oldin jamg‘armani avtomatlashtiring. Ko‘rmagan pulingizni qidirmaysiz.",
            "bullets": ["Maosh kuni avtomatik o‘tkazmani sozlang", "Jamg‘armaga majburiy to‘lov kabi qarang", "Ulushni asta-sekin oshiring"],
        },
    },
    "credit-and-debt": {
        "ru": {
            "title": "Кредиты и долги",
            "intro": "Хорошая кредитная история делает займы дешевле. Управляйте долгами осознанно.",
            "bullets": ["Платите вовремя — всегда", "Держите загрузку кредитного лимита низкой", "Сначала гасите долги с высокой ставкой"],
        },
        "uz": {
            "title": "Kredit va qarzlar",
            "intro": "Yaxshi kredit tarixi qarz olishni arzonlashtiradi. Qarzlarni ongli boshqaring.",
            "bullets": ["Har doim o‘z vaqtida to‘lang", "Kredit limitidan foydalanishni past ushlang", "Avval yuqori foizli qarzlarni yoping"],
        },
    },
    "long-term-wealth": {
        "ru": {
            "title": "Капитал на долгий срок",
            "intro": "Время на рынке важнее попыток угадать момент. Начинайте рано и будьте последовательны.",
            "bullets": ["Инвестируйте регулярно", "Реинвестируйте доход", "Дайте сложному проценту работать десятилетиями"],
            "table": {"title": "$200 в месяц под 7%",
                      "rows": [["Лет", "Примерно"], ["10", "$34 000"], ["20", "$104 000"], ["30", "$243 000"]]},
        },
        "uz": {
            "title": "Uzoq muddatli boylik",
            "intro": "Bozorda bo‘lgan vaqt to‘g‘ri paytni topishdan muhimroq. Erta boshlang va izchil bo‘ling.",
            "bullets": ["Muntazam investitsiya qiling", "Daromadni qayta investitsiya qiling", "Murakkab foizga o‘n yillab ishlash imkonini bering"],
            "table": {"title": "Oyiga $200, yillik 7%",
                      "rows": [["Yil", "Taxminan"], ["10", "$34 000"], ["20", "$104 000"], ["30", "$243 000"]]},
        },
    },
    "emergency-fund": {
        "ru": {
            "title": "Резервный фонд",
            "intro": "Резервный фонд — деньги, отложенные на непредвиденное. Он не даёт неожиданному счёту превратиться в дорогой долг.",
            "bullets": ["Цель — 3–6 месяцев обязательных расходов", "Держите его доступным: вклад, а не акции", "Восстановите его, прежде чем вернуться к другим целям"],
        },
        "uz": {
            "title": "Favqulodda jamg‘arma",
            "intro": "Favqulodda jamg‘arma — kutilmagan holatlar uchun ajratilgan pul. U kutilmagan hisobni qimmat qarzga aylantirmaydi.",
            "bullets": ["Maqsad — 3–6 oylik zarur xarajatlar", "Oson olinadigan joyda saqlang: omonat, aksiya emas", "Boshqa maqsadlarga qaytishdan oldin uni to‘ldiring"],
        },
    },
    "debt-payoff-strategies": {
        "ru": {
            "title": "Как гасить долги",
            "intro": "Два проверенных метода: «лавина» экономит на процентах, «снежный ком» даёт мотивацию. Лучший — тот, который вы доведёте до конца.",
            "bullets": ["Лавина: сначала самая высокая ставка", "Снежный ком: сначала самый маленький долг", "Всегда вносите все минимальные платежи"],
            "table": {"title": "Лавина или снежный ком",
                      "rows": [["Метод", "Порядок", "Выигрыш"], ["Лавина", "Высшая ставка", "Меньше процентов"],
                               ["Снежный ком", "Меньший долг", "Мотивация"]]},
        },
        "uz": {
            "title": "Qarzni yopish usullari",
            "intro": "Ikki sinalgan usul: «ko‘chki» foizlarni tejaydi, «qor to‘pi» motivatsiya beradi. Eng yaxshisi — oxirigacha yetkazadiganingiz.",
            "bullets": ["Ko‘chki: avval eng yuqori foiz", "Qor to‘pi: avval eng kichik qarz", "Barcha minimal to‘lovlarni doim qiling"],
            "table": {"title": "Ko‘chki yoki qor to‘pi",
                      "rows": [["Usul", "Tartib", "Yutuq"], ["Ko‘chki", "Eng yuqori foiz", "Kamroq foiz"],
                               ["Qor to‘pi", "Eng kichik qarz", "Motivatsiya"]]},
        },
    },
    "retirement-accounts": {
        "ru": {
            "title": "Пенсионные счета",
            "intro": "Счета с налоговыми льготами дают вложениям расти без ежегодного налогового тормоза. Счёт — это обёртка, а инвестиции лежат внутри.",
            "bullets": ["401(k): взносы до налогов, налог — при снятии", "Roth IRA: налог сейчас, снятие без налога", "Сначала заберите полный взнос работодателя"],
        },
        "uz": {
            "title": "Pensiya hisoblari",
            "intro": "Soliq imtiyozli hisoblar investitsiyalarga har yilgi soliq tormozisiz o‘sish imkonini beradi. Hisob — bu qobiq, investitsiyalar esa uning ichida.",
            "bullets": ["401(k): badallar soliqdan oldin, soliq — yechib olishda", "Roth IRA: soliq hozir, yechib olish soliqsiz", "Avval ish beruvchining to‘liq badalini oling"],
        },
    },
}
