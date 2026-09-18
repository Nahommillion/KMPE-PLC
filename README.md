# KMPE PLC Website

A dark cinematic Flask website for KMPE PLC, with public pages and a private admin panel for projects, images, news, vacancies and contact messages.

## Deploy to Render

1. Push these files to a GitHub repository.
2. In Render, create a new Web Service from the repository.
3. Render can use `render.yaml`, or enter:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Set environment variables:
   - `ADMIN_USERNAME` = your admin username
   - `ADMIN_PASSWORD` = your strong admin password
   - `SECRET_KEY` = a long random secret
   - `DATA_DIR` = `/var/data`
5. The included `render.yaml` requests a 1 GB persistent disk at `/var/data` so SQLite data and uploaded images can persist. Availability/pricing of persistent disks depends on the Render plan.

## Admin

Public navigation does not show the admin link. Open `/admin` directly and sign in with the Render environment-variable credentials.

## Important

Do not commit a real `.env` file or real admin password to GitHub. Use Render environment variables.

## Main features

- Dark cinematic metallic design
- Responsive desktop/mobile layout
- Animated scroll reveals and hero interaction
- Fountain, finishing and construction service sections
- Projects/gallery
- News
- Vacancies
- Contact form stored in the database
- Private admin login
- Admin image upload
- Admin project/news/vacancy management
- Contact message inbox
- Health endpoint at `/health`
