import threading
import time
from flask import Flask
from voice_commands import VoiceCommandSystem
from sms_integration import sms_webhook, send_manual_briefing
from tactical_briefing_web import app as web_app

class AimeeCompleteSystem:
    def __init__(self):
        self.voice_system = VoiceCommandSystem()
        self.web_app = web_app
        self.services_running = False

    def start_web_service(self):
        """Start the web dashboard"""
        print("🌐 Starting web dashboard on port 5001...")
        self.web_app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)

    def start_sms_service(self):
        """Start SMS webhook service"""
        print("📱 Starting SMS service on port 5002...")
        from sms_integration import app as sms_app
        sms_app.run(host='0.0.0.0', port=5002, debug=False, use_reloader=False)

    def start_voice_service(self):
        """Start voice command system"""
        print("🎤 Starting voice command system...")
        time.sleep(2)  # Let other services start first
        self.voice_system.start_listening()

    def start_all_services(self):
        """Start all Aimee services"""
        print("🍷 AIMEE COMPLETE SYSTEM ACTIVATION")
        print("=" * 50)
        
        # Start web service in background
        web_thread = threading.Thread(target=self.start_web_service, daemon=True)
        web_thread.start()
        
        # Start SMS service in background  
        sms_thread = threading.Thread(target=self.start_sms_service, daemon=True)
        sms_thread.start()
        
        # Give services time to start
        time.sleep(3)
        
        print("✅ Web Dashboard: http://localhost:5001")
        print("✅ SMS Webhook: http://localhost:5002") 
        print("✅ Voice Commands: Listening for 'Hey Aimee'")
        print()
        print("🎯 ALL SYSTEMS OPERATIONAL")
        print("🍷 Aimee is ready for tactical dominance")
        print()
        
        # Start voice commands (blocking)
        self.start_voice_service()

if __name__ == "__main__":
    system = AimeeCompleteSystem()
    system.start_all_services()