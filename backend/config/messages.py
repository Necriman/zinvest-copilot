"""
What the server says in `detail` — errors and short notices — in Russian and
Uzbek as well as English.

Views keep writing plain English, which stays the source of truth (and what the
logs and tests read). This middleware translates the `detail` of a JSON
response into the request's language on the way out, so every screen that
shows `detail` shows it in the reader's language without each view knowing
about languages. learning.test_languages checks that every message in the code
has a translation here, so a new one cannot slip through in English.
"""
import json
import re

from django.core.serializers.json import DjangoJSONEncoder

from . import languages

# English → (Russian, Uzbek)
EXACT = {
    "A letter is already on its way. Try again in an hour.": (
        "Письмо уже в пути. Попробуйте снова через час.",
        "Xat allaqachon yo‘lda. Bir soatdan keyin qayta urinib ko‘ring."),
    "A question is required.": ("Нужен вопрос.", "Savol kiriting."),
    "AI features are paused by the Zinvest team. Please try again later.": (
        "Команда Zinvest временно приостановила функции ИИ. Попробуйте позже.",
        "Zinvest jamoasi AI imkoniyatlarini vaqtincha to‘xtatdi. Keyinroq urinib ko‘ring."),
    "AI service error.": ("Ошибка сервиса ИИ.", "AI xizmatida xatolik."),
    "AI token quota exhausted for this cycle.": (
        "Лимит ИИ на этот период исчерпан.", "Ushbu davr uchun AI limiti tugadi."),
    "Account is disabled.": ("Аккаунт отключён.", "Hisob o‘chirilgan."),
    "Already played.": ("Уже сыграно.", "Allaqachon o‘ynalgan."),
    "An account with this email already exists.": (
        "Аккаунт с этой почтой уже существует.", "Bu elektron pochta bilan hisob allaqachon mavjud."),
    "An account with this email already exists. Sign in instead.": (
        "Аккаунт с этой почтой уже есть. Войдите в него.",
        "Bu pochta bilan hisob allaqachon bor. Unga kiring."),
    "Please wait before asking for another code.": (
        "Подождите немного, прежде чем просить новый код.",
        "Yangi kod so‘rashdan oldin biroz kuting."),
    "Too many codes for this address. Try again later.": (
        "Слишком много кодов на этот адрес. Попробуйте позже.",
        "Bu manzilga juda ko‘p kod yuborildi. Keyinroq urinib ko‘ring."),
    "We sent a code to your email.": ("Мы отправили код на вашу почту.", "Pochtangizga kod yubordik."),
    "This code has expired. Ask for a new one.": (
        "Код больше не действует. Запросите новый.", "Bu kod endi ishlamaydi. Yangisini so‘rang."),
    "Too many attempts. Try again in 15 minutes.": (
        "Слишком много попыток. Попробуйте через 15 минут.", "Juda ko‘p urinish. 15 daqiqadan keyin qayta urinib ko‘ring."),
    "Wrong code.": ("Неверный код.", "Kod noto‘g‘ri."),
    "Ask another owner to change your own role.": (
        "Попросите другого владельца изменить вашу роль.", "O‘z rolingizni o‘zgartirishni boshqa egadan so‘rang."),
    "Authentication credentials were not provided.": ("Нужно войти в аккаунт.", "Hisobga kirish kerak."),
    "Cannot connect to yourself.": ("Нельзя добавить в контакты самого себя.", "O‘zingiz bilan bog‘lana olmaysiz."),
    "Change by 1 to 100 000 coins.": ("Изменение — от 1 до 100 000 монет.", "O‘zgarish — 1 dan 100 000 tangagacha."),
    "Choose a reason.": ("Выберите причину.", "Sababni tanlang."),
    "Choose a valid answer.": ("Выберите вариант ответа.", "Javob variantini tanlang."),
    "Choose an employee.": ("Выберите сотрудника.", "Xodimni tanlang."),
    "Choose an image within the upload limit.": (
        "Выберите изображение в пределах лимита загрузки.", "Yuklash limitiga mos rasmni tanlang."),
    "Complete the onboarding assessment first.": ("Сначала пройдите вступительный тест.", "Avval kirish testidan o‘ting."),
    "Confirm it's you again to make changes.": (
        "Чтобы внести изменения, подтвердите, что это вы.", "O‘zgartirish uchun bu siz ekanligingizni yana tasdiqlang."),
    "Could not read AI recommendations. Please retry.": (
        "Не удалось получить рекомендации ИИ. Попробуйте ещё раз.", "AI tavsiyalarini olib bo‘lmadi. Qayta urinib ko‘ring."),
    "Current password is incorrect.": ("Текущий пароль неверный.", "Joriy parol noto‘g‘ri."),
    "Daily limit for new voice clips reached.": (
        "Дневной лимит новых озвучек исчерпан.", "Yangi ovozli yozuvlar uchun kunlik limit tugadi."),
    "Email and password are required.": ("Введите почту и пароль.", "Elektron pochta va parolni kiriting."),
    "Email confirmed. Thank you.": ("Почта подтверждена. Спасибо!", "Elektron pochta tasdiqlandi. Rahmat!"),
    "Enter a valid email address.": ("Введите корректный адрес почты.", "To‘g‘ri elektron pochta manzilini kiriting."),
    "Enter a whole number of coins.": ("Введите целое число монет.", "Tangalar sonini butun son bilan kiriting."),
    "Every row must be an object.": ("Каждая строка должна быть объектом.", "Har bir qator obyekt bo‘lishi kerak."),
    "Expected a JSON object.": ("Ожидался JSON-объект.", "JSON obyekt kutilgan edi."),
    "Expected an object.": ("Ожидался объект.", "Obyekt kutilgan edi."),
    "Fix the questions first.": ("Сначала исправьте вопросы.", "Avval savollarni tuzating."),
    "If that address has an account, a letter with a link is on its way.": (
        "Если на этот адрес есть аккаунт, письмо со ссылкой уже в пути.",
        "Agar bu manzilda hisob bo‘lsa, havolali xat yo‘lda."),
    "If the details are valid, the account has been created. You can now sign in.": (
        "Если данные верны, аккаунт создан. Теперь можно войти.",
        "Agar ma’lumotlar to‘g‘ri bo‘lsa, hisob yaratildi. Endi kirishingiz mumkin."),
    "Invalid JSON.": ("Некорректный JSON.", "Noto‘g‘ri JSON."),
    "Invalid cost type.": ("Неверный тип расхода.", "Xarajat turi noto‘g‘ri."),
    "Invalid email or password.": ("Неверная почта или пароль.", "Elektron pochta yoki parol noto‘g‘ri."),
    "Invalid or expired access token.": ("Сессия недействительна или истекла.", "Sessiya yaroqsiz yoki muddati tugagan."),
    "Invalid product kind.": ("Неверный тип продукта.", "Mahsulot turi noto‘g‘ri."),
    "Invalid refresh token.": ("Сессия недействительна. Войдите снова.", "Sessiya yaroqsiz. Qayta kiring."),
    "Invalid stage or customer market.": ("Неверная стадия или рынок клиентов.", "Bosqich yoki mijozlar bozori noto‘g‘ri."),
    "Invalid stage, customer market or team size.": (
        "Неверная стадия, рынок клиентов или размер команды.", "Bosqich, mijozlar bozori yoki jamoa hajmi noto‘g‘ri."),
    "Accept the Terms and Privacy Policy and confirm your age to sign up.": ("Чтобы зарегистрироваться, примите Условия и Политику конфиденциальности и подтвердите возраст.", "Ro‘yxatdan o‘tish uchun Shartlar va Maxfiylik siyosatini qabul qiling hamda yoshingizni tasdiqlang."),
    "Type your email address to confirm.": ("Введите свой email для подтверждения.", "Tasdiqlash uchun emailingizni kiriting."),
    "For your safety, sign in again and then delete the account.": ("Ради безопасности войдите заново, а затем удалите аккаунт.", "Xavfsizlik uchun qaytadan kiring, keyin hisobni o‘chiring."),
    "Sign in with Google again, then open the panel within 15 minutes.": ("Войдите через Google заново и откройте панель в течение 15 минут.", "Google orqali qaytadan kiring va panelni 15 daqiqa ichida oching."),
    "Choose the language of this version: en, ru or uz.": ("Выберите язык этой версии: en, ru или uz.", "Ushbu versiya tilini tanlang: en, ru yoki uz."),
    "The lesson is too long to save.": ("Урок слишком длинный, чтобы его сохранить.", "Dars saqlash uchun juda uzun."),
    "The lesson cannot be empty.": ("Урок не может быть пустым.", "Dars bo‘sh bo‘lishi mumkin emas."),
    "Finish the startup questions first.": (
        "Сначала ответьте на вопросы о стартапе.", "Avval startap haqidagi savollarga javob bering."),
    "AI is not connected yet.": ("ИИ пока не подключён.", "AI hali ulanmagan."),
    'Enter the cash you have as a number.': (
        'Введите сумму денег числом.',
        'Pul miqdorini raqam bilan kiriting.'),
    'Choose how the business is registered.': (
        'Выберите, как зарегистрирован бизнес.',
        'Biznes qanday ro‘yxatdan o‘tganini tanlang.'),
    'Describe your income and expenses first.': (
        'Сначала опишите доходы и расходы.',
        'Avval daromad va xarajatlarni yozing.'),
    'No amounts were found in the text. Write them with numbers.': (
        'В тексте не нашлось сумм. Укажите их цифрами.',
        'Matnda summalar topilmadi. Ularni raqam bilan yozing.'),
    'Add your income and expenses first.': (
        'Сначала добавьте доходы и расходы.',
        'Avval daromad va xarajatlarni qo‘shing.'),
    'Enter how much cash the business has now.': (
        'Укажите, сколько денег у бизнеса сейчас.',
        'Biznesda hozir qancha pul borligini kiriting.'),
    'Enter the loan amount and the term in months.': (
        'Укажите сумму кредита и срок в месяцах.',
        'Kredit summasi va muddatini oylarda kiriting.'),
    "None of the banks' products fits this amount and term. Try a smaller amount or another term.": (
        'Ни один кредит банков не подходит под эту сумму и срок. Попробуйте меньшую сумму или другой срок.',
        'Bu summa va muddatga mos bank krediti yo‘q. Kamroq summa yoki boshqa muddatni sinab ko‘ring.'),
    'The AI could not finish this just now. Try again in a minute.': (
        'ИИ не смог закончить работу. Попробуйте через минуту.',
        'AI ishni tugata olmadi. Bir daqiqadan keyin qayta urinib ko‘ring.'),
    'This proposal was already decided.': (
        'По этому предложению уже принято решение.',
        'Bu taklif bo‘yicha qaror allaqachon qabul qilingan.'),
    'Choose approve or reject.': (
        'Выберите «одобрить» или «отклонить».',
        '«Tasdiqlash» yoki «rad etish»ni tanlang.'),
    "Too many requests. Please slow down and try again in a minute.": (
        "Слишком много запросов. Подождите минуту и попробуйте снова.",
        "So‘rovlar juda ko‘p. Bir daqiqa kutib, qayta urinib ko‘ring."),
    "Too many requests came from your network, so it is blocked for a while. Please try again later.": (
        "Из вашей сети пришло слишком много запросов, поэтому она временно заблокирована. Попробуйте позже.",
        "Tarmog‘ingizdan juda ko‘p so‘rov keldi, shuning uchun u vaqtincha bloklandi. Keyinroq urinib ko‘ring."),
    "This account is blocked. If you think this is a mistake, write to the Zinvest team.": (
        "Этот аккаунт заблокирован. Если это ошибка, напишите команде Zinvest.",
        "Bu hisob bloklangan. Agar bu xato bo‘lsa, Zinvest jamoasiga yozing."),
    "This ban is already lifted.": ("Эта блокировка уже снята.", "Bu bloklash allaqachon olib tashlangan."),
    "We sent a link to the new address. The email changes once you open it.": (
        "Мы отправили ссылку на новый адрес. Почта сменится, когда вы её откроете.",
        "Yangi manzilga havola yubordik. Uni ochganingizda pochta o‘zgaradi."),
    "Email changed. Sign in with the new address.": (
        "Почта изменена. Войдите с новым адресом.", "Pochta o‘zgartirildi. Yangi manzil bilan kiring."),
    "The question is too long. Please make it shorter.": (
        "Вопрос слишком длинный. Сократите его, пожалуйста.", "Savol juda uzun. Iltimos, qisqartiring."),
    "Finish the earlier steps first.": (
        "Сначала выполните предыдущие шаги.", "Avval oldingi qadamlarni bajaring."),
    "Only the latest finished step can be reopened.": (
        "Вернуть можно только последний выполненный шаг.", "Faqat oxirgi bajarilgan qadamni qaytarish mumkin."),
    "This step is no longer in the roadmap.": (
        "Этого шага уже нет в дорожной карте.", "Bu qadam endi yo‘l xaritasida yo‘q."),
    "The roadmap could not be built just now. Try again in a minute.": (
        "Сейчас не получилось построить дорожную карту. Попробуйте через минуту.",
        "Hozir yo‘l xaritasini tuzib bo‘lmadi. Bir daqiqadan keyin qayta urinib ko‘ring."),
    "done must be true or false.": ("Поле done должно быть true или false.", "done qiymati true yoki false bo‘lishi kerak."),
    "Please answer the questions.": ("Ответьте на вопросы.", "Savollarga javob bering."),
    "Please answer every required question.": (
        "Ответьте на все обязательные вопросы.", "Barcha majburiy savollarga javob bering."),
    "Letter sent.": ("Письмо отправлено.", "Xat yuborildi."),
    "Logged out.": ("Вы вышли из аккаунта.", "Hisobdan chiqdingiz."),
    "Malformed JSON body.": ("Некорректный JSON в запросе.", "So‘rovdagi JSON noto‘g‘ri."),
    "Malformed JSON.": ("Некорректный JSON.", "Noto‘g‘ri JSON."),
    "Message must contain 1–5000 characters.": (
        "Сообщение должно содержать от 1 до 5000 символов.", "Xabar 1 dan 5000 gacha belgidan iborat bo‘lishi kerak."),
    "Method not allowed.": ("Метод не поддерживается.", "Bu usulga ruxsat yo‘q."),
    "New email is required.": ("Введите новую почту.", "Yangi elektron pochtani kiriting."),
    "New password is required.": ("Введите новый пароль.", "Yangi parolni kiriting."),
    "No file uploaded.": ("Файл не загружен.", "Fayl yuklanmadi."),
    "No question to answer.": ("Нет вопроса для ответа.", "Javob beriladigan savol yo‘q."),
    "No refresh token.": ("Сессия не найдена. Войдите снова.", "Sessiya topilmadi. Qayta kiring."),
    "No rounds left today.": ("На сегодня раунды закончились.", "Bugungi raundlar tugadi."),
    "No such question or option.": ("Такого вопроса или варианта нет.", "Bunday savol yoki variant yo‘q."),
    "No such round or choice.": ("Такого раунда или варианта нет.", "Bunday raund yoki tanlov yo‘q."),
    "Nothing to report here.": ("Здесь не на что жаловаться.", "Bu yerda shikoyat qiladigan narsa yo‘q."),
    "Nothing was imported. Fix these rows and try again.": (
        "Ничего не импортировано. Исправьте эти строки и попробуйте снова.",
        "Hech narsa import qilinmadi. Bu qatorlarni tuzatib, qayta urinib ko‘ring."),
    "Only an owner can change a team account.": (
        "Изменить аккаунт команды может только владелец.", "Jamoa hisobini faqat ega o‘zgartira oladi."),
    "Only an owner can delete accounts.": ("Удалять аккаунты может только владелец.", "Hisoblarni faqat ega o‘chira oladi."),
    "Only an owner can disable a team account.": (
        "Отключить аккаунт команды может только владелец.", "Jamoa hisobini faqat ega faolsizlantira oladi."),
    "Only posts can be hidden.": ("Скрывать можно только публикации.", "Faqat postlarni yashirish mumkin."),
    "Only the recipient can accept.": ("Принять может только получатель.", "Faqat qabul qiluvchi qabul qila oladi."),
    "Pass mark must be a number.": ("Проходной балл должен быть числом.", "O‘tish bali son bo‘lishi kerak."),
    "Pass mark must be between 10% and 100%.": (
        "Проходной балл — от 10% до 100%.", "O‘tish bali 10% dan 100% gacha bo‘lishi kerak."),
    "Password does not meet requirements.": ("Пароль не соответствует требованиям.", "Parol talablarga javob bermaydi."),
    "Password is incorrect.": ("Неверный пароль.", "Parol noto‘g‘ri."),
    "Password updated. You can sign in now.": ("Пароль обновлён. Теперь можно войти.", "Parol yangilandi. Endi kirishingiz mumkin."),
    "Please answer all five questions.": (
        "Ответьте, пожалуйста, на все пять вопросов.", "Iltimos, barcha beshta savolga javob bering."),
    "Posting is paused by the Zinvest team for a moment.": (
        "Команда Zinvest ненадолго приостановила публикации.", "Zinvest jamoasi post joylashni biroz to‘xtatdi."),
    "Publish your founder profile before connecting.": (
        "Опубликуйте профиль основателя, прежде чем добавлять контакты.",
        "Bog‘lanishdan oldin asoschi profilingizni e’lon qiling."),
    "Publish your founder profile first.": (
        "Сначала опубликуйте профиль основателя.", "Avval asoschi profilingizni e’lon qiling."),
    "Recommendations are temporarily unavailable.": ("Рекомендации временно недоступны.", "Tavsiyalar vaqtincha mavjud emas."),
    "Refresh token expired.": ("Сессия истекла. Войдите снова.", "Sessiya muddati tugadi. Qayta kiring."),
    "Refresh token reuse detected; session revoked.": (
        "Сессия отозвана из соображений безопасности. Войдите снова.",
        "Xavfsizlik uchun sessiya bekor qilindi. Qayta kiring."),
    "Resolve or dismiss the report.": ("Решите или отклоните жалобу.", "Shikoyatni hal qiling yoki rad eting."),
    "Say why (it goes to the audit log).": (
        "Укажите причину (она попадёт в журнал аудита).", "Sababini yozing (u audit jurnaliga tushadi)."),
    "Say why the account is disabled (staff see it later).": (
        "Укажите, почему аккаунт отключён (сотрудники увидят это позже).",
        "Hisob nega o‘chirilganini yozing (xodimlar keyin ko‘radi)."),
    "Say why the post is hidden.": ("Укажите, почему публикация скрыта.", "Post nega yashirilganini yozing."),
    "Server auth misconfiguration.": ("Ошибка настройки авторизации на сервере.", "Serverda avtorizatsiya sozlamasi xato."),
    "Session not found.": ("Сессия не найдена.", "Sessiya topilmadi."),
    "Session was signed out. Please sign in again.": ("Сессия завершена. Войдите снова.", "Sessiya yakunlandi. Qayta kiring."),
    "Sign-ups are paused right now. Please try again later.": (
        "Регистрация сейчас приостановлена. Попробуйте позже.",
        "Ro‘yxatdan o‘tish hozir to‘xtatilgan. Keyinroq urinib ko‘ring."),
    "Start the setup again.": ("Начните настройку заново.", "Sozlashni qaytadan boshlang."),
    "Superusers are removed on the server.": ("Суперпользователей удаляют на сервере.", "Superfoydalanuvchilar serverda o‘chiriladi."),
    "Text is required.": ("Нужен текст.", "Matn kiriting."),
    "Thanks. The team will take a look.": ("Спасибо. Команда посмотрит.", "Rahmat. Jamoa ko‘rib chiqadi."),
    "That code does not match. Check the time on your phone and try again.": (
        "Код не подходит. Проверьте время на телефоне и попробуйте снова.",
        "Kod mos kelmadi. Telefoningizdagi vaqtni tekshirib, qayta urinib ko‘ring."),
    "That email cannot be used.": ("Эту почту использовать нельзя.", "Bu elektron pochtadan foydalanib bo‘lmaydi."),
    "The Telegram bot is not configured.": ("Telegram-бот не настроен.", "Telegram bot sozlanmagan."),
    "The admin panel is for the Zinvest team.": ("Админ-панель — только для команды Zinvest.", "Admin panel faqat Zinvest jamoasi uchun."),
    "The file has no rows to import.": ("В файле нет строк для импорта.", "Faylda import qilinadigan qatorlar yo‘q."),
    "The file is larger than 2 MB.": ("Файл больше 2 МБ.", "Fayl 2 MB dan katta."),
    "The limit must be a whole number.": ("Лимит должен быть целым числом.", "Limit butun son bo‘lishi kerak."),
    "The limit must be between 0 and 100 000 000 tokens.": (
        "Лимит — от 0 до 100 000 000 токенов.", "Limit 0 dan 100 000 000 tokengacha bo‘lishi kerak."),
    "The server voice is not available.": ("Серверная озвучка недоступна.", "Server ovozi mavjud emas."),
    "The server voice is not configured.": ("Серверная озвучка не настроена.", "Server ovozi sozlanmagan."),
    "This account is a superuser; change it on the server.": (
        "Это суперпользователь — меняйте его на сервере.", "Bu superfoydalanuvchi — uni serverda o‘zgartiring."),
    "This address is already confirmed.": ("Этот адрес уже подтверждён.", "Bu manzil allaqachon tasdiqlangan."),
    "This link is invalid or has expired. Ask for a new one.": (
        "Ссылка недействительна или устарела. Запросите новую.", "Havola yaroqsiz yoki eskirgan. Yangisini so‘rang."),
    "This report has no account attached.": ("К этой жалобе не привязан аккаунт.", "Bu shikoyatga hisob biriktirilmagan."),
    "This unit is locked.": ("Этот раздел пока закрыт.", "Bu bo‘lim hozircha yopiq."),
    "Title: 1-120 characters.": ("Название: от 1 до 120 символов.", "Sarlavha: 1 dan 120 gacha belgi."),
    "Title: 1-140 characters.": ("Название: от 1 до 140 символов.", "Sarlavha: 1 dan 140 gacha belgi."),
    "Title: 1–120 characters. Description: up to 5000.": (
        "Название: от 1 до 120 символов. Описание: до 5000.", "Sarlavha: 1 dan 120 gacha belgi. Tavsif: 5000 gacha."),
    "Too many attempts. Please try again later.": (
        "Слишком много попыток. Попробуйте позже.", "Juda ko‘p urinish. Keyinroq qayta urinib ko‘ring."),
    "Too many downloads. Try again in an hour.": (
        "Слишком много скачиваний. Попробуйте через час.", "Juda ko‘p yuklab olish. Bir soatdan keyin urinib ko‘ring."),
    "Too many failed attempts. Please try again later.": (
        "Слишком много неудачных попыток. Попробуйте позже.", "Juda ko‘p muvaffaqiyatsiz urinish. Keyinroq qayta urinib ko‘ring."),
    "Too many sign-ups from this network. Please try again later.": (
        "Слишком много регистраций из этой сети. Попробуйте позже.",
        "Bu tarmoqdan juda ko‘p ro‘yxatdan o‘tildi. Keyinroq urinib ko‘ring."),
    "Too many wrong attempts. Try again in 15 minutes.": (
        "Слишком много неверных попыток. Попробуйте через 15 минут.",
        "Juda ko‘p noto‘g‘ri urinish. 15 daqiqadan keyin qayta urinib ko‘ring."),
    "Turn on two-factor sign-in first.": ("Сначала включите двухфакторный вход.", "Avval ikki bosqichli kirishni yoqing."),
    "Two-factor sign-in is already on.": ("Двухфакторный вход уже включён.", "Ikki bosqichli kirish allaqachon yoqilgan."),
    "Type the account's email to confirm.": (
        "Для подтверждения введите почту аккаунта.", "Tasdiqlash uchun hisobning elektron pochtasini kiriting."),
    "Unknown action.": ("Неизвестное действие.", "Noma’lum amal."),
    "Unknown plan.": ("Неизвестный тариф.", "Noma’lum tarif."),
    "Unknown report target.": ("Неизвестный объект жалобы.", "Shikoyat obyekti noma’lum."),
    "Unknown role.": ("Неизвестная роль.", "Noma’lum rol."),
    "Unknown theme.": ("Неизвестная тема оформления.", "Noma’lum mavzu."),
    "Upload PNG, JPEG, GIF or WebP.": ("Загрузите PNG, JPEG, GIF или WebP.", "PNG, JPEG, GIF yoki WebP yuklang."),
    "Upload a PNG, JPEG, GIF or WebP image.": (
        "Загрузите изображение PNG, JPEG, GIF или WebP.", "PNG, JPEG, GIF yoki WebP rasm yuklang."),
    "Use a valid date (YYYY-MM-DD).": ("Укажите дату в формате ГГГГ-ММ-ДД.", "Sanani YYYY-MM-DD formatida kiriting."),
    "Use a valid month (YYYY-MM).": ("Укажите месяц в формате ГГГГ-ММ.", "Oyni YYYY-MM formatida kiriting."),
    "Use log out to end the current session.": (
        "Чтобы завершить текущую сессию, нажмите «Выйти».", "Joriy sessiyani yakunlash uchun «Chiqish»ni bosing."),
    "Use your own settings for your account.": (
        "Свой аккаунт меняйте в собственных настройках.", "O‘z hisobingizni shaxsiy sozlamalarda o‘zgartiring."),
    "User not found or inactive.": ("Пользователь не найден или отключён.", "Foydalanuvchi topilmadi yoki faol emas."),
    "Voice service error.": ("Ошибка сервиса озвучки.", "Ovoz xizmatida xatolik."),
    "Wrong or expired code from the authenticator app.": (
        "Неверный или устаревший код из приложения-аутентификатора.",
        "Autentifikator ilovasidagi kod noto‘g‘ri yoki eskirgan."),
    "Wrong password.": ("Неверный пароль.", "Parol noto‘g‘ri."),
    "You are doing that too often. Please wait a little.": ("Слишком часто. Подождите немного.", "Juda tez-tez. Biroz kuting."),
    "You can view announcements but not publish them.": (
        "Вы можете просматривать объявления, но не публиковать их.",
        "E’lonlarni ko‘rishingiz mumkin, lekin e’lon qila olmaysiz."),
    "You cannot change platform settings.": ("Вы не можете менять настройки платформы.", "Platforma sozlamalarini o‘zgartira olmaysiz."),
    "You cannot reset your own two-factor here.": (
        "Свой двухфакторный вход здесь сбросить нельзя.",
        "O‘zingizning ikki bosqichli kirishingizni bu yerda tiklab bo‘lmaydi."),
    "You have sent a lot of reports today. The team will get to them.": (
        "Сегодня вы отправили много жалоб. Команда их рассмотрит.",
        "Bugun ko‘p shikoyat yubordingiz. Jamoa ularni ko‘rib chiqadi."),
    "amount must be a non-negative number.": (
        "Сумма должна быть неотрицательным числом.", "Summa manfiy bo‘lmagan son bo‘lishi kerak."),
    "brand_color must be a #RRGGBB value.": (
        "Цвет бренда должен быть в формате #RRGGBB.", "Brend rangi #RRGGBB formatida bo‘lishi kerak."),
    "content must be a string.": ("Содержимое должно быть строкой.", "Mazmun matn bo‘lishi kerak."),
    "entry_type must be 'revenue' or 'spending'.": (
        "Тип записи — «доход» или «расход».", "Yozuv turi — «daromad» yoki «xarajat»."),
    "full_name cannot be empty.": ("Имя не может быть пустым.", "Ism bo‘sh bo‘lishi mumkin emas."),
    "full_name is required.": ("Укажите имя.", "Ismni kiriting."),
    "kind must be product, service or subscription.": (
        "Тип — товар, услуга или подписка.", "Turi — mahsulot, xizmat yoki obuna."),
    "name cannot be empty.": ("Название не может быть пустым.", "Nom bo‘sh bo‘lishi mumkin emas."),
    "name is required.": ("Укажите название.", "Nomni kiriting."),
    "order must be an integer.": ("Порядок должен быть целым числом.", "Tartib butun son bo‘lishi kerak."),
    "price must be a non-negative number.": ("Цена должна быть неотрицательным числом.", "Narx manfiy bo‘lmagan son bo‘lishi kerak."),
    "profile must be an object.": ("Профиль должен быть объектом.", "Profil obyekt bo‘lishi kerak."),
    "quiz must be a list.": ("Ответы теста должны быть списком.", "Test javoblari ro‘yxat bo‘lishi kerak."),
    "raw_text is required.": ("Нужен текст описания.", "Tavsif matnini kiriting."),
    "salary must be a non-negative number.": (
        "Зарплата должна быть неотрицательным числом.", "Maosh manfiy bo‘lmagan son bo‘lishi kerak."),
    "target_score must be an integer.": ("Целевой балл должен быть целым числом.", "Maqsadli ball butun son bo‘lishi kerak."),
    "title cannot be empty.": ("Название не может быть пустым.", "Sarlavha bo‘sh bo‘lishi mumkin emas."),
    "title is required.": ("Укажите название.", "Sarlavhani kiriting."),
}

# Messages with a number or a name in them: English pattern → (Russian, Uzbek),
# the captured parts filled into {0}, {1}, …
PATTERNS = [
    (re.compile(r"^Image must be under (\S+)MB\.$"),
     ("Изображение должно быть меньше {0} МБ.", "Rasm {0} MB dan kichik bo‘lishi kerak.")),
    (re.compile(r"^Import up to (\d+) rows at a time\.$"),
     ("За раз можно импортировать до {0} строк.", "Bir martada {0} tagacha qator import qilish mumkin.")),
    (re.compile(r"^Text is longer than (\d+) characters\.$"),
     ("Текст длиннее {0} символов.", "Matn {0} belgidan uzun.")),
    (re.compile(r"^(\w+) must be a whole number\.$"),
     ("{0}: нужно целое число.", "{0}: butun son kerak.")),
    (re.compile(r"^(\w+) must be between (\S+) and (\S+)\.$"),
     ("{0}: от {1} до {2}.", "{0}: {1} dan {2} gacha.")),
]

_COLUMN = {"ru": 0, "uz": 1}


def translate(text, lang=None):
    """`text` in `lang` when we have it; otherwise unchanged (English)."""
    column = _COLUMN.get(languages.normalize(lang) or languages.current())
    if column is None or not isinstance(text, str):
        return text
    pair = EXACT.get(text)
    if pair:
        return pair[column]
    for pattern, pair in PATTERNS:
        match = pattern.match(text)
        if match:
            return pair[column].format(*match.groups())
    return text


class TranslateMessagesMiddleware:
    """
    Translates `detail` in JSON responses into the request's language. Sits
    inside LanguageMiddleware, so the language is already current here. Big
    bodies are left alone: a message is a small object, a payload is not.
    """

    MAX_BYTES = 64 * 1024

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if languages.current() == languages.BASE or getattr(response, "streaming", False):
            return response
        if not response.get("Content-Type", "").startswith("application/json"):
            return response
        body = response.content
        if b'"detail"' not in body or len(body) > self.MAX_BYTES:
            return response
        try:
            data = json.loads(body)
        except ValueError:
            return response
        if not isinstance(data, dict) or not isinstance(data.get("detail"), str):
            return response
        translated = translate(data["detail"])
        if translated != data["detail"]:
            data["detail"] = translated
            response.content = json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False).encode("utf-8")
            if response.has_header("Content-Length"):
                response["Content-Length"] = str(len(response.content))
        return response
