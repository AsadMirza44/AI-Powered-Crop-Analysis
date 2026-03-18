---
title: Smart Crop AI
emoji: "\U0001F33E"
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
suggested_hardware: cpu-basic
startup_duration_timeout: 1h
short_description: Django crop monitoring dashboard with TensorFlow disease detection and scikit-learn yield forecasting.
---

# Smart Crop AI

The repository now follows the proposal-aligned architecture directly: a `Django` web dashboard backed by `TensorFlow`, `OpenCV`, `Scikit-learn`, and a local database.

## Active Stack

- `Web`: Django
- `Disease pipeline`: TensorFlow + OpenCV
- `Yield pipeline`: Scikit-learn
- `Recommendations`: rule-based irrigation and fertilizer engine
- `Database`: SQLite by default, `MySQL Community` ready through environment variables
- `Delivery`: local web application

## What Is Working Now

- monitoring overview dashboard
- disease upload flow with PlantVillage + PlantDoc TensorFlow prediction and visual overlay
- yield forecasting form backed by FAOSTAT, PBS, NASA POWER, and SoilGrids features
- irrigation and fertilizer recommendations
- separate recommendation center
- stored prediction history
- Django admin support
- local tests for overview, disease upload, yield forecasting, and recommendation routes

## Quick Start

```powershell
cd C:\Users\AsadMirza\source\repos\crop-ai-dashboard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python training\disease\train_demo_disease_model.py
python training\yield\train_yield_model.py
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Hugging Face Spaces Deployment

This repository is prepared for `Hugging Face Spaces` as a `Docker` Space.

Files added for deployment:

- `Dockerfile`
- `.dockerignore`
- `space-entrypoint.sh`
- `requirements-space.txt`

Recommended steps:

1. Create a new `Docker` Space on Hugging Face.
2. Push this repository to the Space.
3. Add these Space secrets/variables:
   - `DJANGO_SECRET_KEY`
   - `DJANGO_DEBUG=0`
   - `DJANGO_ALLOWED_HOSTS=<your-space-subdomain>.hf.space`
   - `DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-space-subdomain>.hf.space`
4. Let the build finish and verify:
   - `/`
   - `/disease/`
   - `/yield/`
   - `/recommendations/`
   - `/metrics/`
   - `/sources/`

Important deployment limitation:

- the free Space is effectively stateless for this project, so `SQLite` history, uploaded images, and generated overlays can reset after rebuilds or restarts.

## MySQL Option

If MySQL Community is installed locally, set these variables in `.env` or your shell before running:

- `MYSQL_DB`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_HOST`
- `MYSQL_PORT`

If those variables are empty, Django falls back to `SQLite` so the project still runs without extra setup.

## Data And Model Status

The app is fully runnable and the active artifacts now use real public data sources:

- disease model: TensorFlow MobileNetV2 transfer-learning baseline trained from `PlantVillage` and `PlantDoc`
- yield model: scikit-learn regressor trained from `FAOSTAT` crop statistics, `PBS` crop-output context, `NASA POWER` weather, and `SoilGrids` soil properties

## Key Commands

```powershell
python manage.py runserver
python manage.py test
python training\disease\train_demo_disease_model.py
python training\yield\train_yield_model.py
```

## Key Data Outputs

- `data/processed/disease/disease_dataset_manifest.csv`
- `data/processed/pakistan_multi_crop_yield_dataset.csv`
- `models/disease/smart_crop_disease.keras`
- `models/yield/smart_crop_yield_model.joblib`

## Archived Legacy Code

The earlier `Next.js + FastAPI` prototype was moved out of this repository to:

`C:\Users\AsadMirza\source\repos\crop-ai-dashboard-legacy-archive`
