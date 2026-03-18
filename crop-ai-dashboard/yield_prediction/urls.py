from django.urls import path

from .views import yield_forecast


app_name = "yield_prediction"

urlpatterns = [
    path("", yield_forecast, name="forecast"),
]
