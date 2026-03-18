# Smart Crop AI

The repository follows the proposal-aligned architecture directly: a `Django` web dashboard backed by `TensorFlow`, `OpenCV`, `Scikit-learn`, and a local database.

## Active Stack

- `Web`: Django
- `Disease pipeline`: TensorFlow + OpenCV
- `Yield pipeline`: Scikit-learn
- `Recommendations`: rule-based irrigation and fertilizer engine
- `Database`: SQLite
- `Delivery`: local web application for clone-and-run handover

## What Is Working Now

- monitoring overview dashboard
- disease upload flow for `maize`, `potato`, `tomato`, `cotton`, and `sugarcane` with TensorFlow prediction and visual overlay
- yield forecasting form for `maize`, `wheat`, `rice`, `cotton`, and `sugarcane`, backed by FAOSTAT, PBS, NASA POWER, and SoilGrids features
- irrigation and fertilizer recommendations
- separate recommendation center
- stored prediction history
- Django admin support
- local tests for overview, disease upload, yield forecasting, and recommendation routes

## Run Locally

The repository already includes the trained model files and processed dataset files needed for normal use.

For normal project execution, do **not** retrain the models.

### Prerequisites

- Python `3.11` recommended
- Windows PowerShell

### Setup

If you cloned the outer repository, first move into the Django project folder:

```powershell
git clone <your-github-repo-url>
cd AI-Powered-Crop-Analysis\crop-ai-dashboard
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` is the normal clone-and-run dependency file. It is enough for running the dashboard locally.

Apply database migrations:

```powershell
python manage.py migrate
```

Start the project:

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

The repository already includes a local `.env` file for zero-setup sharing. Edit it only if you want to change local host settings.

### Main Pages

- `/` overview dashboard
- `/disease/` crop disease analysis
- `/yield/` yield prediction
- `/recommendations/` recommendation center
- `/metrics/` model metrics
- `/sources/` data sources and limitations

### Optional Validation

Run the built-in tests:

```powershell
python manage.py test
```

## Data And Model Status

The app is fully runnable and the active artifacts now use real public data sources:

- disease model: TensorFlow MobileNetV2 transfer-learning baseline trained from `PlantVillage`, `PlantDoc`, and public `Mendeley` cotton/sugarcane disease datasets
- yield model: scikit-learn regressor trained from `FAOSTAT` crop statistics, `PBS` crop-output context, `NASA POWER` weather, and `SoilGrids` soil properties

Validated crop coverage:

- disease: `maize`, `potato`, `tomato`, `cotton`, `sugarcane`
- yield: `maize`, `wheat`, `rice`, `cotton`, `sugarcane`

## Optional Retraining

Retraining is optional. Use it only if you want to rebuild the shipped model artifacts.

Dependency rule:

- for normal project usage, install only `requirements.txt`
- for retraining, keep the normal runtime install and then install `requirements-training.txt` as an extra layer

If you already completed the normal setup above, install the extra training dependencies with:

```powershell
pip install -r requirements-training.txt
```

If you are setting up a retraining-only environment from scratch, `requirements-training.txt` already includes `requirements.txt`.

- `python training\disease\train_demo_disease_model.py`
- `python training\yield\train_yield_model.py --refresh-sources`

## Key Data Outputs

- `data/processed/disease/disease_dataset_manifest.csv`
- `data/processed/pakistan_multi_crop_yield_dataset.csv`
- `models/disease/smart_crop_disease.keras`
- `models/yield/smart_crop_yield_model.joblib`

## Archived Legacy Code

The earlier `Next.js + FastAPI` prototype was moved out of this repository into a separate local archive and is not part of the handover package.
