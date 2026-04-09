import schedule
import time
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.audio import MIMEAudio
from email.mime.text import MIMEText

load_dotenv()

def generate_morning_briefing():
    """Generate and optionally email morning briefing"""
    print(f"🌅 Generating morning briefing at {datetime.now()}")
    
    # Call your tactical briefing generator
    try:
        response = requests.get("http://localhost:5001/briefing/daily")
        
        if response.status_code == 200:
            # Save the audio file
            with open(f"daily_briefing_{datetime.now().strftime('%Y%m%d')}.mp3", "wb") as f:
                f.write(response.content)
            
            print("✅ Morning briefing generated successfully")
            
            # Optional: Send via email
            send_briefing_email(response.content)
            
        else:
            print(f"❌ Error generating briefing: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Automation error: {e}")

def send_briefing_email(audio_content):
    """Send briefing as email attachment"""
    try:
        msg = MIMEMultipart()
        msg['From'] = os.getenv("EMAIL_FROM")
        msg['To'] = os.getenv("EMAIL_TO") 
        msg['Subject'] = f"Daily Tactical Briefing - {datetime.now().strftime('%B %d, %Y')}"
        
        body = """
        Good morning Phoenix,
        
        Your daily tactical briefing is attached.
        
        Total pipeline value active.
        Strike with precision.
        
        - Aimee
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach audio
        audio_attachment = MIMEAudio(audio_content)
        audio_attachment.add_header('Content-Disposition', 'attachment', 
                                  filename=f"briefing_{datetime.now().strftime('%Y%m%d')}.mp3")
        msg.attach(audio_attachment)
        
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_PASSWORD"))
        text = msg.as_string()
        server.sendmail(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_TO"), text)
        server.quit()
        
        print("✅ Briefing emailed successfully")
        
    except Exception as e:
        print(f"❌ Email error: {e}")

def schedule_briefings():
    """Set up automated scheduling"""
    
    # Daily morning briefing
    schedule.every().day.at("07:00").do(generate_morning_briefing)
    
    # Weekly pipeline review (Mondays at 8 AM)
    schedule.every().monday.at("08:00").do(generate_weekly_review)
    
    # Urgent follow-ups (every 4 hours during business)
    schedule.every(4).hours.do(check_urgent_followups)
    
    print("📅 Automation scheduled:")
    print("  • Daily briefings at 7:00 AM")
    print("  • Weekly reviews on Mondays at 8:00 AM")  
    print("  • Urgent checks every 4 hours")
    print("🚀 Automation running...")

def generate_weekly_review():
    """Generate weekly pipeline review"""
    print("📊 Generating weekly pipeline review...")
    # Implementation for weekly analysis

def check_urgent_followups():
    """Check for urgent follow-ups needed"""
    print("⚡ Checking urgent follow-ups...")
    # Implementation for urgent checks

if __name__ == "__main__":
    schedule_briefings()
    
    while True:
        schedule.run_pending()
        time.sleep(60)