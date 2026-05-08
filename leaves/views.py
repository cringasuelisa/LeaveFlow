from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView, DetailView, FormView, ListView, RedirectView, TemplateView,
)

from .emails import notify_employee_decision, notify_managers_new_request
from .forms import ApprovalForm, LeaveRequestForm, RegisterForm, RejectionForm
from .models import LeaveRequest, Signature
from .templatetags.leave_extras import user_color


class RegisterView(FormView):
    template_name = "registration/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Cont creat cu succes! Bine ai venit pe LeaveFlow.")
        return super().form_valid(form)


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = False

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_manager or u.is_admin_role or u.is_superuser)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Nu ai drepturi de manager pentru aceasta actiune.")
            return redirect("dashboard")
        return super().handle_no_permission()


class DashboardView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        u = self.request.user
        if u.is_manager or u.is_admin_role or u.is_superuser:
            return ["leaves/dashboard_manager.html"]
        return ["leaves/dashboard_employee.html"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        if u.is_manager or u.is_admin_role or u.is_superuser:
            qs = LeaveRequest.objects.select_related("employee")
            ctx["pending_requests"] = qs.filter(status=LeaveRequest.Status.PENDING)
            ctx["recent_decisions"] = qs.exclude(status=LeaveRequest.Status.PENDING)[:10]
        else:
            qs = LeaveRequest.objects.filter(employee=u)
            ctx["my_requests"] = qs[:10]

        ctx["stats"] = {
            "total": qs.count(),
            "pending": qs.filter(status=LeaveRequest.Status.PENDING).count(),
            "approved": qs.filter(status=LeaveRequest.Status.APPROVED).count(),
            "rejected": qs.filter(status=LeaveRequest.Status.REJECTED).count(),
        }
        return ctx


class LeaveCreateView(LoginRequiredMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = "leaves/leave_form.html"

    def form_valid(self, form):
        form.instance.employee = self.request.user
        try:
            response = super().form_valid(form)
        except Exception as exc:
            form.add_error(
                "attachment",
                "Atasamentul nu a putut fi incarcat. "
                "Verifica ca este un PDF sau DOCX valid si reincearca. "
                f"({type(exc).__name__})"
            )
            return self.form_invalid(form)

        try:
            notify_managers_new_request(self.object)
        except Exception:
            pass
        messages.success(
            self.request,
            "Cererea a fost trimisa. Managerii au fost notificati pe email.",
        )
        return response

    def get_success_url(self):
        return reverse_lazy("leave_detail", kwargs={"pk": self.object.pk})


class LeaveListView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = "leaves/leave_list.html"
    paginate_by = 20
    context_object_name = "requests"

    def get_queryset(self):
        u = self.request.user
        qs = LeaveRequest.objects.select_related("employee", "decided_by")
        if not (u.is_manager or u.is_admin_role or u.is_superuser):
            qs = qs.filter(employee=u)
        status = self.request.GET.get("status")
        if status in dict(LeaveRequest.Status.choices):
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = LeaveRequest.Status.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        return ctx


class LeaveDetailView(LoginRequiredMixin, DetailView):
    model = LeaveRequest
    template_name = "leaves/leave_detail.html"
    context_object_name = "leave"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        u = self.request.user
        if not (u.is_manager or u.is_admin_role or u.is_superuser or obj.employee_id == u.id):
            raise Http404
        return obj


class ApproveLeaveView(ManagerRequiredMixin, FormView):
    template_name = "leaves/leave_approve.html"
    form_class = ApprovalForm

    def dispatch(self, request, *args, **kwargs):
        self.leave = get_object_or_404(LeaveRequest, pk=kwargs["pk"])
        if not self.leave.is_pending:
            messages.warning(request, "Aceasta cerere a fost deja procesata.")
            return redirect("leave_detail", pk=self.leave.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["leave"] = self.leave
        return ctx

    def form_valid(self, form):
        signature_file = form.get_signature_file()
        if signature_file is None:
            messages.error(self.request, "Semnatura nu a putut fi procesata. Reincearca.")
            return self.form_invalid(form)

        try:
            self.leave.mark_approved(self.request.user, note=form.cleaned_data.get("note", ""))
            Signature.objects.update_or_create(
                leave_request=self.leave,
                defaults={"manager": self.request.user, "image": signature_file},
            )
        except Exception as exc:
            form.add_error(
                None,
                "Semnatura nu a putut fi salvata. Reincearca cu o imagine valida (PNG/JPG). "
                f"({type(exc).__name__})"
            )
            return self.form_invalid(form)

        try:
            notify_employee_decision(self.leave)
        except Exception:
            pass

        messages.success(self.request, "Cerere aprobata si semnata. Angajatul a fost notificat.")
        return redirect("leave_detail", pk=self.leave.pk)


class RejectLeaveView(ManagerRequiredMixin, FormView):
    template_name = "leaves/leave_reject.html"
    form_class = RejectionForm

    def dispatch(self, request, *args, **kwargs):
        self.leave = get_object_or_404(LeaveRequest, pk=kwargs["pk"])
        if not self.leave.is_pending:
            messages.warning(request, "Aceasta cerere a fost deja procesata.")
            return redirect("leave_detail", pk=self.leave.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["leave"] = self.leave
        return ctx

    def form_valid(self, form):
        self.leave.mark_rejected(self.request.user, note=form.cleaned_data["note"])
        try:
            notify_employee_decision(self.leave)
        except Exception:
            pass
        messages.success(self.request, "Cerere respinsa. Angajatul a fost notificat.")
        return redirect("leave_detail", pk=self.leave.pk)


class LeaveDocumentView(LoginRequiredMixin, DetailView):
    model = LeaveRequest
    template_name = "leaves/leave_document.html"
    context_object_name = "leave"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        u = self.request.user
        if not (u.is_manager or u.is_admin_role or u.is_superuser or obj.employee_id == u.id):
            raise Http404
        if not obj.is_approved:
            raise Http404("Document disponibil doar pentru cereri aprobate.")
        return obj


class LeavePDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        leave = get_object_or_404(LeaveRequest, pk=pk)
        u = request.user
        if not (u.is_manager or u.is_admin_role or u.is_superuser or leave.employee_id == u.id):
            raise Http404
        if not leave.is_approved:
            raise Http404("PDF disponibil doar pentru cereri aprobate.")

        from io import BytesIO

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
            title=f"Cerere concediu #{leave.pk}",
        )
        styles = getSampleStyleSheet()
        title = ParagraphStyle("title", parent=styles["Title"], alignment=1, fontSize=18)
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceBefore=12)
        story = [Paragraph("CERERE DE CONCEDIU", title), Spacer(1, 12)]

        emp = leave.employee
        story.append(Paragraph(
            f"Subsemnatul/a <b>{emp.get_full_name() or emp.username}</b>, "
            f"departamentul <b>{emp.department or '-'}</b>, "
            f"prin prezenta solicit acordarea unui concediu dupa cum urmeaza:",
            styles["BodyText"],
        ))
        story.append(Spacer(1, 12))

        data = [
            ["Tip concediu", leave.get_leave_type_display()],
            ["Perioada", f"{leave.start_date:%d.%m.%Y} - {leave.end_date:%d.%m.%Y}"],
            ["Numar zile", str(leave.days)],
            ["Status", leave.get_status_display()],
            ["Trimisa la", leave.created_at.strftime("%d.%m.%Y %H:%M")],
            ["Decisa la", leave.decided_at.strftime("%d.%m.%Y %H:%M") if leave.decided_at else "-"],
            ["Aprobata de", str(leave.decided_by) if leave.decided_by else "-"],
        ]
        table = Table(data, colWidths=[5 * cm, 11 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 18))

        story.append(Paragraph("Motiv:", h2))
        story.append(Paragraph(leave.reason.replace("\n", "<br/>"), styles["BodyText"]))

        if leave.decision_note:
            story.append(Paragraph("Nota manager:", h2))
            story.append(Paragraph(leave.decision_note.replace("\n", "<br/>"), styles["BodyText"]))

        if hasattr(leave, "signature") and leave.signature.image:
            story.append(Spacer(1, 24))
            story.append(Paragraph("Semnatura manager:", h2))
            try:
                story.append(Image(leave.signature.image.path, width=6 * cm, height=3 * cm))
            except Exception:
                try:
                    import urllib.request
                    req = urllib.request.Request(
                        leave.signature.image.url,
                        headers={"User-Agent": "LeaveFlow/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=10) as r:
                        story.append(Image(BytesIO(r.read()), width=6 * cm, height=3 * cm))
                except Exception:
                    pass

        doc.build(story)
        pdf = buf.getvalue()
        buf.close()

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="cerere_{leave.pk}.pdf"'
        return response


class CalendarPageView(ManagerRequiredMixin, TemplateView):
    template_name = "leaves/calendar.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        approved = (
            LeaveRequest.objects
            .filter(status=LeaveRequest.Status.APPROVED)
            .select_related("employee")
        )
        seen = {}
        for lr in approved:
            seen.setdefault(lr.employee_id, lr.employee)
        ctx["legend_users"] = list(seen.values())
        return ctx


class CalendarEventsView(ManagerRequiredMixin, View):
    def get(self, request):
        qs = LeaveRequest.objects.filter(
            status=LeaveRequest.Status.APPROVED
        ).select_related("employee")

        start_param = request.GET.get("start")
        end_param = request.GET.get("end")
        try:
            if start_param and end_param:
                start = datetime.fromisoformat(start_param.replace("Z", "+00:00")).date()
                end = datetime.fromisoformat(end_param.replace("Z", "+00:00")).date()
                qs = qs.filter(start_date__lt=end, end_date__gte=start)
        except ValueError:
            pass

        events = []
        for lr in qs:
            color = user_color(lr.employee)
            employee_name = lr.employee.get_full_name() or lr.employee.username
            events.append({
                "id": lr.id,
                "title": f"{employee_name} - {lr.get_leave_type_display()}",
                "start": lr.start_date.isoformat(),
                # FullCalendar foloseste end exclusiv, deci adaugam o zi
                "end": (lr.end_date + timedelta(days=1)).isoformat(),
                "allDay": True,
                "backgroundColor": color,
                "borderColor": color,
                "url": str(lr.get_absolute_url()),
                "extendedProps": {
                    "employee": employee_name,
                    "department": lr.employee.department or "",
                    "type": lr.get_leave_type_display(),
                    "days": lr.days,
                },
            })
        return JsonResponse(events, safe=False)


class HomeRedirect(RedirectView):
    pattern_name = "dashboard"
    permanent = False


def placeholder(request):
    return redirect("dashboard")
