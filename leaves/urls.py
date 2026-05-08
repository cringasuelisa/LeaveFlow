from django.urls import path

from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),

    path("register/", views.RegisterView.as_view(), name="register"),

    path("requests/", views.LeaveListView.as_view(), name="leave_list"),
    path("requests/new/", views.LeaveCreateView.as_view(), name="leave_create"),
    path("requests/<int:pk>/", views.LeaveDetailView.as_view(), name="leave_detail"),
    path("requests/<int:pk>/approve/", views.ApproveLeaveView.as_view(), name="leave_approve"),
    path("requests/<int:pk>/reject/", views.RejectLeaveView.as_view(), name="leave_reject"),
    path("requests/<int:pk>/document/", views.LeaveDocumentView.as_view(), name="leave_document"),
    path("requests/<int:pk>/pdf/", views.LeavePDFView.as_view(), name="leave_pdf"),

    path("calendar/", views.CalendarPageView.as_view(), name="leave_calendar"),
    path("calendar/events/", views.CalendarEventsView.as_view(), name="leave_calendar_events"),
]
