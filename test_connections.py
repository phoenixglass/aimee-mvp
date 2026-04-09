import os
from dotenv import load_dotenv
import requests
from twilio.rest import Client

load_dotenv()

print("🔧 Testing connections...")

# Test ElevenLabs
try:
    headers = {"xi-api-key": os.getenv("ELEVENLABS_API_KEY")}
    response = requests.get("https://api.elevenlabs.io/v1/user", headers=headers)
    if response.status_code == 200:
        print("✅ ElevenLabs connected!")
    else:
        print(f"❌ ElevenLabs error: {response.status_code}")
except Exception as e:
    print(f"❌ ElevenLabs error: {e}")

# Test Twilio
try:
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    account = client.api.accounts(os.getenv("TWILIO_ACCOUNT_SID")).fetch()
    print(f"✅ Twilio connected! Account: {account.friendly_name}")
except Exception as e:
    print(f"❌ Twilio error: {e}")