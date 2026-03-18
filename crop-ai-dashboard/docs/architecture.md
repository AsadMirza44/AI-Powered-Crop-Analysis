# Architecture Notes

## Active Implementation

```text
Browser
  -> Django web application
       -> dashboard templates and static assets
       -> TensorFlow + OpenCV disease diagnostics
       -> scikit-learn yield forecasting
       -> irrigation and fertilizer recommendations
       -> recommendation center
       -> prediction history
       -> Django admin
       -> SQLite configuration
```

## What Changed

The Django implementation is now the only active runtime path in this repository. The older `Next.js + FastAPI + ONNX + XGBoost` code was moved into a separate local archive and is not part of this handover repository.

## Current Runtime Notes

- `SQLite` is the active database and the app runs immediately without extra database setup.
- TensorFlow and scikit-learn artifacts are stored under `models/`.
- Disease training now uses `PlantVillage + PlantDoc`.
- Yield training now uses `FAOSTAT + PBS + NASA POWER + SoilGrids`.
- Uploaded media and overlays are stored under `media/`.

## Current Limitation

The architecture now runs on real public data, but the yield history context is still Pakistan-level rather than district-labeled ground truth.
