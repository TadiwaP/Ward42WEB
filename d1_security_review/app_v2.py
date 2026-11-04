# app_v2.py: Fixed Answer for D1
#
# Must be Run it with a secret key set, for example (Windows PowerShell):
#     $env:SECRET_KEY = "any-long-random-text-here"
#     flask --app app_v2 run

import os
import sqlite3
import uuid

from flask import Flask, abort, render_template_string, request, session
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

app = Flask(__name__)

# FIX 7: the secret key comes from the environment, never from the code.
# If it is missing the app refuses to start, instead of using a weak default.
app.secret_key = os.environ["SECRET_KEY"]

app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024   # FIX 6: hard limit on any request
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

# FIX 5: every POST request must now carry a valid CSRF token.
csrf = CSRFProtect(app)

# FIX 2 and 3: the template is fixed text. The person's input is passed in
# as variables, so Jinja escapes it and never treats it as template code.
SEARCH_PAGE = """
<h2>Reports for {{ street }}</h2>
<ul>
{% for r in rows %}<li>#{{ r[0] }} {{ r[1] }}: {{ r[2] }}</li>{% endfor %}
</ul>
"""


@app.after_request
def add_security_headers(response):
    # FIX 2 (extra layer): the browser may only run scripts from our own site.
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/search")
def search():
    street = request.args.get("street", "")
    conn = sqlite3.connect("fixit.db")
    # FIX 1: the ? is a placeholder. The value is sent separately from the
    # SQL, so it can only ever be data, never part of the command.
    rows = conn.execute(
        "SELECT id, category, status FROM reports WHERE street = ?", (street,)
    ).fetchall()
    conn.close()
    return render_template_string(SEARCH_PAGE, street=street, rows=rows)


# FIX 5: POST only. A link or an image tag on another page can only cause a GET.
@app.route("/report/<int:report_id>/close", methods=["POST"])
def close_report(report_id):
    # FIX 4: only a logged-in coordinator may close a report.
    if "coordinator_id" not in session:
        abort(401)
    conn = sqlite3.connect("fixit.db")
    conn.execute("UPDATE reports SET status = 'Closed' WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    return "Report closed"


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_PHOTO_BYTES = 2 * 1024 * 1024


def real_image_type(stream):
    """Look at the first bytes of the file to see what it really is."""
    header = stream.read(12)
    stream.seek(0)
    if header[:3] == b"\xff\xd8\xff":
        return "jpg"
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


@app.route("/upload", methods=["POST"])
def upload():
    photo = request.files.get("photo")
    if photo is None or photo.filename == "":
        abort(400)

    # FIX 6: only allow image file endings, after cleaning the name.
    safe_name = secure_filename(photo.filename)
    extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        abort(400)

    # FIX 6: check the real contents, and the size.
    kind = real_image_type(photo.stream)
    if kind is None:
        abort(400)
    photo.stream.seek(0, 2)
    size = photo.stream.tell()
    photo.stream.seek(0)
    if size > MAX_PHOTO_BYTES:
        abort(413)

    # FIX 6: our own random file name, so nothing the person sent is used in the path.
    os.makedirs("uploads", exist_ok=True)
    unique_name = uuid.uuid4().hex + "." + kind
    photo.save(os.path.join("uploads", unique_name))
    return "Photo saved"


if __name__ == "__main__":
    # FIX 8: debug mode is off. Debug mode shows an interactive console and
    # the source code to anyone who can trigger an error.
    app.run(debug=False)