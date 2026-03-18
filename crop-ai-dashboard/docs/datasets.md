# Dataset Strategy

## Active Goal

Use free and public data sources that support a proposal-aligned implementation with:

- disease detection,
- yield prediction,
- irrigation recommendation,
- fertilizer recommendation,
- a realistic monitoring dashboard.

## Disease Data

### Primary Sources

- `PlantVillage`: baseline disease classification
- `PlantDoc`: field-style disease images for realism

### Optional Source

- custom smartphone images collected locally for final evaluation

### Disease Data Notes

- Start with PlantVillage to build the first stable TensorFlow classifier.
- Use PlantDoc to improve robustness on more realistic backgrounds.
- Use OpenCV during preprocessing and explainability rendering.

## Yield Data

### Primary Sources

- `Pakistan Bureau of Statistics`
- `FAOSTAT`

### Enrichment Sources

- `NASA POWER` for weather variables
- `SoilGrids` for soil variables

### Optional Later Source

- vegetation indices such as `NDVI` or `EVI` if free time remains

## Crop Coverage Strategy

The plan stays broad, but data quality controls the final validated crop list.

- disease coverage target: `tomato`, `potato`, `maize/corn`
- yield coverage target: `maize`, `wheat`, `rice`

If some crops do not have clean free historical data, keep the architecture crop-aware and document which crops are validated in the final report.

## Data Assembly Rules

1. Do not mix incompatible spatial levels.
2. Do not mix incompatible seasonal windows.
3. Prefer official data over scraped unofficial tables.
4. Document every dataset link, license note, and citation requirement.
5. Store raw, interim, and processed data separately.

## Planned Folder Use

- `data/raw/`: downloaded source files
- `data/interim/`: cleaned but not final tables
- `data/processed/`: model-ready image manifests and tabular datasets

## Current Repository Reality

The repository now includes processed real-data artifacts for the active Django implementation:

- `models/disease/smart_crop_disease.keras`
- `models/yield/smart_crop_yield_model.joblib`
- `data/processed/disease/disease_dataset_manifest.csv`
- `data/processed/pakistan_multi_crop_yield_dataset.csv`

Current caveat: the yield dataset uses real Pakistan crop statistics and real weather/soil enrichment, but the historical comparison context remains Pakistan-level rather than district-labeled yield history. That should be stated clearly in the final report.
