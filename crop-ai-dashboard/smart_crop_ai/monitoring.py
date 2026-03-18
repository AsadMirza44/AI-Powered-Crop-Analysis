from __future__ import annotations

from typing import Iterable


SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


def disease_alert_severity(label: str, confidence: float, hotspot_pct: float) -> str:
    normalized = label.strip().lower()
    if normalized == "healthy":
        return "low"
    if confidence >= 0.8 or hotspot_pct >= 15:
        return "high"
    return "medium"


def yield_alert_severity(delta_vs_average_pct: float, recommendations: Iterable[dict]) -> str:
    priorities = {str(item.get("priority", "low")).lower() for item in recommendations}
    if "high" in priorities or abs(delta_vs_average_pct) >= 15:
        return "high"
    if "medium" in priorities or abs(delta_vs_average_pct) >= 8:
        return "medium"
    return "low"


def severity_label(severity: str) -> str:
    return {
        "high": "High Alert",
        "medium": "Watch",
        "low": "Stable",
    }.get(severity, "Stable")


def severity_count(items: Iterable[str], severity: str) -> int:
    return sum(1 for item in items if item == severity)
