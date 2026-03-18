from django.contrib import messages
from django.shortcuts import render

from dashboard.services import annotate_yield_records, build_svg_points
from smart_crop_ai.demo_data import YIELD_DEMO_SCENARIOS
from smart_crop_ai.monitoring import severity_label, yield_alert_severity
from smart_crop_ai.reference_data import CROP_PROFILES, DISTRICT_PROFILES

from .forms import YieldForecastForm
from .models import YieldPrediction
from .services import get_yield_service


def yield_forecast(request):
    form = YieldForecastForm(request.POST or None) if request.method == "POST" else YieldForecastForm(initial=_default_payload())
    result = None

    if request.method == "POST" and form.is_valid():
        try:
            payload = form.cleaned_data
            service = get_yield_service()
            prediction = service.predict(payload)

            result = YieldPrediction.objects.create(
                crop=payload["crop"],
                district=payload["district"],
                province=prediction.province,
                season=payload["season"],
                year=payload["year"],
                rainfall_mm=payload["rainfall_mm"],
                avg_temp_c=payload["avg_temp_c"],
                soil_ph=payload["soil_ph"],
                organic_carbon_pct=payload["organic_carbon_pct"],
                nitrogen_ppm=payload["nitrogen_ppm"],
                phosphorus_ppm=payload["phosphorus_ppm"],
                potassium_ppm=payload["potassium_ppm"],
                cultivated_area_hectares=payload["cultivated_area_hectares"],
                predicted_yield_t_ha=prediction.predicted_yield_t_ha,
                historical_average_t_ha=prediction.historical_average_t_ha,
                delta_vs_average_pct=prediction.delta_vs_average_pct,
                summary=prediction.summary,
                top_factors=prediction.top_factors,
                recommendations=prediction.recommendations,
                historical_series=prediction.historical_series,
            )
            result.alert_severity = yield_alert_severity(result.delta_vs_average_pct, result.recommendations)
            result.alert_label = severity_label(result.alert_severity)
            messages.success(request, "Yield forecast completed and stored in history.")
        except FileNotFoundError as exc:
            messages.error(request, str(exc))

    context = {
        "form": form,
        "result": result,
        "result_chart_points": build_svg_points(result.historical_series, 340, 120) if result else "",
        "recent_predictions": annotate_yield_records(YieldPrediction.objects.order_by("-created_at")[:5]),
        "district_profiles": DISTRICT_PROFILES,
        "district_autofill": {
            district: {
                "rainfall_mm": profile["rainfall_baseline_mm"],
                "avg_temp_c": profile["avg_temp_c"],
                "soil_ph": profile["soil_ph"],
                "organic_carbon_pct": profile["organic_carbon_pct"],
            }
            for district, profile in DISTRICT_PROFILES.items()
        },
        "crop_defaults": {
            crop: {
                "season": profile["season"] if profile["season"] in {"Kharif", "Rabi"} else "",
                "nitrogen_ppm": profile["nitrogen_target"],
                "phosphorus_ppm": profile["phosphorus_target"],
                "potassium_ppm": profile["potassium_target"],
            }
            for crop, profile in CROP_PROFILES.items()
            if profile["supports_yield"]
        },
        "yield_demo_scenarios": [
            {"key": key, "title": value["title"], "description": value["description"], "payload": value["payload"]}
            for key, value in YIELD_DEMO_SCENARIOS.items()
        ],
    }
    return render(request, "yield_prediction/forecast.html", context)


def _default_payload() -> dict:
    return dict(YIELD_DEMO_SCENARIOS["maize_balanced"]["payload"])
