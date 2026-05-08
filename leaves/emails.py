"""Helper pentru trimiterea emailurilor (via Resend SMTP)."""
import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def _absolute_url(path: str) -> str:
    """Construieste un URL absolut pentru link-urile din email."""
    host = getattr(settings, "PUBLIC_BASE_URL", "")
    if not host:
        # fallback - merge bine in dezvoltare locala
        host = "http://127.0.0.1:8000"
    return host.rstrip("/") + path


def _send_sync(subject: str, to: list, template_base: str, context: dict) -> None:
    """Trimitere efectiva (apelata in thread)."""
    try:
        if not to:
            return
        text_body = render_to_string(f"emails/{template_base}.txt", context)
        html_body = render_to_string(f"emails/{template_base}.html", context)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("Email failed (%s): %s", template_base, e)


def _send(subject: str, to: list, template_base: str, context: dict) -> None:
    """Lanseaza trimiterea intr-un thread daemon.

    Astfel request-ul HTTP nu mai asteapta SMTP-ul, returneaza imediat raspunsul.
    Pierdem garantia ca emailul a plecat (poate fi chiar avantaj la presiune mare),
    dar pentru un proiect academic e suficient.
    """
    if not to:
        return
    t = threading.Thread(
        target=_send_sync,
        args=(subject, to, template_base, context),
        daemon=True,
    )
    t.start()


def notify_managers_new_request(leave_request) -> None:
    """Trimite mail tuturor managerilor cand un angajat creeaza o cerere."""
    from .models import CustomUser

    managers = CustomUser.objects.filter(role=CustomUser.Role.MANAGER, is_active=True)
    emails = [m.email for m in managers if m.email]
    if not emails:
        return

    context = {
        "request_obj": leave_request,
        "employee": leave_request.employee,
        "url": _absolute_url(reverse("leave_detail", args=[leave_request.pk])),
    }
    _send(
        subject=f"[LeaveFlow] Cerere noua de la {leave_request.employee}",
        to=emails,
        template_base="new_request",
        context=context,
    )


def notify_employee_decision(leave_request) -> None:
    """Trimite mail angajatului cand cererea e aprobata sau respinsa."""
    employee = leave_request.employee
    if not employee.email:
        return

    is_approved = leave_request.is_approved
    context = {
        "request_obj": leave_request,
        "employee": employee,
        "is_approved": is_approved,
        "url": _absolute_url(reverse("leave_detail", args=[leave_request.pk])),
    }
    subject = "[LeaveFlow] Cererea ta a fost aprobata" if is_approved else "[LeaveFlow] Cererea ta a fost respinsa"
    _send(
        subject=subject,
        to=[employee.email],
        template_base="decision",
        context=context,
    )
