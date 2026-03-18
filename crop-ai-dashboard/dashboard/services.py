from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from django.conf import settings

from disease.models import DiseasePrediction
from smart_crop_ai.monitoring import (
    disease_alert_severity,
    severity_count,
    severity_label,
    yield_alert_severity,
)
from smart_crop_ai.reference_data import CROP_PROFILES, DISTRICT_PROFILES
from yield_prediction.models import YieldPrediction
from yield_prediction.services import get_yield_service


def annotate_disease_records(records) -> list:
    annotated = []
    for item in records:
        severity = disease_alert_severity(item.predicted_label, item.confidence, item.hotspot_pct)
        item.alert_severity = severity
        item.alert_label = severity_label(severity)
        annotated.append(item)
    return annotated


def annotate_yield_records(records) -> list:
    annotated = []
    for item in records:
        severity = yield_alert_severity(item.delta_vs_average_pct, item.recommendations)
        item.alert_severity = severity
        item.alert_label = severity_label(severity)
        annotated.append(item)
    return annotated


def alert_summary(disease_predictions: list, yield_predictions: list) -> dict[str, int]:
    severities = [item.alert_severity for item in disease_predictions] + [item.alert_severity for item in yield_predictions]
    return {
        "high": severity_count(severities, "high"),
        "medium": severity_count(severities, "medium"),
        "low": severity_count(severities, "low"),
    }


def overview_context() -> dict:
    disease_predictions = annotate_disease_records(DiseasePrediction.objects.order_by("-created_at")[:4])
    yield_predictions = annotate_yield_records(YieldPrediction.objects.order_by("-created_at")[:4])
    total_predictions = DiseasePrediction.objects.count() + YieldPrediction.objects.count()

    avg_confidence_values = list(DiseasePrediction.objects.values_list("confidence", flat=True))
    avg_yield_values = list(YieldPrediction.objects.values_list("predicted_yield_t_ha", flat=True))

    spotlight_crop = "maize"
    spotlight_district = "Faisalabad"
    try:
        yield_service = get_yield_service()
        history = yield_service.history_for(spotlight_crop)
    except FileNotFoundError:
        history = []

    province_names = sorted({profile["province"] for profile in DISTRICT_PROFILES.values()})
    province_summaries = [
        {
            "province": province,
            "districts": sum(1 for entry in DISTRICT_PROFILES.values() if entry["province"] == province),
        }
        for province in province_names
    ]

    return {
        "total_predictions": total_predictions,
        "crop_count": len(CROP_PROFILES),
        "location_count": len(DISTRICT_PROFILES),
        "avg_confidence_pct": round((mean(avg_confidence_values) * 100), 1) if avg_confidence_values else 0,
        "avg_yield_t_ha": round(mean(avg_yield_values), 2) if avg_yield_values else 0,
        "recent_disease_predictions": disease_predictions,
        "recent_yield_predictions": yield_predictions,
        "alert_counts": alert_summary(disease_predictions, yield_predictions),
        "spotlight_crop_label": CROP_PROFILES[spotlight_crop]["label"],
        "spotlight_district": spotlight_district,
        "yield_history": history,
        "yield_chart_points": build_svg_points(history, 340, 120),
        "province_summaries": province_summaries,
        "operations_notes": [
            "Local Django monitoring board is now the active implementation path.",
            "TensorFlow disease inference now uses PlantVillage and PlantDoc transfer learning artifacts.",
            "Scikit-learn yield forecasting now uses FAOSTAT, PBS, NASA POWER, and SoilGrids features.",
            "SQLite is the active local database for zero-setup project handover.",
        ],
    }


def metrics_context() -> dict:
    disease_metadata = _load_metadata(Path(settings.DISEASE_METADATA_PATH))
    yield_metadata = _load_metadata(Path(settings.YIELD_METADATA_PATH))
    disease_source_totals = _sum_source_counts(disease_metadata.get("class_counts", {}))

    disease_crop_metrics = []
    for crop_code, profile in CROP_PROFILES.items():
        if not profile["supports_disease"]:
            continue
        class_count = sum(
            1
            for details in disease_metadata.get("class_details", {}).values()
            if details.get("crop") == crop_code
        )
        disease_crop_metrics.append({"label": profile["label"], "class_count": class_count})

    yield_history = yield_metadata.get("historical_series", {})
    year_values = []
    for series in yield_history.values():
        if isinstance(series, dict):
            for nested_series in series.values():
                year_values.extend(point["year"] for point in nested_series)
        else:
            year_values.extend(point["year"] for point in series)

    return {
        "disease_model": {
            "family": disease_metadata.get("model_family", "TensorFlow CNN"),
            "test_accuracy_pct": round(float(disease_metadata.get("test_accuracy", 0.0)) * 100, 2),
            "validation_accuracy_pct": round(float(disease_metadata.get("finetune_val_accuracy", 0.0)) * 100, 2),
            "image_count": disease_metadata.get("manifest_rows", 0),
            "class_count": len(disease_metadata.get("class_names", [])),
            "source_totals": disease_source_totals,
            "notes": disease_metadata.get("notes", ""),
            "crop_metrics": disease_crop_metrics,
        },
        "yield_model": {
            "family": str(yield_metadata.get("best_model", "scikit-learn")).replace("_", " ").title(),
            "feature_count": len(yield_metadata.get("feature_columns", [])),
            "history_context": yield_metadata.get("history_context", "Pakistan historical average"),
            "candidate_metrics": [
                {
                    "label": model_name.replace("_", " ").title(),
                    "rmse": metrics["rmse"],
                    "mae": metrics["mae"],
                    "r2": metrics["r2"],
                    "is_best": model_name == yield_metadata.get("best_model"),
                }
                for model_name, metrics in yield_metadata.get("candidate_metrics", {}).items()
            ],
            "year_span": f"{min(year_values)}-{max(year_values)}" if year_values else "n/a",
            "notes": yield_metadata.get("notes", ""),
        },
        "runtime_metrics": {
            "stored_disease_predictions": DiseasePrediction.objects.count(),
            "stored_yield_predictions": YieldPrediction.objects.count(),
            "supported_disease_crops": [profile["label"] for profile in CROP_PROFILES.values() if profile["supports_disease"]],
            "supported_yield_crops": [profile["label"] for profile in CROP_PROFILES.values() if profile["supports_yield"]],
            "district_count": len(DISTRICT_PROFILES),
        },
    }


def sources_context() -> dict:
    return {
        "source_cards": [
            {
                "title": "PlantVillage",
                "category": "Disease imagery",
                "use_case": "Transfer-learning base images for healthy and disease-labelled crop leaves.",
                "access": "Free via TensorFlow Datasets / public research distribution",
                "status": "Active in the current TensorFlow disease model",
            },
            {
                "title": "PlantDoc",
                "category": "Field imagery",
                "use_case": "Field-style disease images used to reduce the gap between lab images and real leaf captures.",
                "access": "Free public dataset",
                "status": "Active in the current TensorFlow disease model",
            },
            {
                "title": "FAOSTAT",
                "category": "Yield history",
                "use_case": "Historical Pakistan crop-yield series for maize, wheat, and rice.",
                "access": "Free public statistics",
                "status": "Active in the scikit-learn yield dataset",
            },
            {
                "title": "Pakistan Bureau of Statistics",
                "category": "Economic context",
                "use_case": "Annual crop output indicators used as macro-agriculture context features.",
                "access": "Free public reports",
                "status": "Active in the scikit-learn yield dataset",
            },
            {
                "title": "NASA POWER",
                "category": "Weather features",
                "use_case": "Seasonal rainfall and temperature context for district-level yield inputs.",
                "access": "Free public API",
                "status": "Active in the scikit-learn yield dataset",
            },
            {
                "title": "SoilGrids",
                "category": "Soil features",
                "use_case": "Baseline soil pH, organic carbon, and nitrogen context for operational districts.",
                "access": "Free public data service",
                "status": "Active in the scikit-learn yield dataset and autofill layer",
            },
        ],
        "limitations": [
            "Yield benchmarking is still anchored to Pakistan historical averages, not district-labeled ground-truth yield targets.",
            "Disease performance is stronger than the old synthetic baseline, but field generalization is still bounded by the PlantVillage-to-PlantDoc domain gap.",
            "Irrigation and fertilizer outputs are rule-based recommendations tied to the current model inputs, not an expert-certified agronomy system.",
            "SQLite is used for local storage and sharing, so the current app is intended for single-machine use rather than concurrent multi-user deployment.",
        ],
        "runtime_notes": [
            "The dashboard is local-web first and intentionally avoids paid cloud dependencies.",
            "Demo scenarios and district smart autofill are included to make prediction flows reproducible during evaluation.",
            "All current data sources used in the app are free or publicly accessible.",
        ],
    }


def build_svg_points(history: list[dict], width: int, height: int) -> str:
    if not history:
        return ""
    xs = [point["year"] for point in history]
    ys = [point["yield_t_ha"] for point in history]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1)
    span_y = max(max_y - min_y, 0.1)

    points: list[str] = []
    for point in history:
        x_pos = ((point["year"] - min_x) / span_x) * width
        y_pos = height - (((point["yield_t_ha"] - min_y) / span_y) * height)
        points.append(f"{x_pos:.1f},{y_pos:.1f}")
    return " ".join(points)


def _load_metadata(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _sum_source_counts(class_counts: dict) -> list[dict]:
    totals: dict[str, int] = {}
    for source_map in class_counts.values():
        for source, count in source_map.items():
            label = source.replace("_", " ").title()
            totals[label] = totals.get(label, 0) + int(count)
    return [{"label": label, "count": count} for label, count in totals.items()]
