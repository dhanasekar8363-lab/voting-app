from flask import Flask, render_template, redirect, session, jsonify, request, url_for
from supabase import create_client
import os
from flask_dance.contrib.google import make_google_blueprint, google

# 🔐 Fix Google OAuth scope issue
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-in-production")

# ================= SUPABASE =================

# 👉 🔴 PASTE YOUR VALUES HERE
SUPABASE_URL = "https://mqjcgerkrspofowvqced.supabase.co"
SUPABASE_KEY = "sb_publishable_p5Zeatd1YcCUlTcR_eIT7A_qf75b8Mx"

# Example:
# SUPABASE_URL = "https://abcd1234.supabase.co"
# SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= GOOGLE LOGIN =================

google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["openid", "email", "profile"],
    redirect_to="google_login"
)

app.register_blueprint(google_bp, url_prefix="/login")

# ================= HOME =================

@app.route('/')
def home():
    return render_template("login.html")

# ================= GOOGLE CALLBACK =================

@app.route("/google_login")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("https://www.googleapis.com/oauth2/v2/userinfo")

    if not resp.ok:
        return "Google API failed ❌", 500

    info = resp.json()
    email = info.get("email")

    if not email.endswith("@gmail.com"):
        return "Only Gmail allowed ❌"

    session["email"] = email

    # 👉 CREATE USER (IF NOT EXISTS)
    supabase.table("users").upsert({
        "email": email,
        "voted": False
    }).execute()

    user = supabase.table("users").select("*").eq("email", email).execute()

    if user.data and user.data[0]["voted"]:
        return redirect('/results')

    return redirect('/vote')

# ================= VOTE =================

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'email' not in session:
        return redirect('/')

    email = session['email']

    user = supabase.table("users").select("*").eq("email", email).execute()

    if user.data and user.data[0]["voted"]:
        return redirect('/results')

    if request.method == 'POST':
        party = request.form.get('party')

        if not party:
            return "Invalid vote ❌"

        # 👉 INSERT VOTE
        supabase.table("votes").insert({"party": party}).execute()

        # 👉 UPDATE USER
        supabase.table("users").update({
            "voted": True
        }).eq("email", email).execute()

        return redirect('/results')

    return render_template("vote.html")

# ================= RESULTS =================

@app.route('/results')
def results():
    return render_template("result.html")

# ================= API =================

@app.route('/api/results')
def api_results():
    parties = ["TVK", "DMK", "NTK", "ADMK"]
    data = {}

    for p in parties:
        res = supabase.table("votes").select("*").eq("party", p).execute()
        data[p] = len(res.data)

    return jsonify(data)

# ================= LOGOUT =================

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= RUN =================

if __name__ == "__main__":
    app.run()