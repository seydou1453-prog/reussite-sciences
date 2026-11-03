import os
import sqlite3
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "reussite_sciences.db"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp", "doc", "docx"}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-before-deployment")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

init_db()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        if not email or not phone or len(password) < 8:
            flash("Remplissez tous les champs. Le mot de passe doit contenir au moins 8 caractères.")
            return render_template("register.html")
        try:
            with db() as con:
                con.execute(
                    "INSERT INTO users(email, phone, password_hash) VALUES (?, ?, ?)",
                    (email, phone, generate_password_hash(password))
                )
            flash("Compte créé. Vous pouvez vous connecter.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Cette adresse e-mail possède déjà un compte.")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            return redirect(url_for("dashboard"))
        flash("Adresse e-mail ou mot de passe incorrect.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as con:
        docs = con.execute(
            "SELECT * FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC",
            (session["user_id"],)
        ).fetchall()
    return render_template("dashboard.html", docs=docs)

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("document")
    if not file or not file.filename:
        flash("Choisissez un fichier avant de l'envoyer.")
        return redirect(url_for("dashboard"))
    if not allowed_file(file.filename):
        flash("Format non accepté. Utilisez PDF, image ou document Word.")
        return redirect(url_for("dashboard"))
    safe_name = secure_filename(file.filename)
    stored_name = f"user{session['user_id']}_{os.urandom(6).hex()}_{safe_name}"
    file.save(UPLOAD_DIR / stored_name)
    with db() as con:
        con.execute(
            "INSERT INTO documents(user_id, filename, original_name) VALUES (?, ?, ?)",
            (session["user_id"], stored_name, file.filename)
        )
    flash("Document enregistré. L'analyse automatique par IA sera ajoutée dans une prochaine version.")
    return redirect(url_for("dashboard"))

@app.route("/files/<int:doc_id>")
@login_required
def download_document(doc_id):
    with db() as con:
        doc = con.execute(
            "SELECT * FROM documents WHERE id = ? AND user_id = ?",
            (doc_id, session["user_id"])
        ).fetchone()
    if not doc:
        return "Document introuvable", 404
    return send_from_directory(UPLOAD_DIR, doc["filename"], as_attachment=True,
                               download_name=doc["original_name"])

@app.route("/professeur-ia")
@login_required
def ai_tutor():
    return render_template("ai_tutor.html")

@app.route("/entrainement")
@login_required
def training():
    return render_template("training.html")

@app.route("/sujets")
@login_required
def exams():
    return render_template("exams.html")

@app.errorhandler(413)
def too_large(_):
    flash("Fichier trop volumineux. La limite actuelle est de 20 Mo.")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
