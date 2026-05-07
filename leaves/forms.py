"""Forms pentru LeaveFlow."""
import base64
import uuid

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile

from .models import CustomUser, LeaveRequest


# ---------------------------------------------------------------------------
# Inregistrare
# ---------------------------------------------------------------------------
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=150, required=True, label="Prenume")
    last_name = forms.CharField(max_length=150, required=True, label="Nume")
    department = forms.CharField(max_length=100, required=False, label="Departament")
    role = forms.ChoiceField(
        choices=CustomUser.Role.choices,
        initial=CustomUser.Role.EMPLOYEE,
        label="Rol",
        help_text="Pentru proiect: alege Manager daca vrei sa aprobi cereri.",
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


# ---------------------------------------------------------------------------
# Cerere concediu
# ---------------------------------------------------------------------------
class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ("leave_type", "start_date", "end_date", "reason", "attachment")
        widgets = {
            "leave_type": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 4,
                                            "placeholder": "Descrie pe scurt motivul cererii..."}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("Data de sfarsit nu poate fi inainte de data de inceput.")
        return cleaned


# ---------------------------------------------------------------------------
# Decizie manager
# ---------------------------------------------------------------------------
class RejectionForm(forms.Form):
    note = forms.CharField(
        label="Motivul respingerii",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        required=True,
    )


class ApprovalForm(forms.Form):
    """Formular pentru aprobare cu semnatura.

    Semnatura poate veni in unul din doua moduri:
      1. `signature_image` -> upload de fisier (input file)
      2. `signature_data`  -> data URL PNG generat de canvas-ul HTML
    """

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
    signature_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        img = cleaned.get("signature_image")
        data = cleaned.get("signature_data")
        if not img and not data:
            raise forms.ValidationError(
                "Trebuie sa adaugi o semnatura: fie incarcand o imagine, fie semnand in caseta."
            )
        return cleaned

    def get_signature_file(self):
        """Returneaza un Django File-like cu semnatura, indiferent de sursa."""
        img = self.cleaned_data.get("signature_image")
        if img:
            return img

        data = self.cleaned_data.get("signature_data") or ""
        if data.startswith("data:image"):
            try:
                header, b64 = data.split(",", 1)
                ext = "png"
                if "image/jpeg" in header:
                    ext = "jpg"
                content = base64.b64decode(b64)
                name = f"signature_{uuid.uuid4().hex}.{ext}"
                return ContentFile(content, name=name)
            except (ValueError, base64.binascii.Error):
                return None
        return None
