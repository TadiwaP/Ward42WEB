

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

# One shared database object. app.py connects it to the Flask app.
db = SQLAlchemy()

# The allowed values from Table 1. They live here so the forms, routes and
# dashboard all use the same lists.
CATEGORIES = ["Pothole", "Water leak", "Streetlight", "Illegal dumping", "Other"]
STATUSES = ["Open", "In progress", "Closed"]


def now_utc():
    """The current date and time, set by the server (never by the browser)."""
    return datetime.now(timezone.utc)


class Report(db.Model):
    """One fault reported by a resident. Matches Table 1 field for field."""

    __tablename__ = "reports"

    # The database's own number for the row. We also use it to build the
    # reference, so references can never repeat.
    id = db.Column(db.Integer, primary_key=True)

    # e.g. "W42-0153". It is filled in right after the first save, once we
    # know the id, so it starts empty (nullable) and is then unique.
    reference = db.Column(db.String(20), unique=True, nullable=True)

    category = db.Column(db.String(30), nullable=False)
    street = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500), nullable=False)

    # Personal information (POPIA). Never shown on the public status page.
    reporter_name = db.Column(db.String(100), nullable=False)
    reporter_cell = db.Column(db.String(10), nullable=False)

    # Only the PATH to the image file, e.g. "uploads/3f9a....jpg".
    # The image itself stays in the uploads folder, not in the database.
    photo_path = db.Column(db.String(200), nullable=True)

    status = db.Column(db.String(20), nullable=False, default="Open")
    created_at = db.Column(db.DateTime, nullable=False, default=now_utc)

    # Extra safety net: even if the code has a bug, the database itself
    # refuses a category or status that is not on the allowed list.
    __table_args__ = (
        db.CheckConstraint(
            "category IN ('Pothole', 'Water leak', 'Streetlight', "
            "'Illegal dumping', 'Other')",
            name="ck_category",
        ),
        db.CheckConstraint(
            "status IN ('Open', 'In progress', 'Closed')",
            name="ck_status",
        ),
    )

    @property
    def photo_filename(self):
        """Just the file name part of photo_path (used to build the photo URL)."""
        if not self.photo_path:
            return None
        return self.photo_path.split("/")[-1]

    def assign_reference(self):
        """Build the reference from the row id, e.g. id 153 -> 'W42-0153'.

        Call this AFTER db.session.flush(), because the id only exists once
        the database has accepted the new row.
        """
        self.reference = "W42-" + str(self.id).zfill(4)

    def __repr__(self):
        return "<Report " + str(self.reference) + ">"


class Coordinator(db.Model):
    """A coordinator who may log in (for example Mr Mahlangu)."""

    __tablename__ = "coordinators"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)

    # We store a HASH of the password, never the password itself.
    # If someone stole the database they still could not read the password.
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
