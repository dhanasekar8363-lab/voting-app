from flask import Flask, render_template, redirect, session, jsonify, request, url_for
import sqlite3
import os
from flask_dance.contrib.google import make_google_blueprint, google

# 🔐 Fix Google OAuth scope issue
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

app = Flask(__name__)

# 🔐 Use strong secret key (set in Render ENV)
app.secret_key = os.getenv("SECRET_KEY", "change-this-in-production")

# ================= GOOGLE LOGIN =================

google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["openid", "email", "profile"],
    redirect_to="google_login"
)

app.register_blueprint(google_bp, url_prefix="/login")

# ================= DATABASE =================

DB_PATH = os.path.join(os.getcwd(), "database.db")

def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        voted INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS votes (
        party TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ================= HOME =================

@app.route('/')
def home():
    return render_template("login.html")

# ================= GOOGLE CALLBACK =================

@app.route("/google_login")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    try:
        resp = google.get("https://www.googleapis.com/oauth2/v2/userinfo")

        if not resp.ok:
            return "Google API failed ❌", 500

        info = resp.json()
        email = info.get("email")

        if not email:
            return "Email not found ❌", 500

        if not email.endswith("@gmail.com"):
            return "Only Gmail allowed ❌"

        session["email"] = email

        conn = get_db()
        c = conn.cursor()

        c.execute("INSERT OR IGNORE INTO users (email) VALUES (?)", (email,))
        conn.commit()

        c.execute("SELECT voted FROM users WHERE email=?", (email,))
        result = c.fetchone()
        conn.close()

        if result and result[0] == 1:
            return redirect('/results')

        return redirect('/vote')

    except Exception as e:
        print("ERROR:", e)
        return "Internal Server Error ❌", 500

# ================= VOTE =================

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'email' not in session:
        return redirect('/')

    email = session['email']

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT voted FROM users WHERE email=?", (email,))
    result = c.fetchone()

    if result and result[0] == 1:
        conn.close()
        return redirect('/results')

    if request.method == 'POST':
        party = request.form.get('party')

        if not party:
            conn.close()
            return "Invalid vote ❌", 400

        c.execute("INSERT INTO votes (party) VALUES (?)", (party,))
        c.execute("UPDATE users SET voted=1 WHERE email=?", (email,))

        conn.commit()
        conn.close()

        return redirect('/results')

    conn.close()
    return render_template("vote.html")

# ================= RESULTS PAGE =================

@app.route('/results')
def results():
    return render_template("result.html")

# ================= API =================

@app.route('/api/results')
def api_results():
    try:
        conn = get_db()
        c = conn.cursor()

        parties = ["TVK", "DMK", "NTK", "ADMK"]
        data = {}

        for p in parties:
            c.execute("SELECT COUNT(*) FROM votes WHERE party=?", (p,))
            data[p] = c.fetchone()[0]

        conn.close()
        return jsonify(data)

    except Exception as e:
        print("API ERROR:", e)
        return jsonify({"error": "server error"}), 500

# ================= LOGOUT =================

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= RUN =================

if __name__ == "__main__":
    app.run()