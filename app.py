"""
app.py -  will be the entry point. `flask run` looks for this file and the `app`
object at the bottom.
"""

import os

from flask import Flask
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import Coordinator, db
from routes import bp

# CSRFProtect checks the CSRF token on EVERY POST request in the whole app,
# so we cannot forget to protect a form (Topic 7, CSRF).
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Make sure the uploads folder exists.
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Connect the extensions to this app.
    db.init_app(app)
    csrf.init_app(app)

    # Add the pages from routes.py.
    app.register_blueprint(bp)

    # Create the tables and a test coordinator the first time the app runs,
    # so there are no extra setup steps after `pip install`.
    with app.app_context():
        db.create_all()
        seed_coordinator(app)

    # Runs after every response and adds security headers.
    @app.after_request
    def add_security_headers(response):
        # Content Security Policy: the browser may only load scripts, styles,
        # images and media from our own site. This limits XSS (Topic 7).
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "media-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        # Do not let the browser guess a file's type (stops disguised uploads).
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Do not allow other sites to show our pages inside a frame.
        response.headers["X-Frame-Options"] = "DENY"
        # Do not send our URLs to other sites when someone clicks a link.
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    return app


def seed_coordinator(app):
    """Create the test coordinator account if there are no coordinators yet."""
    if Coordinator.query.first() is None:
        coordinator = Coordinator(username=app.config["COORDINATOR_USERNAME"])
        coordinator.set_password(app.config["COORDINATOR_PASSWORD"])
        db.session.add(coordinator)
        db.session.commit()


# `flask run` finds this variable.
app = create_app()
