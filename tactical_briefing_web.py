"""
tactical_briefing_web.py
Aimee Flask backend - Salesforce integration + briefing routes
Runs on port 5000

Usage:
  1. Configure SF_CONSUMER_KEY, SF_CONSUMER_SECRET, SF_CALLBACK_URL in .env
  2. Start the server: python tactical_briefing_web.py
  3. Visit http://localhost:5000/voice for the voice interface
"""

import os
import re
import time
import secrets
import tempfile
from urllib.parse import urlencode

from flask import Flask, request, jsonify, redirect, session, send_from_directory, render_template
from dotenv import load_dotenv
import requests as http_requests

load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

os.makedirs("uploads", exist_ok=True)

# Salesforce config
SF_CONSUMER_KEY    = os.getenv("SF_CONSUMER_KEY")
SF_CONSUMER_SECRET = os.getenv("SF_CONSUMER_SECRET")
SF_DOMAIN          = os.getenv("SF_DOMAIN", "login")
SF_CALLBACK_URL    = os.getenv("SF_CALLBACK_URL", "http://localhost:5000/salesforce/callback")
SF_API_VERSION     = os.getenv("SF_API_VERSION", "v58.0")

_sf_token = {
    "access_token":  None,
    "refresh_token": None,
    "instance_url":  None,
}


# ── Salesforce helpers ─────────────────────────────────────────────────────────

def _token_url():
    return f"https://{SF_DOMAIN}.salesforce.com/services/oauth2/token"


def _refresh_access_token():
    if not _sf_token["refresh_token"]:
        return False
    payload = {
        "grant_type":    "refresh_token",
        "client_id":     SF_CONSUMER_KEY,
        "client_secret": SF_CONSUMER_SECRET,
        "refresh_token": _sf_token["refresh_token"],
    }
    try:
        resp = http_requests.post(_token_url(), data=payload, timeout=30)
    except http_requests.RequestException as e:
        print(f"SF token refresh network error: {e}")
        return False
    if resp.status_code == 200:
        data = resp.json()
        _sf_token["access_token"] = data["access_token"]
        _sf_token["instance_url"] = data.get("instance_url", _sf_token["instance_url"])
        print("Salesforce access token refreshed")
        return True
    print(f"SF token refresh failed {resp.status_code}: {resp.text}")
    _sf_token["refresh_token"] = None
    return False


def get_sf_token():
    if _sf_token["access_token"]:
        return _sf_token
    return None


def _sf_request(method, path, **kwargs):
    token = get_sf_token()
    if not token:
        return None
    url = f"{token['instance_url']}{path}"
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token['access_token']}"
    try:
        resp = http_requests.request(method, url, headers=headers, timeout=30, **kwargs)
    except http_requests.RequestException as e:
        print(f"SF request network error: {e}")
        return None
    if resp.status_code == 401 and _refresh_access_token():
        headers["Authorization"] = f"Bearer {_sf_token['access_token']}"
        try:
            resp = http_requests.request(method, url, headers=headers, timeout=30, **kwargs)
        except http_requests.RequestException as e:
            print(f"SF retry network error: {e}")
            return None
    return resp


def sf_query(soql: str):
    resp = _sf_request("GET", f"/services/data/{SF_API_VERSION}/query", params={"q": soql})
    if resp is None:
        return []
    if resp.status_code == 200:
        return resp.json().get("records", [])
    print(f"SOQL error {resp.status_code}: {resp.text}")
    return []


def sf_create(obj_type: str, data: dict):
    resp = _sf_request(
        "POST",
        f"/services/data/{SF_API_VERSION}/sobjects/{obj_type}",
        json=data,
        headers={"Content-Type": "application/json"},
    )
    if resp is None:
        return None
    if resp.status_code in (200, 201):
        return resp.json().get("id")
    print(f"SF create error {resp.status_code}: {resp.text}")
    return None


# ── Voice intelligence ─────────────────────────────────────────────────────────

def _generate_response(text):
    """Match text to intent and return a response."""
    t = text.lower()
    start = time.time()

    if re.search(r'today|daily|focus|priorit', t):
        response = ("Your top priorities today: LaBella's Fine Wine - Sofia is overdue at day 23 "
                    "of the 21-day cycle. Barcelona Wine Bar - Chef Misha needs Rioja samples. "
                    "Spiga Wine Bar - Dan Camporeale expects an allocation call. Strike with precision.")
        intent, score = "daily_briefing", 0.92

    elif re.search(r'barcelona', t):
        response = ("Barcelona Wine Bar Norwalk: Spanish natural wine program expanding. "
                    "Chef Misha Ryklin is your key contact. They're running low on rare Rioja. "
                    "Priority: bring samples this week. Annual spend estimate $35,000.")
        intent, score = "account_briefing", 0.88

    elif re.search(r'spiga', t):
        response = ("Spiga Wine Bar: Dan Camporeale is your contact. Italian-focused program "
                    "with strong Barolo and Brunello interest. They're expecting an allocation call "
                    "for premium bottles. Annual spend estimate $28,000.")
        intent, score = "account_briefing", 0.88

    elif re.search(r'labella|la bella', t):
        response = ("LaBella's Fine Wine and Spirits, Riverside. Sofia Martinez is your contact. "
                    "Bordeaux allocation meeting is overdue - you're at day 23 of a 21-day cycle. "
                    "Wine Warehouse is circling. Call Sofia today. Annual value $24,000.")
        intent, score = "account_briefing", 0.88

    elif re.search(r'bin.?100', t):
        response = ("Bin 100 Milford: Strong Napa Cab program. Key opportunity: their Italian section "
                    "is underdeveloped. Recommend Barolo and Amarone to fill the gap. Annual spend estimate $22,000.")
        intent, score = "account_briefing", 0.88

    elif re.search(r'\belm\b|new canaan', t):
        response = ("ELM New Canaan: Farm-to-table focused with strong natural wine interest. "
                    "Looking for organic and biodynamic options. Annual spend estimate $18,000.")
        intent, score = "account_briefing", 0.85

    elif re.search(r'pipeline|total value', t):
        response = ("Total pipeline across 17 Fairfield County accounts is approximately $450,000 annually. "
                    "Top accounts: Barcelona Wine Bar $35,000, Spiga $28,000, LaBella's $24,000.")
        intent, score = "pipeline_status", 0.90

    elif re.search(r'urgent|hot|immediate', t):
        response = ("Three urgent priorities: One - LaBella's, Sofia overdue at day 23. "
                    "Two - Barcelona Wine Bar, Rioja samples needed for Chef Misha. "
                    "Three - Spiga Wine Bar, Dan Camporeale expects allocation call. Act now.")
        intent, score = "urgent_priorities", 0.91

    elif re.search(r'pitch|talking point|meeting', t):
        m = re.search(r'(?:for|about)\s+(.+?)(?:\s+meeting)?$', t)
        account = m.group(1) if m else "your account"
        response = (f"Tactical pitch for {account}: Lead with allocation scarcity to create urgency. "
                    "Reference their current program gaps. Offer exclusive access to limited bottles. "
                    "Close with a specific ask - a purchase order or tasting appointment.")
        intent, score = "generate_pitch", 0.85

    elif re.search(r'missing|gap|wine list', t):
        m = re.search(r'(?:from|for|at)\s+(.+?)(?:\'s)?\s*(?:wine list|list)?$', t)
        account = m.group(1) if m else "that account"
        response = (f"Gap analysis for {account}: They're likely missing premium Burgundy, "
                    "Super Tuscan options, and high-end domestic Pinot Noir. "
                    "These represent your best upsell opportunities.")
        intent, score = "gap_analysis", 0.83

    elif re.search(r'distributor|connecticut', t):
        response = ("Key Connecticut distributors: Brescome Barton is the dominant player. "
                    "Wine Warehouse is aggressive in Fairfield County. "
                    "Your competitive advantage is personalized service and allocation access.")
        intent, score = "distributor_info", 0.82

    else:
        response = ("I'm Aimee, your Connecticut wine market intelligence assistant. "
                    "Ask me about account briefings, daily priorities, pipeline status, "
                    "urgent accounts, or tactical pitches. Try asking about Barcelona Wine Bar, Spiga, or LaBella's.")
        intent, score = "default", 0.5

    return response, intent, score, round(time.time() - start, 2)


def _elevenlabs_tts(text):
    """Generate speech via ElevenLabs. Returns audio bytes or None."""
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        return None
    try:
        resp = http_requests.post(
            "https://api.elevenlabs.io/v1/text-to-speech/rzsnuMd2pwYz1rGtMIVI",
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.4, "similarity_boost": 0.8},
            },
            headers={
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": key,
            },
            timeout=30,
        )
        return resp.content if resp.status_code == 200 else None
    except Exception as e:
        print(f"ElevenLabs error: {e}")
        return None


# ── Voice interface routes ─────────────────────────────────────────────────────

@app.route("/voice")
def voice_demo():
    return render_template("voice_demo.html")


@app.route("/process-text", methods=["POST"])
def process_text():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400

    response_text, intent, score, processing_time = _generate_response(text)

    audio_url = None
    audio_bytes = _elevenlabs_tts(response_text)
    if audio_bytes:
        filename = f"response_{int(time.time())}.mp3"
        with open(os.path.join("uploads", filename), "wb") as f:
            f.write(audio_bytes)
        audio_url = f"/audio/{filename}"

    return jsonify({
        "response_text": response_text,
        "response_audio": audio_url,
        "intent": intent,
        "score": score,
        "processing_time": str(processing_time),
        "model_used": "aimee_intelligence",
    })


@app.route("/upload", methods=["POST"])
def upload_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(tmp_path)
        transcript = result["text"].strip()
    except Exception as e:
        return jsonify({"error": f"Transcription failed: {e}"}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    response_text, intent, score, processing_time = _generate_response(transcript)

    audio_url = None
    audio_bytes = _elevenlabs_tts(response_text)
    if audio_bytes:
        filename = f"response_{int(time.time())}.mp3"
        with open(os.path.join("uploads", filename), "wb") as f:
            f.write(audio_bytes)
        audio_url = f"/audio/{filename}"

    return jsonify({
        "transcript": transcript,
        "response_text": response_text,
        "response_audio": audio_url,
        "intent": intent,
        "score": score,
        "processing_time": str(processing_time),
        "model_used": "whisper+aimee",
    })


@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory("uploads", filename)


# ── OAuth Web Server flow ──────────────────────────────────────────────────────

@app.route("/salesforce/login")
def sf_login():
    if not SF_CONSUMER_KEY or not SF_CONSUMER_SECRET:
        return jsonify({
            "error": "Salesforce Connected App not configured. "
                     "Set SF_CONSUMER_KEY and SF_CONSUMER_SECRET in .env."
        }), 500
    state = secrets.token_urlsafe(32)
    session["sf_oauth_state"] = state
    params = {
        "response_type": "code",
        "client_id":     SF_CONSUMER_KEY,
        "redirect_uri":  SF_CALLBACK_URL,
        "scope":         "api refresh_token offline_access",
        "state":         state,
    }
    auth_url = (
        f"https://{SF_DOMAIN}.salesforce.com/services/oauth2/authorize?"
        + urlencode(params)
    )
    return redirect(auth_url)


@app.route("/salesforce/callback")
def sf_callback():
    code  = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    if error:
        return jsonify({"error": error, "description": request.args.get("error_description")}), 400
    if not code:
        return jsonify({"error": "No code returned"}), 400
    expected_state = session.pop("sf_oauth_state", None)
    if not expected_state or state != expected_state:
        return jsonify({"error": "Invalid OAuth state"}), 400
    payload = {
        "grant_type":    "authorization_code",
        "client_id":     SF_CONSUMER_KEY,
        "client_secret": SF_CONSUMER_SECRET,
        "redirect_uri":  SF_CALLBACK_URL,
        "code":          code,
    }
    try:
        resp = http_requests.post(_token_url(), data=payload, timeout=30)
    except http_requests.RequestException as e:
        return jsonify({"error": f"Network error: {e}"}), 502
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), 400
    data = resp.json()
    _sf_token["access_token"]  = data["access_token"]
    _sf_token["refresh_token"] = data.get("refresh_token")
    _sf_token["instance_url"]  = data["instance_url"]
    return jsonify({
        "status": "authenticated",
        "instance_url": data["instance_url"],
        "has_refresh_token": bool(data.get("refresh_token")),
    })


@app.route("/salesforce/logout", methods=["POST"])
def sf_logout():
    _sf_token["access_token"]  = None
    _sf_token["refresh_token"] = None
    _sf_token["instance_url"]  = None
    return jsonify({"status": "logged out"})


# ── Salesforce routes ──────────────────────────────────────────────────────────

def _escape_soql(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


@app.route("/salesforce/account", methods=["POST"])
def sf_account():
    body         = request.get_json(silent=True) or {}
    account_name = (body.get("account_name") or "").strip()
    if not account_name:
        return jsonify({"error": "account_name required"}), 400
    safe_name = _escape_soql(account_name)
    records = sf_query(
        f"SELECT Id, Name, Phone, BillingCity, BillingState, "
        f"Industry, AnnualRevenue, Description "
        f"FROM Account WHERE Name LIKE '%{safe_name}%' LIMIT 5"
    )
    if not records:
        return jsonify({"error": f"No account found for '{account_name}'"}), 404
    acct = records[0]
    city     = acct.get("BillingCity") or ""
    state    = acct.get("BillingState") or ""
    phone    = acct.get("Phone") or "no phone on file"
    industry = acct.get("Industry") or "unknown industry"
    revenue  = acct.get("AnnualRevenue")
    location = f"{city}, {state}".strip(", ") or "location not listed"
    revenue_str = f"${revenue:,.0f} annual revenue" if revenue else "revenue not listed"
    summary = (
        f"{acct.get('Name', account_name)} is a {industry} account located in {location}. "
        f"Phone: {phone}. {revenue_str}."
    )
    if len(records) > 1:
        others = ", ".join(r.get("Name", "") for r in records[1:])
        summary += f" Similar accounts: {others}."
    return jsonify({"voice_summary": summary, "records": records})


@app.route("/salesforce/opportunities", methods=["POST"])
def sf_opportunities():
    body         = request.get_json(silent=True) or {}
    account_name = (body.get("account_name") or "").strip()
    if not account_name:
        return jsonify({"error": "account_name required"}), 400
    safe_name = _escape_soql(account_name)
    records = sf_query(
        f"SELECT Id, Name, StageName, Amount, CloseDate, Probability "
        f"FROM Opportunity "
        f"WHERE Account.Name LIKE '%{safe_name}%' "
        f"AND IsClosed = false ORDER BY CloseDate ASC LIMIT 10"
    )
    if not records:
        return jsonify({"error": f"No open opportunities for '{account_name}'"}), 404
    total = sum(r.get("Amount") or 0 for r in records)
    lines = []
    for r in records:
        amt   = f"${r['Amount']:,.0f}" if r.get("Amount") else "amount TBD"
        stage = r.get("StageName", "unknown stage")
        close = r.get("CloseDate", "no close date")
        lines.append(f"{r.get('Name', 'Unnamed')}: {amt}, {stage}, closing {close}")
    summary = (
        f"{len(records)} open {'opportunity' if len(records)==1 else 'opportunities'} "
        f"for {account_name}, totaling ${total:,.0f}. " + ". ".join(lines) + "."
    )
    return jsonify({"voice_summary": summary, "records": records})


@app.route("/salesforce/log-call", methods=["POST"])
def sf_log_call():
    body         = request.get_json(silent=True) or {}
    account_name = (body.get("account_name") or "").strip()
    subject      = body.get("subject") or f"Call - {account_name}"
    description  = body.get("description") or ""
    if not account_name:
        return jsonify({"error": "account_name required"}), 400
    safe_name = _escape_soql(account_name)
    accounts = sf_query(
        f"SELECT Id, Name FROM Account WHERE Name LIKE '%{safe_name}%' LIMIT 1"
    )
    if not accounts:
        return jsonify({"error": f"Account '{account_name}' not found in Salesforce"}), 404
    task_id = sf_create("Task", {
        "WhatId":      accounts[0]["Id"],
        "Subject":     subject,
        "Description": description,
        "Status":      "Completed",
        "TaskSubtype": "Call",
    })
    if task_id:
        return jsonify({"voice_summary": f"Call note logged for {account_name} in Salesforce.", "task_id": task_id})
    return jsonify({"error": "Failed to create task in Salesforce"}), 500


@app.route("/salesforce/recent-activity", methods=["POST"])
def sf_recent_activity():
    body         = request.get_json(silent=True) or {}
    account_name = (body.get("account_name") or "").strip()
    if not account_name:
        return jsonify({"error": "account_name required"}), 400
    safe_name = _escape_soql(account_name)
    accounts = sf_query(f"SELECT Id, Name FROM Account WHERE Name LIKE '%{safe_name}%' LIMIT 1")
    if not accounts:
        return jsonify({"error": f"Account '{account_name}' not found"}), 404
    account_id   = accounts[0]["Id"]
    account_name = accounts[0]["Name"]
    records = sf_query(
        f"SELECT Subject, Description, ActivityDate, Status, TaskSubtype "
        f"FROM Task WHERE WhatId = '{account_id}' "
        f"ORDER BY ActivityDate DESC NULLS LAST LIMIT 5"
    )
    if not records:
        return jsonify({"voice_summary": f"No logged activity found for {account_name} in Salesforce."}), 404
    latest = records[0]
    desc = latest.get("Description") or ""
    desc_snippet = (desc[:100] + "...") if len(desc) > 100 else desc
    summary = (
        f"Most recent activity for {account_name}: {latest.get('Subject') or 'unspecified'} "
        f"on {latest.get('ActivityDate') or 'unknown date'}. "
        + (f"Notes: {desc_snippet}" if desc_snippet else "No notes recorded.")
        + (f" {len(records)-1} additional activities on file." if len(records) > 1 else "")
    )
    return jsonify({"voice_summary": summary, "records": records})


# ── Account list / dashboard ───────────────────────────────────────────────────

@app.route("/accounts")
def get_accounts():
    if not get_sf_token():
        return jsonify({"error": "Not authenticated to Salesforce", "login_url": "/salesforce/login"}), 401
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 200))
    except (TypeError, ValueError):
        limit = 50
    records = sf_query(
        f"SELECT Id, Name, AnnualRevenue, BillingCity, BillingState, Industry, Phone "
        f"FROM Account ORDER BY Name LIMIT {limit}"
    )
    accounts = {}
    for r in records:
        accounts[r["Id"]] = {
            "name":     r.get("Name", ""),
            "value":    int(r.get("AnnualRevenue") or 0),
            "city":     r.get("BillingCity") or "",
            "state":    r.get("BillingState") or "",
            "industry": r.get("Industry") or "",
            "phone":    r.get("Phone") or "",
        }
    return jsonify(accounts)


@app.route("/accounts/list")
def list_accounts_page():
    if not get_sf_token():
        return (
            "<h1>Aimee - Salesforce Accounts</h1>"
            "<p>Not authenticated. <a href='/salesforce/login'>Connect to Salesforce</a></p>",
            200, {"Content-Type": "text/html"},
        )
    records = sf_query(
        "SELECT Id, Name, Industry, BillingCity, BillingState, AnnualRevenue "
        "FROM Account ORDER BY Name LIMIT 100"
    )
    rows = "".join(
        f"<tr><td>{r.get('Name','')}</td><td>{r.get('Industry') or ''}</td>"
        f"<td>{(r.get('BillingCity') or '')}, {(r.get('BillingState') or '')}</td>"
        f"<td style='text-align:right'>"
        f"{('${:,.0f}'.format(r['AnnualRevenue'])) if r.get('AnnualRevenue') else ''}</td></tr>"
        for r in records
    )
    html = (
        "<!doctype html><html><head><title>Aimee Accounts</title>"
        "<style>body{font-family:sans-serif;max-width:900px;margin:2em auto;}"
        "table{width:100%;border-collapse:collapse;}"
        "th,td{padding:8px;border-bottom:1px solid #eee;text-align:left;}"
        "th{background:#f5f5f5;}</style></head><body>"
        f"<h1>Salesforce Accounts ({len(records)})</h1>"
        "<p><a href='/voice'>Voice Interface</a> | "
        "<a href='/salesforce/logout' onclick=\"event.preventDefault();"
        "fetch('/salesforce/logout',{method:'POST'}).then(()=>location.reload());\">Log out of Salesforce</a></p>"
        "<table><thead><tr><th>Name</th><th>Industry</th><th>Location</th><th>Annual Revenue</th></tr></thead>"
        f"<tbody>{rows or '<tr><td colspan=4>No accounts returned.</td></tr>'}</tbody>"
        "</table></body></html>"
    )
    return html, 200, {"Content-Type": "text/html"}


@app.route("/test-tactical-briefing", methods=["POST"])
def test_tactical_briefing():
    if not get_sf_token():
        return jsonify({
            "main_response": "Tactical briefing not available - Salesforce not connected. Visit /salesforce/login.",
            "authenticated": False,
        }), 200
    records = sf_query("SELECT Name, BillingCity, Industry FROM Account ORDER BY Name LIMIT 10")
    if records:
        names = ", ".join(r.get("Name", "") for r in records[:3])
        response_text = (
            f"Here is your tactical briefing. You have {len(records)} active accounts in Salesforce. "
            f"Top accounts include: {names}. Review your open opportunities before each visit."
        )
    else:
        response_text = "Tactical briefing ready. No accounts found in Salesforce yet."
    return jsonify({"main_response": response_text, "authenticated": True})


@app.route("/pitch/generate", methods=["POST"])
def generate_pitch():
    body = request.get_json(silent=True) or {}
    account_id = body.get("account_id", "")
    return jsonify({"pitch": f"Pitch generated for account {account_id}."})


@app.route("/health")
def health():
    token = get_sf_token()
    return jsonify({
        "status":     "ok",
        "salesforce": "connected" if token else "not authenticated",
        "instance":   token["instance_url"] if token else None,
    })


# ── Startup ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Aimee Flask backend on port 5000...")
    if SF_CONSUMER_KEY and SF_CONSUMER_SECRET:
        print("Salesforce Connected App configured.")
        print("Visit http://localhost:5000/salesforce/login to authenticate.")
    else:
        print("WARNING: SF_CONSUMER_KEY / SF_CONSUMER_SECRET missing - set them in .env")
    print("Voice interface: http://localhost:5000/voice")
    print("Accounts dashboard: http://localhost:5000/accounts/list")
    app.run(host="0.0.0.0", port=5000, debug=False)
