import sqlite3
import os
import getpass
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"txt"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def init_db():
    conn = sqlite3.connect("people.db")
    c = conn.cursor()

    # Uploads table
    c.execute('''CREATE TABLE IF NOT EXISTS uploads (
                    id INTEGER PRIMARY KEY,
                    filename TEXT,
                    username TEXT,
                    upload_time TEXT,
                    message TEXT,
                    genre TEXT)''')

    conn.commit()
    conn.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST" and "file" in request.files:
        file = request.files["file"]
        message = request.form.get("message", "").strip()
        genre = request.form.get("genre", "Uncategorized")

        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)

            # Metadata
            username = getpass.getuser()
            upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Save metadata to DB
            conn = sqlite3.connect("people.db")
            c = conn.cursor()
            c.execute("INSERT INTO uploads (filename, username, upload_time, message, genre) VALUES (?, ?, ?, ?, ?)",
                      (file.filename, username, upload_time, message, genre))
            conn.commit()
            conn.close()

            flash(f"File '{file.filename}' uploaded by {username} at {upload_time}")
        else:
            flash("Invalid file type! Only .txt files are allowed.")
        return redirect(url_for("index"))

    # Search/filter parameters
    search_query = request.args.get("search", "").strip()
    genre_filter = request.args.get("genre_filter", "")
    user_filter = request.args.get("user_filter", "")

    # Fetch names
    conn = sqlite3.connect("people.db")
    c = conn.cursor()

    # Build query with filters
    query = "SELECT filename, username, upload_time, message, genre FROM uploads WHERE 1=1"
    params = []

    if search_query:
        query += " AND (filename LIKE ? OR message LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    if genre_filter:
        query += " AND genre=?"
        params.append(genre_filter)
    if user_filter:
        query += " AND username=?"
        params.append(user_filter)

    query += " ORDER BY id DESC"
    c.execute(query, params)
    uploads = c.fetchall()

    # Distinct genres and usernames for filter dropdowns
    c.execute("SELECT DISTINCT genre FROM uploads")
    genres = [row[0] for row in c.fetchall() if row[0]]

    c.execute("SELECT DISTINCT username FROM uploads")
    users = [row[0] for row in c.fetchall() if row[0]]

    conn.close()

    return render_template("index.html", uploads=uploads, genres=genres, users=users)


@app.route("/view/<filename>")
def view_file(filename):
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.isfile(filepath):
        abort(404, description="File not found")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    conn = sqlite3.connect("people.db")
    c = conn.cursor()
    c.execute("SELECT username, upload_time, message, genre FROM uploads WHERE filename=?", (filename,))
    row = c.fetchone()
    conn.close()

    if row:
        username, upload_time, message, genre = row
    else:
        username, upload_time, message, genre = ("Unknown", "Unknown", "", "Uncategorized")

    return render_template("view_file.html", filename=filename, content=content,
                           username=username, upload_time=upload_time, message=message, genre=genre)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
