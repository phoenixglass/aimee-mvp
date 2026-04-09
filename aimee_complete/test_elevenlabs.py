# Create test_elevenlabs.py
import os
from dotenv import load_dotenv
import requests

load_dotenv()

api_key = os.getenv("ELEVENLABS_API_KEY")
print(f"API Key found: {'Yes' if api_key else 'No'}")
print(f"Key length: {len(api_key) if api_key else 0}")
print(f"Key starts with: {api_key[:10]}..." if api_key else "No key")

# Test the API
headers = {
    "Accept": "application/json",
    "xi-api-key": api_key
}

response = requests.get("https://api.elevenlabs.io/v1/user", headers=headers)
print(f"\nAPI Response: {response.status_code}")
if response.status_code == 200:
    print("✅ API key is valid!")
else:
    print("❌ API key is invalid or expired")
    print(f"Error: {response.text}")