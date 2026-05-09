import os
import re
import time
import tempfile
from flask import request, jsonify, render_template, send_from_directory
from tactical_briefing_web import app

os.makedirs("uploads", exist_ok=True)


def _generate_response(text):
    t = text.lower()
    start = time.time()

    if re.search(r'today|daily|focus|priorit', t):
        response = ("Your top priorities today: LaBella's Fine Wine - Sofia is overdue at day 23 "
                    "of the 21-day cycle. Barcelona Wine Bar - Chef Misha needs Rioja samples. "
                    "Spiga Wine Bar - Dan Camporeale expects an allocation call. Strike with precision.")
        intent, score = "daily_briefing", 0.92
    elif re.search(r'barcelona', t):
        response = ("Barcelona Wine Bar Norwalk: Spanish natural wine program expanding. "
                    "Chef Misha Ryklin is your key contact. Running low on rare Rioja. "
                    "Priority: bring samples this week. Annual spend estimate $35,000.")
        intent, score = "account_briefing", 0.88
    elif re.search(r'spiga', t):
        response = ("Spiga Wine Bar: Dan Camporeale is your contact. Italian-focused program "
                    "with strong Barolo and Brunello interest. Expecting an allocation call. "
                    "Annual spend estimate $28,000.")
        intent, score = "account_briefing", 0.88
    elif re.search(r'labella|la bella', t):
        response = ("LaBella's Fine Wine and Spirits, Riverside. Sofia Martinez is your contact. "
                    "Bordeaux allocation meeting overdue - day 23 of a 21-day cycle. "
                    "Wine Warehouse is circling. Call Sofia today. Annual value $24,000.")
        intent, score = "account_briefing", 0.88
    elif re.search(r'bin.?100', t):
        response = ("Bin 100 Milford: Strong Napa Cab program. Italian section underdeveloped. "
                    "Recommend Barolo and Amarone to fill the gap. Annual spend estimate $22,000.")
        intent, score = "account_briefing", 0.88
    elif re.search(r'\belm\b|new canaan', t):
        response = ("ELM New Canaan: Farm-to-table focused, strong natural wine interest. "
                    "Looking for organic and biodynamic options. Annual spend estimate $18,000.")
        intent, score = "account_briefing", 0.85
    elif re.search(r'pipeline|total value', t):
        response = ("Total pipeline across 17 Fairfield County accounts is approximately $450,000 annually. "
                    "Top accounts: Barcelona $35,000, Spiga $28,000, LaBella's $24,000.")
        intent, score = "pipeline_status", 0.90
    elif re.search(r'urgent|hot|immediate', t):
        response = ("Three urgent priorities: One - LaBella's, Sofia overdue at day 23. "
                    "Two - Barcelona Wine Bar, Rioja samples needed for Chef Misha. "
                    "Three - Spiga Wine Bar, Dan Camporeale expects allocation call. Act now.")
        intent, score = "urgent_priorities", 0.91
    elif re.search(r'pitch|talking point|meeting', t):
        m = re.search(r'(?:for|about)\s+(.+?)(?:\s+meeting)?$', t)
        account = m.group(1) if m else "your account"
        response = (f"Tactical pitch for {account}: Lead with allocation scarcity. "
                    "Reference program gaps. Offer exclusive access to limited bottles. "
                    "Close with a specific ask.")
        intent, score = "generate_pitch", 0.85
    elif re.search(r'missing|gap|wine list', t):
        m = re.search(r'(?:from|for|at)\s+(.+?)(?:\'s)?\s*(?:wine list|list)?$', t)
        account = m.group(1) if m else "that account"
        response = (f"Gap analysis for {account}: Likely missing premium Burgundy, "
                    "Super Tuscan options, and high-end domestic Pinot Noir.")
        intent, score = "gap_analysis", 0.83
    else:
        response = ("I'm Aimee, your Connecticut wine market intelligence assistant. "
                    "Ask about account briefings, daily priorities, pipeline, or pitches. "
                    "Try: Barcelona Wine Bar, Spiga, LaBella's, or 'what should I focus on today?'")
        intent, score = "default", 0.5

    return response, intent, score, round(time.time() - start, 2)


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
    return jsonify({
        "response_text": response_text,
        "response_audio": None,
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
    return jsonify({
        "transcript": transcript,
        "response_text": response_text,
        "response_audio": None,
        "intent": intent,
        "score": score,
        "processing_time": str(processing_time),
        "model_used": "whisper+aimee",
    })


if __name__ == "__main__":
    print("Starting Aimee with voice interface on port 5000...")
    print("Voice interface: http://localhost:5000/voice")
    app.run(host="0.0.0.0", port=5000, debug=False)
