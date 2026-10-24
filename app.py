import os
import json
import sqlite3
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, flash, g, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
DATABASE = os.path.join(DATA_DIR, "kmpe.db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.secret_key = os.environ.get("SECRET_KEY", "CHANGE_THIS_SECRET_KEY")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE, timeout=30)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_database():
    db = sqlite3.connect(DATABASE, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            description TEXT,
            image TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            image TEXT,
            published INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            location TEXT,
            employment_type TEXT,
            description TEXT,
            requirements TEXT,
            closing_date TEXT,
            published INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT
        );
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, vacancy_id INTEGER, full_name TEXT NOT NULL,
            email TEXT NOT NULL, phone TEXT, education TEXT, experience TEXT, cover_letter TEXT,
            cv_filename TEXT, created_at TEXT NOT NULL,
            FOREIGN KEY(vacancy_id) REFERENCES vacancies(id) ON DELETE SET NULL
        );
    """)
    # Safe schema migrations keep existing production databases and content intact.
    for table in ("projects", "news"):
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        if "images_json" not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN images_json TEXT DEFAULT '[]'")
    project_columns = {row[1] for row in db.execute("PRAGMA table_info(projects)").fetchall()}
    if "status" not in project_columns:
        db.execute("ALTER TABLE projects ADD COLUMN status TEXT DEFAULT 'Completed'")
    db.execute("""CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        icon TEXT DEFAULT '',
        enabled INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )""")
    # Normalize older service tables created by previous website versions.
    service_columns = {row[1] for row in db.execute("PRAGMA table_info(services)").fetchall()}
    for column, definition in (("title", "TEXT"), ("description", "TEXT DEFAULT ''"), ("icon", "TEXT DEFAULT ''"), ("enabled", "INTEGER DEFAULT 1"), ("created_at", "TEXT DEFAULT ''")):
        if column not in service_columns:
            db.execute(f"ALTER TABLE services ADD COLUMN {column} {definition}")
    service_columns = {row[1] for row in db.execute("PRAGMA table_info(services)").fetchall()}
    if "name" in service_columns:
        db.execute("UPDATE services SET title=name WHERE title IS NULL OR trim(title)=''")
    if "category" in service_columns:
        db.execute("UPDATE services SET title=category WHERE title IS NULL OR trim(title)=''")
    db.execute("UPDATE services SET title='Service' WHERE title IS NULL OR trim(title)=''")
    db.execute("UPDATE services SET created_at=? WHERE created_at IS NULL OR trim(created_at)=''", (now(),))
    defaults = {
        "about_heading": "Craftsmanship with a construction mindset.",
        "about_text": "KPME PLC is a construction company focused on practical, high-quality execution across fountain works, finishing works and wider construction activities.",
        "about_extra": "We showcase completed work, company news, career opportunities and make it easy for clients to contact our team.",
        "vision_heading": "Our Vision",
        "vision_text": "To be a trusted construction and finishing partner, recognized for quality, innovation and lasting value.",
        "mission_heading": "Our Mission",
        "mission_text": "To deliver reliable construction, fountain and finishing solutions through skilled workmanship, careful planning and client-focused service.",
        "values_heading": "Our Values",
        "values_text": "Quality, integrity, safety, accountability, teamwork and respect for every client and project.",
        "tender_heading": "Tenders & Procurement",
        "tender_text": "KPME PLC tender announcements and procurement notices will be published here. Please use the Contact page for inquiries.",
        "hero_heading": "Building spaces that leave a mark.",
        "hero_text": "Fountain works, finishing works and construction solutions delivered with precision, craftsmanship and a modern vision.",
        "contact_heading": "Let's build something remarkable.", "contact_text": "Tell us about your construction, fountain or finishing project.",
        "contact_location": "Ethiopia", "contact_email": "info@kpmeplc.com", "contact_phone": "+251 XXX XXX XXX",
        "service1_title": "Fountain Works", "service1_text": "Fountain construction, water-feature works and finishing details designed for attractive public and private spaces.",
        "service2_title": "Finishing Works", "service2_text": "Interior and exterior finishing activities with attention to clean workmanship and detail.",
        "service3_title": "Construction Works", "service3_text": "General construction and civil works delivered with organized execution and quality control.",
        "service4_title": "Special Works", "service4_text": "Additional construction activities tailored to client needs.",
        "social_facebook": "", "social_instagram": "", "social_linkedin": "", "social_telegram": "", "social_youtube": "", "social_tiktok": "", "logo_filename": ""
    }
    for key, value in defaults.items():
        db.execute("INSERT OR IGNORE INTO settings(setting_key,setting_value) VALUES(?,?)", (key, value))
    if db.execute("SELECT COUNT(*) FROM services").fetchone()[0] == 0:
        seed_services = [
            ("Fountain Works", "Fountain construction, water features and related installations.", "", 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("Finishing Works", "Interior and exterior finishing, surfaces and detailed workmanship.", "", 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("Construction Works", "General construction and coordinated civil works.", "", 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("Special Works", "Specialized works tailored to client needs.", "", 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ]
        db.executemany("INSERT INTO services(title,description,icon,enabled,created_at) VALUES(?,?,?,?,?)", seed_services)
    db.commit()
    db.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def allowed_file(filename):
    return bool(filename and "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS)


def save_uploaded_image(file):
    if not file or not file.filename or not allowed_file(file.filename):
        return None
    original = secure_filename(file.filename)
    ext = os.path.splitext(original)[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    file.save(os.path.join(UPLOAD_DIR, filename))
    return filename


def save_uploaded_images(files):
    saved = []
    for file in files or []:
        if file and file.filename:
            filename = save_uploaded_image(file)
            if filename:
                saved.append(filename)
    return saved


def collect_images(row):
    """Return legacy single image plus any newer gallery images, without duplicates."""
    try:
        images = json.loads(row.get("images_json") or "[]") if isinstance(row, dict) else json.loads(row["images_json"] or "[]")
    except (ValueError, TypeError, KeyError):
        images = []
    legacy = row.get("image") if isinstance(row, dict) else row["image"]
    result = []
    for filename in ([legacy] if legacy else []) + (images if isinstance(images, list) else []):
        if filename and filename not in result:
            result.append(filename)
    return result


def enrich_gallery(rows):
    enriched = []
    for row in rows:
        item = dict(row)
        item["gallery"] = collect_images(item)
        enriched.append(item)
    return enriched


def delete_uploaded_image(filename):
    if filename:
        path = os.path.join(UPLOAD_DIR, os.path.basename(filename))
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year, "site_logo": public_settings().get("logo_filename", "") if request else ""}


def public_settings():
    db = get_db()
    return {r["setting_key"]: r["setting_value"] for r in db.execute("SELECT setting_key,setting_value FROM settings").fetchall()}


def public_services():
    return get_db().execute("SELECT * FROM services WHERE enabled=1 ORDER BY id").fetchall()


def public_projects(limit=None):
    sql = "SELECT * FROM projects ORDER BY id DESC"
    if limit:
        sql += " LIMIT ?"
        rows = get_db().execute(sql, (limit,)).fetchall()
    else:
        rows = get_db().execute(sql).fetchall()
    return enrich_gallery(rows)


@app.route("/")
def home():
    db = get_db()
    projects = public_projects(12)
    news = enrich_gallery(db.execute("SELECT * FROM news WHERE published=1 ORDER BY id DESC LIMIT 3").fetchall())
    services = public_services()
    vacancies = db.execute("SELECT * FROM vacancies WHERE published=1 ORDER BY id DESC LIMIT 3").fetchall()
    settings = public_settings()
    slides = []
    for project in projects:
        for photo in project["gallery"]:
            slides.append({"filename": photo, "title": project["title"], "description": project["description"], "status": project.get("status") or "Completed"})
    return render_template("home.html", projects=projects, news=news, vacancies=vacancies, settings=settings, services=services, slides=slides[:16])


@app.route("/about")
def about_page():
    return render_template("about.html", settings=public_settings())


@app.route("/vision")
def vision_page():
    return render_template("company_page.html", page_key="vision", heading_key="vision_heading", text_key="vision_text", settings=public_settings())


@app.route("/mission")
def mission_page():
    return render_template("company_page.html", page_key="mission", heading_key="mission_heading", text_key="mission_text", settings=public_settings())


@app.route("/values")
def values_page():
    return render_template("company_page.html", page_key="values", heading_key="values_heading", text_key="values_text", settings=public_settings())


@app.route("/tender")
def tender_page():
    return render_template("company_page.html", page_key="tender", heading_key="tender_heading", text_key="tender_text", settings=public_settings())


@app.route("/media")
def media_page():
    projects = public_projects()
    news = enrich_gallery(get_db().execute("SELECT * FROM news WHERE published=1 ORDER BY id DESC").fetchall())
    media = []
    for project in projects:
        for filename in project["gallery"]:
            media.append({"filename": filename, "title": project["title"], "description": project["description"] or "", "kind": "Project"})
    for item in news:
        for filename in item["gallery"]:
            media.append({"filename": filename, "title": item["title"], "description": item["content"] or "", "kind": "News"})
    return render_template("media.html", media=media, settings=public_settings())


@app.route("/services")
def services_page():
    return render_template("services.html", services=public_services(), settings=public_settings())


@app.route("/projects")
def projects_page():
    status = request.args.get("status", "All").strip()
    valid_statuses = ["Completed", "Ongoing", "Pending", "Other"]
    projects = public_projects()
    if status in valid_statuses:
        projects = [p for p in projects if (p.get("status") or "Completed").lower() == status.lower()]
    elif status != "All":
        status = "All"
    return render_template("projects.html", projects=projects, status=status, statuses=valid_statuses, settings=public_settings())


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    row = get_db().execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        return redirect(url_for("projects_page"))
    project = enrich_gallery([row])[0]
    return render_template("project_detail.html", project=project, settings=public_settings())


@app.route("/news")
def news_page():
    rows = get_db().execute("SELECT * FROM news WHERE published=1 ORDER BY id DESC").fetchall()
    return render_template("news.html", news=enrich_gallery(rows), settings=public_settings())


@app.route("/news/<int:news_id>")
def news_detail(news_id):
    row = get_db().execute("SELECT * FROM news WHERE id=? AND published=1", (news_id,)).fetchone()
    if not row:
        return redirect(url_for("news_page"))
    return render_template("news_detail.html", item=enrich_gallery([row])[0], settings=public_settings())


@app.route("/vacancies")
def vacancies_page():
    vacancies = get_db().execute("SELECT * FROM vacancies WHERE published=1 ORDER BY id DESC").fetchall()
    return render_template("vacancies.html", vacancies=vacancies, settings=public_settings())


@app.route("/contact")
def contact_page():
    return render_template("contact.html", settings=public_settings())


# Compatibility endpoint for legacy templates and existing links.
app.add_url_rule("/", endpoint="index", view_func=home)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    message = request.form.get("message", "").strip()
    if not name or not message:
        flash("Please enter your name and message.", "error")
        return redirect(url_for("contact_page"))
    db = get_db()
    db.execute("INSERT INTO messages(name,email,phone,message,is_read,created_at) VALUES(?,?,?,?,?,?)", (name, email, phone, message, 0, now()))
    db.commit()
    flash("Thank you. Your message has been received.", "success")
    return redirect(url_for("contact_page"))


@app.route("/login", methods=["GET", "POST"])
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect username or password.", "error")
    logo = get_db().execute("SELECT setting_value FROM settings WHERE setting_key='logo_filename'").fetchone()
    return render_template("login.html", logo_filename=(logo[0] if logo else ""))


@app.route("/admin/site-content", methods=["POST"])
@admin_required
def save_site_content():
    keys = ["hero_heading", "hero_text", "about_heading", "about_text", "about_extra", "vision_heading", "vision_text", "mission_heading", "mission_text", "values_heading", "values_text", "tender_heading", "tender_text", "service1_title", "service1_text", "service2_title", "service2_text", "service3_title", "service3_text", "service4_title", "service4_text", "contact_heading", "contact_text", "contact_location", "contact_email", "contact_phone", "social_facebook", "social_instagram", "social_linkedin", "social_telegram", "social_youtube", "social_tiktok"]
    db = get_db()
    logo = request.files.get("logo")
    if logo and logo.filename:
        logo_filename = save_uploaded_image(logo)
        if logo_filename:
            db.execute("INSERT INTO settings(setting_key,setting_value) VALUES('logo_filename',?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value", (logo_filename,))
    for key in keys:
        db.execute("INSERT INTO settings(setting_key,setting_value) VALUES(?,?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value", (key, request.form.get(key, "").strip()))
    db.commit()
    flash("Website content updated successfully.", "success")
    return redirect(url_for("admin_dashboard") + "#site-content-admin")


@app.route("/careers/apply/<int:vacancy_id>", methods=["POST"])
def apply_vacancy(vacancy_id):
    db = get_db()
    vacancy = db.execute("SELECT id FROM vacancies WHERE id=? AND published=1", (vacancy_id,)).fetchone()
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    if not vacancy or not full_name or not email:
        flash("Please provide your full name and email to apply.", "error")
        return redirect(url_for("vacancies_page"))
    cv = request.files.get("cv")
    cv_filename = None
    if cv and cv.filename:
        if cv.filename.rsplit(".", 1)[-1].lower() not in {"pdf", "doc", "docx"}:
            flash("CV must be a PDF, DOC, or DOCX file.", "error")
            return redirect(url_for("vacancies_page"))
        ext = secure_filename(cv.filename).rsplit(".", 1)[-1].lower()
        cv_filename = f"{uuid.uuid4().hex}.{ext}"
        cv.save(os.path.join(UPLOAD_DIR, cv_filename))
    db.execute("INSERT INTO applications(vacancy_id,full_name,email,phone,education,experience,cover_letter,cv_filename,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (vacancy_id, full_name, email, request.form.get("phone", "").strip(), request.form.get("education", "").strip(), request.form.get("experience", "").strip(), request.form.get("cover_letter", "").strip(), cv_filename, now()))
    db.commit()
    flash("Your application has been submitted successfully.", "success")
    return redirect(url_for("vacancies_page"))


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    db = get_db()
    projects = enrich_gallery(db.execute("SELECT * FROM projects ORDER BY id DESC").fetchall())
    news = enrich_gallery(db.execute("SELECT * FROM news ORDER BY id DESC").fetchall())
    services = db.execute("SELECT * FROM services ORDER BY id").fetchall()
    vacancies = db.execute("SELECT * FROM vacancies ORDER BY id DESC").fetchall()
    messages = db.execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
    applications = db.execute("SELECT applications.*, vacancies.title AS vacancy_title FROM applications LEFT JOIN vacancies ON vacancies.id=applications.vacancy_id ORDER BY applications.id DESC").fetchall()
    settings = {r["setting_key"]: r["setting_value"] for r in db.execute("SELECT setting_key,setting_value FROM settings").fetchall()}
    unread_messages = db.execute("SELECT COUNT(*) FROM messages WHERE is_read=0").fetchone()[0]
    return render_template("admin.html", projects=projects, news=news, vacancies=vacancies, messages=messages, applications=applications, settings=settings, unread_messages=unread_messages, services=services)


@app.route("/admin/projects/add", methods=["POST"])
@admin_required
def add_project():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    status = request.form.get("status", "Completed").strip()
    if status not in {"Completed", "Ongoing", "Pending", "Other"}:
        status = "Other"
    images = save_uploaded_images(request.files.getlist("images"))
    image = images[0] if images else None
    if not title:
        flash("Project title is required.", "error")
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    db.execute("INSERT INTO projects(title,category,description,image,images_json,status,created_at) VALUES(?,?,?,?,?,?,?)", (title, category, description, image, json.dumps(images), status, now()))
    db.commit()
    flash("Project added successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/projects/delete/<int:project_id>", methods=["POST"])
@admin_required
def delete_project(project_id):
    db = get_db()
    item = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if item:
        for filename in collect_images(dict(item)):
            delete_uploaded_image(filename)
        db.execute("DELETE FROM projects WHERE id=?", (project_id,))
        db.commit()
    flash("Project deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/news/add", methods=["POST"])
@admin_required
def add_news():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    published = 1 if request.form.get("published") else 0
    images = save_uploaded_images(request.files.getlist("images"))
    image = images[0] if images else None
    if not title:
        flash("News title is required.", "error")
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    db.execute("INSERT INTO news(title,content,image,images_json,published,created_at) VALUES(?,?,?,?,?,?)", (title, content, image, json.dumps(images), published, now()))
    db.commit()
    flash("News published successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/news/delete/<int:news_id>", methods=["POST"])
@admin_required
def delete_news(news_id):
    db = get_db()
    item = db.execute("SELECT * FROM news WHERE id=?", (news_id,)).fetchone()
    if item:
        for filename in collect_images(dict(item)):
            delete_uploaded_image(filename)
        db.execute("DELETE FROM news WHERE id=?", (news_id,))
        db.commit()
    flash("News deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/vacancies/add", methods=["POST"])
@admin_required
def add_vacancy():
    title = request.form.get("title", "").strip()
    location = request.form.get("location", "").strip()
    employment_type = request.form.get("employment_type", "").strip()
    description = request.form.get("description", "").strip()
    requirements = request.form.get("requirements", "").strip()
    closing_date = request.form.get("closing_date", "").strip()
    published = 1 if request.form.get("published") else 0
    if not title:
        flash("Vacancy title is required.", "error")
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    db.execute("INSERT INTO vacancies(title,location,employment_type,description,requirements,closing_date,published,created_at) VALUES(?,?,?,?,?,?,?,?)", (title, location, employment_type, description, requirements, closing_date, published, now()))
    db.commit()
    flash("Vacancy added successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/vacancies/delete/<int:vacancy_id>", methods=["POST"])
@admin_required
def delete_vacancy(vacancy_id):
    db = get_db()
    db.execute("DELETE FROM vacancies WHERE id=?", (vacancy_id,))
    db.commit()
    flash("Vacancy deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/messages/read/<int:message_id>", methods=["POST"])
@admin_required
def mark_message_read(message_id):
    db = get_db()
    db.execute("UPDATE messages SET is_read=1 WHERE id=?", (message_id,))
    db.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/messages/delete/<int:message_id>", methods=["POST"])
@admin_required
def delete_message(message_id):
    db = get_db()
    db.execute("DELETE FROM messages WHERE id=?", (message_id,))
    db.commit()
    flash("Message deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/services/<int:service_id>")
def service_detail(service_id):
    db = get_db()
    service = db.execute("SELECT * FROM services WHERE id=? AND enabled=1", (service_id,)).fetchone()
    if not service:
        return redirect(url_for("home") + "#services")
    rows = db.execute("SELECT * FROM projects WHERE lower(trim(category))=lower(trim(?)) ORDER BY id DESC", (service["title"],)).fetchall()
    projects = enrich_gallery(rows)
    return render_template("service_detail.html", service=service, projects=projects, settings=public_settings())


@app.route("/admin/services/add", methods=["POST"])
@admin_required
def add_service():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    icon = ""
    enabled = 1 if request.form.get("enabled") else 0
    if not title:
        flash("Service name is required.", "error")
        return redirect(url_for("admin_dashboard") + "#services-admin")
    db = get_db()
    db.execute("INSERT INTO services(title,description,icon,enabled,created_at) VALUES(?,?,?,?,?)", (title, description, icon, enabled, now()))
    db.commit()
    flash("Service added. If enabled, it is now shown on the public website.", "success")
    return redirect(url_for("admin_dashboard") + "#services-admin")


@app.route("/admin/services/toggle/<int:service_id>", methods=["POST"])
@admin_required
def toggle_service(service_id):
    db = get_db()
    db.execute("UPDATE services SET enabled=CASE WHEN enabled=1 THEN 0 ELSE 1 END WHERE id=?", (service_id,))
    db.commit()
    flash("Service visibility updated.", "success")
    return redirect(url_for("admin_dashboard") + "#services-admin")


@app.route("/admin/services/delete/<int:service_id>", methods=["POST"])
@admin_required
def delete_service(service_id):
    db = get_db()
    db.execute("DELETE FROM services WHERE id=?", (service_id,))
    db.commit()
    flash("Service deleted.", "success")
    return redirect(url_for("admin_dashboard") + "#services-admin")


@app.route("/health")
def health():
    return {"status": "ok", "company": "KPME PLC"}


@app.route("/robots.txt")
def robots():
    return "User-agent: *\nDisallow: /admin\nDisallow: /admin/\n"


init_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
