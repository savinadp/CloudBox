import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import URL
from dotenv import load_dotenv
from uuid import uuid4
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
import re
from werkzeug.security import generate_password_hash
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import IntegrityError
from flask import session
from functools import wraps
from werkzeug.security import check_password_hash

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    flash
)
from werkzeug.utils import secure_filename

app = Flask(__name__)

load_dotenv()

app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    database=os.getenv("DB_NAME")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.secret_key = os.getenv("SECRET_KEY")
csrf = CSRFProtect(app)

db = SQLAlchemy(app)

class File(db.Model):

    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)

    filename = db.Column(
        db.String(255), nullable=False
    )

    stored_name = db.Column(
        db.String(255), unique=True, nullable=False
    )

    file_size = db.Column(
        db.Integer, nullable=False
    )

    file_type = db.Column(
        db.String(20), nullable=False
    )

    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

class User(db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer, primary_key=True
    )

    username = db.Column(
        db.String(80), unique=True, nullable=False
    )

    password_hash = db.Column(
        db.String(255), nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        nullable=False
    )

class ActivityLog(db.Model):

    __tablename__ = "activity_logs"

    id = db.Column(
        db.Integer, primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    action = db.Column(
        db.String(50),
        nullable=False
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        nullable=False
    )

UPLOAD_FOLDER = Path(app.root_path) / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {
    "txt",
    "pdf",
    "png",
    "jpg",
    "jpeg"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Maximum upload size: 5 MB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            flash("Please log in first.")

            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


def log_activity(action, filename):

    activity = ActivityLog(
        user_id=session["user_id"],
        action=action,
        filename=filename
    )

    db.session.add(activity)

@app.route("/", methods=["GET", "POST"])
@login_required
def home():

    if request.method == "POST":

        file = request.files.get("file")

        if not file or file.filename == "":
            flash("Please choose a file.")
            return redirect(url_for("home"))

        filename = secure_filename(file.filename)

        if not filename or len(filename) > 255:
            flash("Invalid filename.")
            return redirect(url_for("home"))

        if not allowed_file(filename):
            flash("File type not allowed.")
            return redirect(url_for("home"))

        file_type = filename.rsplit(".", 1)[1].lower()

        stored_name = f"{uuid4().hex}.{file_type}"

        file_path = UPLOAD_FOLDER / stored_name

        try:
            file.save(file_path)

            new_file = File(
                filename=filename,
                stored_name=stored_name,
                file_size=file_path.stat().st_size,
                file_type=file_type,
                user_id=session["user_id"]
            )

            db.session.add(new_file)
            log_activity("Uploaded", filename)
            db.session.commit()

        except (OSError, SQLAlchemyError):
            db.session.rollback()
            file_path.unlink(missing_ok=True)
            flash("File upload failed.")
            return redirect(url_for("home"))

        flash("File uploaded successfully.")

        return redirect(url_for("home"))

    files = File.query.filter_by(
    user_id=session["user_id"]
    ).order_by(
        File.uploaded_at.desc()
    ).all()

    activities = ActivityLog.query.filter_by(
        user_id=session["user_id"]
    ).order_by(
        ActivityLog.created_at.desc(),
        ActivityLog.id.desc()
    ).limit(10).all()

    return render_template(
        "index.html",
        files=files,
        activities=activities
    )

@app.route("/download/<int:file_id>")
@login_required
def download_file(file_id):

    file = File.query.filter_by(
        id=file_id,
        user_id=session["user_id"]
    ).first_or_404()

    response = send_from_directory(
        app.config["UPLOAD_FOLDER"],
        file.stored_name,
        as_attachment=True,
        download_name=file.filename
    )

    try:
        log_activity("Downloaded", file.filename)
        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        response.close()
        flash("Download failed.")
        return redirect(url_for("home"))

    return response


@app.route("/delete/<int:file_id>", methods=["POST"])
@login_required
def delete_file(file_id):

    file = File.query.filter_by(
        id=file_id,
        user_id=session["user_id"]
    ).first_or_404()
    
    file_path = UPLOAD_FOLDER / file.stored_name

    try:
        log_activity("Deleted", file.filename)
        db.session.delete(file)
        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        flash("File deletion failed.")
        return redirect(url_for("home"))

    try:
        file_path.unlink(missing_ok=True)
        flash("File deleted successfully.")

    except OSError:
        flash("Database record removed, but storage cleanup failed.")

    return redirect(url_for("home"))


@app.errorhandler(413)
def file_too_large(error):

    flash("File is too large. Maximum size is 5 MB.")

    return redirect(url_for("home"))

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip().lower()

        password = request.form.get("password", "")

        if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
            flash("Invalid username.")
            return redirect(url_for("register"))

        if not 12 <= len(password) <= 128:
            flash("Password must be 12-128 characters.")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:
            flash("Username already exists.")
            return redirect(url_for("register"))

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )

        try:
            db.session.add(new_user)
            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            flash("Username already exists.")
            return redirect(url_for("register"))

        flash("Account created successfully.")

        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip().lower()

        password = request.form.get("password", "")

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password_hash, password
        ):

            session.clear()

            session["user_id"] = user.id
            session["username"] = user.username

            flash("Login successful.")

            return redirect(url_for("home"))

        flash("Invalid username or password.")

        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    session.clear()

    flash("Logged out successfully.")

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)