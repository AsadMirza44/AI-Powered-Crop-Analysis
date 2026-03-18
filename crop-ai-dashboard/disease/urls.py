from django.urls import path

from .views import disease_analysis


app_name = "disease"

urlpatterns = [
    path("", disease_analysis, name="analysis"),
]
