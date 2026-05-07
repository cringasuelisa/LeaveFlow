"""Modele pentru aplicatia LeaveFlow.

Contine:
- CustomUser: utilizator extins cu rol (employee/manager/admin)
- LeaveRequest: cererea de concediu
- Signature: semnatura managerului care aproba (Cloudinary)
"""
from datetime import date

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.urls import reverse
from django.utils import timezone


def _attachment_storage():
    """Storage pentru atasamente (PDF/DOCX) - raw resource pe Cloudinary."""
    from django.conf import settings
    if getattr(settings, "CLOUDINARY_STORAGE", {}).get("CLOUD_NAME"):
        from cloudinary_storage.storage import RawMediaCloudinaryStorage
        return RawMediaCloudinaryStorage()
    return FileSystemStorage()


def _signature_storage():
    """Storage pentru semnaturi - image resource pe Cloudinary."""
    from django.conf import settings
    if getattr(settings, "CLOUDINARY_STORAGE", {}).get("CLOUD_NAME"):
        from cloudinary_storage.storage import MediaCloudinaryStorage
        return MediaCloudinaryStorage()
    return FileSystemStorage()


# ---------------------------------------------------------------------------
# Utilizator
# ---------------------------------------------------------------------------
class CustomUser(AbstractUser):
    """Utilizator extins cu rol (angajat / manager / admin)."""

    class Role(models.TextChoices):
        EMPLOYEE = "employee", "Angajat"
        MANAGER = "manager", "Manager"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        verbose_name="Rol",
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Departament",
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Telefon",
    )

    class Meta:
        verbose_name = "Utilizator"
        verbose_name_plural = "Utilizatori"

    @property
    def is_employee(self) -> bool:
        return self.role == self.Role.EMPLOYEE

    @property
    def is_manager(self) -> bool:
        return self.role == self.Role.MANAGER

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN

    def __str__(self) -> str:
        full = self.get_full_name()
        return full or self.username


# ---------------------------------------------------------------------------
# Cerere concediu
# ---------------------------------------------------------------------------
class LeaveRequest(models.Model):
    """Cerere de concediu trimisa de un angajat."""

    class LeaveType(models.TextChoices):
        ANNUAL = "annual", "Concediu de odihna"
        MEDICAL = "medical", "Concediu medical"
        UNPAID = "unpaid", "Concediu fara plata"
        STUDY = "study", "Concediu de studii"
        MATERNITY = "maternity", "Concediu maternitate / paternitate"
        SPECIAL = "special", "Concediu pentru evenimente speciale"

    class Status(models.TextChoices):
        PENDING = "pending", "In asteptare"
        APPROVED = "approved", "Aprobata"
        REJECTED = "rejected", "Respinsa"

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leave_requests",
        verbose_name="Angajat",
    )
    leave_type = models.CharField(
        max_length=20,
        choices=LeaveType.choices,
        default=LeaveType.ANNUAL,
        verbose_name="Tip concediu",
    )
    start_date = models.DateField(verbose_name="Data inceput")
    end_date = models.DateField(verbose_name="Data sfarsit")
    days = models.PositiveIntegerField(
        default=0,
        verbose_name="Numar zile",
        help_text="Calculat automat la salvare.",
    )
    reason = models.TextField(verbose_name="Motiv")

    attachment = models.FileField(
        upload_to="leaves/attachments/",
        storage=_attachment_storage,
        blank=True,
        null=True,
        verbose_name="Atasament justificativ (optional)",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status",
    )

    # Cine a luat decizia + cand + motiv (pentru respingere sau nota la aprobare)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_requests",
        verbose_name="Decis de",
    )
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name="Data deciziei")
    decision_note = models.TextField(
        blank=True,
        verbose_name="Nota decizie",
        help_text="Motivul respingerii sau orice observatii la aprobare.",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creata la")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Actualizata la")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Cerere de concediu"
        verbose_name_plural = "Cereri de concediu"

    def __str__(self) -> str:
        return f"Cerere #{self.pk} - {self.employee} ({self.get_status_display()})"

    def get_absolute_url(self) -> str:
        return reverse("leave_detail", kwargs={"pk": self.pk})

    # ------------------------------------------------------------------
    # Logica
    # ------------------------------------------------------------------
    def calculate_days(self) -> int:
        """Numarul de zile calendaristice incluse in interval (inclusiv ambele capete)."""
        if not self.start_date or not self.end_date:
            return 0
        delta = (self.end_date - self.start_date).days + 1
        return max(delta, 0)

    def save(self, *args, **kwargs):
        # recalculam zilele de fiecare data, ca sa fie mereu corecte
        self.days = self.calculate_days()
        super().save(*args, **kwargs)

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def is_approved(self) -> bool:
        return self.status == self.Status.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.status == self.Status.REJECTED

    def mark_approved(self, manager, note: str = "") -> None:
        self.status = self.Status.APPROVED
        self.decided_by = manager
        self.decided_at = timezone.now()
        self.decision_note = note
        self.save()

    def mark_rejected(self, manager, note: str = "") -> None:
        self.status = self.Status.REJECTED
        self.decided_by = manager
        self.decided_at = timezone.now()
        self.decision_note = note
        self.save()


# ---------------------------------------------------------------------------
# Semnatura manager
# ---------------------------------------------------------------------------
class Signature(models.Model):
    """Semnatura adaugata de manager la aprobarea unei cereri.

    Imaginea poate veni:
    - prin upload (input file)
    - prin canvas HTML5 (frontend trimite un PNG codificat base64 -> convertim)
    """

    leave_request = models.OneToOneField(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="signature",
        verbose_name="Cerere",
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="signatures",
        verbose_name="Manager",
    )
    image = models.ImageField(
        upload_to="leaves/signatures/",
        storage=_signature_storage,
        verbose_name="Imagine semnatura",
        help_text="Stocata in Cloudinary in productie.",
    )
    signed_at = models.DateTimeField(auto_now_add=True, verbose_name="Semnata la")

    class Meta:
        verbose_name = "Semnatura"
        verbose_name_plural = "Semnaturi"

    def __str__(self) -> str:
        return f"Semnatura cererea #{self.leave_request_id} de {self.manager}"
