import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import URL

from backend import auth, files
from backend.models import db

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

upload_folder = Path(app.root_path) / "uploads"
upload_folder.mkdir(exist_ok=True)
app.config["UPLOAD_FOLDER"] = upload_folder
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

CSRFProtect(app)
db.init_app(app)

app.add_url_rule("/register", view_func=auth.register, methods=["GET", "POST"])
app.add_url_rule("/login", view_func=auth.login, methods=["GET", "POST"])
app.add_url_rule("/logout", view_func=auth.logout, methods=["POST"])

app.add_url_rule("/", view_func=files.home, methods=["GET", "POST"])
app.add_url_rule("/download/<int:file_id>", view_func=files.download_file)
app.add_url_rule("/delete/<int:file_id>", view_func=files.delete_file, methods=["POST"])
app.register_error_handler(413, files.file_too_large)


if __name__ == "__main__":
    app.run(debug=True)
