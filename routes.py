"""
routes.py - the URLs of the app and what happens when someone visits them.

A "route" connects a URL (like /report) to a Python function (a "view").
The function does the work (check the form, read or write the database) and
sends back a page. This is the "backend processing" step in the five-step
interaction from Study Guide Section 3.2.5.

All routes are grouped in a Blueprint called "main". app.py registers it.
"""

import os
import re
import uuid
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_wtf.csrf import CSRFError
from sqlalchemy import func
from werkzeug.utils import secure_filename

from forms import LoginForm, ReportForm, StatusUpdateForm, detect_image_type
from models import CATEGORIES, STATUSES, Coordinator, Report, db

bp = Blueprint("main", __name__)

# A reference looks like W42-0153: "W42-" followed by at least 4 digits.
REFERENCE_PATTERN = re.compile(r"^W42-\d{4,}$")

# The file ending we give each real image type when we save it.
EXTENSION_FOR_TYPE = {"jpeg": "jpg", "png": "png", "webp": "webp"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_required(view):
    """Put @login_required under a route to protect it.

    If the coordinator is not logged in they are sent to the login page.
    """

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "coordinator_id" not in session:
            flash("Please log in to see that page.", "warning")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped_view


def save_photo(file):
   
    # secure_filename will removes dangerous characters, e.g. "../../x.png" -> "x.png"
    safe_name = secure_filename(file.filename)
    stem = os.path.splitext(safe_name)[0][:30]

    extension = EXTENSION_FOR_TYPE[detect_image_type(file)]

    # uuid4 makes a random unique name, so two photos can never overwrite
    # each other and nobody can guess another photo's name.
    unique_name = uuid.uuid4().hex
    if stem:
        unique_name = unique_name + "_" + stem
    unique_name = unique_name + "." + extension

    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name))

    # We store only this path text in the database (Table 1: photo_path).
    return "uploads/" + unique_name


def delete_photo(photo_path):
    """Remove a saved photo (used if saving the report fails afterwards)."""
    if not photo_path:
        return
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], photo_path.split("/")[-1])
    if os.path.exists(full_path):
        os.remove(full_path)


def get_summary():
    """Count reports per category and per status for the dashboard.

    The same numbers feed the Dashboard page and the JSON API.
    """
    # Start every category and status at 0 so ones with no reports still show.
    by_category = {name: 0 for name in CATEGORIES}
    by_status = {name: 0 for name in STATUSES}

    # SQL idea: SELECT category, COUNT(id) FROM reports GROUP BY category
    category_rows = db.session.execute(
        db.select(Report.category, func.count(Report.id)).group_by(Report.category)
    ).all()
    for category, count in category_rows:
        by_category[category] = count

    status_rows = db.session.execute(
        db.select(Report.status, func.count(Report.id)).group_by(Report.status)
    ).all()
    for status, count in status_rows:
        by_status[status] = count

    return {
        "total": sum(by_status.values()),
        "by_category": by_category,
        "by_status": by_status,
    }


# ---------------------------------------------------------------------------
# Pages for residents
# ---------------------------------------------------------------------------

@bp.route("/")
def home():
    return render_template("home.html")


@bp.route("/report", methods=["GET", "POST"])
def report():
    """Show the report form (GET) and handle it when it is sent (POST)."""
    form = ReportForm()

    # validate_on_submit() is True only for a POST that passes every rule
    # in forms.py, including the CSRF token.
    if form.validate_on_submit():
        photo_path = None
        file = form.photo.data
        if file and file.filename:
            photo_path = save_photo(file)

        new_report = Report(
            category=form.category.data,
            street=form.street.data,
            description=form.description.data,
            reporter_name=form.reporter_name.data,
            reporter_cell=form.reporter_cell.data,
            photo_path=photo_path,
            status="Open",
        )

        try:
            db.session.add(new_report)
            db.session.flush()  # the database gives the new row its id
            new_report.assign_reference()  # now we can build W42-0153
            db.session.commit()
        except Exception:
            # Something went wrong: undo the database change and the photo,
            # so we never keep half a report. The real error goes to the log
            # only, so the resident never sees technical details.
            db.session.rollback()
            delete_photo(photo_path)
            current_app.logger.exception("Could not save a report")
            flash("Sorry, we could not save your report. Please try again.", "danger")
            return render_template("report_form.html", form=form), 500

        return redirect(url_for("main.confirmation", reference=new_report.reference))

    # GET request, or a POST that failed validation. Errors show next to the
    # fields. 400 tells tools like REST Client that the request was rejected.
    status_code = 400 if form.errors else 200
    return render_template("report_form.html", form=form), status_code


@bp.route("/confirmation/<reference>")
def confirmation(reference):
    """The page shown after a report is saved. Shows the reference only."""
    if not REFERENCE_PATTERN.match(reference):
        return render_template("error.html", message="We could not find that page."), 404

    saved = Report.query.filter_by(reference=reference).first()
    if saved is None:
        return render_template("error.html", message="We could not find that page."), 404

    return render_template("confirmation.html", reference=saved.reference)


@bp.route("/status")
def status():
    """Look up a report by its reference number, e.g. /status?reference=W42-0153"""
    reference = request.args.get("reference", "").strip().upper()
    result = None
    message = None
    status_code = 200

    if reference:
        if not REFERENCE_PATTERN.match(reference):
            message = "That reference does not look right. It should look like W42-0153."
            status_code = 400
        else:
            found = Report.query.filter_by(reference=reference).first()
            if found is None:
                message = "We could not find a report with that reference."
                status_code = 404
            else:
                # Only share what is safe to show publicly. We deliberately
                # leave out the name, cell number, street, description and
                # photo, because anyone can try reference numbers (POPIA).
                result = {
                    "reference": found.reference,
                    "category": found.category,
                    "status": found.status,
                    "created_at": found.created_at,
                }

    return render_template(
        "status.html", reference=reference, result=result, message=message
    ), status_code


# ---------------------------------------------------------------------------
# PWA files (Part C): offline page, service worker and manifest
# ---------------------------------------------------------------------------

@bp.route("/offline")
def offline():
    """The page the service worker shows when the phone has no connection."""
    return render_template("offline.html")


@bp.route("/sw.js")
def service_worker():
    """The service worker must be served from the site root (/sw.js) so it
    can control every page. no-cache makes the browser check for updates."""
    response = send_from_directory(
        current_app.static_folder, "sw.js", mimetype="application/javascript"
    )
    response.headers["Cache-Control"] = "no-cache"
    return response


@bp.route("/manifest.json")
def manifest():
    """The web app manifest: name, icons, colours and start page."""
    return send_from_directory(
        current_app.static_folder, "manifest.json", mimetype="application/manifest+json"
    )


# ---------------------------------------------------------------------------
# Coordinator login and logout
# ---------------------------------------------------------------------------

@bp.route("/login", methods=["GET", "POST"])
def login():
    if "coordinator_id" in session:
        return redirect(url_for("main.reports"))

    form = LoginForm()
    failed = False

    if form.validate_on_submit():
        user = Coordinator.query.filter_by(username=form.username.data).first()
        if user is not None and user.check_password(form.password.data):
            session.clear()  # start a fresh session for the logged-in person
            session["coordinator_id"] = user.id
            flash("You are now logged in.", "success")
            return redirect(url_for("main.reports"))

        # Same message whether the username or the password was wrong, so an
        # attacker cannot tell which usernames exist.
        flash("The username or password is not correct.", "danger")
        failed = True

    status_code = 401 if failed else (400 if form.errors else 200)
    return render_template("login.html", form=form), status_code


@bp.route("/logout", methods=["POST"])
def logout():
    """POST only (and CSRF-protected), so another website cannot log you out."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


# ---------------------------------------------------------------------------
# Coordinator pages (all protected by @login_required)
# ---------------------------------------------------------------------------

@bp.route("/reports")
@login_required
def reports():
    """The table of all reports, with optional category and status filters."""
    category = request.args.get("category", "")
    status_filter = request.args.get("status", "")

    query = Report.query
    # Only use a filter if it is one of the allowed values.
    if category in CATEGORIES:
        query = query.filter_by(category=category)
    if status_filter in STATUSES:
        query = query.filter_by(status=status_filter)

    all_reports = query.order_by(Report.created_at.desc(), Report.id.desc()).all()

    return render_template(
        "reports.html",
        reports=all_reports,
        categories=CATEGORIES,
        statuses=STATUSES,
        selected_category=category,
        selected_status=status_filter,
    )


@bp.route("/reports/<int:report_id>")
@login_required
def report_detail(report_id):
    """One report in full: personal details, full photo and a status form."""
    found = db.get_or_404(Report, report_id)
    form = StatusUpdateForm(data={"status": found.status})
    return render_template("report_detail.html", report=found, form=form)


@bp.route("/reports/<int:report_id>/status", methods=["POST"])
@login_required
def update_status(report_id):
    found = db.get_or_404(Report, report_id)
    form = StatusUpdateForm()

    if form.validate_on_submit():
        found.status = form.status.data
        db.session.commit()
        flash("Status updated to " + found.status + ".", "success")
    else:
        flash("That status is not allowed.", "danger")

    return redirect(url_for("main.report_detail", report_id=found.id))


@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", summary=get_summary())


@bp.route("/photos/<filename>")
@login_required
def photo(filename):
    """Send a stored photo. Only logged-in coordinators may see photos.

    send_from_directory refuses paths that try to escape the uploads folder.
    """
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


# ---------------------------------------------------------------------------
# JSON API (read-only), used by fetch() on the dashboard in Question E2
# ---------------------------------------------------------------------------

@bp.route("/api/reports/summary")
def api_summary():
    if "coordinator_id" not in session:
        return jsonify({"error": "Login required"}), 401
    return jsonify(get_summary())


# ---------------------------------------------------------------------------
# Friendly error pages
# ---------------------------------------------------------------------------

@bp.app_errorhandler(CSRFError)
def handle_csrf_error(error):
    return render_template(
        "error.html",
        message="Your form could not be checked, so it was not sent. "
        "Please go back, refresh the page and try again.",
    ), 400


@bp.app_errorhandler(413)
def handle_too_large(error):
    return render_template(
        "error.html",
        message="That upload is too big. Photos must be smaller than 2 MB.",
    ), 413


@bp.app_errorhandler(404)
def handle_not_found(error):
    return render_template("error.html", message="We could not find that page."), 404


@bp.app_errorhandler(500)
def handle_server_error(error):
    return render_template(
        "error.html", message="Something went wrong on our side. Please try again later."
    ), 500
