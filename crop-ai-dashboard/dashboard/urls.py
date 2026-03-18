from django.urls import path

from .views import dashboard_home, history_view, metrics_view, sources_view


app_name = "dashboard"

urlpatterns = [
    path("", dashboard_home, name="home"),
    path("history/", history_view, name="history"),
    path("metrics/", metrics_view, name="metrics"),
    path("sources/", sources_view, name="sources"),
]
