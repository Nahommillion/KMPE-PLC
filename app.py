import os
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
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
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
    """)
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
    return {"current_year": datetime.now().year}


@app.route("/")
def home():
    db = get_db()
    projects = db.execute("SELECT * FROM projects ORDER BY id DESC LIMIT 6").fetchall()
    news = db.execute("SELECT * FROM news WHERE published=1 ORDER BY id DESC LIMIT 3").fetchall()
    vacancies = db.execute("SELECT * FROM vacancies WHERE published=1 ORDER BY id DESC LIMIT 3").fetchall()
    return render_template("index.html", projects=projects, news=news, vacancies=vacancies)


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
        return redirect(url_for("home") + "#contact")
    db = get_db()
    db.execute("INSERT INTO messages(name,email,phone,message,is_read,created_at) VALUES(?,?,?,?,?,?)", (name, email, phone, message, 0, now()))
    db.commit()
    flash("Thank you. Your message has been received.", "success")
    return redirect(url_for("home") + "#contact")


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
    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    db = get_db()
    projects = db.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
    news = db.execute("SELECT * FROM news ORDER BY id DESC").fetchall()
    vacancies = db.execute("SELECT * FROM vacancies ORDER BY id DESC").fetchall()
    messages = db.execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
    unread_messages = db.execute("SELECT COUNT(*) FROM messages WHERE is_read=0").fetchone()[0]
    return render_template("admin.html", projects=projects, news=news, vacancies=vacancies, messages=messages, unread_messages=unread_messages)


@app.route("/admin/projects/add", methods=["POST"])
@admin_required
def add_project():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    image = save_uploaded_image(request.files.get("image"))
    if not title:
        flash("Project title is required.", "error")
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    db.execute("INSERT INTO projects(title,category,description,image,created_at) VALUES(?,?,?,?,?)", (title, category, description, image, now()))
    db.commit()
    flash("Project added successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/projects/delete/<int:project_id>", methods=["POST"])
@admin_required
def delete_project(project_id):
    db = get_db()
    item = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if item:
        delete_uploaded_image(item["image"])
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
    image = save_uploaded_image(request.files.get("image"))
    if not title:
        flash("News title is required.", "error")
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    db.execute("INSERT INTO news(title,content,image,published,created_at) VALUES(?,?,?,?,?)", (title, content, image, published, now()))
    db.commit()
    flash("News published successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/news/delete/<int:news_id>", methods=["POST"])
@admin_required
def delete_news(news_id):
    db = get_db()
    item = db.execute("SELECT * FROM news WHERE id=?", (news_id,)).fetchone()
    if item:
        delete_uploaded_image(item["image"])
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


@app.route("/health")
def health():
    return {"status": "ok", "company": "KMPE PLC"}


@app.route("/robots.txt")
def robots():
    return "User-agent: *\nDisallow: /admin\nDisallow: /admin/\n"


init_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
