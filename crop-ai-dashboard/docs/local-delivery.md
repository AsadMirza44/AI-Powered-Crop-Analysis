# Local Delivery Notes

## Active Run Mode

The project now runs as a local Django application.

```powershell
python manage.py migrate
python manage.py runserver
```

## Local Storage

- `db.sqlite3` for zero-setup local runs
- `media/` for uploaded images and overlays
- `models/` for TensorFlow and scikit-learn artifacts

## Why This Fits The Proposal

- Python-first architecture
- proposal-aligned libraries
- no cloud dependency required
- realistic dashboard delivered through the web interface
