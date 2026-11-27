from uuid import uuid4

from flask import (
    current_app, flash, redirect, render_template, request,
    send_from_directory, session, url_for
)
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from .auth import login_required
from .models import ActivityLog, File, db


ALLOWED_EXTENSIONS = {
    "txt",
    "pdf",
    "png",
    "jpg",
    "jpeg"
}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def log_activity(action, filename):

    activity = ActivityLog(
        user_id=session["user_id"],
        action=action,
        filename=filename
    )

    db.session.add(activity)


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

        file_path = current_app.config["UPLOAD_FOLDER"] / stored_name

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

    search = request.args.get("search", "").replace("\x00", "").strip()
    query = File.query.filter_by(
        user_id=session["user_id"]
    )
    if search:
        query = query.filter(
            File.filename.icontains(search, autoescape=True)
        )
    files = query.order_by(
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
        activities=activities,
        search=search
    )


@login_required
def download_file(file_id):

    file = File.query.filter_by(
        id=file_id,
        user_id=session["user_id"]
    ).first_or_404()

    response = send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
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



@login_required
def delete_file(file_id):

    file = File.query.filter_by(
        id=file_id,
        user_id=session["user_id"]
    ).first_or_404()

    file_path = current_app.config["UPLOAD_FOLDER"] / file.stored_name

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



def file_too_large(error):

    flash("File is too large. Maximum size is 5 MB.")

    return redirect(url_for("home"))
