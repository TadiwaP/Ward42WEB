# Ward 42 Fix-It

A community service-reporting web app for the **Mamelodi East Residents' Association** (Ward 42, Tshwane).

Residents report potholes, water leaks, broken streetlights and illegal dumping from their phones, with an optional photo, and can check the progress of their report with a reference number. The volunteer coordinator logs in to see all reports, filter them, update their status and view a dashboard of counts.

Built for WST262 (Web Systems and Technologies), Summative Project SS3.

## What it does

**Residents**
- Report a fault: category, street, description, name, cell number and an optional photo
- Check a report's status with its reference number (for example `W42-0001`)
- Watch a short tutorial video on the home page
- Install the app on a phone (PWA) and still see a helpful page when offline

**Coordinator (login required)**
- See all reports in a table with photo thumbnails, and filter by category and status
- Open a report to see the full details and photo, and change its status (Open, In progress, Closed)
- View a dashboard with the number of reports per category and per status

## Built with

Flask, Flask-SQLAlchemy and Flask-WTF (back end), SQLite (database), Bootstrap 5, HTML5, CSS and JavaScript (front end). Bootstrap is included in `static/vendor`, so the app needs no internet connection for its own files.

## How to install and run

You need Python 3.9 or newer.

**Windows (PowerShell or the VS Code terminal)**

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
flask run
```

**Mac or Linux**

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run
```

Then open **http://127.0.0.1:5000** in Chrome or Edge.

The first time the app starts it creates the database (`fixit.db`), the `uploads` folder and the test coordinator account. No other setup is needed. Stop the app with `Ctrl+C`.

If PowerShell says scripts are disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and activate again.

## Test coordinator login

| | |
|---|---|
| Username | `coordinator` |
| Password | `Ward42-Fixit!` |

Log in from **Coordinator login** in the menu. These details are for testing only. Change them before using the app for real (see below).

## Settings (optional)

These can be set as environment variables. The defaults work for testing on your own computer.

| Variable | What it does | Default |
|---|---|---|
| `SECRET_KEY` | Signs the session cookie and CSRF tokens. **Set a long random value when deploying.** | a development value |
| `COOKIE_SECURE` | Set to `1` once the app is served over HTTPS, so the session cookie is only sent securely | `0` |
| `COORDINATOR_USERNAME` | Username of the coordinator account created on first run | `coordinator` |
| `COORDINATOR_PASSWORD` | Password of that account (stored as a hash) | `Ward42-Fixit!` |

The coordinator account is only created when the database has no coordinators yet. To change the login, delete `fixit.db` and start the app again.

## Project structure

```
app.py               starts the app, security headers
config.py            settings
models.py            database tables (Report, Coordinator)
forms.py             forms and server-side checks (Flask-WTF)
routes.py            pages, login, photo serving, JSON API
requirements.txt     Python packages
security_tests.http  attack requests for the REST Client extension
templates/           Jinja pages (base.html is the shared layout)
static/css/          our own styles
static/js/app.js     form checks, live filter, saved draft, dashboard fetch
static/sw.js         service worker (offline support)
static/manifest.json web app manifest
static/vendor/       Bootstrap 5
static/media/        tutorial video and captions
uploads/             stored photos (not in the repository)
d1_security_review/app_v1.py , app_v2.py  Tests for Question D
```

## Security and privacy (POPIA)

- Every query goes through the SQLAlchemy ORM, so user input is never pasted into SQL
- Every form is checked again on the server, as well as in the browser
- CSRF tokens on every form that changes data
- Passwords are stored as hashes, never as plain text
- Session cookies are `HttpOnly` and `SameSite=Strict` (and `Secure` when `COOKIE_SECURE=1`)
- Security headers: Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- Photos: only JPEG, PNG or WebP, checked by extension, content type and the file's real contents, at most 2 MB, renamed with a random name, stored outside `templates` and `static`, and only visible to a logged-in coordinator
- The public status page shows only the category, date and status, never a name, cell number, street or photo
- The saved draft in the browser never includes the name or cell number
- The service worker never caches reports, photos or coordinator pages

## Testing the security checks

1. Install the **REST Client** extension in VS Code.
2. Start the app, open `security_tests.http` and follow the steps at the top of the file.
3. Each request should be rejected, as described in its comment.

## Credits

Bootstrap 5.3.3 is used under the MIT licence (see `static/vendor/bootstrap/LICENSE`).
