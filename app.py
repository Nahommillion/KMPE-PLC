import os, sqlite3, uuid
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
DATABASE = os.path.join(DATA_DIR, "kmpe.db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
ALLOWED_EXTENSIONS = {"png","jpg","jpeg","gif","webp","svg"}

def db():
    c=sqlite3.connect(DATABASE); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,description TEXT,image TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS news(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,content TEXT,image TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS vacancies(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,description TEXT,deadline TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT,phone TEXT,message TEXT NOT NULL,is_read INTEGER DEFAULT 0,created_at TEXT NOT NULL);
    """)
    c.commit(); c.close()
init_db()

def allowed(name): return "." in name and name.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS
def upload(f):
    if not f or not f.filename or not allowed(f.filename): return None
    ext=f.filename.rsplit(".",1)[1].lower()
    name=f"{uuid.uuid4().hex}.{ext}"
    f.save(os.path.join(UPLOAD_DIR,name)); return name

def admin_required(fn):
    @wraps(fn)
    def w(*a,**k):
        if not session.get("admin"): return redirect(url_for("admin"))
        return fn(*a,**k)
    return w

@app.route("/")
def index():
    c=db()
    p=c.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
    n=c.execute("SELECT * FROM news ORDER BY id DESC").fetchall()
    v=c.execute("SELECT * FROM vacancies ORDER BY id DESC").fetchall()
    c.close(); return render_template("index.html",projects=p,news=n,vacancies=v)

@app.post("/contact")
def contact():
    name=request.form.get("name","").strip(); message=request.form.get("message","").strip()
    if name and message:
        c=db(); c.execute("INSERT INTO messages(name,email,phone,message,created_at) VALUES(?,?,?,?,?)",
        (name,request.form.get("email",""),request.form.get("phone",""),message,datetime.utcnow().isoformat()))
        c.commit(); c.close(); flash("Thank you. Your message has been sent.","success")
    else: flash("Please enter your name and message.","error")
    return redirect(url_for("index")+"#contact")

@app.route("/uploads/<path:filename>")
def uploads(filename): return send_from_directory(UPLOAD_DIR,filename)

@app.route("/admin",methods=["GET","POST"])
def admin():
    if request.method=="POST":
        if request.form.get("username")==ADMIN_USERNAME and request.form.get("password")==ADMIN_PASSWORD:
            session["admin"]=True; return redirect(url_for("dashboard"))
        flash("Invalid username or password.","error")
    if session.get("admin"): return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.get("/admin/logout")
def logout(): session.clear(); return redirect(url_for("admin"))

@app.get("/admin/dashboard")
@admin_required
def dashboard():
    c=db()
    data={x:c.execute(f"SELECT * FROM {x} ORDER BY id DESC").fetchall() for x in ["projects","news","vacancies","messages"]}
    c.close(); return render_template("admin.html",**data)

@app.post("/admin/projects/add")
@admin_required
def add_project():
    title=request.form.get("title","").strip()
    if title:
        c=db(); c.execute("INSERT INTO projects(title,description,image,created_at) VALUES(?,?,?,?)",
        (title,request.form.get("description",""),upload(request.files.get("image")),datetime.utcnow().isoformat()))
        c.commit(); c.close(); flash("Project added.","success")
    return redirect(url_for("dashboard"))

@app.post("/admin/projects/delete/<int:item_id>")
@admin_required
def delete_project(item_id):
    c=db(); row=c.execute("SELECT image FROM projects WHERE id=?",(item_id,)).fetchone()
    if row and row["image"]:
        try: os.remove(os.path.join(UPLOAD_DIR,row["image"]))
        except OSError: pass
    c.execute("DELETE FROM projects WHERE id=?",(item_id,)); c.commit(); c.close()
    return redirect(url_for("dashboard"))

@app.post("/admin/news/add")
@admin_required
def add_news():
    title=request.form.get("title","").strip()
    if title:
        c=db(); c.execute("INSERT INTO news(title,content,image,created_at) VALUES(?,?,?,?)",
        (title,request.form.get("content",""),upload(request.files.get("image")),datetime.utcnow().isoformat()))
        c.commit(); c.close(); flash("News added.","success")
    return redirect(url_for("dashboard"))

@app.post("/admin/news/delete/<int:item_id>")
@admin_required
def delete_news(item_id):
    c=db(); row=c.execute("SELECT image FROM news WHERE id=?",(item_id,)).fetchone()
    if row and row["image"]:
        try: os.remove(os.path.join(UPLOAD_DIR,row["image"]))
        except OSError: pass
    c.execute("DELETE FROM news WHERE id=?",(item_id,)); c.commit(); c.close()
    return redirect(url_for("dashboard"))

@app.post("/admin/vacancies/add")
@admin_required
def add_vacancy():
    title=request.form.get("title","").strip()
    if title:
        c=db(); c.execute("INSERT INTO vacancies(title,description,deadline,created_at) VALUES(?,?,?,?)",
        (title,request.form.get("description",""),request.form.get("deadline",""),datetime.utcnow().isoformat()))
        c.commit(); c.close(); flash("Vacancy added.","success")
    return redirect(url_for("dashboard"))

@app.post("/admin/vacancies/delete/<int:item_id>")
@admin_required
def delete_vacancy(item_id):
    c=db(); c.execute("DELETE FROM vacancies WHERE id=?",(item_id,)); c.commit(); c.close()
    return redirect(url_for("dashboard"))

@app.post("/admin/messages/read/<int:item_id>")
@admin_required
def read_message(item_id):
    c=db(); c.execute("UPDATE messages SET is_read=1 WHERE id=?",(item_id,)); c.commit(); c.close()
    return redirect(url_for("dashboard"))

@app.post("/admin/messages/delete/<int:item_id>")
@admin_required
def delete_message(item_id):
    c=db(); c.execute("DELETE FROM messages WHERE id=?",(item_id,)); c.commit(); c.close()
    return redirect(url_for("dashboard"))

@app.get("/health")
def health(): return {"status":"ok"}

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
