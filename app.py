import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash

# --------------------------------------------------
# KMPE PLC WEBSITE
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# IMPORTANT:
# We DO NOT use DATA_DIR=/var/data.
# Everything is stored inside the normal application folder.
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

DATABASE = os.path.join(DATA_DIR, "kmpe.db")

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "kmpe-development-secret"
)

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin123"
)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    connection = get_db()

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT ''
        );
        """
    )

    # Add initial project if database is empty
    project_count = connection.execute(
        "SELECT COUNT(*) FROM projects"
    ).fetchone()[0]

    if project_count == 0:

        connection.execute(
            """
            INSERT INTO projects(title, description)
            VALUES (?, ?)
            """,
            (
                "KMPE PLC Construction",
                "Construction, fountain works and finishing works."
            )
        )

    # Add initial news
    news_count = connection.execute(
        "SELECT COUNT(*) FROM news"
    ).fetchone()[0]

    if news_count == 0:

        connection.execute(
            """
            INSERT INTO news(title, content)
            VALUES (?, ?)
            """,
            (
                "Welcome to KMPE PLC",
                "KMPE PLC provides professional construction, fountain and finishing services."
            )
        )

    connection.commit()
    connection.close()


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def index():

    connection = get_db()

    projects = connection.execute(
        "SELECT * FROM projects ORDER BY id DESC"
    ).fetchall()

    news = connection.execute(
        "SELECT * FROM news ORDER BY id DESC"
    ).fetchall()

    vacancies = connection.execute(
        "SELECT * FROM vacancies ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return render_template(
        "index.html",
        projects=projects,
        news=news,
        vacancies=vacancies
    )


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session["admin"] = True

            return redirect(url_for("admin"))

        flash("Incorrect username or password.")

    return render_template("login.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


# --------------------------------------------------
# ADMIN
# --------------------------------------------------

@app.route("/admin")
def admin():

    if not session.get("admin"):

        return redirect(url_for("login"))

    connection = get_db()

    projects = connection.execute(
        "SELECT * FROM projects ORDER BY id DESC"
    ).fetchall()

    news = connection.execute(
        "SELECT * FROM news ORDER BY id DESC"
    ).fetchall()

    vacancies = connection.execute(
        "SELECT * FROM vacancies ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return render_template(
        "admin.html",
        projects=projects,
        news=news,
        vacancies=vacancies
    )


# --------------------------------------------------
# PROJECTS
# --------------------------------------------------

@app.post("/admin/project")
def add_project():

    if not session.get("admin"):

        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if title:

        connection = get_db()

        connection.execute(
            """
            INSERT INTO projects(title, description)
            VALUES (?, ?)
            """,
            (title, description)
        )

        connection.commit()
        connection.close()

    return redirect(url_for("admin"))


@app.post("/admin/project/<int:item_id>/delete")
def delete_project(item_id):

    if not session.get("admin"):

        return redirect(url_for("login"))

    connection = get_db()

    connection.execute(
        "DELETE FROM projects WHERE id=?",
        (item_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("admin"))


# --------------------------------------------------
# NEWS
# --------------------------------------------------

@app.post("/admin/news")
def add_news():

    if not session.get("admin"):

        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if title:

        connection = get_db()

        connection.execute(
            """
            INSERT INTO news(title, content)
            VALUES (?, ?)
            """,
            (title, content)
        )

        connection.commit()
        connection.close()

    return redirect(url_for("admin"))


@app.post("/admin/news/<int:item_id>/delete")
def delete_news(item_id):

    if not session.get("admin"):

        return redirect(url_for("login"))

    connection = get_db()

    connection.execute(
        "DELETE FROM news WHERE id=?",
        (item_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("admin"))


# --------------------------------------------------
# VACANCIES
# --------------------------------------------------

@app.post("/admin/vacancy")
def add_vacancy():

    if not session.get("admin"):

        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if title:

        connection = get_db()

        connection.execute(
            """
            INSERT INTO vacancies(title, description)
            VALUES (?, ?)
            """,
            (title, description)
        )

        connection.commit()
        connection.close()

    return redirect(url_for("admin"))


@app.post("/admin/vacancy/<int:item_id>/delete")
def delete_vacancy(item_id):

    if not session.get("admin"):

        return redirect(url_for("login"))

    connection = get_db()

    connection.execute(
        "DELETE FROM vacancies WHERE id=?",
        (item_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("admin"))


# --------------------------------------------------
# STARTUP
# --------------------------------------------------

init_db()


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
