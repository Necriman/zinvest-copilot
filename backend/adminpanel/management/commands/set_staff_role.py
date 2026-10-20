"""
Give someone a role in the admin panel (or take it away).

    python manage.py set_staff_role founder@zinvest.uz owner
    python manage.py set_staff_role helper@zinvest.uz support
    python manage.py set_staff_role former@zinvest.uz none

Roles: owner, admin, support, content, analyst. Use it for the first owner;
after that owners manage the team from the admin panel.
"""
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User

ROLES = {"owner", "admin", "support", "content", "analyst", "none"}


class Command(BaseCommand):
    help = "Set a user's admin panel role (owner, admin, support, content, analyst, none)."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("role", choices=sorted(ROLES))

    def handle(self, email, role, **options):
        user = User.objects.filter(email__iexact=email.strip()).first()
        if user is None:
            raise CommandError(f"No account with the email {email}.")
        user.staff_role = "" if role == "none" else role
        user.save(update_fields=["staff_role"])
        if role == "none":
            user.sudo_grants.all().delete()
        self.stdout.write(self.style.SUCCESS(f"{user.email}: {role}"))
