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
       -> report and CSV export views
       -> prediction history
       -> Django admin
       -> SQLite default / MySQL-ready configuration
```

## What Changed

The Django implementation is now the only active runtime path in this repository. The older `Next.js + FastAPI + ONNX + XGBoost` code was moved to:

`C:\Users\AsadMirza\source\repos\crop-ai-dashboard-legacy-archive`

## Current Runtime Notes

- `SQLite` is the zero-setup default so the app runs immediately.
- `MySQL Community` is supported through environment variables and should be used when local MySQL is available.
- TensorFlow and scikit-learn artifacts are stored under `models/`.
- Disease training now uses `PlantVillage + PlantDoc`.
- Yield training now uses `FAOSTAT + PBS + NASA POWER + SoilGrids`.
- Uploaded media and overlays are stored under `media/`.

## Current Limitation

The architecture now runs on real public data, but the yield history context is still Pakistan-level rather than district-labeled ground truth. The remaining work is presentation-grade evidence capture and final write-up packaging.
