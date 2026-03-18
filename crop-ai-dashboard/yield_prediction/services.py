from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings

from recommendations.services import build_agronomic_recommendations
from smart_crop_ai.reference_data import CROP_PROFILES, DISTRICT_PROFILES


@dataclass
class YieldResult:
    province: str
    predicted_yield_t_ha: float
    historical_average_t_ha: float
    delta_vs_average_pct: float
    summary: str
    top_factors: list[dict]
    recommendations: list[dict]
    historical_series: list[dict]


class YieldPredictionService:
    def __init__(self) -> None:
        self.model_path = Path(settings.YIELD_MODEL_PATH)
        self.metadata_path = Path(settings.YIELD_METADATA_PATH)
        self.dataset_path = Path(settings.BASE_DIR) / "data" / "processed" / "pakistan_multi_crop_yield_dataset.csv"
        if not self.model_path.exists() or not self.metadata_path.exists():
            raise FileNotFoundError(
                "Scikit-learn yield artifacts are missing. Run training/yield/train_yield_model.py first."
            )
        self.model = joblib.load(self.model_path)
        self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        self.reference_frame = pd.read_csv(self.dataset_path) if self.dataset_path.exists() else pd.DataFrame()

    def predict(self, payload: dict) -> YieldResult:
        district = payload["district"]
        province = DISTRICT_PROFILES[district]["province"]
        feature_columns = self.metadata["feature_columns"]
        features = self._feature_frame(payload, feature_columns)
        predicted_yield = max(float(self.model.predict(features)[0]), 0.1)
        historical_series = self.history_for(payload["crop"], district)
        historical_average = self._historical_average(payload["crop"], district)
        delta_pct = ((predicted_yield - historical_average) / historical_average) * 100

        crop_label = CROP_PROFILES[payload["crop"]]["label"]
        direction = "above" if delta_pct >= 0 else "below"
        history_context = self.metadata.get("history_context")
        if not history_context:
            average_entry = self.metadata["historical_average"][payload["crop"]]
            history_context = "district historical average" if isinstance(average_entry, dict) else "Pakistan historical average"
        summary = (
            f"Projected {crop_label.lower()} yield is {predicted_yield:.2f} t/ha, "
            f"{abs(delta_pct):.1f}% {direction} the {history_context}. "
            f"{district} remains the operational location context for weather and recommendation inputs."
        )

        return YieldResult(
            province=province,
            predicted_yield_t_ha=round(predicted_yield, 3),
            historical_average_t_ha=round(historical_average, 3),
            delta_vs_average_pct=round(delta_pct, 2),
            summary=summary,
            top_factors=self._top_factors(payload),
            recommendations=build_agronomic_recommendations(payload, predicted_yield, historical_average),
            historical_series=historical_series,
        )

    def history_for(self, crop: str, district: str | None = None) -> list[dict]:
        series = self.metadata["historical_series"][crop]
        if isinstance(series, dict):
            if district is None:
                return next(iter(series.values()))
            return series[district]
        return series

    def _historical_average(self, crop: str, district: str | None = None) -> float:
        average = self.metadata["historical_average"][crop]
        if isinstance(average, dict):
            if district is None:
                return float(next(iter(average.values())))
            return float(average[district])
        return float(average)

    def _feature_frame(self, payload: dict, feature_columns: list[str]) -> pd.DataFrame:
        row = {column: payload[column] for column in feature_columns if column in payload}
        if "soil_nitrogen_ppm" in feature_columns and "soil_nitrogen_ppm" not in row:
            row["soil_nitrogen_ppm"] = payload.get("nitrogen_ppm", 0.0)

        context = self._year_context(payload["year"])
        for field in ("pbs_crops_output_constant_rs_mn", "pbs_important_crops_output_constant_rs_mn"):
            if field in feature_columns and field not in row:
                row[field] = context[field]

        return pd.DataFrame([{column: row[column] for column in feature_columns}])

    def _year_context(self, requested_year: int) -> dict[str, float]:
        lookup = self.metadata.get("annual_feature_lookup")
        if isinstance(lookup, dict) and lookup:
            year = self._nearest_year(requested_year, [int(value) for value in lookup])
            return lookup[str(year)]

        if self.reference_frame.empty:
            return {
                "pbs_crops_output_constant_rs_mn": 0.0,
                "pbs_important_crops_output_constant_rs_mn": 0.0,
            }

        reference = (
            self.reference_frame[["year", "pbs_crops_output_constant_rs_mn", "pbs_important_crops_output_constant_rs_mn"]]
            .drop_duplicates()
            .sort_values("year")
        )
        year = self._nearest_year(requested_year, reference["year"].astype(int).tolist())
        row = reference[reference["year"] == year].iloc[0]
        return {
            "pbs_crops_output_constant_rs_mn": float(row["pbs_crops_output_constant_rs_mn"]),
            "pbs_important_crops_output_constant_rs_mn": float(row["pbs_important_crops_output_constant_rs_mn"]),
        }

    @staticmethod
    def _nearest_year(requested_year: int, available_years: list[int]) -> int:
        eligible = [year for year in available_years if year <= requested_year]
        if eligible:
            return max(eligible)
        return min(available_years)

    def _top_factors(self, payload: dict) -> list[dict]:
        crop_profile = CROP_PROFILES[payload["crop"]]
        return [
            {
                "label": "Rainfall positioning",
                "impact": round(payload["rainfall_mm"] - crop_profile["ideal_rainfall_mm"], 1),
                "summary": (
                    "Current season rainfall is close to target."
                    if abs(payload["rainfall_mm"] - crop_profile["ideal_rainfall_mm"]) < 40
                    else "Rainfall is pushing the forecast away from the crop comfort zone."
                ),
            },
            {
                "label": "Temperature stress",
                "impact": round(crop_profile["ideal_temp_c"] - payload["avg_temp_c"], 1),
                "summary": (
                    "Temperature is within a workable band."
                    if abs(payload["avg_temp_c"] - crop_profile["ideal_temp_c"]) < 2
                    else "Temperature is a meaningful stress signal."
                ),
            },
            {
                "label": "Nitrogen status",
                "impact": round(payload["nitrogen_ppm"] - crop_profile["nitrogen_target"], 1),
                "summary": (
                    "Nitrogen support is near target."
                    if payload["nitrogen_ppm"] >= crop_profile["nitrogen_target"] - 6
                    else "Nitrogen is suppressing forecast potential."
                ),
            },
            {
                "label": "Organic carbon buffer",
                "impact": round(payload["organic_carbon_pct"] - crop_profile["organic_carbon_floor"], 2),
                "summary": (
                    "Organic carbon is helping nutrient stability."
                    if payload["organic_carbon_pct"] >= crop_profile["organic_carbon_floor"]
                    else "Organic carbon is below the preferred floor."
                ),
            },
        ]


@lru_cache(maxsize=1)
def get_yield_service() -> YieldPredictionService:
    return YieldPredictionService()
