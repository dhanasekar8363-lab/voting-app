from flask import Flask, render_template, redirect, session, jsonify
import sqlite3
import os

from flask_dance.contrib.google import make_google_blueprint, google

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key")

# ================= GOOGLE LOGIN =================
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["profile", "email"],
    redirect_url="/google_login"
)

app.register_blueprint(google_bp, url_prefix="/login")

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("database.db")
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
        return redirect("/login/google")

    resp = google.get("/oauth2/v2/userinfo")
    info = resp.json()

    email = info.get("email")

    # ✅ Only Gmail allowed
    if not email or not email.endswith("@gmail.com"):
        return "Only Gmail accounts allowed ❌"

    session["email"] = email

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("INSERT OR IGNORE INTO users (email) VALUES (?)", (email,))
    conn.commit()

    c.execute("SELECT voted FROM users WHERE email=?", (email,))
    result = c.fetchone()
    voted = result[0] if result else 0

    conn.close()

    if voted == 1:
        return redirect('/results')

    return redirect('/vote')

# ================= VOTE =================
@app.route('/vote', methods=['GET','POST'])
def vote():
    from flask import request

    if 'email' not in session:
        return redirect('/')

    email = session['email']

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT voted FROM users WHERE email=?", (email,))
    result = c.fetchone()

    if result and result[0] == 1:
        conn.close()
        return redirect('/results')

    if request.method == 'POST':
        party = request.form['party']

        c.execute("INSERT INTO votes (party) VALUES (?)", (party,))
        c.execute("UPDATE users SET voted=1 WHERE email=?", (email,))

        conn.commit()
        conn.close()

        return redirect('/results')

    conn.close()
    return render_template("vote.html")

# ================= RESULTS =================
@app.route('/results')
def results():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    parties = ["TVK", "DMK", "NTK", "ADMK"]
    data = {}

    for p in parties:
        c.execute("SELECT COUNT(*) FROM votes WHERE party=?", (p,))
        data[p] = c.fetchone()[0]

    conn.close()
    return render_template("result.html", data=data)

# ================= API =================
@app.route('/api/results')
def api_results():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    parties = ["TVK", "DMK", "NTK", "ADMK"]
    data = {}

    for p in parties:
        c.execute("SELECT COUNT(*) FROM votes WHERE party=?", (p,))
        data[p] = c.fetchone()[0]

    conn.close()
    return jsonify(data)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= RUN =================
if __name__ == "__main__":
    app.run()