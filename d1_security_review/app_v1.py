# app_v1.py: first draft of the Ward 42 Fix-It back end
from flask import Flask, request, render_template_string
import sqlite3, os

app = Flask(__name__)
app.secret_key = "ward42"

@app.route("/search")
def search():
    street = request.args.get("street", "")
    conn = sqlite3.connect("fixit.db")
    rows = conn.execute(
        f"SELECT id, category, status FROM reports WHERE street = '{street}'"
    ).fetchall()
    conn.close()
    html = "<h2>Reports for " + street + "</h2><ul>"
    for r in rows:
        html += f"<li>#{r[0]} {r[1]}: {r[2]}</li>"
    return render_template_string(html + "</ul>")

@app.route("/report/<int:report_id>/close", methods=["GET", "POST"])
def close_report(report_id):
    conn = sqlite3.connect("fixit.db")
    conn.execute("UPDATE reports SET status = 'Closed' WHERE id = ?",
                 (report_id,))
    conn.commit()
    conn.close()
    return "Report closed"

@app.route("/upload", methods=["POST"])
def upload():
    photo = request.files["photo"]
    photo.save(os.path.join("uploads", photo.filename))
    return "Photo saved"

if __name__ == "__main__":
    app.run(debug=True)