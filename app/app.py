"""
Harness DBDO Tidbit — Backward-Compatible Schema Changes + Feature Flags
Feature Flag: use-split-name

v1 behavior (flag OFF):  reads/writes 'name' column
v2 behavior (flag ON):   reads/writes 'first_name' + 'last_name' columns

Run locally:
    pip install -r requirements.txt
    python app.py
"""

import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request
from splitio import get_factory
from splitio.exceptions import TimeoutException

app = Flask(__name__)

# ── Database connection ───────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "ecommerce"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

# ── Harness FME SDK setup ─────────────────────────────────────────────────────
SDK_KEY   = os.getenv("SDK_KEY", "SERVER_SIDE_SDK_HERE")
USER_KEY  = "user_anonymous"
FLAG_NAME = "use-split-name"

LOCALHOST_CONFIG = {"splitFile": "flags.yaml"}

print("Initializing Harness FME SDK...")
if SDK_KEY in ("YOUR_SERVER_SIDE_SDK_KEY", "localhost"):
    factory = get_factory("localhost", config=LOCALHOST_CONFIG)
else:
    factory = get_factory(SDK_KEY)

try:
    factory.block_until_ready(10)
    print("SDK initialized successfully.")
except TimeoutException:
    print("SDK initialization timed out. Check your SDK key.")

split_client = factory.client()

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    treatment = split_client.get_treatment(USER_KEY, FLAG_NAME)
    schema_version = "v2 — first_name / last_name" if treatment == "on" else "v1 — name"

    try:
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if treatment == "on":
            cur.execute("SELECT id, first_name, last_name, email, created_at FROM users ORDER BY id")
        else:
            cur.execute("SELECT id, name, email, created_at FROM users ORDER BY id")

        users = cur.fetchall()
        cur.close()
        conn.close()
        db_error = None
    except Exception as e:
        users    = []
        db_error = str(e)

    rows_html = ""
    for u in users:
        if treatment == "on":
            display_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
        else:
            display_name = u.get("name", "")

        rows_html += f"""
        <tr>
            <td>{u['id']}</td>
            <td>{display_name}</td>
            <td>{u['email']}</td>
        </tr>"""

    error_html = f'<p style="color:red">DB Error: {db_error}</p>' if db_error else ""

    flag_color  = "#4CAF50" if treatment == "on" else "#1565C0"
    flag_label  = f"🟢 Flag ON — using v2 schema (first_name / last_name)" if treatment == "on" \
                  else f"🔵 Flag OFF — using v1 schema (name)"

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Harness E-Commerce Store — DBDO</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        .badge {{ display: inline-block; background: #306998; color: white;
                  padding: 4px 12px; border-radius: 12px; font-size: 13px;
                  font-weight: bold; margin-bottom: 8px; }}
        .flag-banner {{ background: {flag_color}; color: white; padding: 12px 16px;
                        border-radius: 8px; font-weight: bold; margin: 16px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #f0f0f0; }}
        .schema-note {{ font-size: 12px; color: #888; margin-top: 8px; }}
        form {{ margin-top: 24px; padding: 16px; background: #f9f9f9; border-radius: 8px; }}
        input {{ padding: 8px; margin: 4px; border: 1px solid #ccc; border-radius: 4px; }}
        button {{ padding: 8px 16px; background: #1565C0; color: white;
                  border: none; border-radius: 4px; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="badge">🐍 Python SDK — port 5001</div>
    <h1>🛍️ Harness E-Commerce Store</h1>

    <div class="flag-banner">{flag_label}</div>
    {error_html}

    <h2>Users</h2>
    <p class="schema-note">Active schema: <strong>{schema_version}</strong> | Flag: <code>{FLAG_NAME}</code> | Treatment: <strong>{treatment}</strong></p>

    <table>
        <tr><th>ID</th><th>Name</th><th>Email</th></tr>
        {rows_html}
    </table>

    <form method="POST" action="/users">
        <h3>Add a User</h3>
        <input name="first_name" placeholder="First name" required />
        <input name="last_name"  placeholder="Last name" required />
        <input name="email"      placeholder="Email" required />
        <button type="submit">Add User</button>
        <p class="schema-note">
            {'Writes to first_name + last_name (v2). Trigger auto-populates name for v1 compatibility.' if treatment == 'on'
             else 'Writes to name (v1). Trigger auto-populates first_name + last_name for v2 compatibility.'}
        </p>
    </form>
</body>
</html>"""


@app.route("/users", methods=["POST"])
def add_user():
    first_name = request.form.get("first_name", "").strip()
    last_name  = request.form.get("last_name",  "").strip()
    email      = request.form.get("email",      "").strip()
    treatment  = split_client.get_treatment(USER_KEY, FLAG_NAME)

    try:
        conn = get_db()
        cur  = conn.cursor()

        if treatment == "on":
            # v2 path: write first_name + last_name; trigger fills 'name'
            cur.execute(
                "INSERT INTO users (first_name, last_name, name, email) VALUES (%s, %s, %s, %s)",
                (first_name, last_name, f"{first_name} {last_name}", email)
            )
        else:
            # v1 path: write name; trigger fills first_name + last_name
            cur.execute(
                "INSERT INTO users (name, email) VALUES (%s, %s)",
                (f"{first_name} {last_name}", email)
            )

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return f"<p>Error: {e}</p><a href='/'>Back</a>", 500

    from flask import redirect
    return redirect("/")


@app.route("/api/users")
def api_users():
    """JSON endpoint — shows what both v1 and v2 see in the DB."""
    try:
        conn  = get_db()
        cur   = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Post-V4: 'name' column has been dropped — only first_name and last_name remain
        cur.execute("SELECT id, first_name, last_name, email, created_at FROM users ORDER BY id")
        users = [dict(u) for u in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({"users": users, "count": len(users)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
