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

## MySQL Community Path

If MySQL Community is installed, the same app can switch databases by setting:

- `MYSQL_DB`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_HOST`
- `MYSQL_PORT`

## Why This Fits The Proposal

- Python-first architecture
- proposal-aligned libraries
- no cloud dependency required
- realistic dashboard delivered through the web interface
