import os
from dotenv import load_dotenv

# Try loading .env explicitly
load_dotenv()

# Get the API key
api_key = os.getenv("ELEVENLABS_API_KEY")

# Check for hidden characters
print(f"API Key length: {len(api_key) if api_key else 'None'}")
print(f"First 10 chars: '{api_key[:10] if api_key else 'None'}'")
print(f"Last 5 chars: '{api_key[-5:] if api_key else 'None'}'")

# Check for spaces or newlines
if api_key:
    print(f"Starts with space: {api_key[0] == ' '}")
    print(f"Ends with space: {api_key[-1] == ' '}")
    print(f"Contains newline: {'\\n' in api_key}")
    
    # Show hex of first few chars to detect encoding issues
    print(f"Hex of first 5 chars: {api_key[:5].encode('utf-8').hex()}")