from django.shortcuts import render

from dashboard.services import alert_summary, annotate_disease_records, annotate_yield_records
from disease.models import DiseasePrediction
from smart_crop_ai.monitoring import severity_label
from yield_prediction.models import YieldPrediction


def recommendation_center(request):
    recent_disease_items = annotate_disease_records(DiseasePrediction.objects.order_by("-created_at")[:6])
    recent_yield_items = annotate_yield_records(YieldPrediction.objects.order_by("-created_at")[:6])
    latest_disease = recent_disease_items[0] if recent_disease_items else None
    latest_yield = recent_yield_items[0] if recent_yield_items else None

    agronomy_recommendations = latest_yield.recommendations if latest_yield else []
    disease_recommendations = latest_disease.recommendations if latest_disease else []
    category_counts: dict[str, int] = {}
    for item in agronomy_recommendations:
        category = item["category"]
        category_counts[category] = category_counts.get(category, 0) + 1
        item["alert_severity"] = item.get("priority", "low")
        item["alert_label"] = severity_label(item["alert_severity"])

    context = {
        "latest_disease": latest_disease,
        "latest_yield": latest_yield,
        "agronomy_recommendations": agronomy_recommendations,
        "disease_recommendations": disease_recommendations,
        "category_counts": category_counts,
        "alert_counts": alert_summary(recent_disease_items, recent_yield_items),
        "recent_yield_items": recent_yield_items,
        "recent_disease_items": recent_disease_items,
    }
    return render(request, "recommendations/center.html", context)
