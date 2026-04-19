from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        phone TEXT PRIMARY KEY,
        voted INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS votes (
        party TEXT
    )''')

    conn.commit()
    conn.close()

# ================= LOGIN =================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']

        session['phone'] = phone

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # Create user if not exists
        c.execute("INSERT OR IGNORE INTO users (phone) VALUES (?)", (phone,))
        conn.commit()

        # Check if already voted
        c.execute("SELECT voted FROM users WHERE phone=?", (phone,))
        voted = c.fetchone()[0]

        conn.close()

        if voted == 1:
            return "❌ You already voted!"

        return redirect('/vote')

    return render_template("login.html")

# ================= VOTE =================
@app.route('/vote', methods=['GET','POST'])
def vote():
    if 'phone' not in session:
        return redirect('/')

    if request.method == 'POST':
        party = request.form['party']
        phone = session['phone']

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # double-check protection
        c.execute("SELECT voted FROM users WHERE phone=?", (phone,))
        if c.fetchone()[0] == 1:
            return "❌ Already voted!"

        c.execute("INSERT INTO votes (party) VALUES (?)", (party,))
        c.execute("UPDATE users SET voted=1 WHERE phone=?", (phone,))

        conn.commit()
        conn.close()

        return redirect('/results')

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

# ================= LIVE API =================
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

# ================= RUN =================
if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)