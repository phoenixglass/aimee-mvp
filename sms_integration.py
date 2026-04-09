from twilio.rest import Client
import requests
import os
from dotenv import load_dotenv
from flask import Flask, request, Response
import re

load_dotenv()

# Initialize Twilio
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

app = Flask(__name__)

# SMS command patterns
SMS_COMMANDS = {
    'briefing': r'(?i)\b(brief|briefing|update|status)\b',
    'account': r'(?i)\b(brief|info|intel)\s+(barcelona|spiga|labella|bin\s*100|elm)\b',
    'urgent': r'(?i)\b(urgent|priority|hot|fire)\b',
    'pitch': r'(?i)\b(pitch|call|contact)\s+(barcelona|spiga|labella|bin\s*100|elm)\b',
    'pipeline': r'(?i)\b(pipeline|total|value|money)\b'
}

def send_sms(to_number, message):
    """Send SMS via Twilio"""
    try:
        message = twilio_client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=to_number
        )
        return True
    except Exception as e:
        print(f"SMS Error: {e}")
        return False

def send_audio_sms(to_number, audio_url, caption=""):
    """Send audio file via SMS"""
    try:
        message = twilio_client.messages.create(
            body=caption,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=to_number,
            media_url=[audio_url]
        )
        return True
    except Exception as e:
        print(f"Audio SMS Error: {e}")
        return False

def process_sms_command(message_body, from_number):
    """Process incoming SMS commands"""
    
    # Daily briefing request
    if re.search(SMS_COMMANDS['briefing'], message_body):
        try:
            # Generate briefing audio
            response = requests.get("http://localhost:5001/briefing/daily")
            if response.status_code == 200:
                # Save temporarily and create public URL
                audio_path = save_temp_audio(response.content, "daily_briefing")
                audio_url = create_public_url(audio_path)
                
                send_audio_sms(from_number, audio_url, "🎯 Your daily tactical briefing:")
                return "✅ Daily briefing sent"
            else:
                send_sms(from_number, "❌ Unable to generate briefing")
                return "Error generating briefing"
        except Exception as e:
            send_sms(from_number, f"❌ Error: {str(e)[:100]}")
            return f"Error: {e}"
    
    # Account-specific briefing
    account_match = re.search(SMS_COMMANDS['account'], message_body)
    if account_match:
        account_name = account_match.group(2).lower().replace(" ", "_")
        account_map = {
            'barcelona': 'barcelona_norwalk',
            'spiga': 'spiga', 
            'labella': 'labellas',
            'bin_100': 'bin_100',
            'elm': 'elm'
        }
        
        account_id = account_map.get(account_name)
        if account_id:
            try:
                response = requests.get(f"http://localhost:5001/briefing/account/{account_id}")
                if response.status_code == 200:
                    audio_path = save_temp_audio(response.content, f"{account_id}_briefing")
                    audio_url = create_public_url(audio_path)
                    
                    send_audio_sms(from_number, audio_url, f"📋 {account_name.title()} tactical brief:")
                    return f"✅ {account_name} briefing sent"
                else:
                    send_sms(from_number, f"❌ Account {account_name} not found")
                    return "Account not found"
            except Exception as e:
                send_sms(from_number, f"❌ Error: {str(e)[:100]}")
                return f"Error: {e}"
    
    # Pipeline value request
    if re.search(SMS_COMMANDS['pipeline'], message_body):
        # Calculate total pipeline value
        accounts_response = requests.get("http://localhost:5001/accounts")
        if accounts_response.status_code == 200:
            accounts = accounts_response.json()
            total_value = sum(int(account['value']) for account in accounts.values())
            
            message = f"💰 Total Pipeline: ${total_value:,}\n"
            message += f"🔥 Active Accounts: {len(accounts)}\n"
            message += "🎯 Ready for battle."
            
            send_sms(from_number, message)
            return "✅ Pipeline status sent"
    
    # Urgent priorities
    if re.search(SMS_COMMANDS['urgent'], message_body):
        urgent_message = """🔥 URGENT PRIORITIES:
        
📞 LaBella's - Sofia overdue (Day 23)
⚡ Barcelona - Rioja samples needed
🎯 Spiga - Dan expects allocation call

Strike now."""
        send_sms(from_number, urgent_message)
        return "✅ Urgent priorities sent"
    
    # Default help
    help_message = """🍷 Aimee SMS Commands:
    
📊 "briefing" - Daily briefing
📋 "brief [account]" - Account intel
💰 "pipeline" - Pipeline value
🔥 "urgent" - Hot priorities
🎤 "pitch [account]" - Generate pitch

Text any command to activate."""
    
    send_sms(from_number, help_message)
    return "Help sent"

def save_temp_audio(audio_content, filename):
    """Save audio to temporary public directory"""
    import tempfile
    import uuid
    
    temp_dir = os.path.join(tempfile.gettempdir(), "aimee_public")
    os.makedirs(temp_dir, exist_ok=True)
    
    audio_path = os.path.join(temp_dir, f"{filename}_{uuid.uuid4().hex}.mp3")
    with open(audio_path, "wb") as f:
        f.write(audio_content)
    
    return audio_path

def create_public_url(audio_path):
    """Create publicly accessible URL for audio"""
    # Use ngrok or your domain - for demo, using local
    filename = os.path.basename(audio_path)
    return f"http://your-domain.com/public/{filename}"

@app.route('/sms/webhook', methods=['POST'])
def sms_webhook():
    """Handle incoming SMS messages"""
    message_body = request.form.get('Body', '')
    from_number = request.form.get('From', '')
    
    print(f"📱 SMS from {from_number}: {message_body}")
    
    # Process the command
    result = process_sms_command(message_body, from_number)
    print(f"✅ SMS Response: {result}")
    
    return Response('SMS processed', mimetype='text/plain')

@app.route('/sms/send-briefing')
def send_manual_briefing():
    """Manually trigger SMS briefing"""
    to_number = request.args.get('to', os.getenv("YOUR_PHONE_NUMBER"))
    
    try:
        response = requests.get("http://localhost:5001/briefing/daily")
        if response.status_code == 200:
            audio_path = save_temp_audio(response.content, "manual_briefing")
            audio_url = create_public_url(audio_path)
            
            if send_audio_sms(to_number, audio_url, "🎯 Your tactical briefing:"):
                return "✅ Briefing sent via SMS"
            else:
                return "❌ Failed to send SMS"
        else:
            return "❌ Failed to generate briefing"
    except Exception as e:
        return f"❌ Error: {e}"

if __name__ == '__main__':
    print("📱 SMS Integration Server Starting...")
    print("Commands available:")
    for cmd, pattern in SMS_COMMANDS.items():
        print(f"  • {cmd}: {pattern}")
    
    app.run(debug=True, port=5002)