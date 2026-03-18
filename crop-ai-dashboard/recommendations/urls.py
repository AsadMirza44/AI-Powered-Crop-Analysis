from django.urls import path

from .views import recommendation_center


app_name = "recommendations"

urlpatterns = [
    path("", recommendation_center, name="center"),
]
