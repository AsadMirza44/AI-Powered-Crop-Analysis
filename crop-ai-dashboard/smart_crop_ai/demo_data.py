from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

YIELD_DEMO_SCENARIOS: dict[str, dict[str, object]] = {
    "maize_balanced": {
        "title": "Balanced Maize Season",
        "description": "Healthy Kharif maize outlook for Faisalabad with near-target rainfall and soil support.",
        "payload": {
            "crop": "maize",
            "district": "Faisalabad",
            "season": "Kharif",
            "year": 2025,
            "rainfall_mm": 412.0,
            "avg_temp_c": 28.4,
            "soil_ph": 7.1,
            "organic_carbon_pct": 1.03,
            "nitrogen_ppm": 58.0,
            "phosphorus_ppm": 22.0,
            "potassium_ppm": 195.0,
            "cultivated_area_hectares": 1500000.0,
        },
    },
    "wheat_heat_stress": {
        "title": "Heat-Stress Wheat Watch",
        "description": "Rabi wheat case with above-normal temperature and below-target soil support.",
        "payload": {
            "crop": "wheat",
            "district": "Multan",
            "season": "Rabi",
            "year": 2025,
            "rainfall_mm": 210.0,
            "avg_temp_c": 24.1,
            "soil_ph": 7.6,
            "organic_carbon_pct": 0.78,
            "nitrogen_ppm": 42.0,
            "phosphorus_ppm": 17.0,
            "potassium_ppm": 158.0,
            "cultivated_area_hectares": 1820000.0,
        },
    },
    "rice_low_fertility": {
        "title": "Low-Fertility Rice Case",
        "description": "Rice scenario with workable rainfall but weak nutrient support and organic matter.",
        "payload": {
            "crop": "rice",
            "district": "Hyderabad",
            "season": "Kharif",
            "year": 2025,
            "rainfall_mm": 528.0,
            "avg_temp_c": 29.4,
            "soil_ph": 7.4,
            "organic_carbon_pct": 0.68,
            "nitrogen_ppm": 52.0,
            "phosphorus_ppm": 18.0,
            "potassium_ppm": 176.0,
            "cultivated_area_hectares": 980000.0,
        },
    },
}


DISEASE_DEMO_SAMPLES: dict[str, dict[str, object]] = {
    "maize_rust": {
        "title": "Maize Rust Sample",
        "description": "Quick-run sample for common rust on maize foliage.",
        "crop": "maize",
        "static_path": "dashboard/demo/maize_rust.jpg",
        "file_path": BASE_DIR / "static" / "dashboard" / "demo" / "maize_rust.jpg",
        "upload_name": "maize_rust_demo.jpg",
    },
    "potato_late_blight": {
        "title": "Potato Late Blight Sample",
        "description": "Quick-run sample with strong late blight visual cues.",
        "crop": "potato",
        "static_path": "dashboard/demo/potato_late_blight.jpg",
        "file_path": BASE_DIR / "static" / "dashboard" / "demo" / "potato_late_blight.jpg",
        "upload_name": "potato_late_blight_demo.jpg",
    },
    "tomato_yellow_leaf_curl": {
        "title": "Tomato Yellow Leaf Curl Sample",
        "description": "Quick-run sample for tomato viral stress and leaf curl symptoms.",
        "crop": "tomato",
        "static_path": "dashboard/demo/tomato_yellow_leaf_curl.jpg",
        "file_path": BASE_DIR / "static" / "dashboard" / "demo" / "tomato_yellow_leaf_curl.jpg",
        "upload_name": "tomato_yellow_leaf_curl_demo.jpg",
    },
}
