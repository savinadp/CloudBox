import re
from functools import wraps

from flask import flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from .models import User, db


def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            flash("Please log in first.")

            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


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


@login_required
def logout():

    session.clear()

    flash("Logged out successfully.")

    return redirect(url_for("login"))
