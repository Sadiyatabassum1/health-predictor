"""Health Prediction Application - Flask backend with SQLite storage."""
import os
import sqlite3

from flask import Flask, flash, g, redirect, render_template, request, url_for

import ai_service
from validators import validate_record

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "patients.db"))
AI_FAILED_REMARK = "AI prediction unavailable - use Re-run AI on the record to retry."

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    glucose REAL NOT NULL,
    haemoglobin REAL NOT NULL,
    cholesterol REAL NOT NULL,
    remarks TEXT NOT NULL DEFAULT ''
)
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(SCHEMA)


def get_remarks(rec):
    try:
        return ai_service.predict_remarks(
            rec["dob"], rec["glucose"], rec["haemoglobin"], rec["cholesterol"]
        ), None
    except ai_service.AIServiceError as exc:
        return AI_FAILED_REMARK, str(exc)


def email_taken(email, exclude_id=None):
    row = get_db().execute(
        "SELECT id FROM patients WHERE email = ? AND id != ?", (email, exclude_id or -1)
    ).fetchone()
    return row is not None


def fmt(n):
    return ("%g" % n)


app.jinja_env.filters["num"] = fmt


@app.route("/")
def index():
    rows = get_db().execute("SELECT * FROM patients ORDER BY id").fetchall()
    return render_template("index.html", patients=rows, form={})


@app.route("/add", methods=["POST"])
def add():
    rec, errors = validate_record(request.form)
    if not errors and email_taken(rec["email"]):
        errors.append("A record with this email address already exists (duplicate entry).")
    if errors:
        for e in errors:
            flash(e, "error")
        rows = get_db().execute("SELECT * FROM patients ORDER BY id").fetchall()
        return render_template("index.html", patients=rows, form=request.form), 400

    remarks, ai_error = get_remarks(rec)
    db = get_db()
    db.execute(
        "INSERT INTO patients (full_name, dob, email, glucose, haemoglobin, cholesterol, remarks) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (rec["full_name"], rec["dob"], rec["email"], rec["glucose"],
         rec["haemoglobin"], rec["cholesterol"], remarks),
    )
    db.commit()
    flash(f"Record for {rec['full_name']} saved.", "success")
    if ai_error:
        flash(f"AI remarks could not be generated: {ai_error}", "error")
    return redirect(url_for("index"))


@app.route("/edit/<int:pid>", methods=["GET", "POST"])
def edit(pid):
    db = get_db()
    row = db.execute("SELECT * FROM patients WHERE id = ?", (pid,)).fetchone()
    if row is None:
        flash("Record not found.", "error")
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template("edit.html", p=row, form=dict(row))

    rec, errors = validate_record(request.form)
    if not errors and email_taken(rec["email"], exclude_id=pid):
        errors.append("Another record already uses this email address.")
    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("edit.html", p=row, form=request.form), 400

    remarks, ai_error = row["remarks"], None
    changed = any(rec[k] != row[k] for k in ("dob", "glucose", "haemoglobin", "cholesterol"))
    if changed or row["remarks"] == AI_FAILED_REMARK:
        remarks, ai_error = get_remarks(rec)

    db.execute(
        "UPDATE patients SET full_name=?, dob=?, email=?, glucose=?, haemoglobin=?, "
        "cholesterol=?, remarks=? WHERE id=?",
        (rec["full_name"], rec["dob"], rec["email"], rec["glucose"],
         rec["haemoglobin"], rec["cholesterol"], remarks, pid),
    )
    db.commit()
    flash("Record updated.", "success")
    if ai_error:
        flash(f"AI remarks could not be regenerated: {ai_error}", "error")
    return redirect(url_for("index"))


@app.route("/rerun/<int:pid>", methods=["POST"])
def rerun(pid):
    db = get_db()
    row = db.execute("SELECT * FROM patients WHERE id = ?", (pid,)).fetchone()
    if row is None:
        flash("Record not found.", "error")
    else:
        remarks, ai_error = get_remarks(dict(row))
        if ai_error:
            flash(f"AI remarks could not be generated: {ai_error}", "error")
        else:
            db.execute("UPDATE patients SET remarks=? WHERE id=?", (remarks, pid))
            db.commit()
            flash("AI remarks refreshed.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:pid>", methods=["POST"])
def delete(pid):
    db = get_db()
    cur = db.execute("DELETE FROM patients WHERE id = ?", (pid,))
    db.commit()
    flash("Record deleted." if cur.rowcount else "Record not found.",
          "success" if cur.rowcount else "error")
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=False, port=5000)
