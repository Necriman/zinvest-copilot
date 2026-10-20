"""
Everything the bot says, in the three languages the app speaks.

Two things worth knowing before editing:

* The nudges are a *pool* per situation, not one line — the same sentence every
  evening is what turns a reminder into an alarm clock. handlers.py never picks
  the line it used last time.
* Messages are written as small cards: a title line, a blank line, then the
  numbers. In a chat that reads far better than a paragraph, and the inline
  buttons under each card carry the actions.
"""
import random

LANGS = ("ru", "en", "uz")

ANSWER_TITLE = {"ru": "Ответ Zinvest", "en": "Zinvest answers", "uz": "Zinvest javobi"}

AI_ERROR = {
    "ru": "💬 <b>Не удалось получить ответ</b>\n\nСервис ИИ сейчас недоступен. Попробуйте ещё раз чуть позже.\nУчёт денег и меню продолжают работать.",
    "en": "💬 <b>Couldn’t get an answer</b>\n\nThe AI service is unavailable. Please try again shortly.\nMoney entries and the menu still work.",
    "uz": "💬 <b>Javobni olib bo‘lmadi</b>\n\nAI xizmati hozir mavjud emas. Birozdan keyin qayta urinib ko‘ring.\nPul hisobi va menyu ishlashda davom etadi.",
}

WELCOME_BACK = {
    "ru": "👋 <b>Zinvest · Главное меню</b>\n\nПришлите чек, голосовое или выберите раздел.\nВсе возможности — /help",
    "en": "👋 <b>Zinvest · Main menu</b>\n\nSend a receipt, voice note or choose a section.\nExplore all features — /help",
    "uz": "👋 <b>Zinvest · Asosiy menyu</b>\n\nChek, ovozli xabar yuboring yoki bo‘limni tanlang.\nBarcha imkoniyatlar — /help",
}

SETTINGS_OFF = {
    "ru": "⚙️ <b>Напоминания</b>\n\n🔕 Выключены\n\nВключите ежедневные напоминания или итоги недели.",
    "en": "⚙️ <b>Reminders</b>\n\n🔕 Off\n\nEnable daily reminders or a weekly recap.",
    "uz": "⚙️ <b>Eslatmalar</b>\n\n🔕 O‘chirilgan\n\nKundalik eslatmalar yoki hafta yakunini yoqing.",
}


def pick(table, lang):
    return table.get(lang) or table["ru"]


# --------------------------------------------------------------------------- #
# Meeting the bot
HELLO = {'ru': '👋 <b>Zinvest</b>\n'
       'Деньги вашего дела — под рукой.\n'
       '\n'
       'Чеки, голосовые и быстрые записи.\n'
       'Уроки и ответы на вопросы о бизнесе.',
 'en': '👋 <b>Zinvest</b>\n'
       'Your business money, at a glance.\n'
       '\n'
       'Receipts, voice notes and quick entries.\n'
       'Lessons and answers about your business.',
 'uz': '👋 <b>Zinvest</b>\n'
       'Biznesingiz puli — doim yoningizda.\n'
       '\n'
       'Cheklar, ovozli xabarlar va tez yozuvlar.\n'
       'Darslar va biznes savollariga javoblar.'}

NEED_LINK = {'ru': '✈️ <b>Подключите аккаунт</b>\n\nВ приложении: <b>Настройки → Telegram → Подключить</b>.',
 'en': '✈️ <b>Connect your account</b>\n\nIn the app: <b>Settings → Telegram → Connect</b>.',
 'uz': '✈️ <b>Hisobingizni ulang</b>\n\nIlovada: <b>Sozlamalar → Telegram → Ulash</b>.'}

LINKED = {'ru': '🤝 <b>Аккаунт подключён</b>\n'
       '\n'
       '{name}, начнём с первой записи?\n'
       'Пришлите чек или напишите <code>-50000 мука</code>.',
 'en': '🤝 <b>Account connected</b>\n'
       '\n'
       '{name}, ready for your first entry?\n'
       'Send a receipt or type <code>-50000 flour</code>.',
 'uz': '🤝 <b>Hisob ulandi</b>\n'
       '\n'
       '{name}, birinchi yozuvdan boshlaymizmi?\n'
       'Chek yuboring yoki <code>-50000 un</code> deb yozing.'}

BAD_CODE = {
    "ru": "Код не подошёл — скорее всего, он устарел.\nВозьмите новый: приложение → Настройки → Telegram.",
    "en": "That code didn't work — most likely it expired.\nGet a fresh one: app → Settings → Telegram.",
    "uz": "Kod ishlamadi — ehtimol eskirgan.\nYangisini oling: ilova → Sozlamalar → Telegram.",
}

UNLINKED = {
    "ru": "Отвязал чат. В приложении всё осталось на месте — возвращайтесь, когда будет удобно.",
    "en": "Chat unlinked. Nothing in the app changed — come back whenever you like.",
    "uz": "Chat uzildi. Ilovada hammasi joyida — xohlaganingizda qaytib keling.",
}

HELP = {'ru': '🐻 <b>Ваш помощник Zinvest</b>\n'
       '\n'
       '🧾 Чеки и голосовые → доходы и расходы\n'
       '✍️ <code>-50000 мука</code> → быстрая запись\n'
       '💬 Вопрос о бизнесе → ответ\n'
       '🧠 /quiz → тренажёр с разбором\n'
       '📈 /predict → угадайте, куда пошёл курс\n'
       '\n'
       'Выберите действие ниже.\n'
       'Все разделы доступны в меню команд /',
 'en': '🐻 <b>Your Zinvest assistant</b>\n'
       '\n'
       '🧾 Receipts and voice → income and expenses\n'
       '✍️ <code>-50000 flour</code> → quick entry\n'
       '💬 Business question → answer\n'
       '🧠 /quiz → practice with explanations\n'
       '📈 /predict → guess where the price went\n'
       '\n'
       'Choose an action below.\n'
       'All sections are in the command menu /',
 'uz': '🐻 <b>Zinvest yordamchingiz</b>\n'
       '\n'
       '🧾 Chek va ovoz → daromad va xarajat\n'
       '✍️ <code>-50000 un</code> → tez yozuv\n'
       '💬 Biznes savoli → javob\n'
       '🧠 /quiz → izohli mashq\n'
       '📈 /predict → narx qayoqqa ketganini toping\n'
       '\n'
       'Quyidan amalni tanlang.\n'
       'Barcha bo‘limlar buyruqlar menyusida /'}

# --------------------------------------------------------------------------- #
# Money
DRAFT = {
    "ru": "{icon} <b>{title}</b>\n\n<b>{amount}</b>{currency}\n{category}{description}\n🗓 {date}{note}",
    "en": "{icon} <b>{title}</b>\n\n<b>{amount}</b>{currency}\n{category}{description}\n🗓 {date}{note}",
    "uz": "{icon} <b>{title}</b>\n\n<b>{amount}</b>{currency}\n{category}{description}\n🗓 {date}{note}",
}

DRAFT_TITLE = {
    "spending": {"ru": "Расход", "en": "Expense", "uz": "Xarajat"},
    "revenue": {"ru": "Доход", "en": "Income", "uz": "Daromad"},
}

# Shown when the model is unsure, so a misread number is caught before it lands
# in the books rather than after.
LOW_CONFIDENCE = {
    "ru": "\n\n⚠️ Сумму видно плохо — проверьте, прежде чем записывать.",
    "en": "\n\n⚠️ The total is hard to read — check it before saving.",
    "uz": "\n\n⚠️ Summa yaxshi ko‘rinmadi — saqlashdan oldin tekshiring.",
}

PICK_CATEGORY = {
    "ru": "Куда записать {amount}?",
    "en": "Which category for {amount}?",
    "uz": "{amount} qaysi turkumga?",
}

# A number arrived with nothing saying where the money went. Guessing would put
# a wrong figure in the books, so the chat asks — one tap and it is written.
WHICH_WAY = {
    "ru": "🪙 <b>{amount}</b> · {category}\n\nЭто расход или доход?",
    "en": "🪙 <b>{amount}</b> · {category}\n\nMoney out or money in?",
    "uz": "🪙 <b>{amount}</b> · {category}\n\nBu xarajatmi yoki daromadmi?",
}

SAVED = {'ru': '✅ <b>Записал · {kind}</b>\n\n<b>{amount}{currency}</b>\n{category}',
 'en': '✅ <b>Saved · {kind}</b>\n\n<b>{amount}{currency}</b>\n{category}',
 'uz': '✅ <b>Yozildi · {kind}</b>\n\n<b>{amount}{currency}</b>\n{category}'}

DROPPED = {"ru": "Не записал.", "en": "Not saved.", "uz": "Yozilmadi."}

KIND = {
    "spending": {"ru": "расход", "en": "spending", "uz": "xarajat"},
    "revenue": {"ru": "доход", "en": "income", "uz": "daromad"},
}

NO_AMOUNT = {
    "ru": "Сумму я не разобрал. Напишите её сами — например: <code>-50000 мука</code>",
    "en": "I couldn't read the total. Type it instead — for example: <code>-50000 flour</code>",
    "uz": "Summani o‘qiy olmadim. O‘zingiz yozing — masalan: <code>-50000 un</code>",
}

NO_AI = {'ru': '💬 <b>Сейчас не могу ответить</b>\n'
       '\n'
       'Попробуйте позже. Записи по тексту работают:\n'
       '<code>-50000 мука</code>',
 'en': '💬 <b>Temporarily unavailable</b>\n'
       '\n'
       'Please try again later. Text entries still work:\n'
       '<code>-50000 flour</code>',
 'uz': '💬 <b>Hozir javob bera olmayman</b>\n'
       '\n'
       'Keyinroq urinib ko‘ring. Matnli yozuvlar ishlaydi:\n'
       '<code>-50000 un</code>'}

MONEY = {'ru': '💵 <b>Деньги · {month}</b>\n'
       '\n'
       '↗️ Доход: <b>{income}</b>\n'
       '↘️ Расход: <b>{spending}</b>\n'
       '\n'
       '👛 <b>Итог: {total}</b>\n'
       '\n'
       '{top}<i>Записей: {count}</i>',
 'en': '💵 <b>Money · {month}</b>\n'
       '\n'
       '↗️ Income: <b>{income}</b>\n'
       '↘️ Expenses: <b>{spending}</b>\n'
       '\n'
       '👛 <b>Net: {total}</b>\n'
       '\n'
       '{top}<i>Entries: {count}</i>',
 'uz': '💵 <b>Pul · {month}</b>\n'
       '\n'
       '↗️ Daromad: <b>{income}</b>\n'
       '↘️ Xarajat: <b>{spending}</b>\n'
       '\n'
       '👛 <b>Natija: {total}</b>\n'
       '\n'
       '{top}<i>Yozuvlar: {count}</i>'}

MONEY_TOP = {'ru': '<b>Основные расходы</b>\n{rows}\n\n',
 'en': '<b>Top expenses</b>\n{rows}\n\n',
 'uz': '<b>Asosiy xarajatlar</b>\n{rows}\n\n'}

MONEY_EMPTY = {
    "ru": "💵 <b>{month}</b>\n\nЗаписей пока нет.\n\nПришлите фото чека или напишите <code>-50000 мука</code> — и здесь появятся цифры.",
    "en": "💵 <b>{month}</b>\n\nNothing logged yet.\n\nSend a photo of a receipt or type <code>-50000 flour</code> and the numbers appear here.",
    "uz": "💵 <b>{month}</b>\n\nHali yozuv yo‘q.\n\nChek rasmini yuboring yoki <code>-50000 un</code> deb yozing.",
}

# --------------------------------------------------------------------------- #
# Learning
TODAY = {'ru': '📚 <b>Урок на сегодня</b>\n\n<b>{title}</b>\n\n~{minutes} мин · 🔥 Серия: {streak} дн.',
 'en': '📚 <b>Today’s lesson</b>\n\n<b>{title}</b>\n\n~{minutes} min · 🔥 Streak: {streak} days',
 'uz': '📚 <b>Bugungi dars</b>\n\n<b>{title}</b>\n\n~{minutes} daqiqa · 🔥 Seriya: {streak} kun'}

TODAY_DONE = {
    "ru": "✅ На сегодня всё пройдено.\n🔥 Серия: {streak} дн. Отдыхайте.",
    "en": "✅ Everything for today is done.\n🔥 Streak: {streak} days. Rest well.",
    "uz": "✅ Bugungi hammasi bajarildi.\n🔥 Seriya: {streak} kun. Dam oling.",
}

LEAGUE = {
    "ru": "🏆 <b>{division}</b>\n\n{rank} место из {total} · <b>{points}</b> очков\n\n{board}\n{hint}",
    "en": "🏆 <b>{division}</b>\n\nPlace {rank} of {total} · <b>{points}</b> points\n\n{board}\n{hint}",
    "uz": "🏆 <b>{division}</b>\n\n{total} dan {rank}-o‘rin · <b>{points}</b> ochko\n\n{board}\n{hint}",
}

LEAGUE_HINT_UP = {
    "ru": "Вы в зоне повышения — держитесь.",
    "en": "You're in the promotion zone — hold on.",
    "uz": "Ko‘tarilish zonasidasiz — ushlab turing.",
}
LEAGUE_HINT_DOWN = {
    "ru": "Один урок вытащит вас из зоны вылета.",
    "en": "One lesson pulls you out of the drop zone.",
    "uz": "Bitta dars sizni tushish zonasidan chiqaradi.",
}
LEAGUE_HINT_MID = {
    "ru": "До зоны повышения — {gap} очков.",
    "en": "{gap} points to the promotion zone.",
    "uz": "Ko‘tarilish zonasigacha {gap} ochko.",
}

# --------------------------------------------------------------------------- #
# Settings
SETTINGS = {'ru': '⚙️ <b>Напоминания</b>\n\n🔔 <b>{mode}</b>\n⏰ Около {hour}:00\n\nВыберите частоту и время ниже.',
 'en': '⚙️ <b>Reminders</b>\n\n🔔 <b>{mode}</b>\n⏰ Around {hour}:00\n\nChoose frequency and time below.',
 'uz': '⚙️ <b>Eslatmalar</b>\n'
       '\n'
       '🔔 <b>{mode}</b>\n'
       '⏰ Taxminan {hour}:00\n'
       '\n'
       'Quyidan takrorlanish va vaqtni tanlang.'}

MODES = {
    "daily": {"ru": "каждый день", "en": "daily", "uz": "har kuni"},
    "weekly": {"ru": "раз в неделю", "en": "weekly", "uz": "haftada bir"},
    "off": {"ru": "выключены", "en": "off", "uz": "o‘chirilgan"},
}

SETTINGS_SAVED = {"ru": "Хорошо, запомнил.", "en": "Noted.", "uz": "Yaxshi, eslab qoldim."}
LATER = {"ru": "Напомню через час.", "en": "I'll come back in an hour.", "uz": "Bir soatdan keyin eslataman."}
NOT_TODAY = {"ru": "Хорошо, сегодня не трогаю. Серия подождёт.", "en": "Fine — nothing more today. The streak can wait.", "uz": "Mayli, bugun bezovta qilmayman."}

TOO_FAST = {
    "ru": "Слишком много сообщений подряд. Подождите минуту, пожалуйста.",
    "en": "That's a lot of messages at once. Give me a minute, please.",
    "uz": "Juda ko‘p xabar. Iltimos, bir daqiqa kuting.",
}

# --------------------------------------------------------------------------- #
# Buttons. The first block is the keyboard that sits under the chat all the
# time; handlers.py matches its labels in every language.
MENU = {
    "money": {"ru": "💵 Деньги", "en": "💵 Money", "uz": "💵 Pul"},
    "today": {"ru": "📚 Сегодня", "en": "📚 Today", "uz": "📚 Bugun"},
    "quiz": {"ru": "🧠 Тренажёр", "en": "🧠 Practice", "uz": "🧠 Mashq"},
    "predict": {"ru": "📈 Вверх или вниз", "en": "📈 Up or down", "uz": "📈 Yuqorimi-pastmi"},
    "league": {"ru": "🏆 Лига", "en": "🏆 League", "uz": "🏆 Liga"},
    "settings": {"ru": "⚙️ Настройки", "en": "⚙️ Settings", "uz": "⚙️ Sozlamalar"},
}

BTN = {
    "save": {"ru": "Записать", "en": "Save", "uz": "Yozish"},
    "spending": {"ru": "Расход", "en": "Spending", "uz": "Xarajat"},
    "revenue": {"ru": "Доход", "en": "Income", "uz": "Daromad"},
    "drop": {"ru": "Отмена", "en": "Discard", "uz": "Kerak emas"},
    "category": {"ru": "Категория", "en": "Category", "uz": "Turkum"},
    "back": {"ru": "Назад", "en": "Back", "uz": "Orqaga"},
    "open": {"ru": "Открыть приложение", "en": "Open app", "uz": "Ilovada ochish"},
    "lesson": {"ru": "5 минут сейчас", "en": "5 minutes now", "uz": "Hozir 5 daqiqa"},
    "later": {"ru": "Позже", "en": "Later", "uz": "Keyinroq"},
    "not_today": {"ru": "Не сегодня", "en": "Not today", "uz": "Bugun emas"},
    "weekly": {"ru": "Раз в неделю", "en": "Weekly", "uz": "Haftada bir"},
    "off": {"ru": "Выключить", "en": "Off", "uz": "Yozma"},
    "daily": {"ru": "Каждый день", "en": "Daily", "uz": "Har kuni"},
    "league": {"ru": "Вся таблица", "en": "Full board", "uz": "To‘liq jadval"},
    "help": {"ru": "Что ты умеешь", "en": "What you can do", "uz": "Nimani uddalaysan"},
    "hour": {"ru": "Время: {hour}:00", "en": "Time: {hour}:00", "uz": "Vaqt: {hour}:00"},
}

# The "/" menu inside Telegram (setMyCommands).
COMMANDS = {
    "money": {"ru": "Деньги за месяц", "en": "This month's money", "uz": "Oylik pul"},
    "today": {"ru": "Урок на сегодня", "en": "Today's lesson", "uz": "Bugungi dars"},
    "quiz": {"ru": "Тренажёр: тесты с разбором", "en": "Practice: questions with explanations", "uz": "Mashq: izohli testlar"},
    "predict": {"ru": "Игра «Вверх или вниз?»", "en": "The “Up or down?” game", "uz": "«Yuqorimi yoki pastmi?» o‘yini"},
    "league": {"ru": "Моё место в лиге", "en": "My league place", "uz": "Ligadagi o‘rnim"},
    "settings": {"ru": "Напоминания", "en": "Nudges", "uz": "Eslatmalar"},
    "help": {"ru": "Что умеет бот", "en": "What the bot can do", "uz": "Bot nimani uddalaydi"},
    "stop": {"ru": "Отвязать чат", "en": "Unlink the chat", "uz": "Chatni uzish"},
}

ABOUT_SHORT = {
    "ru": "Фото чека → запись в расходы. Голосом тоже. И короткие уроки про деньги.",
    "en": "A photo of a receipt becomes an expense. Voice too. Plus short money lessons.",
    "uz": "Chek rasmi — xarajat yozuvi. Ovoz orqali ham. Va qisqa pul darslari.",
}

ABOUT = {'ru': 'Zinvest — деньги вашего дела под рукой.\n'
       '\n'
       '• Доходы и расходы по чеку, голосом или текстом\n'
       '• Короткие уроки\n'
       '• Тренажёр и игра «Вверх или вниз?»\n'
       '• Ответы на вопросы о бизнесе',
 'en': 'Zinvest — your business money, at a glance.\n'
       '\n'
       '• Income and expenses by receipt, voice or text\n'
       '• Short lessons\n'
       '• Practice questions and the “Up or down?” game\n'
       '• Answers to business questions',
 'uz': 'Zinvest — biznesingiz puli yoningizda.\n'
       '\n'
       '• Chek, ovoz yoki matn orqali daromad va xarajatlar\n'
       '• Qisqa darslar\n'
       '• Mashq va «Yuqorimi yoki pastmi?» o‘yini\n'
       '• Biznes savollariga javoblar'}

# --------------------------------------------------------------------------- #
# The bear's check-in
NUDGES = {
    "first": {
        "ru": [
            "Первый урок — самый короткий. {minutes} минут, и дальше проще.",
            "Начнём с «{title}»? Это {minutes} минут, а деньги перестанут быть туманом.",
            "У вас ещё нет серии. Заведём её сегодня — {minutes} минут.",
        ],
        "en": [
            "The first lesson is the shortest one. {minutes} minutes and it gets easier.",
            "Shall we start with “{title}”? {minutes} minutes.",
            "No streak yet. Let's start one today — {minutes} minutes.",
        ],
        "uz": [
            "Birinchi dars — eng qisqasi. {minutes} daqiqa, keyin osonlashadi.",
            "«{title}» dan boshlaymizmi? {minutes} daqiqa.",
            "Hali seriya yo‘q. Bugun boshlaymiz — {minutes} daqiqa.",
        ],
    },
    "keep": {
        "ru": [
            "Второй день подряд — это уже привычка. «{title}», {minutes} минут.",
            "Серия {streak} дн. Сегодня ждёт «{title}».",
            "{minutes} минут — и день засчитан.",
        ],
        "en": [
            "Two days in a row is a habit forming. “{title}”, {minutes} minutes.",
            "Streak: {streak} days. Today it's “{title}”.",
            "{minutes} minutes and the day counts.",
        ],
        "uz": [
            "Ketma-ket ikki kun — odat boshlanishi. «{title}», {minutes} daqiqa.",
            "Seriya: {streak} kun. Bugun «{title}».",
            "{minutes} daqiqa — va kun hisoblanadi.",
        ],
    },
    "streak": {
        "ru": [
            "{streak} дней подряд. Сегодня — «{title}», {minutes} минут.",
            "Такую серию жалко ронять: {minutes} минут и она цела.",
            "{streak} дней. Думаю, вы знаете, что делать.",
        ],
        "en": [
            "{streak} days in a row. Today: “{title}”, {minutes} minutes.",
            "A streak like that deserves {minutes} minutes.",
            "{streak} days. You know the drill.",
        ],
        "uz": [
            "Ketma-ket {streak} kun. Bugun — «{title}», {minutes} daqiqa.",
            "Bunday seriyani yo‘qotish achinarli: {minutes} daqiqa yetarli.",
            "{streak} kun. Nima qilishni bilasiz.",
        ],
    },
    "risk": {
        "ru": [
            "Серия {streak} дн. сгорит после полуночи. {minutes} минут — и нет.",
            "До конца дня немного, а урок короткий: {minutes} минут.",
        ],
        "en": [
            "Your {streak}-day streak ends at midnight. {minutes} minutes saves it.",
            "Not much day left, and the lesson is short: {minutes} minutes.",
        ],
        "uz": [
            "{streak} kunlik seriya yarim tunda tugaydi. {minutes} daqiqa saqlab qoladi.",
            "Kun tugayapti, dars esa qisqa: {minutes} daqiqa.",
        ],
    },
    "league": {
        "ru": [
            "В лиге вы {rank}-й. Один урок — плюс {lesson_points} очков.",
            "{division}: до зоны повышения {gap} очков. Один урок закрывает почти всё.",
        ],
        "en": [
            "You're {rank} in the league. One lesson is +{lesson_points} points.",
            "{division}: {gap} points to the promotion zone. One lesson nearly covers it.",
        ],
        "uz": [
            "Ligada {rank}-o‘rindasiz. Bitta dars — +{lesson_points} ochko.",
            "{division}: ko‘tarilishgacha {gap} ochko. Bitta dars deyarli yetadi.",
        ],
    },
}

WEEKLY = {
    "ru": "🐻 <b>Итоги недели</b>\n\n📚 Уроков: {lessons}\n🏆 {division}, {rank} место · {points} очков\n"
          "🪙 Монеты: {coins}\n🔥 Серия: {streak} дн.\n\n{closing}",
    "en": "🐻 <b>Your week</b>\n\n📚 Lessons: {lessons}\n🏆 {division}, place {rank} · {points} points\n"
          "🪙 Coins: {coins}\n🔥 Streak: {streak} days\n\n{closing}",
    "uz": "🐻 <b>Hafta yakuni</b>\n\n📚 Darslar: {lessons}\n🏆 {division}, {rank}-o‘rin · {points} ochko\n"
          "🪙 Tangalar: {coins}\n🔥 Seriya: {streak} kun\n\n{closing}",
}

WEEKLY_CLOSING = {
    "ru": ["Хорошая неделя. Следующая — ещё лучше.", "Так держать.", "Спокойно и по чуть-чуть — это и работает."],
    "en": ["A good week. Next one, better.", "Keep it up.", "Small and steady is what works."],
    "uz": ["Yaxshi hafta. Keyingisi yanada yaxshi.", "Shunday davom eting.", "Oz-ozdan — eng ishlaydigan yo‘l."],
}


def nudge_line(key, lang, avoid="", **kw):
    """One line from the pool for `key`, never the one used last time."""
    pool = list(pick(NUDGES[key], lang))
    fresh = [line for line in pool if f"{key}:{pool.index(line)}" != avoid] or pool
    line = random.choice(fresh)
    return line.format(**kw), f"{key}:{pool.index(line)}"


def menu_keyboard(lang):
    """The buttons that live under the chat, so there is always a way forward."""
    return {
        "keyboard": [
            [{"text": pick(MENU["money"], lang)}, {"text": pick(MENU["today"], lang)}],
            [{"text": pick(MENU["quiz"], lang)}, {"text": pick(MENU["predict"], lang)}],
            [{"text": pick(MENU["league"], lang)}, {"text": pick(MENU["settings"], lang)}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
        "input_field_placeholder": pick({"ru": "Чек, голосовое или вопрос…", "en": "Receipt, voice note or question…", "uz": "Chek, ovozli xabar yoki savol…"}, lang),
    }


def menu_command(text):
    """Which command a tap on the keyboard means, in any of the languages."""
    cleaned = (text or "").strip()
    # Buttons sent before the custom money icon was introduced still work.
    if cleaned.startswith("💰 "):
        cleaned = "💵 " + cleaned[2:]
    for command, table in MENU.items():
        if any(cleaned in (label, label.split(" ", 1)[-1]) for label in table.values()):
            return command
    return ""


# --------------------------------------------------------------------------- #
# The illustrated screens (see cards.py) and the buttons that open them
FEATURES = {'receipt': {'ru': '📷 <b>Фото чека</b>\n'
                   '\n'
                   'Пришлите чёткое фото — покажу сумму, дату и продавца.\n'
                   '\n'
                   '<i>Проверьте карточку и нажмите «Записать».</i>',
             'en': '📷 <b>Receipt photo</b>\n'
                   '\n'
                   'Send a clear photo to see the amount, date and shop.\n'
                   '\n'
                   '<i>Check the draft, then tap Save.</i>',
             'uz': '📷 <b>Chek rasmi</b>\n'
                   '\n'
                   'Aniq surat yuboring — summa, sana va do‘konni ko‘rsataman.\n'
                   '\n'
                   '<i>Kartani tekshirib, «Yozish» tugmasini bosing.</i>'},
 'voice': {'ru': '🎙 <b>Голосовая запись</b>\n'
                 '\n'
                 'Например: «Сегодня выручка 300 тысяч».\n'
                 '\n'
                 '<i>Покажу запись на проверку. Можно и задать вопрос.</i>',
           'en': '🎙 <b>Voice entry</b>\n'
                 '\n'
                 'Try: “Today’s sales were 300 thousand”.\n'
                 '\n'
                 '<i>Review the entry before saving. You can ask a question too.</i>',
           'uz': '🎙 <b>Ovozli yozuv</b>\n'
                 '\n'
                 'Masalan: «Bugun 300 ming tushdi».\n'
                 '\n'
                 '<i>Saqlashdan oldin yozuvni tekshiring. Savol ham berishingiz mumkin.</i>'},
 'quick': {'ru': '✍️ <b>Быстрая запись</b>\n'
                 '\n'
                 'Со знаком: <code>-50000 мука</code> · <code>+300к выручка</code>\n'
                 'Словами: <code>потратил 50 тысяч на муку</code>\n'
                 'Или просто: <code>300 тысяч</code> — спрошу, расход это или доход.\n'
                 '\n'
                 '<i>Сохраню сразу в Cashflow. Отменить можно кнопкой под записью.</i>',
           'en': '✍️ <b>Quick entry</b>\n'
                 '\n'
                 'With a sign: <code>-50000 flour</code> · <code>+300k sales</code>\n'
                 'In words: <code>spent 50 thousand on flour</code>\n'
                 'Or just: <code>300 thousand</code> — I will ask which way it went.\n'
                 '\n'
                 '<i>Saved to your cashflow at once. Tap Undo below the entry to reverse it.</i>',
           'uz': '✍️ <b>Tez yozuv</b>\n'
                 '\n'
                 'Ishora bilan: <code>-50000 un</code> · <code>+300k savdo</code>\n'
                 'So‘z bilan: <code>unga 50 ming xarajat</code>\n'
                 'Yoki shunchaki: <code>300 ming</code> — qaysi tomonga ketganini so‘rayman.\n'
                 '\n'
                 '<i>Darhol Cashflow‘ga saqlanadi. Yozuv ostidagi tugma bilan bekor qilinadi.</i>'},
 'question': {'ru': '💬 <b>Вопрос о бизнесе</b>\n'
                    '\n'
                    'Напишите или спросите голосом.\n'
                    'Например: «Как рассчитать себестоимость?»',
              'en': '💬 <b>Business question</b>\n'
                    '\n'
                    'Type or send a voice note.\n'
                    'Try: “How do I calculate unit cost?”',
              'uz': '💬 <b>Biznes savoli</b>\n'
                    '\n'
                    'Yozing yoki ovozli so‘rang.\n'
                    'Masalan: «Tannarxni qanday hisoblayman?»'}}

STOP_CONFIRM = {'ru': '🔗 <b>Отвязать чат?</b>\n'
       '\n'
       'Бот перестанет получать данные аккаунта.\n'
       'Записи в приложении сохранятся.\n'
       'Подключиться снова можно в настройках.',
 'en': '🔗 <b>Unlink this chat?</b>\n'
       '\n'
       'The bot will lose access to your account.\n'
       'Your entries stay in the app.\n'
       'Reconnect anytime in settings.',
 'uz': '🔗 <b>Chatni uzish kerakmi?</b>\n'
       '\n'
       'Bot hisob ma’lumotlariga kira olmaydi.\n'
       'Yozuvlar ilovada saqlanadi.\n'
       'Sozlamalarda qayta ulanish mumkin.'}

LEAGUE_RULES = {
    "ru": "🏆 <b>Как считаются очки</b>\n\n📚 Пройденный урок — +{lesson}\n🎯 Сданный тест раздела — +{test}\n"
          "🔥 День, когда вы занимались — +{day}\n\nКаждый понедельник — новая группа из 25 человек. "
          "Топ-{promote} идут выше, последние {demote} — ниже. Монеты от поддержки в зачёт не идут.",
    "en": "🏆 <b>How points work</b>\n\n📚 Lesson finished — +{lesson}\n🎯 Unit test passed — +{test}\n"
          "🔥 A day you showed up — +{day}\n\nEvery Monday a new group of 25. Top {promote} move up, "
          "the last {demote} move down. Coins given by support do not count.",
    "uz": "🏆 <b>Ochkolar qanday hisoblanadi</b>\n\n📚 Tugatilgan dars — +{lesson}\n🎯 Topshirilgan test — +{test}\n"
          "🔥 Shug‘ullangan kun — +{day}\n\nHar dushanba yangi 25 kishilik guruh. Yuqori {promote} ko‘tariladi, "
          "oxirgi {demote} tushadi. Qo‘llab-quvvatlash bergan tangalar hisoblanmaydi.",
}

UNDONE = {
    "ru": "↩️ Запись удалена.",
    "en": "↩️ Entry removed.",
    "uz": "↩️ Yozuv o‘chirildi.",
}

EXTRA = {
    "undo": {"ru": "Отменить", "en": "Undo", "uz": "Bekor qilish"},
    "month": {"ru": "За месяц", "en": "This month", "uz": "Oylik natija"},
    "rules": {"ru": "Правила лиги", "en": "League rules", "uz": "Liga qoidalari"},
    "unlink": {"ru": "Отвязать чат", "en": "Unlink the chat", "uz": "Chatni uzish"},
    "yes_unlink": {"ru": "Да, отвязать", "en": "Yes, unlink", "uz": "Ha, uzilsin"},
    "cancel": {"ru": "Отмена", "en": "Cancel", "uz": "Bekor qilish"},
    "receipt": {"ru": "Фото чека", "en": "Receipt photo", "uz": "Chek rasmi"},
    "voice": {"ru": "Голосовые", "en": "Voice", "uz": "Ovozli"},
    "quick": {"ru": "Быстрая запись", "en": "Quick entry", "uz": "Tez yozuv"},
    "question": {"ru": "Вопрос", "en": "A question", "uz": "Savol"},
}


# --------------------------------------------------------------------------- #
# Practice (/quiz): the question bank as native quiz polls
QUIZ_INTRO = {
    "ru": "🧠 <b>Тренажёр</b>\n\n{count} вопросов о деньгах, инвестициях и бизнесе. Отвечайте прямо в опросе — "
          "сразу увидите, верно ли и почему. Непонятно — спросите ИИ под ответом.{today}",
    "en": "🧠 <b>Practice</b>\n\n{count} questions on money, investing and business. Answer right in the poll — "
          "you see at once whether you were right and why. Still unclear? Ask the AI under the answer.{today}",
    "uz": "🧠 <b>Mashq</b>\n\nPul, investitsiya va biznes haqida {count} ta savol. Javobni so‘rovnomada bering — "
          "to‘g‘rimi va nega ekanini darhol ko‘rasiz. Tushunarsiz bo‘lsa, javob ostida AI dan so‘rang.{today}",
}

QUIZ_TODAY = {
    "ru": "\n\n<i>Сегодня: {correct} из {total} верно</i>",
    "en": "\n\n<i>Today: {correct} of {total} right</i>",
    "uz": "\n\n<i>Bugun: {total} tadan {correct} tasi to‘g‘ri</i>",
}

QUIZ_RIGHT = {
    "ru": "✅ <b>Верно!</b>\n\n💡 {explain}{today}",
    "en": "✅ <b>Correct!</b>\n\n💡 {explain}{today}",
    "uz": "✅ <b>To‘g‘ri!</b>\n\n💡 {explain}{today}",
}

QUIZ_WRONG = {
    "ru": "❌ <b>Не совсем</b>\n\nПравильный ответ: <b>{answer}</b>\n\n💡 {explain}{today}",
    "en": "❌ <b>Not quite</b>\n\nThe right answer: <b>{answer}</b>\n\n💡 {explain}{today}",
    "uz": "❌ <b>Unchalik emas</b>\n\nTo‘g‘ri javob: <b>{answer}</b>\n\n💡 {explain}{today}",
}

QUIZ_EMPTY = {
    "ru": "🧠 Вопросов пока нет — загляните чуть позже.",
    "en": "🧠 No questions yet — check back a little later.",
    "uz": "🧠 Hozircha savollar yo‘q — birozdan keyin qaytib keling.",
}

# --------------------------------------------------------------------------- #
# "Up or down?" (/predict): real market moments, cut where you make the call
PREDICT_ROUND = {
    "ru": "📈 <b>Вверх или вниз?</b> · раунд {round} из {per_day}\n\n<b>{asset}</b> · {when}\n📰 {headline}\n\n"
          "❓ {question}\n\n<i>Верный прогноз — +{coins} 🪙</i>",
    "en": "📈 <b>Up or down?</b> · round {round} of {per_day}\n\n<b>{asset}</b> · {when}\n📰 {headline}\n\n"
          "❓ {question}\n\n<i>A right call pays +{coins} 🪙</i>",
    "uz": "📈 <b>Yuqorimi yoki pastmi?</b> · {per_day} dan {round}-raund\n\n<b>{asset}</b> · {when}\n📰 {headline}\n\n"
          "❓ {question}\n\n<i>To‘g‘ri bashorat — +{coins} 🪙</i>",
}

# Before the very first round: what the game is, once.
PREDICT_INTRO = {
    "ru": "📈 <b>Вверх или вниз?</b>\n\nРеальные моменты из истории рынков. Я показываю график до момента решения — "
          "вы угадываете, куда цена пошла дальше. Потом — что было на самом деле и почему.\n\n"
          "<i>{per_day} раунда в день · верный прогноз +{coins} 🪙</i>",
    "en": "📈 <b>Up or down?</b>\n\nReal moments from market history. I show the chart up to the moment of the call — "
          "you guess where the price went next. Then what really happened, and why.\n\n"
          "<i>{per_day} rounds a day · a right call pays +{coins} 🪙</i>",
    "uz": "📈 <b>Yuqorimi yoki pastmi?</b>\n\nBozorlar tarixidagi haqiqiy lahzalar. Grafikni qaror lahzasigacha ko‘rsataman — "
          "narx keyin qayoqqa ketganini topasiz. So‘ng — aslida nima bo‘lgani va nega.\n\n"
          "<i>Kuniga {per_day} ta raund · to‘g‘ri bashorat +{coins} 🪙</i>",
}

PREDICT_CALL = {
    "ru": "Ваш прогноз: <b>{choice}</b>",
    "en": "Your call: <b>{choice}</b>",
    "uz": "Bashoratingiz: <b>{choice}</b>",
}

PREDICT_RIGHT = {
    "ru": "✅ <b>В точку! +{coins} 🪙</b>\n{asset}: {start} → <b>{end}</b>{change}\n\n💡 {explain}\n\n🎓 {lesson}\n\n{stats}",
    "en": "✅ <b>Spot on! +{coins} 🪙</b>\n{asset}: {start} → <b>{end}</b>{change}\n\n💡 {explain}\n\n🎓 {lesson}\n\n{stats}",
    "uz": "✅ <b>Topdingiz! +{coins} 🪙</b>\n{asset}: {start} → <b>{end}</b>{change}\n\n💡 {explain}\n\n🎓 {lesson}\n\n{stats}",
}

PREDICT_WRONG = {
    "ru": "❌ <b>Мимо — рынок пошёл {direction}</b>\n{asset}: {start} → <b>{end}</b>{change}\n\n💡 {explain}\n\n🎓 {lesson}\n\n{stats}",
    "en": "❌ <b>Missed — the market went {direction}</b>\n{asset}: {start} → <b>{end}</b>{change}\n\n💡 {explain}\n\n🎓 {lesson}\n\n{stats}",
    "uz": "❌ <b>Topa olmadingiz — bozor {direction} ketdi</b>\n{asset}: {start} → <b>{end}</b>{change}\n\n💡 {explain}\n\n🎓 {lesson}\n\n{stats}",
}

PREDICT_STATS = {
    "ru": "<i>Серия: {streak} · верно {correct} из {played}{left}</i>",
    "en": "<i>Streak: {streak} · {correct} of {played} right{left}</i>",
    "uz": "<i>Seriya: {streak} · {played} tadan {correct} tasi to‘g‘ri{left}</i>",
}

PREDICT_LEFT = {
    "ru": " · сегодня ещё {left}",
    "en": " · {left} more today",
    "uz": " · bugun yana {left} ta",
}

PREDICT_LIMIT = {
    "ru": "📈 <b>Вверх или вниз?</b>\n\nНа сегодня все {per_day} раунда сыграны — завтра новые моменты рынка.\n\n"
          "<i>Серия: {streak} · верно {correct} из {played} · заработано {coins} 🪙</i>\n\nА пока можно потренироваться: /quiz",
    "en": "📈 <b>Up or down?</b>\n\nAll {per_day} rounds for today are played — new market moments tomorrow.\n\n"
          "<i>Streak: {streak} · {correct} of {played} right · {coins} 🪙 earned</i>\n\nMeanwhile, there is practice: /quiz",
    "uz": "📈 <b>Yuqorimi yoki pastmi?</b>\n\nBugungi {per_day} ta raund o‘ynaldi — ertaga bozorning yangi lahzalari.\n\n"
          "<i>Seriya: {streak} · {played} tadan {correct} tasi to‘g‘ri · {coins} 🪙 topildi</i>\n\nHozircha mashq qilish mumkin: /quiz",
}

PREDICT_ALL_DONE = {
    "ru": "📈 <b>Вверх или вниз?</b>\n\nВы сыграли все эпизоды: {played}, из них верно {correct}. Скоро добавим новые.\n\n"
          "А пока можно потренироваться: /quiz",
    "en": "📈 <b>Up or down?</b>\n\nYou have played every episode: {played}, {correct} of them right. New ones are coming.\n\n"
          "Meanwhile, there is practice: /quiz",
    "uz": "📈 <b>Yuqorimi yoki pastmi?</b>\n\nBarcha epizodlarni o‘ynadingiz: {played} ta, {correct} tasi to‘g‘ri. "
          "Tez orada yangilari qo‘shiladi.\n\nHozircha mashq qilish mumkin: /quiz",
}

PREDICT_REFUSED = {
    "played": {"ru": "Этот раунд уже сыгран.", "en": "You have already played this round.", "uz": "Bu raund allaqachon o‘ynalgan."},
    "limit": {"ru": "На сегодня раунды закончились — завтра новые.", "en": "That’s all the rounds for today — new ones tomorrow.",
              "uz": "Bugungi raundlar tugadi — ertaga yangilari."},
}

DIRECTION = {
    "up": {"ru": "вверх", "en": "up", "uz": "yuqoriga"},
    "down": {"ru": "вниз", "en": "down", "uz": "pastga"},
}

GAME_BTN = {
    "ask_ai": {"ru": "Спросить ИИ", "en": "Ask the AI", "uz": "AI dan so‘rash"},
    "next_question": {"ru": "Ещё вопрос", "en": "Next question", "uz": "Keyingi savol"},
    "up": {"ru": "Вверх", "en": "Up", "uz": "Yuqoriga"},
    "down": {"ru": "Вниз", "en": "Down", "uz": "Pastga"},
    "next_round": {"ru": "Следующий раунд", "en": "Next round", "uz": "Keyingi raund"},
    "practice": {"ru": "Тренажёр", "en": "Practice", "uz": "Mashq"},
}

# --------------------------------------------------------------------------- #
# "Ask the AI" under a quiz answer or a round. Written in the learner's
# language, so the model has no reason to answer in another one.
EXPLAIN_TITLE = {"ru": "Разбор Zinvest AI", "en": "Zinvest AI explains", "uz": "Zinvest AI tahlili"}

EXPLAINING = {"ru": "Секунду, разбираю…", "en": "One moment…", "uz": "Bir soniya…"}

ANSWER_FIRST = {
    "ru": "Сначала ответьте — потом разберём.",
    "en": "Answer first — then we’ll go through it.",
    "uz": "Avval javob bering — keyin tahlil qilamiz.",
}

QUIZ_AI = {
    "ru": "Объясни простыми словами вопрос из тренажёра.\nВопрос: {question}\nВарианты: {options}\n"
          "Правильный ответ: {correct}\n{chosen}Почему верно именно это? Приведи короткий пример из жизни.",
    "en": "Explain a practice question in plain words.\nQuestion: {question}\nOptions: {options}\n"
          "Right answer: {correct}\n{chosen}Why is that the right one? Give a short everyday example.",
    "uz": "Mashqdagi savolni oddiy so‘zlar bilan tushuntiring.\nSavol: {question}\nVariantlar: {options}\n"
          "To‘g‘ri javob: {correct}\n{chosen}Nega aynan shu to‘g‘ri? Hayotdan qisqa misol keltiring.",
}

QUIZ_AI_CHOSEN = {
    "ru": "Я ответил: {chosen} — почему это неверно?\n",
    "en": "I answered: {chosen} — why is that wrong?\n",
    "uz": "Men shunday javob berdim: {chosen} — nega bu noto‘g‘ri?\n",
}

PREDICT_AI = {
    "ru": "Разбери эпизод из игры «Вверх или вниз?».\n{asset}, {when}. Новость: {headline}\n"
          "Дальше цена пошла {direction}: {start} → {end}{change}.\n"
          "Почему рынок повёл себя именно так и чему это учит начинающего инвестора?",
    "en": "Walk me through an episode from the “Up or down?” game.\n{asset}, {when}. The news: {headline}\n"
          "Then the price went {direction}: {start} → {end}{change}.\n"
          "Why did the market move that way, and what does it teach a beginner investor?",
    "uz": "«Yuqorimi yoki pastmi?» o‘yinidagi epizodni tahlil qiling.\n{asset}, {when}. Yangilik: {headline}\n"
          "Keyin narx {direction} ketdi: {start} → {end}{change}.\n"
          "Nega bozor aynan shunday harakat qildi va bu boshlovchi investorga nimani o‘rgatadi?",
}
