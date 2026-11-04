

from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Regexp, ValidationError

from models import CATEGORIES, STATUSES

# Photo rules from Question E1.
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}


def clean_text(value):
    """Remove spaces at the start and end of what the person typed."""
    if value is None:
        return value
    return value.strip()


def detect_image_type(file_storage):
    """Look at the first bytes of the file to see what it REALLY is.

    A file's name and content type come from the browser, so an attacker can
    fake them. The first few bytes (the "magic number") are much harder to
    fake. Returns "jpeg", "png", "webp" or None.
    """
    header = file_storage.stream.read(12)
    file_storage.stream.seek(0)  # go back to the start so the file can be saved later

    if header[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


class ReportForm(FlaskForm):
    """The 'Report a fault' form."""

    # The first choice has an empty value, so "Choose a category" counts as
    # "nothing chosen yet" and DataRequired complains.
    category = SelectField(
        "Category",
        choices=[("", "Choose a category")] + [(c, c) for c in CATEGORIES],
        validators=[DataRequired(message="Please choose a category.")],
    )

    street = StringField(
        "Street name and nearest house number or landmark",
        filters=[clean_text],
        validators=[
            DataRequired(message="Please tell us where the fault is."),
            Length(max=150, message="Please use 150 characters or fewer."),
        ],
    )

    description = TextAreaField(
        "Describe the problem",
        filters=[clean_text],
        validators=[
            DataRequired(message="Please describe the problem."),
            Length(
                min=10,
                max=500,
                message="The description must be between 10 and 500 characters.",
            ),
        ],
    )

    reporter_name = StringField(
        "Your name",
        filters=[clean_text],
        validators=[
            DataRequired(message="Please enter your name."),
            Length(min=2, max=100, message="Your name must be 2 to 100 characters."),
        ],
    )

    # South African cell number: 10 digits, starting with 0.
    reporter_cell = StringField(
        "Your cell number",
        filters=[clean_text],
        validators=[
            DataRequired(message="Please enter your cell number."),
            Regexp(
                r"^0\d{9}$",
                message="Enter a 10-digit cell number starting with 0, for example 0821234567.",
            ),
        ],
    )

    # Optional photo. We check it ourselves in validate_photo below.
    photo = FileField("Photo of the problem (optional)")

    def validate_photo(self, field):
        """WTForms runs any method named validate_<fieldname> automatically."""
        file = field.data

        # No file chosen because the photo is optional.
        if file is None or not getattr(file, "filename", ""):
            return

        # Check 1: the file extension.
        filename = file.filename.lower()
        extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
        if extension not in ALLOWED_EXTENSIONS:
            raise ValidationError("Photos must be JPEG, PNG or WebP files.")

        # Check 2: the content type the browser reported.
        if file.mimetype not in ALLOWED_MIMETYPES:
            raise ValidationError("Photos must be JPEG, PNG or WebP files.")

        # Check 3: the real content of the file (its first bytes).
        if detect_image_type(file) is None:
            raise ValidationError("That file is not a real JPEG, PNG or WebP image.")

        # Check 4: the size. Move to the end of the file to measure it.
        file.stream.seek(0, 2)
        size = file.stream.tell()
        file.stream.seek(0)
        max_bytes = current_app.config["MAX_PHOTO_BYTES"]
        if size > max_bytes:
            raise ValidationError("That photo is too big. Please choose one smaller than 2 MB.")


class StatusUpdateForm(FlaskForm):
    """Used by the coordinator to change a report's status."""

    status = SelectField(
        "Status",
        choices=[(s, s) for s in STATUSES],
        validators=[DataRequired(message="Please choose a status.")],
    )


class LoginForm(FlaskForm):
    """The coordinator login form."""

    username = StringField(
        "Username",
        filters=[clean_text],
        validators=[DataRequired(message="Please enter your username.")],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Please enter your password.")],
    )
