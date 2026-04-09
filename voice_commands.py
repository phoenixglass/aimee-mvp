import speech_recognition as sr
import pyaudio
import requests
import os
import re
from dotenv import load_dotenv
import threading
import queue
import time
from pydub import AudioSegment
from pydub.playback import play
import io

load_dotenv()

# Salesforce is accessed via the Flask API at localhost:5000
SF_BASE = "http://localhost:5000/salesforce"

class VoiceCommandSystem:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.listening = False
        self.command_queue = queue.Queue()
        
        # Voice command patterns
        self.VOICE_COMMANDS = {
            'wake': r'(?i)\b(aimee|amy|aimi|amie)\b',
            'briefing': r'(?i)\b(brief|briefing|update|status)\b',
            'account': r'(?i)\b(?:brief|tell\s+me\s+about|info\s+on)\s+(barcelona|spiga|labella|bin\s*100|elm)\b',
            'daily': r'(?i)\b(daily|today|morning)\s+(brief|priorities|update)\b',
            'urgent': r'(?i)\b(urgent|priority|hot|fire|critical)\b',
            'pipeline': r'(?i)\b(pipeline|total|value|money|revenue)\b',
            'pitch': r'(?i)\b(pitch|call|generate\s+pitch)\s+(for\s+)?(barcelona|spiga|labella|bin\s*100|elm)\b',
            'stop': r'(?i)\b(stop|quit|exit|done|enough)\b',
            # Salesforce commands
            'sf_lookup': r'(?i)\b(?:pull|look\s+up|salesforce|crm|find)\s+(?:account\s+)?(.+?)(?:\s+in\s+salesforce)?\s*$',
            'sf_opportunities': r'(?i)\b(?:opportunities?|deals?|pipeline)\s+(?:for\s+)?(.+)',
            'sf_log_call': r'(?i)\b(?:log\s+(?:a\s+)?call|note|record\s+call)\s+(?:for\s+)?(.+)',
            'sf_update': r'(?i)\bupdate\s+(.+?)\s+(?:in\s+salesforce|record)\b',
            'sf_activity': r'(?i)\b(?:recent\s+activity|last\s+contact|activity)\s+(?:for\s+)?(.+)',
        }
        
        # Adjust for ambient noise
        with self.microphone as source:
            print("🎤 Calibrating microphone...")
            self.recognizer.adjust_for_ambient_noise(source)
            print("✅ Microphone ready")

    def listen_for_wake_word(self):
        """Continuously listen for wake word 'Aimee'"""
        print("👂 Listening for 'Hey Aimee' or 'Aimee'...")
        
        while True:
            try:
                with self.microphone as source:
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # Use Google Speech Recognition
                text = self.recognizer.recognize_google(audio).lower()
                print(f"🎧 Heard: '{text}'")
                
                # Check for wake word
                if re.search(self.VOICE_COMMANDS['wake'], text):
                    print("🔥 Wake word detected! Listening for command...")
                    self.listen_for_command()
                    
            except sr.WaitTimeoutError:
                pass  # Normal timeout, continue listening
            except sr.UnknownValueError:
                pass  # Couldn't understand audio
            except sr.RequestError as e:
                print(f"❌ Speech recognition error: {e}")
                time.sleep(5)

    def listen_for_command(self):
        """Listen for actual command after wake word"""
        try:
            with self.microphone as source:
                print("🎯 Ready for command...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            command_text = self.recognizer.recognize_google(audio).lower()
            print(f"💬 Command: '{command_text}'")
            
            # Process the command
            self.process_voice_command(command_text)
            
        except sr.WaitTimeoutError:
            self.speak("I didn't hear a command. Try again.")
        except sr.UnknownValueError:
            self.speak("I couldn't understand that. Please repeat.")
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")

    def process_voice_command(self, command_text):
        """Process recognized voice command"""
        
        # Stop listening
        if re.search(self.VOICE_COMMANDS['stop'], command_text):
            self.speak("Voice commands deactivated. See you soon, Phoenix.")
            return False
        
        # Daily briefing
        if re.search(self.VOICE_COMMANDS['daily'], command_text) or re.search(self.VOICE_COMMANDS['briefing'], command_text):
            self.speak("Generating your daily tactical briefing.")
            self.request_briefing("daily")
            return True
        
        # Account-specific briefing
        account_match = re.search(self.VOICE_COMMANDS['account'], command_text)
        if account_match:
            account_name = account_match.group(1).lower().replace(" ", "_")
            account_map = {
                'barcelona': 'barcelona_norwalk',
                'spiga': 'spiga',
                'labella': 'labellas', 
                'bin_100': 'bin_100',
                'elm': 'elm'
            }
            
            account_id = account_map.get(account_name)
            if account_id:
                self.speak(f"Retrieving tactical intelligence for {account_name}.")
                self.request_briefing("account", account_id)
                return True
        
        # Pipeline status
        if re.search(self.VOICE_COMMANDS['pipeline'], command_text):
            self.speak("Calculating pipeline status.")
            self.get_pipeline_status()
            return True
        
        # Urgent priorities  
        if re.search(self.VOICE_COMMANDS['urgent'], command_text):
            self.speak("Activating urgent priority briefing.")
            self.get_urgent_priorities()
            return True
        
        # Generate pitch
        pitch_match = re.search(self.VOICE_COMMANDS['pitch'], command_text)
        if pitch_match:
            account_name = pitch_match.group(3).lower() if pitch_match.group(3) else "default"
            self.speak(f"Generating tactical pitch for {account_name}.")
            self.generate_pitch(account_name)
            return True
        
        # ── Salesforce: account lookup ─────────────────────────────────
        sf_lookup = re.search(self.VOICE_COMMANDS['sf_lookup'], command_text)
        if sf_lookup:
            account_name = sf_lookup.group(1).strip()
            self.speak(f"Pulling {account_name} from Salesforce.")
            self.sf_get_account(account_name)
            return True

        # ── Salesforce: opportunities ──────────────────────────────────
        sf_opps = re.search(self.VOICE_COMMANDS['sf_opportunities'], command_text)
        if sf_opps:
            account_name = sf_opps.group(1).strip()
            self.speak(f"Checking Salesforce opportunities for {account_name}.")
            self.sf_get_opportunities(account_name)
            return True

        # ── Salesforce: log call note ──────────────────────────────────
        sf_log = re.search(self.VOICE_COMMANDS['sf_log_call'], command_text)
        if sf_log:
            account_name = sf_log.group(1).strip()
            self.speak(f"What are your call notes for {account_name}?")
            self.sf_capture_and_log_call(account_name)
            return True

        # ── Salesforce: recent activity ────────────────────────────────
        sf_act = re.search(self.VOICE_COMMANDS['sf_activity'], command_text)
        if sf_act:
            account_name = sf_act.group(1).strip()
            self.speak(f"Retrieving recent Salesforce activity for {account_name}.")
            self.sf_get_recent_activity(account_name)
            return True

        # Default response
        self.speak("Command not recognized. Available commands: briefing, account intel, pipeline status, urgent priorities, generate pitch, pull account from Salesforce, log call, or check opportunities.")
        return True

    def request_briefing(self, briefing_type, account_id=None):
        """Request briefing from web service"""
        try:
            if briefing_type == "daily":
                response = requests.post("http://localhost:5000/test-tactical-briefing",
                                         json={"query": "daily priorities"})
            elif briefing_type == "account" and account_id:
                response = requests.post("http://localhost:5000/test-tactical-briefing",
                                         json={"query": f"brief me on {account_id}"})
            else:
                self.speak("Invalid briefing request.")
                return

            if response.status_code == 200:
                data = response.json()
                self.speak(data.get("main_response", "Briefing not available."))
            else:
                self.speak("Unable to generate briefing.")
                
        except Exception as e:
            print(f"❌ Briefing request error: {e}")
            self.speak("Error retrieving briefing.")

    def get_pipeline_status(self):
        """Get and announce pipeline status"""
        try:
            response = requests.get("http://localhost:5000/accounts")
            if response.status_code == 200:
                accounts = response.json()
                total_value = sum(int(account['value']) for account in accounts.values())
                
                message = f"Total pipeline value is {total_value:,} dollars across {len(accounts)} active accounts."
                self.speak(message)
            else:
                self.speak("Unable to retrieve pipeline data.")
        except Exception as e:
            print(f"❌ Pipeline status error: {e}")
            self.speak("Error retrieving pipeline status.")

    def get_urgent_priorities(self):
        """Announce urgent priorities"""
        urgent_text = """Three urgent priorities detected. LaBella's Fine Wine, Sofia overdue at day 23. Barcelona Wine Bar, Rioja samples needed for Chef Misha. Spiga Wine Bar, Dan Camporeale expects allocation call. Strike with precision."""
        self.speak(urgent_text)

    def generate_pitch(self, account_name):
        """Generate tactical pitch"""
        try:
            account_map = {
                'barcelona': 'barcelona_norwalk',
                'spiga': 'spiga',
                'labella': 'labellas',
                'bin_100': 'bin_100', 
                'elm': 'elm'
            }
            
            account_id = account_map.get(account_name, 'spiga')
            
            pitch_data = {
                "account_id": account_id,
                "tone": "tactical",
                "wine": "premium allocation",
                "gap": "portfolio"
            }
            
            response = requests.post("http://localhost:5000/pitch/generate", json=pitch_data)
            
            if response.status_code == 200:
                self.play_audio_response(response.content)
            else:
                self.speak("Unable to generate pitch.")
                
        except Exception as e:
            print(f"❌ Pitch generation error: {e}")
            self.speak("Error generating pitch.")

    def speak(self, text):
        """Convert text to speech using ElevenLabs"""
        try:
            url = "https://api.elevenlabs.io/v1/text-to-speech/rzsnuMd2pwYz1rGtMIVI"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": os.getenv("ELEVENLABS_API_KEY")
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.4,
                    "similarity_boost": 0.8,
                    "style": 0.25,
                    "use_speaker_boost": True
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                self.play_audio_response(response.content)
            else:
                print(f"❌ TTS Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Speech error: {e}")

    def play_audio_response(self, audio_content):
        """Play audio response"""
        try:
            # Create audio segment from bytes
            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_content))
            
            # Play the audio
            play(audio_segment)
            
        except Exception as e:
            print(f"❌ Audio playback error: {e}")

    # ── Salesforce helpers ─────────────────────────────────────────────────

    def sf_get_account(self, account_name: str):
        """Pull account info from Salesforce and speak the summary."""
        try:
            response = requests.post(
                f"{SF_BASE}/account",
                json={"account_name": account_name},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                self.speak(data.get("voice_summary", f"Got account info for {account_name}."))
            elif response.status_code == 404:
                self.speak(f"I couldn't find {account_name} in Salesforce.")
            else:
                error = response.json().get("error", "Unknown error")
                self.speak(f"Salesforce returned an error: {error}")
        except requests.exceptions.ConnectionError:
            self.speak("Aimee server is not running. Please start the Flask app first.")
        except Exception as e:
            print(f"❌ SF account lookup error: {e}")
            self.speak("Error retrieving account from Salesforce.")

    def sf_get_opportunities(self, account_name: str):
        """Pull open opportunities for an account and speak the summary."""
        try:
            response = requests.post(
                f"{SF_BASE}/opportunities",
                json={"account_name": account_name},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                self.speak(data.get("voice_summary", f"Retrieved opportunities for {account_name}."))
            elif response.status_code == 404:
                self.speak(f"No opportunities found for {account_name} in Salesforce.")
            else:
                error = response.json().get("error", "Unknown error")
                self.speak(f"Couldn't retrieve opportunities: {error}")
        except requests.exceptions.ConnectionError:
            self.speak("Aimee server is not running. Please start the Flask app first.")
        except Exception as e:
            print(f"❌ SF opportunities error: {e}")
            self.speak("Error retrieving opportunities from Salesforce.")

    def sf_capture_and_log_call(self, account_name: str):
        """Listen for dictated call notes, then log them as a Task in Salesforce."""
        try:
            with self.microphone as source:
                print("🎙️  Listening for call notes...")
                audio = self.recognizer.listen(source, timeout=15, phrase_time_limit=60)

            notes_text = self.recognizer.recognize_google(audio)
            print(f"📝 Call notes: '{notes_text}'")
            self.speak(f"Got it. Logging call for {account_name}.")

            response = requests.post(
                f"{SF_BASE}/log-call",
                json={
                    "account_name": account_name,
                    "subject": f"Call - {account_name}",
                    "description": notes_text,
                },
                timeout=10,
            )
            if response.status_code == 200:
                self.speak(f"Call note logged for {account_name} in Salesforce.")
            else:
                error = response.json().get("error", "Unknown error")
                self.speak(f"Couldn't log call note: {error}")

        except sr.WaitTimeoutError:
            self.speak("I didn't hear any notes. Call not logged.")
        except sr.UnknownValueError:
            self.speak("I couldn't understand the notes. Please try again.")
        except requests.exceptions.ConnectionError:
            self.speak("Aimee server is not running. Please start the Flask app first.")
        except Exception as e:
            print(f"❌ SF log call error: {e}")
            self.speak("Error logging call note.")

    def sf_get_recent_activity(self, account_name: str):
        """Retrieve and speak recent Salesforce activity for an account."""
        try:
            response = requests.post(
                f"{SF_BASE}/recent-activity",
                json={"account_name": account_name},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                self.speak(data.get("voice_summary", f"Retrieved activity for {account_name}."))
            elif response.status_code == 404:
                self.speak(f"No activity found for {account_name} in Salesforce.")
            else:
                error = response.json().get("error", "Unknown error")
                self.speak(f"Couldn't retrieve activity: {error}")
        except requests.exceptions.ConnectionError:
            self.speak("Aimee server is not running. Please start the Flask app first.")
        except Exception as e:
            print(f"❌ SF activity error: {e}")
            self.speak("Error retrieving Salesforce activity.")

    def start_listening(self):
        """Start the voice command system"""
        print("🎤 Aimee Voice Command System Activated")
        print("Say 'Hey Aimee' or 'Aimee' followed by your command")
        print("Commands:")
        print("  • 'daily briefing' - Get daily tactical briefing")
        print("  • 'brief [account]' - Get account intelligence")
        print("  • 'pipeline status' - Get pipeline value")
        print("  • 'urgent priorities' - Get hot priorities")
        print("  • 'generate pitch for [account]' - Create tactical pitch")
        print("  • 'stop' - Deactivate voice commands")
        print("  • 'pull [account] from Salesforce' - Account info from CRM")
        print("  • 'opportunities for [account]' - Open deals in Salesforce")
        print("  • 'log call for [account]' - Dictate and log a call note")
        print("  • 'recent activity for [account]' - Last logged activity")
        
        try:
            self.listen_for_wake_word()
        except KeyboardInterrupt:
            print("\n🛑 Voice commands stopped")

if __name__ == "__main__":
    # Install required packages first
    print("📦 Required packages:")
    print("pip install SpeechRecognition pyaudio pydub")
    print("🎤 Starting Voice Command System...")
    
    voice_system = VoiceCommandSystem()
    voice_system.start_listening()