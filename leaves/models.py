"""Modele LeaveFlow: CustomUser, LeaveRequest, Signature."""
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.urls import reverse
from django.utils import timezone


def _attachment_storage():
    if getattr(settings, "CLOUDINARY_STORAGE", {}).get("CLOUD_NAME"):
        from cloudinary_storage.storage import RawMediaCloudinaryStorage
        return RawMediaCloudinaryStorage()
    return FileSystemStorage()


def _signature_storage():
    if getattr(settings, "CLOUDINARY_STORAGE", {}).get("CLOUD_NAME"):
        from cloudinary_storage.storage import MediaCloudinaryStorage
        return MediaCloudinaryStorage()
    return FileSystemStorage()


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = "employee", "Angajat"
        MANAGER = "manager", "Manager"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.EMPLOYEE,
        verbose_name="Rol",
    )
    department = models.CharField(max_length=100, blank=True, verbose_name="Departament")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Telefon")

    class Meta:
        verbose_name = "Utilizator"
        verbose_name_plural = "Utilizatori"

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    def __str__(self):
        return self.get_full_name() or self.username


class LeaveRequest(models.Model):
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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="leave_requests", verbose_name="Angajat",
    )
    leave_type = models.CharField(
        max_length=20, choices=LeaveType.choices, default=LeaveType.ANNUAL,
        verbose_name="Tip concediu",
    )
    start_date = models.DateField(verbose_name="Data inceput")
    end_date = models.DateField(verbose_name="Data sfarsit")
    days = models.PositiveIntegerField(default=0, verbose_name="Numar zile")
    reason = models.TextField(verbose_name="Motiv")

    attachment = models.FileField(
        upload_to="leaves/attachments/", storage=_attachment_storage,
        blank=True, null=True, verbose_name="Atasament",
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
        verbose_name="Status",
    )

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="decided_requests",
        verbose_name="Decis de",
    )
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name="Data deciziei")
    decision_note = models.TextField(blank=True, verbose_name="Nota decizie")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Cerere de concediu"
        verbose_name_plural = "Cereri de concediu"

    def __str__(self):
        return f"Cerere #{self.pk} - {self.employee} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("leave_detail", kwargs={"pk": self.pk})

    def calculate_days(self):
        if not self.start_date or not self.end_date:
            return 0
        return max((self.end_date - self.start_date).days + 1, 0)

    def save(self, *args, **kwargs):
        self.days = self.calculate_days()
        super().save(*args, **kwargs)

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    @property
    def is_rejected(self):
        return self.status == self.Status.REJECTED

    def mark_approved(self, manager, note=""):
        self.status = self.Status.APPROVED
        self.decided_by = manager
        self.decided_at = timezone.now()
        self.decision_note = note
        self.save()

    def mark_rejected(self, manager, note=""):
        self.status = self.Status.REJECTED
        self.decided_by = manager
        self.decided_at = timezone.now()
        self.decision_note = note
        self.save()


class Signature(models.Model):
    leave_request = models.OneToOneField(
        LeaveRequest, on_delete=models.CASCADE,
        related_name="signature", verbose_name="Cerere",
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="signatures", verbose_name="Manager",
    )
    image = models.ImageField(
        upload_to="leaves/signatures/", storage=_signature_storage,
        verbose_name="Imagine semnatura",
    )
    signed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Semnatura"
        verbose_name_plural = "Semnaturi"

    def __str__(self):
        return f"Semnatura cererea #{self.leave_request_id} de {self.manager}"
