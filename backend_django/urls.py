from django.urls import path

from . import views


urlpatterns = [
    path("", views.index_view, name="index"),
    path("index.html", views.index_view, name="index_html"),
    path("uav-icon.png", views.uav_icon_view, name="uav_icon"),
    path("api/defaults", views.defaults_view, name="defaults"),
    path("api/run-demo", views.run_demo_view, name="run_demo"),
    path("api/auth/state", views.auth_state_view, name="auth_state"),
    path("api/auth/options", views.auth_options_view, name="auth_options"),
    path("api/auth/login", views.auth_login_view, name="auth_login"),
    path("api/auth/logout", views.auth_logout_view, name="auth_logout"),
    path("api/identity", views.identity_view, name="identity"),
    path("api/identity/switch", views.identity_switch_view, name="identity_switch"),
    path("api/tasks", views.tasks_view, name="tasks"),
    path("api/tasks/<str:task_id>", views.task_detail_view, name="task_detail"),
    path("api/tasks/<str:task_id>/control", views.task_control_view, name="task_control"),
    path("api/tasks/<str:task_id>/events", views.task_events_view, name="task_events"),
    path("api/tasks/<str:task_id>/alerts", views.task_alerts_view, name="task_alerts"),
    path("api/tasks/<str:task_id>/replay", views.task_replay_view, name="task_replay"),
    path("api/tasks/<str:task_id>/feedback", views.task_feedback_view, name="task_feedback"),
    path("api/dashboard/summary", views.dashboard_summary_view, name="dashboard_summary"),
]
