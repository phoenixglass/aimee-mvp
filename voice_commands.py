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
            'stop': r'(?i)\b(stop|quit|exit|done|enough)\b'
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
        
        # Default response
        self.speak("Command not recognized. Available commands: briefing, account intel, pipeline status, urgent priorities, or generate pitch.")
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