"""Trimitere emailuri prin backend-ul Resend (HTTP)."""
import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def _absolute_url(path):
    host = getattr(settings, "PUBLIC_BASE_URL", "") or "http://127.0.0.1:8000"
    return host.rstrip("/") + path


def _send_sync(subject, to, template_base, context):
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
    except Exception as e:
        logger.warning("Email failed (%s): %s", template_base, e)


def _send(subject, to, template_base, context):
    """Lanseaza trimiterea intr-un thread daemon ca sa nu blocheze request-ul."""
    if not to:
        return
    t = threading.Thread(
        target=_send_sync,
        args=(subject, to, template_base, context),
        daemon=True,
    )
    t.start()


def notify_managers_new_request(leave_request):
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


def notify_employee_decision(leave_request):
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
    subject = (
        "[LeaveFlow] Cererea ta a fost aprobata"
        if is_approved
        else "[LeaveFlow] Cererea ta a fost respinsa"
    )
    _send(subject=subject, to=[employee.email], template_base="decision", context=context)
