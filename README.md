# Aimee MVP — Voice-Driven Sales Intelligence Platform

Aimee is an AI-powered sales assistant for wine and beverage distributors. It delivers real-time customer intelligence, tactical briefings, and competitive analysis through voice interaction, a web dashboard, and SMS — built to give field reps instant, actionable insights before and during customer visits.

## Features

- **Voice Interface** — Wake-word detection ("Hey Aimee"), intent classification across 33+ commands, and text-to-speech responses via ElevenLabs
- **Customer Intelligence** — Tactical briefings for restaurants and retail accounts with distributor relationships, wine program details, spend estimates, and opportunity scoring
- **Competitive Analysis** — Gap analysis, battle cards, and opportunity identification by account
- **Web Dashboard** — Tactical Command Center with account prioritization and on-demand briefing generation (port 5001)
- **SMS Integration** — Twilio webhook service for SMS-triggered briefings (port 5002)
- **Salesforce Integration** — OAuth 2.0 CRM sync for account data

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| ML / NLP | scikit-learn (TF-IDF + Naive Bayes / Random Forest) |
| Voice Input | `speech_recognition` |
| Voice Output | ElevenLabs API, `pydub`, `pygame` |
| CRM | Salesforce OAuth 2.0 |
| SMS | Twilio webhooks |
| Data | JSON, CSV |

## Project Structure

```
aimee-mvp/
├── aimee_classifier.py              # ML intent classification
├── aimee_fairfield_integration.py   # Customer profiles (17 accounts)
├── aimee_wine_intelligence.py       # Wine recommendation logic
├── aimee_prompt_generator.py        # Briefing template engine
├── aimee_final_elevenlabs_fixed.py  # ElevenLabs voice synthesis wrapper
├── aimee_complete_system.py         # Multi-service orchestrator
├── sms_integration.py               # Twilio SMS webhook handler
├── voice_commands.py                # Voice command system
├── daily_automation.py              # Scheduled briefing delivery
├── aimee_complete/
│   ├── tactical_briefing_web.py     # Flask dashboard app
│   └── templates/
│       └── tactical_dashboard.html
├── templates/
│   ├── index.html                   # Main dashboard
│   └── voice_demo.html              # Voice interface demo
├── aimee_training_data_tagged.json  # 44+ labeled training examples
├── aimee_sales_intelligence_data.json
├── aimee_wine_intelligence.json
├── .env.example                     # Environment variable template
├── integration_guide.md             # Fairfield County integration walkthrough
└── fairfield_county_analysis.md     # Market intelligence & sales strategy
```

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd aimee-mvp
pip install flask scikit-learn pandas numpy speech_recognition elevenlabs pydub pygame python-dotenv requests twilio
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
FLASK_SECRET_KEY=your_random_secret_key

# Salesforce OAuth 2.0
SF_CONSUMER_KEY=your_connected_app_key
SF_CONSUMER_SECRET=your_connected_app_secret
SF_DOMAIN=login
SF_CALLBACK_URL=http://localhost:5000/salesforce/callback
```

### 3. Train the intent classifier

```bash
python aimee_classifier.py
```

### 4. Start the services

**Web dashboard** (port 5001):
```bash
python aimee_complete/tactical_briefing_web.py
```

**SMS webhook** (port 5002):
```bash
python sms_integration.py
```

**Full system** (all services):
```bash
python aimee_complete_system.py
```

## Usage

### Voice Commands (examples)

```
"Hey Aimee, give me a briefing on Barcelona Wine Bar"
"What's my top opportunity in Fairfield County today?"
"What wines should I pitch to Spiga?"
"Who's my CDI contact for Westport accounts?"
"Run competitive analysis on Bin 100"
```

### Web Dashboard

Navigate to `http://localhost:5001` to access the Tactical Command Center. Accounts are prioritized with urgency indicators and support on-demand audio briefing generation.

## Documentation

- [`integration_guide.md`](integration_guide.md) — Step-by-step Fairfield County integration walkthrough with demo commands and testing scenarios
- [`fairfield_county_analysis.md`](fairfield_county_analysis.md) — Market intelligence, distributor mappings, revenue opportunity matrix, and expansion roadmap

## License

Proprietary. All rights reserved.
