from __future__ import annotations

from smart_crop_ai.reference_data import CROP_PROFILES


def build_agronomic_recommendations(payload: dict, predicted_yield: float, historical_average: float) -> list[dict]:
    crop = payload["crop"]
    crop_profile = CROP_PROFILES[crop]
    recommendations: list[dict] = []
    below_average = predicted_yield < historical_average * 0.95

    rainfall_gap = payload["rainfall_mm"] - crop_profile["ideal_rainfall_mm"]
    temp_gap = payload["avg_temp_c"] - crop_profile["ideal_temp_c"]

    if rainfall_gap < -45 or temp_gap > 2.5:
        recommendations.append(
            {
                "category": "irrigation",
                "priority": "high",
                "title": "Increase crop-stage irrigation discipline",
                "action": (
                    "Shorten irrigation intervals, prioritize dawn or late-evening application, "
                    "and protect the crop during flowering or grain-fill stress windows."
                ),
                "rationale": (
                    f"Rainfall is {abs(rainfall_gap):.0f} mm below the crop target or temperature is "
                    f"{temp_gap:.1f} C above the comfort range."
                ),
            }
        )
    elif rainfall_gap > 70:
        recommendations.append(
            {
                "category": "irrigation",
                "priority": "medium",
                "title": "Prevent excess-water losses",
                "action": "Delay non-essential irrigation, check field drainage, and avoid standing water where possible.",
                "rationale": "Current rainfall is materially above the crop target, which raises lodging and nutrient-loss risk.",
            }
        )
    else:
        recommendations.append(
            {
                "category": "irrigation",
                "priority": "low",
                "title": "Maintain standard irrigation scheduling",
                "action": "Keep field moisture checks on a 5 to 7 day cycle and protect uniform water distribution.",
                "rationale": "Current rainfall and temperature remain close to the crop comfort zone.",
            }
        )

    if payload["nitrogen_ppm"] < crop_profile["nitrogen_target"] - 8:
        recommendations.append(
            {
                "category": "fertilizer",
                "priority": "high",
                "title": "Reinforce nitrogen with split feeding",
                "action": "Use split top-dressing rather than one heavy dose and align the next application with irrigation.",
                "rationale": f"Nitrogen is below the crop target of {crop_profile['nitrogen_target']:.0f} ppm.",
            }
        )
    if payload["phosphorus_ppm"] < crop_profile["phosphorus_target"] - 5:
        recommendations.append(
            {
                "category": "fertilizer",
                "priority": "medium",
                "title": "Protect early root development with phosphorus support",
                "action": "Review basal phosphorus placement before increasing total fertilizer rate.",
                "rationale": f"Phosphorus is below the crop target of {crop_profile['phosphorus_target']:.0f} ppm.",
            }
        )
    if payload["potassium_ppm"] < crop_profile["potassium_target"] - 25:
        recommendations.append(
            {
                "category": "fertilizer",
                "priority": "medium",
                "title": "Stabilize potassium support before peak stress",
                "action": "Correct potassium deficiency before the highest heat or grain-fill stress period.",
                "rationale": f"Potassium is below the crop target of {crop_profile['potassium_target']:.0f} ppm.",
            }
        )
    if payload["organic_carbon_pct"] < crop_profile["organic_carbon_floor"]:
        recommendations.append(
            {
                "category": "fertilizer",
                "priority": "medium",
                "title": "Improve organic matter buffering",
                "action": "Add compost, manure, or residue retention planning to improve nutrient holding capacity.",
                "rationale": "Organic carbon is below the crop-specific floor for stable nutrient retention.",
            }
        )
    if below_average:
        recommendations.append(
            {
                "category": "monitoring",
                "priority": "medium",
                "title": "Investigate the yield gap before increasing spend",
                "action": "Check irrigation uniformity, stand health, and timing of previous fertilizer applications.",
                "rationale": "The projected yield remains below the district historical average.",
            }
        )

    return recommendations


def build_disease_recommendations(crop: str, label: str, confidence: float, hotspot_pct: float) -> list[str]:
    crop_label = CROP_PROFILES[crop]["label"]
    normalized = label.strip().lower()
    base_lookup = {
        "healthy": [
            f"{crop_label} leaf looks stable. Keep weekly scouting and avoid unnecessary chemical intervention.",
            "Maintain clean irrigation timing and watch for changes in lower-canopy leaves after humidity spikes.",
        ],
        "common rust": [
            "Inspect surrounding plants for fresh pustules and keep canopy airflow open where possible.",
            "Avoid reacting to a single leaf only; confirm spread level across the block before treatment.",
        ],
        "northern leaf blight": [
            "Remove heavily affected foliage where practical and reduce prolonged leaf wetness periods.",
            "Review fungicide threshold decisions with a local agronomy source before applying treatment.",
        ],
        "early blight": [
            "Remove heavily damaged leaves, especially lower canopy foliage where early blight typically escalates first.",
            "Keep irrigation away from evening leaf wetness periods and avoid unnecessary nitrogen spikes.",
        ],
        "late blight": [
            "Escalate field scouting immediately because late blight can spread quickly under humid conditions.",
            "Isolate highly affected plants and review urgent disease-control steps with a local agronomy source.",
        ],
        "bacterial spot": [
            "Limit leaf wetness duration and avoid overhead irrigation where possible.",
            "Disinfect tools between blocks if plant handling is required.",
        ],
        "bacterial blight": [
            "Avoid moving through wet foliage and reduce splash-heavy irrigation until the spread pattern is confirmed.",
            "Inspect neighboring plants for angular or water-soaked lesions before deciding on treatment intensity.",
        ],
        "leaf mold": [
            "Improve ventilation around the canopy and avoid trapping humidity around foliage.",
            "Check greenhouse or tunnel airflow if the crop is under protected cultivation.",
        ],
        "alternaria leaf spot": [
            "Increase scouting on older leaves and remove heavily affected foliage where practical.",
            "Reduce prolonged leaf wetness and review field sanitation before adding extra chemical cost.",
        ],
        "fusarium wilt": [
            "Check the spread pattern along rows and inspect stems or vascular tissue before making replant decisions.",
            "Avoid over-irrigating stressed sections and isolate badly affected plants where feasible.",
        ],
        "verticillium wilt": [
            "Track patchy wilting zones and compare symptom spread with irrigation uniformity before intervention.",
            "Keep soil moisture stable and avoid adding unnecessary nitrogen to already stressed plants.",
        ],
        "septoria leaf spot": [
            "Increase scouting frequency around older leaves and humid field edges.",
            "Avoid splash-heavy irrigation patterns that keep spreading spores upward.",
        ],
        "tomato yellow leaf curl virus": [
            "Inspect the block for whitefly pressure and remove severely affected plants from active production zones.",
            "Use this result as a scouting trigger for vector management rather than a standalone treatment instruction.",
        ],
        "brown rust": [
            "Increase scouting frequency across the mid-canopy and confirm whether fresh pustules are spreading after humid nights.",
            "Protect airflow where possible and avoid turning a localized case into a field-wide reaction without checking spread.",
        ],
        "pokkah boeng": [
            "Inspect the newest leaves and spindle tissue for deformation before deciding on broad control measures.",
            "Review drainage and canopy humidity because prolonged moisture can worsen symptom progression.",
        ],
        "smut": [
            "Flag affected stools quickly and inspect neighboring plants because smut can escalate through infected planting material.",
            "Use the result as a trigger to review seed cane hygiene and block-level sanitation practices.",
        ],
        "viral disease": [
            "Check the field for vector pressure and remove clearly affected leaves or stools from close observation blocks.",
            "Treat this as an early warning for spread management rather than a standalone chemical recommendation.",
        ],
        "yellow leaf": [
            "Inspect symptom spread along the row and check whether nutrient stress is amplifying the yellowing signal.",
            "Use follow-up scouting to separate persistent leaf disease from temporary nutrient or moisture imbalance.",
        ],
    }
    base = base_lookup.get(
        normalized,
        [
            f"Use the {crop_label.lower()} diagnosis as a scouting aid and confirm the field pattern before any spend decision.",
            "Keep leaf wetness under control and document how rapidly symptoms are spreading.",
        ],
    )

    if confidence >= 0.8 and hotspot_pct > 15:
        base.append("The highlighted stress zone is pronounced, so validate the case in the field within the next 24 hours.")
    else:
        base.append("Confidence is moderate, so use this result as a scouting aid rather than a standalone treatment trigger.")
    return base
