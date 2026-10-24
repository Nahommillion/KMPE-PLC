# KPME PLC Website

Flask website for KPME PLC with a private admin dashboard and individual public pages.

## Public pages
- `/` — Home page with an automatic project-photo carousel
- `/about` — About the company
- `/services` — Enabled services
- `/services/<service_id>` — Service-specific project portfolio
- `/projects` — All projects and status filters
- `/projects?status=Completed` — Completed projects (also `Ongoing`, `Pending`, `Other`)
- `/projects/<project_id>` — Project description and automatic multi-photo gallery
- `/news` and `/news/<news_id>` — News list and news detail/gallery
- `/vacancies` — Published vacancies and application forms
- `/contact` — Contact details, social links and contact form
- `/login` — Admin login (also `/admin`)
- `/admin/dashboard` — Admin dashboard

## Run locally
```bash
pip install -r requirements.txt
python app.py
```

Set `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `SECRET_KEY` in the environment before deployment. Do not use the development fallback password in production.

## Render deployment and uploads
The included `render.yaml` uses `/var/data` for the SQLite database and uploaded files and defines a persistent disk. In the Render service settings, confirm a persistent disk is actually attached and mounted at `/var/data`; if the existing Render service was created without the disk from this Blueprint, add/configure it there. Uploaded project images, company logo, news images, CV files and the SQLite database are stored under `DATA_DIR` and can be lost on redeploy if it points to an ephemeral filesystem.

## Admin usage
1. Sign in at `/login`.
2. Upload the company logo in Website Content. The logo is used in the login screen, public header/footer and admin sidebar.
3. Add services and choose whether they are visible.
4. Add projects with a category, description, status and multiple images. Visitors can open each project and step through its photo gallery. Home automatically rotates through uploaded project images.
5. Publish news with multiple images and manage vacancies and contact messages.
6. Add social URLs in Website Content; valid links appear on the Contact page and in the site footer.

The generated SVG wordmark at `static/images/kpme-logo.svg` is the default until a company logo is uploaded.

## Additional public pages
- `/vision`, `/mission`, and `/values` are individual company-information pages. Their headings and descriptions can be edited from **Admin > Website Editor**.
- `/tender` is the public tenders/procurement information page; its heading and description are editable from the admin panel.
- `/media` automatically displays uploaded project and published-news photographs.
- The home page has both an automatic featured-project slideshow and a continuously moving project-photo ribbon. Add project images from **Admin > Projects & Gallery** to populate both.

If a service detail page previously returned an Internal Server Error, the detail route now passes the public settings required by the shared header/footer. Startup migrations also normalize the service table columns used by the current app.
