#Stores all my settings and stuff 

import os

# The folder this file lives in. We build other paths from it so the app
# works no matter which folder `flask run` is started from.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Secret key -------------------------------------------------------
    # Flask uses this to sign the session cookie and the CSRF tokens.
    # On a real server we set the SECRET_KEY environment variable so the
    # real key is never written in the code (or committed to GitHub).
    # The fallback below is ONLY for running on your own laptop.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-before-deploying")

    # --- Database ---------------------------------------------------------
    # SQLite keeps everything in one file (fixit.db) next to this config.
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "fixit.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Photo uploads ----------------------------------------------------
    # Photos go in a folder that is NOT inside templates/ or static/,
    # so they are never served to the public by accident.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    # The rule is "photos may be at most 2 MB" (checked in forms.py with a
    # clear message). MAX_CONTENT_LENGTH is a hard safety cap for the whole
    # request: Flask refuses anything bigger before reading it all.
    # It is slightly larger than 2 MB to leave room for the text fields.
    MAX_PHOTO_BYTES = 2 * 1024 * 1024
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024

    # --- Session cookie safety (Topic 7) ----------------------------------
    # HttpOnly: JavaScript cannot read the cookie, which limits XSS damage.
    SESSION_COOKIE_HTTPONLY = True
    # SameSite: the browser will not send the cookie on requests that start
    # from another website, which helps against CSRF.
    SESSION_COOKIE_SAMESITE = "Strict"
    # Secure: the cookie is only sent over HTTPS. This needs HTTPS to work
    # properly, so it is OFF for local testing and ON once deployed:
    #     set COOKIE_SECURE=1   (Windows)   /   export COOKIE_SECURE=1   (Mac/Linux)
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"

    # --- Test coordinator login (created automatically on first run) -----
    # Change these (or set them as environment variables) for a real launch.
    COORDINATOR_USERNAME = os.environ.get("COORDINATOR_USERNAME", "coordinator")
    COORDINATOR_PASSWORD = os.environ.get("COORDINATOR_PASSWORD", "Ward42-Fixit!")
