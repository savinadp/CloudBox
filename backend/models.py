from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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
