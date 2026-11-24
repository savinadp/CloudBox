import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import URL
from dotenv import load_dotenv
from uuid import uuid4
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError

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


@app.route("/", methods=["GET", "POST"])
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
                file_type=file_type
            )

            db.session.add(new_file)
            db.session.commit()

        except (OSError, SQLAlchemyError):
            db.session.rollback()
            file_path.unlink(missing_ok=True)
            flash("File upload failed.")
            return redirect(url_for("home"))

        flash("File uploaded successfully.")

        return redirect(url_for("home"))

    files = File.query.order_by(
        File.uploaded_at.desc()
    ).all()

    return render_template("index.html", files=files)


@app.route("/download/<int:file_id>")
def download_file(file_id):

    file = db.get_or_404(File, file_id)

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        file.stored_name,
        as_attachment=True,
        download_name=file.filename
    )


@app.route("/delete/<int:file_id>", methods=["POST"])
def delete_file(file_id):

    file = db.get_or_404(File, file_id)

    file_path = UPLOAD_FOLDER / file.stored_name

    try:
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


if __name__ == "__main__":
    app.run(debug=True)