import os
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

UPLOAD_FOLDER = "uploads"

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

# Required for flash messages
app.secret_key = "cloudbox-dev-secret"


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

        if not allowed_file(file.filename):
            flash(
                "File type not allowed. "
                "Please upload TXT, PDF, PNG, JPG, or JPEG files."
            )
            return redirect(url_for("home"))

        filename = secure_filename(file.filename)

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        file.save(file_path)

        flash("File uploaded successfully.")

        return redirect(url_for("home"))

    files = os.listdir(app.config["UPLOAD_FOLDER"])

    return render_template(
        "index.html",
        files=files
    )


@app.route("/download/<filename>")
def download_file(filename):

    filename = secure_filename(filename)

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=True
    )


@app.route("/delete/<filename>", methods=["POST"])
def delete_file(filename):

    filename = secure_filename(filename)

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    if os.path.exists(file_path):
        os.remove(file_path)
        flash("File deleted successfully.")

    return redirect(url_for("home"))


@app.errorhandler(413)
def file_too_large(error):

    flash("File is too large. Maximum size is 5 MB.")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)