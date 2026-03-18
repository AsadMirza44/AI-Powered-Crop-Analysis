from django.shortcuts import render

from disease.models import DiseasePrediction
from yield_prediction.models import YieldPrediction

from .services import (
    annotate_disease_records,
    annotate_yield_records,
    build_svg_points,
    metrics_context,
    overview_context,
    sources_context,
)


def dashboard_home(request):
    return render(request, "dashboard/home.html", overview_context())


def history_view(request):
    disease_items = annotate_disease_records(DiseasePrediction.objects.order_by("-created_at")[:10])
    yield_items = annotate_yield_records(YieldPrediction.objects.order_by("-created_at")[:10])
    recent_chart_items = list(YieldPrediction.objects.order_by("-created_at")[:8])
    yield_chart = [
        {"year": item.year, "yield_t_ha": item.predicted_yield_t_ha}
        for item in reversed(recent_chart_items)
    ]
    context = {
        "disease_items": disease_items,
        "yield_items": yield_items,
        "yield_chart_points": build_svg_points(yield_chart, 340, 120),
        "yield_chart": yield_chart,
    }
    return render(request, "dashboard/history.html", context)


def metrics_view(request):
    return render(request, "dashboard/metrics.html", metrics_context())


def sources_view(request):
    return render(request, "dashboard/sources.html", sources_context())
