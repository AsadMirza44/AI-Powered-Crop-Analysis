from __future__ import annotations

import calendar
import io
import json
import sys
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests
import rioxarray
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from soilgrids import SoilGrids

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from smart_crop_ai.reference_data import CROP_PROFILES, DISTRICT_PROFILES

RAW_DIR = ROOT_DIR / "data" / "raw" / "yield"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models" / "yield"
FAOSTAT_URL = "https://fenixservices.fao.org/faostat/static/bulkdownloads/Production_Crops_Livestock_E_All_Data_(Normalized).zip"
PBS_URL = "https://www.pbs.gov.pk/wp-content/uploads/2020/07/Annual-National-Accounts-Tables-2024-25-P1-May-2025-2.xlsx"
NASA_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"

CROP_ITEM_MAP = {
    "maize": "Maize (corn)",
    "rice": "Rice",
    "wheat": "Wheat",
}

SOILGRID_SPECS = {
    "soil_ph": {"service": "phh2o", "coverage": "phh2o_0-5cm_mean", "scale": 0.1},
    "organic_carbon_pct": {"service": "soc", "coverage": "soc_0-5cm_mean", "scale": 0.01},
    "soil_nitrogen_ppm": {"service": "nitrogen", "coverage": "nitrogen_0-5cm_mean", "scale": 10.0},
}


def ensure_directories() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "nasa").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "soilgrids").mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


def download_if_missing(url: str, target: Path) -> Path:
    if target.exists():
        return target
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    target.write_bytes(response.content)
    return target


def parse_faostat_crop_panel() -> pd.DataFrame:
    archive_path = download_if_missing(FAOSTAT_URL, RAW_DIR / "faostat_production_crops.zip")
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open("Production_Crops_Livestock_E_All_Data_(Normalized).csv") as handle:
            filtered_chunks: list[pd.DataFrame] = []
            for chunk in pd.read_csv(handle, encoding="latin1", chunksize=200000, low_memory=False):
                subset = chunk[
                    (chunk["Area"] == "Pakistan")
                    & (chunk["Item"].isin(CROP_ITEM_MAP.values()))
                    & (chunk["Element"].isin(["Yield", "Area harvested"]))
                    & (chunk["Year"] >= 2001)
                ][["Item", "Element", "Year", "Unit", "Value"]]
                if not subset.empty:
                    filtered_chunks.append(subset)

    frame = pd.concat(filtered_chunks, ignore_index=True)
    item_to_crop = {label: crop for crop, label in CROP_ITEM_MAP.items()}
    frame["crop"] = frame["Item"].map(item_to_crop)
    pivoted = frame.pivot_table(index=["crop", "Year"], columns="Element", values="Value", aggfunc="first").reset_index()
    pivoted = pivoted.rename(columns={"Year": "year", "Area harvested": "cultivated_area_hectares", "Yield": "yield_kg_ha"})
    pivoted["yield_t_ha"] = pivoted["yield_kg_ha"] / 1000.0
    return pivoted[["crop", "year", "cultivated_area_hectares", "yield_t_ha"]].sort_values(["crop", "year"])


def _parse_pbs_year(column_name: str) -> int | None:
    text = str(column_name).strip()
    if not text or text == "nan":
        return None
    text = (
        text.replace("(p)", "")
        .replace("(r)", "")
        .replace("(f)", "")
        .replace("(P)", "")
        .replace("(R)", "")
        .replace("(F)", "")
        .strip()
    )
    if "-" not in text:
        return None
    tail = text.split("-")[-1].strip()
    tail = tail[-2:]
    return 2000 + int(tail)


def parse_pbs_macro_features() -> pd.DataFrame:
    workbook_path = download_if_missing(PBS_URL, RAW_DIR / "pbs_annual_national_accounts.xlsx")
    frame = pd.read_excel(workbook_path, sheet_name="Table 5", header=None)
    header = [str(value).strip() for value in frame.iloc[2].tolist()]
    data = frame.iloc[4:12].copy()
    data.columns = header
    data = data[["Sector/Industry"] + [column for column in header if _parse_pbs_year(column) is not None]].copy()
    data["Sector/Industry"] = data["Sector/Industry"].astype(str).str.strip()

    rows = {
        "crops_output_constant_rs_mn": data[data["Sector/Industry"].str.contains("Crops", case=False, na=False)].iloc[0],
        "important_crops_output_constant_rs_mn": data[data["Sector/Industry"].str.contains("Important Crops", case=False, na=False)].iloc[0],
    }

    records: list[dict] = []
    year_columns = [column for column in data.columns if column != "Sector/Industry"]
    for column in year_columns:
        year = _parse_pbs_year(column)
        if year is None:
            continue
        records.append(
            {
                "year": year,
                "pbs_crops_output_constant_rs_mn": float(rows["crops_output_constant_rs_mn"][column]),
                "pbs_important_crops_output_constant_rs_mn": float(rows["important_crops_output_constant_rs_mn"][column]),
            }
        )
    return pd.DataFrame(records).sort_values("year")


def _season_month_years(crop: str, year: int) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    for month in CROP_PROFILES[crop]["season_months"]:
        month_year = year if month <= 10 else year - 1
        pairs.append((month_year, month))
    return pairs


def fetch_nasa_monthly_payload(district: str, year: int) -> dict:
    cache_path = RAW_DIR / "nasa" / f"{district}_{year}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    profile = DISTRICT_PROFILES[district]
    params = {
        "parameters": "T2M,PRECTOTCORR",
        "community": "AG",
        "longitude": profile["lon"],
        "latitude": profile["lat"],
        "start": str(year),
        "end": str(year),
        "format": "JSON",
    }
    response = requests.get(NASA_URL, params=params, timeout=90)
    response.raise_for_status()
    payload = response.json()
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def build_weather_features(crop: str, year: int) -> dict[str, float]:
    rainfall_totals: list[float] = []
    temp_totals: list[float] = []
    temp_days: list[int] = []

    for district in CROP_PROFILES[crop]["yield_reference_districts"]:
        year_payloads: dict[int, dict] = {}
        for fetch_year, _ in _season_month_years(crop, year):
            if fetch_year not in year_payloads:
                year_payloads[fetch_year] = fetch_nasa_monthly_payload(district, fetch_year)

        rainfall_sum = 0.0
        temp_weighted_sum = 0.0
        total_days = 0

        for fetch_year, month in _season_month_years(crop, year):
            key = f"{fetch_year}{month:02d}"
            parameters = year_payloads[fetch_year]["properties"]["parameter"]
            temp_value = float(parameters["T2M"][key])
            rain_rate = float(parameters["PRECTOTCORR"][key])
            days_in_month = calendar.monthrange(fetch_year, month)[1]
            rainfall_sum += rain_rate * days_in_month
            temp_weighted_sum += temp_value * days_in_month
            total_days += days_in_month

        rainfall_totals.append(rainfall_sum)
        temp_totals.append(temp_weighted_sum)
        temp_days.append(total_days)

    rainfall_mm = float(np.mean(rainfall_totals))
    avg_temp_c = float(np.sum(temp_totals) / max(np.sum(temp_days), 1))
    return {"rainfall_mm": round(rainfall_mm, 3), "avg_temp_c": round(avg_temp_c, 3)}


def sample_soilgrids_property(district: str, feature_name: str) -> float:
    profile = DISTRICT_PROFILES[district]
    spec = SOILGRID_SPECS[feature_name]
    target_path = RAW_DIR / "soilgrids" / f"{district}_{feature_name}.tif"

    if not target_path.exists():
        soilgrids = SoilGrids()
        delta = 0.2
        soilgrids.get_coverage_data(
            spec["service"],
            spec["coverage"],
            "urn:ogc:def:crs:EPSG::4326",
            profile["lon"] - delta,
            profile["lat"] - delta,
            profile["lon"] + delta,
            profile["lat"] + delta,
            str(target_path),
            width=40,
            height=40,
        )

    raster = rioxarray.open_rasterio(target_path)
    values = raster.values[0].astype("float32")
    valid = values[values != -32768]
    if valid.size == 0:
        raise RuntimeError(f"SoilGrids returned no valid data for {district} {feature_name}.")
    return round(float(valid.mean()) * float(spec["scale"]), 3)


def build_soil_features(crop: str) -> dict[str, float]:
    soil_values: dict[str, list[float]] = {key: [] for key in SOILGRID_SPECS}
    for district in CROP_PROFILES[crop]["yield_reference_districts"]:
        for feature_name in SOILGRID_SPECS:
            soil_values[feature_name].append(sample_soilgrids_property(district, feature_name))
    return {feature_name: round(float(np.mean(values)), 3) for feature_name, values in soil_values.items()}


def build_training_dataset() -> pd.DataFrame:
    faostat_df = parse_faostat_crop_panel()
    pbs_df = parse_pbs_macro_features()
    weather_records: list[dict] = []
    soil_records = {crop: build_soil_features(crop) for crop in CROP_ITEM_MAP}

    for crop in CROP_ITEM_MAP:
        crop_years = faostat_df.loc[faostat_df["crop"] == crop, "year"].tolist()
        for year in crop_years:
            weather = build_weather_features(crop, int(year))
            record = {"crop": crop, "year": int(year), **weather, **soil_records[crop]}
            weather_records.append(record)

    weather_df = pd.DataFrame(weather_records)
    dataset = faostat_df.merge(weather_df, on=["crop", "year"], how="left").merge(pbs_df, on="year", how="left")
    dataset = dataset.dropna().sort_values(["crop", "year"]).reset_index(drop=True)
    dataset_path = PROCESSED_DIR / "pakistan_multi_crop_yield_dataset.csv"
    dataset.to_csv(dataset_path, index=False)
    return dataset


def train() -> None:
    ensure_directories()
    dataset = build_training_dataset()

    feature_columns = [
        "crop",
        "year",
        "rainfall_mm",
        "avg_temp_c",
        "soil_ph",
        "organic_carbon_pct",
        "soil_nitrogen_ppm",
        "cultivated_area_hectares",
        "pbs_crops_output_constant_rs_mn",
        "pbs_important_crops_output_constant_rs_mn",
    ]

    train_df = dataset[dataset["year"] <= dataset["year"].max() - 3].copy()
    test_df = dataset[dataset["year"] > dataset["year"].max() - 3].copy()

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["crop"]),
            (
                "numeric",
                "passthrough",
                [
                    "year",
                    "rainfall_mm",
                    "avg_temp_c",
                    "soil_ph",
                    "organic_carbon_pct",
                    "soil_nitrogen_ppm",
                    "cultivated_area_hectares",
                    "pbs_crops_output_constant_rs_mn",
                    "pbs_important_crops_output_constant_rs_mn",
                ],
            ),
        ]
    )

    candidate_models = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=320, random_state=42, max_depth=12),
        "hist_gradient_boosting": HistGradientBoostingRegressor(random_state=42, max_depth=6),
    }

    best_name = ""
    best_pipeline: Pipeline | None = None
    best_metrics = {"r2": float("-inf")}
    candidate_metrics: dict[str, dict[str, float]] = {}

    for name, estimator in candidate_models.items():
        pipeline = Pipeline([("preprocessor", preprocessor), ("model", estimator)])
        pipeline.fit(train_df[feature_columns], train_df["yield_t_ha"])
        predictions = pipeline.predict(test_df[feature_columns])
        rmse = float(np.sqrt(mean_squared_error(test_df["yield_t_ha"], predictions)))
        metrics = {
            "rmse": round(rmse, 4),
            "mae": round(float(mean_absolute_error(test_df["yield_t_ha"], predictions)), 4),
            "r2": round(float(r2_score(test_df["yield_t_ha"], predictions)), 4),
        }
        candidate_metrics[name] = metrics
        if metrics["r2"] > best_metrics["r2"]:
            best_name = name
            best_pipeline = pipeline
            best_metrics = metrics

    if best_pipeline is None:
        raise RuntimeError("Yield model selection failed.")

    model_path = MODELS_DIR / "smart_crop_yield_model.joblib"
    metadata_path = MODELS_DIR / "smart_crop_yield_metadata.json"
    joblib.dump(best_pipeline, model_path)

    historical_series: dict[str, list[dict]] = {}
    historical_average: dict[str, float] = {}
    for crop_code, crop_df in dataset.groupby("crop"):
        series = crop_df[["year", "yield_t_ha"]].sort_values("year").to_dict(orient="records")
        historical_series[crop_code] = series
        historical_average[crop_code] = round(float(crop_df["yield_t_ha"].mean()), 3)

    metadata = {
        "feature_columns": feature_columns,
        "best_model": best_name,
        "candidate_metrics": candidate_metrics,
        "historical_series": historical_series,
        "historical_average": historical_average,
        "history_context": "Pakistan historical average",
        "annual_feature_lookup": {
            str(int(year)): {
                "pbs_crops_output_constant_rs_mn": float(frame["pbs_crops_output_constant_rs_mn"].iloc[0]),
                "pbs_important_crops_output_constant_rs_mn": float(frame["pbs_important_crops_output_constant_rs_mn"].iloc[0]),
            }
            for year, frame in dataset.groupby("year")
        },
        "notes": (
            "Real-data scikit-learn yield baseline built from FAOSTAT crop statistics, "
            "PBS annual crop-output series, NASA POWER seasonal weather aggregates, and SoilGrids soil properties."
        ),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Saved yield dataset to {PROCESSED_DIR / 'pakistan_multi_crop_yield_dataset.csv'}")
    print(f"Saved scikit-learn yield model to {model_path}")
    print(f"Saved metadata to {metadata_path}")
    print(f"Best model: {best_name}")


if __name__ == "__main__":
    train()
