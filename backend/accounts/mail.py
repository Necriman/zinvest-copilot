"""
The letters Zinvest sends: the six-digit code that finishes a sign-in or a
sign-up, the note that an address already has an account, confirm your
address, move the account to a new address (and tell the old one), and
reset your password.

Sending never blocks the request that triggered it — a dead SMTP server must
not turn a sign-up into a 500, and it must not change the answer either (that
would tell an attacker which addresses exist). Failures are logged and life
goes on. With no EMAIL_HOST configured, Django's console backend prints the
letter, which is what happens in local development.

Letters go out in the language the app was in when the request was made
(``lang``), falling back to Russian.
"""
import logging
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

logger = logging.getLogger(__name__)

LANGS = ("ru", "en", "uz")

TEXTS = {
    "verify": {
        "subject": {
            "ru": "Подтвердите почту в Zinvest",
            "en": "Confirm your email for Zinvest",
            "uz": "Zinvest uchun pochtangizni tasdiqlang",
        },
        "heading": {"ru": "Почти всё", "en": "Almost there", "uz": "Deyarli tayyor"},
        "body": {
            "ru": "Подтвердите адрес — тогда мы сможем вернуть вам доступ, если пароль забудется.",
            "en": "Confirm this address so we can get you back in if you ever lose your password.",
            "uz": "Manzilni tasdiqlang — parolni unutsangiz, hisobingizni tiklay olamiz.",
        },
        "button": {"ru": "Подтвердить почту", "en": "Confirm email", "uz": "Pochtani tasdiqlash"},
        "ignore": {
            "ru": "Если вы не регистрировались в Zinvest, просто удалите это письмо.",
            "en": "If you did not sign up for Zinvest, just delete this letter.",
            "uz": "Agar Zinvestda ro‘yxatdan o‘tmagan bo‘lsangiz, bu xatni o‘chiring.",
        },
    },
    # To the NEW address: the account moves to it only once this link is opened.
    "change": {
        "subject": {
            "ru": "Подтвердите новую почту для Zinvest",
            "en": "Confirm your new email for Zinvest",
            "uz": "Zinvest uchun yangi pochtani tasdiqlang",
        },
        "heading": {"ru": "Новая почта", "en": "A new email", "uz": "Yangi pochta"},
        "body": {
            "ru": "Нажмите кнопку — и вход в Zinvest переедет на этот адрес. Ссылка работает {hours} ч.",
            "en": "Open the link and your Zinvest sign-in moves to this address. It works for {hours} hour(s).",
            "uz": "Havolani oching — Zinvestga kirish shu manzilga o‘tadi. U {hours} soat ishlaydi.",
        },
        "button": {"ru": "Подтвердить новую почту", "en": "Confirm the new email", "uz": "Yangi pochtani tasdiqlash"},
        "ignore": {
            "ru": "Если вы ничего не меняли, просто удалите письмо — без этой ссылки ничего не изменится.",
            "en": "If you did not ask for this, just delete the letter: nothing changes without this link.",
            "uz": "Agar hech narsani o‘zgartirmagan bo‘lsangiz, xatni o‘chiring: bu havolasiz hech narsa o‘zgarmaydi.",
        },
    },
    # To the OLD address, when someone asks to move the account away from it.
    "change_requested": {
        "subject": {
            "ru": "Кто-то хочет сменить почту вашего аккаунта Zinvest",
            "en": "Someone asked to change your Zinvest email",
            "uz": "Kimdir Zinvest hisobingiz pochtasini o‘zgartirmoqchi",
        },
        "heading": {"ru": "Смена почты", "en": "Email change", "uz": "Pochtani o‘zgartirish"},
        "body": {
            "ru": "Запрошен переезд аккаунта на адрес {new}. Он произойдёт, только если по ссылке из письма на новый адрес перейдут.",
            "en": "Someone asked to move your account to {new}. It only happens once the link sent to that address is opened.",
            "uz": "Hisobingizni {new} manziliga o‘tkazish so‘raldi. Bu faqat yangi manzilga yuborilgan havola ochilganda amalga oshadi.",
        },
        "button": {"ru": "Это не я — сменить пароль", "en": "Not me: reset my password", "uz": "Bu men emas — parolni tiklash"},
        "ignore": {
            "ru": "Если это вы, ничего делать не нужно.",
            "en": "If this was you, there is nothing to do.",
            "uz": "Agar bu siz bo‘lsangiz, hech narsa qilish shart emas.",
        },
    },
    # To the OLD address, once the move is done.
    "changed": {
        "subject": {
            "ru": "Почта аккаунта Zinvest изменена",
            "en": "Your Zinvest email was changed",
            "uz": "Zinvest hisobingiz pochtasi o‘zgartirildi",
        },
        "heading": {"ru": "Почта изменена", "en": "Email changed", "uz": "Pochta o‘zgartirildi"},
        "body": {
            "ru": "Теперь вход в Zinvest — по адресу {new}. Все сессии завершены.",
            "en": "You now sign in to Zinvest with {new}. Every session was signed out.",
            "uz": "Endi Zinvestga {new} orqali kirasiz. Barcha seanslar yakunlandi.",
        },
        "button": {"ru": "Это не я — написать нам", "en": "Not me: contact us", "uz": "Bu men emas — bizga yozing"},
        "ignore": {
            "ru": "Если это вы, ничего делать не нужно.",
            "en": "If this was you, there is nothing to do.",
            "uz": "Agar bu siz bo‘lsangiz, hech narsa qilish shart emas.",
        },
    },
    "reset": {
        "subject": {
            "ru": "Восстановление пароля Zinvest",
            "en": "Reset your Zinvest password",
            "uz": "Zinvest parolini tiklash",
        },
        "heading": {"ru": "Новый пароль", "en": "A new password", "uz": "Yangi parol"},
        "body": {
            "ru": "Нажмите кнопку и придумайте новый пароль. Ссылка работает один раз и только {hours} ч.",
            "en": "Open the link and pick a new password. It works once, and only for {hours} hour(s).",
            "uz": "Havolani oching va yangi parol o‘ylab toping. U bir marta va faqat {hours} soat ishlaydi.",
        },
        "button": {"ru": "Задать новый пароль", "en": "Set a new password", "uz": "Yangi parol qo‘yish"},
        "ignore": {
            "ru": "Если вы не просили сбросить пароль, ничего делать не нужно — пароль останется прежним.",
            "en": "If you did not ask for this, do nothing — your password stays as it is.",
            "uz": "Agar buni so‘ramagan bo‘lsangiz, hech narsa qilmang — parolingiz o‘zgarmaydi.",
        },
    },
}

CODE_TEXTS = {
    "subject": {
        "ru": "{code} — ваш код для Zinvest",
        "en": "{code} is your Zinvest code",
        "uz": "{code} — Zinvest uchun kodingiz",
    },
    "heading": {
        "login": {"ru": "Код для входа", "en": "Your sign-in code", "uz": "Kirish kodi"},
        "register": {"ru": "Код для регистрации", "en": "Your sign-up code", "uz": "Ro‘yxatdan o‘tish kodi"},
    },
    "body": {
        "ru": "Введите этот код на странице Zinvest. Он действует {minutes} минут.",
        "en": "Enter this code on the Zinvest page. It works for {minutes} minutes.",
        "uz": "Bu kodni Zinvest sahifasiga kiriting. U {minutes} daqiqa amal qiladi.",
    },
    "ignore": {
        "ru": "Если это были не вы, просто удалите письмо. Без кода в аккаунт никто не войдёт.",
        "en": "If this was not you, delete this letter. Nobody gets in without the code.",
        "uz": "Agar bu siz bo‘lmasangiz, xatni o‘chiring. Kodsiz hech kim hisobga kira olmaydi.",
    },
}

EXISTS_TEXTS = {
    "subject": {
        "ru": "У вас уже есть аккаунт Zinvest",
        "en": "You already have a Zinvest account",
        "uz": "Sizda allaqachon Zinvest hisobi bor",
    },
    "heading": {"ru": "Аккаунт уже есть", "en": "The account already exists", "uz": "Hisob allaqachon bor"},
    "body": {
        "ru": "Кто-то попробовал зарегистрироваться с этим адресом. Если это вы, просто войдите. Забыли пароль? Его можно восстановить на странице входа.",
        "en": "Someone tried to sign up with this address. If it was you, just sign in. Forgot the password? You can reset it on the sign-in page.",
        "uz": "Kimdir shu manzil bilan ro‘yxatdan o‘tmoqchi bo‘ldi. Agar bu siz bo‘lsangiz, shunchaki kiring. Parolni unutdingizmi? Uni kirish sahifasida tiklash mumkin.",
    },
    "button": {"ru": "Войти", "en": "Sign in", "uz": "Kirish"},
    "ignore": {
        "ru": "Если это были не вы, ничего делать не нужно.",
        "en": "If this was not you, there is nothing to do.",
        "uz": "Agar bu siz bo‘lmasangiz, hech narsa qilish shart emas.",
    },
}

FOOTER = {
    "ru": "Это служебное письмо об аккаунте: такие приходят, только когда вы сами входите или меняете данные, рассылок мы не делаем. Отвечать на него не нужно.",
    "en": "This is a service letter about your account: these come only when you sign in or change your details yourself, and we send no newsletters. There is no need to reply.",
    "uz": "Bu hisobingiz haqidagi xizmat xati: bunday xatlar faqat o‘zingiz kirganingizda yoki ma’lumotlarni o‘zgartirganingizda keladi, biz axborot xatlari yubormaymiz. Javob yozish shart emas.",
}
FOOTER_LINKS = {
    "ru": ("Настройки аккаунта", "Конфиденциальность"),
    "en": ("Account settings", "Privacy"),
    "uz": ("Hisob sozlamalari", "Maxfiylik"),
}


def _footer_plain(lang):
    """The footer for the text part: the note, then where to manage the account."""
    settings_label, privacy_label = FOOTER_LINKS[lang]
    origin = settings.APP_ORIGIN
    return f"{FOOTER[lang]}\n{settings_label}: {origin}/app/settings\n{privacy_label}: {origin}/legal/privacy"


def _footer_html(lang):
    """The same for the HTML part, already escaped."""
    settings_label, privacy_label = FOOTER_LINKS[lang]
    origin = escape(settings.APP_ORIGIN)
    link = "color:#5b3bb8;text-decoration:underline"
    return (
        f"{escape(FOOTER[lang])}<br><br>"
        f'<a href="{origin}/app/settings" style="{link}">{escape(settings_label)}</a> · '
        f'<a href="{origin}/legal/privacy" style="{link}">{escape(privacy_label)}</a>'
    )


def pick_lang(value):
    value = str(value or "").lower()[:2]
    return value if value in LANGS else "ru"


def _html(heading, body, button_label, url, ignore, footer):
    """One small, inline-styled letter — mail clients strip <style> blocks."""
    return f"""\
<!doctype html>
<html><body style="margin:0;padding:24px;background:#f4f4f7;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#0f172a">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:16px;padding:32px">
      <tr><td style="font-size:20px;font-weight:800;letter-spacing:-0.02em;padding-bottom:8px">Zinvest</td></tr>
      <tr><td style="font-size:22px;font-weight:800;letter-spacing:-0.02em;padding-bottom:8px">{escape(heading)}</td></tr>
      <tr><td style="font-size:15px;line-height:1.6;color:#475569;padding-bottom:24px">{escape(body)}</td></tr>
      <tr><td style="padding-bottom:24px">
        <a href="{escape(url)}" style="display:inline-block;background:#6943cc;color:#ffffff;text-decoration:none;font-weight:700;font-size:15px;padding:12px 22px;border-radius:999px">{escape(button_label)}</a>
      </td></tr>
      <tr><td style="font-size:13px;line-height:1.6;color:#64748b;word-break:break-all;padding-bottom:16px">{escape(url)}</td></tr>
      <tr><td style="font-size:13px;line-height:1.6;color:#64748b">{escape(ignore)}</td></tr>
      <tr><td style="font-size:12px;line-height:1.6;color:#64748b;padding-top:24px">{footer}</td></tr>
    </table>
  </td></tr></table>
</body></html>"""


def _send(kind, to, url, lang, **format_args):
    lang = pick_lang(lang)
    texts = TEXTS[kind]
    subject = texts["subject"][lang]
    heading = texts["heading"][lang]
    body = texts["body"][lang].format(**format_args)
    button = texts["button"][lang]
    ignore = texts["ignore"][lang]
    plain = f"{heading}\n\n{body}\n\n{url}\n\n{ignore}\n\n{_footer_plain(lang)}"
    try:
        message = EmailMultiAlternatives(subject, plain, settings.DEFAULT_FROM_EMAIL, [to])
        message.attach_alternative(_html(heading, body, button, url, ignore, _footer_html(lang)), "text/html")
        message.send(fail_silently=False)
        return True
    except Exception:  # noqa: BLE001 — any mail failure, the caller must not care
        logger.exception("could not send the %s letter to %s", kind, to)
        return False


def _code_html(heading, body, code, ignore, footer):
    """The code letter: the six digits large enough to read across a room."""
    return f"""\
<!doctype html>
<html><body style="margin:0;padding:24px;background:#f4f4f7;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#0f172a">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:16px;padding:32px">
      <tr><td style="font-size:20px;font-weight:800;letter-spacing:-0.02em;padding-bottom:8px">Zinvest</td></tr>
      <tr><td style="font-size:22px;font-weight:800;letter-spacing:-0.02em;padding-bottom:8px">{escape(heading)}</td></tr>
      <tr><td style="font-size:15px;line-height:1.6;color:#475569;padding-bottom:20px">{escape(body)}</td></tr>
      <tr><td style="padding-bottom:24px">
        <div style="display:inline-block;background:#f5f1fd;border-radius:14px;padding:14px 22px;font-family:SFMono-Regular,Consolas,Menlo,monospace;font-size:34px;font-weight:700;letter-spacing:10px;color:#34216a">{escape(code)}</div>
      </td></tr>
      <tr><td style="font-size:13px;line-height:1.6;color:#64748b">{escape(ignore)}</td></tr>
      <tr><td style="font-size:12px;line-height:1.6;color:#64748b;padding-top:24px">{footer}</td></tr>
    </table>
  </td></tr></table>
</body></html>"""


def _deliver(subject, plain, html, to, kind):
    try:
        message = EmailMultiAlternatives(subject, plain, settings.DEFAULT_FROM_EMAIL, [to])
        message.attach_alternative(html, "text/html")
        message.send(fail_silently=False)
        return True
    except Exception:  # noqa: BLE001 — any mail failure, the caller must not care
        logger.exception("could not send the %s letter to %s", kind, to)
        return False


def send_code(to, code, purpose="login", lang="ru", minutes=10):
    lang = pick_lang(lang)
    subject = CODE_TEXTS["subject"][lang].format(code=code)
    heading = CODE_TEXTS["heading"].get(purpose, CODE_TEXTS["heading"]["login"])[lang]
    body = CODE_TEXTS["body"][lang].format(minutes=minutes)
    ignore = CODE_TEXTS["ignore"][lang]
    plain = f"{heading}\n\n{code}\n\n{body}\n\n{ignore}\n\n{_footer_plain(lang)}"
    return _deliver(subject, plain, _code_html(heading, body, code, ignore, _footer_html(lang)), to, "code")


def send_account_exists(to, url, lang="ru"):
    lang = pick_lang(lang)
    t = EXISTS_TEXTS
    plain = f"{t['heading'][lang]}\n\n{t['body'][lang]}\n\n{url}\n\n{t['ignore'][lang]}\n\n{_footer_plain(lang)}"
    html = _html(t["heading"][lang], t["body"][lang], t["button"][lang], url, t["ignore"][lang], _footer_html(lang))
    return _deliver(t["subject"][lang], plain, html, to, "exists")


def send_verification(to, url, lang="ru"):
    return _send("verify", to, url, lang)


def send_password_reset(to, url, lang="ru", hours=1):
    return _send("reset", to, url, lang, hours=hours)


def send_email_change(to, url, lang="ru", hours=48):
    """To the new address: the link that moves the account to it."""
    return _send("change", to, url, lang, hours=hours)


def send_email_change_requested(to, new, lang="ru"):
    """To the old address: someone asked to move the account (``new`` is masked)."""
    return _send("change_requested", to, f"{settings.APP_ORIGIN}/forgot-password", lang, new=new)


def send_email_changed(to, new, lang="ru"):
    """To the old address: the account has moved (``new`` is masked)."""
    return _send("changed", to, f"mailto:{parseaddr(settings.DEFAULT_FROM_EMAIL)[1]}", lang, new=new)
