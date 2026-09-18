# KMPE PLC Website
Flask construction company website with public pages and an admin dashboard.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`

This version does NOT require a Render persistent disk.
Without persistent storage, SQLite data and uploaded images may be lost after a redeploy/restart.
