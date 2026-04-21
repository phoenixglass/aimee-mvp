"""
tactical_briefing_web.py
Aimee Flask backend — Salesforce integration + briefing routes
Runs on port 5000
"""

import os
import json
from flask import Flask, request, jsonify, redirect, session
from dotenv import load_dotenv
import requests as http_requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

# ── Salesforce config ──────────────────────────────────────────────────────────

SF_CONSUMER_KEY    = os.getenv("SF_CONSUMER_KEY")
SF_CONSUMER_SECRET = os.getenv("SF_CONSUMER_SECRET")
SF_DOMAIN          = os.getenv("SF_DOMAIN", "login")          # "login" or "test"
SF_CALLBACK_URL    = os.getenv("SF_CALLBACK_URL", "http://localhost:5000/salesforce/callback")
SF_USERNAME        = os.getenv("SF_USERNAME")                  # optional: for username/password flow
SF_PASSWORD        = os.getenv("SF_PASSWORD")                  # optional
SF_SECURITY_TOKEN  = os.getenv("SF_SECURITY_TOKEN", "")        # optional

# In-memory token store (persists for the life of the process)
_sf_token = {
    "access_token": None,
    "instance_url": None,
}


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _token_url():
    return f"https://{SF_DOMAIN}.salesforce.com/services/oauth2/token"


def get_sf_token():
    """Return a valid access token, refreshing via username/password if needed."""
    if _sf_token["access_token"]:
        return _sf_token

    # Try username/password flow if credentials are present
    if SF_USERNAME and SF_PASSWORD:
        payload = {
            "grant_type":    "password",
            "client_id":     SF_CONSUMER_KEY,
            "client_secret": SF_CONSUMER_SECRET,
            "username":      SF_USERNAME,
            "password":      SF_PASSWORD + SF_SECURITY_TOKEN,
        }
        resp = http_requests.post(_token_url(), data=payload)
        if resp.status_code == 200:
            data = resp.json()
            _sf_token["access_token"] = data["access_token"]
            _sf_token["instance_url"] = data["instance_url"]
            print("✅ Salesforce authenticated via username/password")
            return _sf_token
        else:
            print(f"❌ SF auth failed: {resp.text}")

    return None


def sf_query(soql: str):
    """Run a SOQL query against Salesforce. Returns list of records or []."""
    token = get_sf_token()
    if not token or not token["access_token"]:
        print("❌ No Salesforce token available")
        return []

    url = f"{token['instance_url']}/services/data/v58.0/query"
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    resp = http_requests.get(url, headers=headers, params={"q": soql})

    if resp.status_code == 200:
        return resp.json().get("records", [])
    else:
        print(f"❌ SOQL error {resp.status_code}: {resp.text}")
        return []


def sf_create(obj_type: str, data: dict):
    """Create a Salesforce record. Returns the new record ID or None."""
    token = get_sf_token()
    if not token or not token["access_token"]:
        return None

    url = f"{token['instance_url']}/services/data/v58.0/sobjects/{obj_type}"
    headers = {
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type":  "application/json",
    }
    resp = http_requests.post(url, headers=headers, json=data)
    if resp.status_code in (200, 201):
        return resp.json().get("id")
    else:
        print(f"❌ SF create error {resp.status_code}: {resp.text}")
        return None


# ── OAuth web flow (optional — used if you prefer browser auth) ────────────────

@app.route("/salesforce/login")
def sf_login():
    auth_url = (
        f"https://{SF_DOMAIN}.salesforce.com/services/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={SF_CONSUMER_KEY}"
        f"&redirect_uri={SF_CALLBACK_URL}"
    )
    return redirect(auth_url)


@app.route("/salesforce/callback")
def sf_callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No code returned"}), 400

    payload = {
        "grant_type":    "authorization_code",
        "client_id":     SF_CONSUMER_KEY,
        "client_secret": SF_CONSUMER_SECRET,
        "redirect_uri":  SF_CALLBACK_URL,
        "code":          code,
    }
    resp = http_requests.post(_token_url(), data=payload)
    if resp.status_code == 200:
        data = resp.json()
        _sf_token["access_token"] = data["access_token"]
        _sf_token["instance_url"] = data["instance_url"]
        return jsonify({"status": "authenticated", "instance_url": data["instance_url"]})
    else:
        return jsonify({"error": resp.text}), 400


# ── Salesforce routes (called by voice_commands.py) ───────────────────────────

@app.route("/salesforce/account", methods=["POST"])
def sf_account():
    """Look up an account by name and return a voice-ready summary."""
    body        = request.get_json(force=True)
    account_name = body.get("account_name", "").strip()

    if not account_name:
        return jsonify({"error": "account_name required"}), 400

    safe_name = account_name.replace("'", "\\'")
    records = sf_query(
        f"SELECT Id, Name, Phone, BillingCity, BillingState, "
        f"Industry, AnnualRevenue, Description "
        f"FROM Account WHERE Name LIKE '%{safe_name}%' LIMIT 5"
    )

    if not records:
        return jsonify({"error": f"No account found for '{account_name}'"}), 404

    acct = records[0]
    name     = acct.get("Name", account_name)
    city     = acct.get("BillingCity") or ""
    state    = acct.get("BillingState") or ""
    phone    = acct.get("Phone") or "no phone on file"
    industry = acct.get("Industry") or "unknown industry"
    revenue  = acct.get("AnnualRevenue")
    location = f"{city}, {state}".strip(", ") or "location not listed"

    revenue_str = f"${revenue:,.0f} annual revenue" if revenue else "revenue not listed"

    summary = (
        f"{name} is a {industry} account located in {location}. "
        f"Phone: {phone}. {revenue_str}."
    )
    if len(records) > 1:
        others = ", ".join(r["Name"] for r in records[1:])
        summary += f" I also found similar accounts: {others}."

    return jsonify({"voice_summary": summary, "records": records})


@app.route("/salesforce/opportunities", methods=["POST"])
def sf_opportunities():
    """Return open opportunities for an account."""
    body         = request.get_json(force=True)
    account_name = body.get("account_name", "").strip()

    if not account_name:
        return jsonify({"error": "account_name required"}), 400

    safe_name = account_name.replace("'", "\\'")
    records = sf_query(
        f"SELECT Id, Name, StageName, Amount, CloseDate, Probability "
        f"FROM Opportunity "
        f"WHERE Account.Name LIKE '%{safe_name}%' "
        f"AND IsClosed = false "
        f"ORDER BY CloseDate ASC LIMIT 10"
    )

    if not records:
        return jsonify({"error": f"No open opportunities for '{account_name}'"}), 404

    total = sum(r.get("Amount") or 0 for r in records)
    lines = []
    for r in records:
        amt   = f"${r['Amount']:,.0f}" if r.get("Amount") else "amount TBD"
        stage = r.get("StageName", "unknown stage")
        close = r.get("CloseDate", "no close date")
        lines.append(f"{r['Name']}: {amt}, {stage}, closing {close}")

    summary = (
        f"{len(records)} open {'opportunity' if len(records)==1 else 'opportunities'} "
        f"for {account_name}, totaling ${total:,.0f}. "
        + ". ".join(lines) + "."
    )

    return jsonify({"voice_summary": summary, "records": records})


@app.route("/salesforce/log-call", methods=["POST"])
def sf_log_call():
    """Log a call note as a Task on the matching account."""
    body         = request.get_json(force=True)
    account_name = body.get("account_name", "").strip()
    subject      = body.get("subject", f"Call - {account_name}")
    description  = body.get("description", "")

    if not account_name:
        return jsonify({"error": "account_name required"}), 400

    # Find the account ID first
    safe_name = account_name.replace("'", "\\'")
    accounts = sf_query(
        f"SELECT Id, Name FROM Account WHERE Name LIKE '%{safe_name}%' LIMIT 1"
    )

    if not accounts:
        return jsonify({"error": f"Account '{account_name}' not found in Salesforce"}), 404

    account_id = accounts[0]["Id"]

    task_id = sf_create("Task", {
        "WhatId":      account_id,
        "Subject":     subject,
        "Description": description,
        "Status":      "Completed",
        "ActivityDate": None,   # Salesforce will default to today
        "TaskSubtype": "Call",
    })

    if task_id:
        return jsonify({
            "voice_summary": f"Call note logged for {account_name} in Salesforce.",
            "task_id": task_id
        })
    else:
        return jsonify({"error": "Failed to create task in Salesforce"}), 500


@app.route("/salesforce/recent-activity", methods=["POST"])
def sf_recent_activity():
    """Return the most recent logged activities for an account."""
    body         = request.get_json(force=True)
    account_name = body.get("account_name", "").strip()

    if not account_name:
        return jsonify({"error": "account_name required"}), 400

    safe_name = account_name.replace("'", "\\'")

    # Find the account first
    accounts = sf_query(
        f"SELECT Id, Name FROM Account WHERE Name LIKE '%{safe_name}%' LIMIT 1"
    )

    if not accounts:
        return jsonify({"error": f"Account '{account_name}' not found"}), 404

    account_id   = accounts[0]["Id"]
    account_name = accounts[0]["Name"]

    records = sf_query(
        f"SELECT Subject, Description, ActivityDate, Status, TaskSubtype "
        f"FROM Task WHERE WhatId = '{account_id}' "
        f"ORDER BY ActivityDate DESC LIMIT 5"
    )

    if not records:
        return jsonify({
            "voice_summary": f"No logged activity found for {account_name} in Salesforce."
        }), 404

    latest = records[0]
    date    = latest.get("ActivityDate") or "unknown date"
    subject = latest.get("Subject") or "unspecified"
    desc    = latest.get("Description") or ""
    desc_snippet = (desc[:100] + "...") if len(desc) > 100 else desc

    summary = (
        f"Most recent activity for {account_name}: {subject} on {date}. "
        + (f"Notes: {desc_snippet}" if desc_snippet else "No notes recorded.")
        + (f" There are {len(records)-1} additional recent activities on file." if len(records) > 1 else "")
    )

    return jsonify({"voice_summary": summary, "records": records})


# ── Legacy routes (keep these so existing voice commands don't break) ──────────

@app.route("/accounts")
def get_accounts():
    """Returns accounts from Salesforce for pipeline status."""
    records = sf_query(
        "SELECT Id, Name, AnnualRevenue FROM Account ORDER BY Name LIMIT 50"
    )
    # Reshape to match what voice_commands.py expects
    accounts = {}
    for r in records:
        accounts[r["Id"]] = {
            "name":  r.get("Name", ""),
            "value": int(r.get("AnnualRevenue") or 0),
        }
    return jsonify(accounts)


@app.route("/test-tactical-briefing", methods=["POST"])
def test_tactical_briefing():
    """Generate a simple tactical briefing response."""
    body  = request.get_json(force=True)
    query = body.get("query", "")

    records = sf_query(
        "SELECT Name, BillingCity, Industry FROM Account ORDER BY Name LIMIT 10"
    )

    if records:
        names = ", ".join(r["Name"] for r in records[:3])
        response_text = (
            f"Here is your tactical briefing. "
            f"You have {len(records)} active accounts in Salesforce. "
            f"Top accounts include: {names}. "
            f"Review your open opportunities before each visit."
        )
    else:
        response_text = (
            "Tactical briefing ready. No accounts found in Salesforce yet. "
            "Add accounts to your org to see live data."
        )

    return jsonify({"main_response": response_text})


@app.route("/pitch/generate", methods=["POST"])
def generate_pitch():
    """Placeholder pitch generator — pulls account name from SF."""
    body       = request.get_json(force=True)
    account_id = body.get("account_id", "")

    return jsonify({
        "pitch": f"Pitch generated for account {account_id}. Connect full pitch engine for detailed output."
    })


# ── Health check ───────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    token = get_sf_token()
    sf_status = "connected" if (token and token["access_token"]) else "not authenticated"
    return jsonify({"status": "ok", "salesforce": sf_status})


# ── Startup ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Starting Aimee Flask backend on port 5000...")
    print("📡 Attempting Salesforce authentication...")
    token = get_sf_token()
    if token and token["access_token"]:
        print(f"✅ Connected to Salesforce: {token['instance_url']}")
    else:
        print("⚠️  Salesforce not authenticated.")
        print("   Option 1: Add SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN to .env")
        print("   Option 2: Visit http://localhost:5000/salesforce/login in your browser")
    print()
    app.run(host="0.0.0.0", port=5000, debug=True)
