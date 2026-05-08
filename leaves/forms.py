import base64
import uuid

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile

from .models import CustomUser, LeaveRequest


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=150, required=True, label="Prenume")
    last_name = forms.CharField(max_length=150, required=True, label="Nume")
    department = forms.CharField(max_length=100, required=False, label="Departament")
    role = forms.ChoiceField(
        choices=CustomUser.Role.choices,
        initial=CustomUser.Role.EMPLOYEE,
        label="Rol",
    )

    class Meta:
        model = CustomUser
        fields = (
            "username", "email", "first_name", "last_name",
            "department", "role", "password1", "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


ALLOWED_ATTACHMENT_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_ATTACHMENT_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
    "application/msword",
}
MAX_ATTACHMENT_SIZE_MB = 5
MAX_ATTACHMENT_SIZE_BYTES = MAX_ATTACHMENT_SIZE_MB * 1024 * 1024


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ("leave_type", "start_date", "end_date", "reason", "attachment")
        widgets = {
            "leave_type": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "reason": forms.Textarea(attrs={
                "class": "form-control", "rows": 4,
                "placeholder": "Descrie pe scurt motivul cererii...",
            }),
            "attachment": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }),
        }
        help_texts = {
            "attachment": (
                f"Optional. Doar fisiere <strong>PDF</strong> sau <strong>DOCX</strong>, "
                f"maxim <strong>{MAX_ATTACHMENT_SIZE_MB} MB</strong>."
            ),
        }

    def clean_attachment(self):
        f = self.cleaned_data.get("attachment")
        if not f:
            return f

        if f.size > MAX_ATTACHMENT_SIZE_BYTES:
            size_mb = f.size / (1024 * 1024)
            raise forms.ValidationError(
                f"Fisierul are {size_mb:.1f} MB, dar limita este de {MAX_ATTACHMENT_SIZE_MB} MB."
            )

        name = (getattr(f, "name", "") or "").lower()
        ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            raise forms.ValidationError(
                "Formatul fisierului nu este acceptat. Sunt permise doar PDF sau DOCX."
            )

        ctype = getattr(f, "content_type", "") or ""
        if ctype and ctype not in ALLOWED_ATTACHMENT_MIME_TYPES:
            raise forms.ValidationError(
                f"Tipul fisierului ({ctype}) nu este acceptat. Trebuie sa fie PDF sau DOCX."
            )

        return f

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError(
                "Data de sfarsit nu poate fi inainte de data de inceput."
            )
        return cleaned


class RejectionForm(forms.Form):
    note = forms.CharField(
        label="Motivul respingerii",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        required=True,
    )


class ApprovalForm(forms.Form):
    note = forms.CharField(
        label="Nota / observatii (optional)",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        required=False,
    )
    signature_image = forms.ImageField(
        label="Incarca o imagine cu semnatura",
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
    signature_data = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("signature_image") and not cleaned.get("signature_data"):
            raise forms.ValidationError(
                "Trebuie sa adaugi o semnatura: fie incarcand o imagine, fie semnand in caseta."
            )
        return cleaned

    def get_signature_file(self):
        img = self.cleaned_data.get("signature_image")
        if img:
            return img

        data = self.cleaned_data.get("signature_data") or ""
        if data.startswith("data:image"):
            try:
                header, b64 = data.split(",", 1)
                ext = "jpg" if "image/jpeg" in header else "png"
                content = base64.b64decode(b64)
                return ContentFile(content, name=f"signature_{uuid.uuid4().hex}.{ext}")
            except (ValueError, base64.binascii.Error):
                return None
        return None
