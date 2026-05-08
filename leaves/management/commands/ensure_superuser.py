"""Creeaza un superuser idempotent, citind credentialele din variabile de mediu."""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creeaza un superuser daca nu exista (foloseste DJANGO_SUPERUSER_*)."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                "DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD lipsesc; sar peste."
            ))
            return

        existing = User.objects.filter(username=username).first()
        if existing:
            updates = []
            if not existing.is_superuser:
                existing.is_superuser = True
                updates.append("is_superuser")
            if not existing.is_staff:
                existing.is_staff = True
                updates.append("is_staff")
            if hasattr(existing, "role") and existing.role != "admin":
                existing.role = "admin"
                updates.append("role")
            if email and existing.email != email:
                existing.email = email
                updates.append("email")
            if updates:
                existing.save(update_fields=updates)
                self.stdout.write(self.style.SUCCESS(
                    f"Superuser '{username}' actualizat ({', '.join(updates)})."
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"Superuser '{username}' exista deja."
                ))
            return

        user = User.objects.create_superuser(username=username, email=email, password=password)
        if hasattr(user, "role"):
            user.role = "admin"
            user.save(update_fields=["role"])
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' creat."))
