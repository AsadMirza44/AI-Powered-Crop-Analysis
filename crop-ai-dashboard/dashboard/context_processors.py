from __future__ import annotations

from smart_crop_ai.reference_data import CROP_PROFILES, DISTRICT_PROFILES


def global_dashboard_context(request):
    disease_crops = [profile["label"] for profile in CROP_PROFILES.values() if profile["supports_disease"]]
    yield_crops = [profile["label"] for profile in CROP_PROFILES.values() if profile["supports_yield"]]
    provinces = sorted({profile["province"] for profile in DISTRICT_PROFILES.values()})
    return {
        "nav_crop_count": len(CROP_PROFILES),
        "nav_disease_crops": disease_crops,
        "nav_yield_crops": yield_crops,
        "nav_province_count": len(provinces),
    }
