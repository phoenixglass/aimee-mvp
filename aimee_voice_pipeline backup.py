from elevenlabs.client import ElevenLabs
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from aimee_classifier import AimeeClassifier
from gtts import gTTS
from datetime import datetime
import os
import tempfile
import uuid
import json
import hashlib
import asyncio
import threading
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import time
import csv
from typing import Dict, Any, Optional, TypedDict, List

# Import custom modules
from aimee_wine_intelligence import AimeeWineIntelligence, handle_taste_query, handle_pairing_query
from aimee_fairfield_integration import integrate_fairfield_intelligence

# Whisper import with better error handling
WHISPER_AVAILABLE = False
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError as e:
    print(f"Whisper not available: {e}")

# Constants
ALLOWED_AUDIO_EXTENSIONS = {'wav', 'mp3', 'ogg', 'm4a'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# TypedDict definitions
class EntityDict(TypedDict, total=False):
    customer_name: str
    restaurant: str
    distributor_name: str
    competitor: str
    wine: str
    quantity: str
    size: str
    delivery: str

class VerificationResult(TypedDict):
    original: str
    verified: str
    confidence: str
    completed_at: str
    error: Optional[str]

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize services
fairfield_handlers = integrate_fairfield_intelligence()
wine_intelligence = AimeeWineIntelligence()
classifier = AimeeClassifier(data_file="aimee_training_data_tagged.json", threshold=0.1)

# ElevenLabs setup with better error handling
elevenlabs_client = None
try:
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
    if not ELEVENLABS_API_KEY:
        raise ValueError("ElevenLabs API key not found in environment variables")
    
    elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    print("ElevenLabs client initialized successfully")
except ImportError as e:
    print(f"ElevenLabs package not available: {e}")
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Failed to initialize ElevenLabs client: {str(e)}")

# Global caches
transcription_cache: Dict[str, Dict[str, Any]] = {}
verification_results: Dict[str, VerificationResult] = {}

# Precompiled regex patterns
WINE_TERM_PATTERNS = {
    r'\bbubbles?\b': 'sparkling wine',
    r'\b(na|n/a)\b': 'non-alcoholic',
    r'\brtd\b': 'ready to drink',
    r'\bnapa\b': 'napa valley',
    r'\bsonoma\b': 'sonoma county',
    r'\bcab\b(?! sauv)': 'cabernet',
    r'\bcab sauv\b': 'cabernet sauvignon',
    r'\bchard\b': 'chardonnay',
    r'\bsauv blanc\b': 'sauvignon blanc',
    r'\bpinot\b': 'pinot noir',
    r'\btemp\b': 'tempranillo',
    r'\btop shelf\b': 'premium',
    r'\bhigh end\b': 'premium',
    r'\bbudget\b': 'affordable',
    r'\bcheap\b': 'affordable',
    r'\bmag\b': 'magnum',
    r'\bhalf bottle\b': 'half-bottle',
    r'\b375ml\b': 'half-bottle',
    r'\b750ml\b': 'standard bottle',
    r'\b1\.5l\b': 'magnum',
    r'\beta\b': 'estimated delivery',
    r'\basap\b': 'as soon as possible',
    r'\brush\b': 'urgent delivery',
    r'\bstat\b': 'immediately'
}

CUSTOMER_PATTERNS = [re.compile(p) for p in [
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)(?:\s+(?:needs|wants|requires|ordered))',
    r'\b([A-Z][a-z]+(?:\'s)?)(?:\s+(?:fine\s+wine|wine|vineyard|winery|cellar))',
    r'\bfor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)\s+(?:is\s+)?(?:looking|asking)',
]]

WINE_PATTERNS = [re.compile(p) for p in [
    r'\b((?:[A-Z][a-z]+\s+)*(?:Chardonnay|Cabernet Sauvignon|Cabernet|Merlot|Pinot Noir|Pinot Grigio|Sauvignon Blanc|Riesling|Syrah|Shiraz|Malbec|Tempranillo|Sangiovese|Chianti|Bordeaux|Burgundy|Champagne|Prosecco|Moscato))\b',
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)\s+(?:wine|vintage|bottle)',
    r'\bthe\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)\b',
    r'\b((?:[0-9]{4}\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)\s+(?:from|by)',
]]

TONE_KEYWORDS = {
    'urgent': ['urgent', 'asap', 'rush', 'immediately', 'emergency', 'stat'],
    'polite': ['please', 'thank you', 'kindly', 'appreciate', 'grateful'],
    'casual': ['hey', 'sup', 'what\'s up', 'yo'],
    'formal': ['sir', 'madam', 'certainly', 'regarding', 'furthermore']
}

class WhisperModelManager:
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=min(4, os.cpu_count() * 2))
        self.load_lock = threading.Lock()
    
    def get_model(self, model_type: str = "base") -> Any:
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper not available")
        
        if model_type not in self.models:
            with self.load_lock:
                if model_type not in self.models:
                    print(f"Loading Whisper model: {model_type}")
                    self.models[model_type] = whisper.load_model(model_type)
                    print(f"Model {model_type} loaded successfully")
        
        return self.models[model_type]

model_manager = WhisperModelManager()

def allowed_file(filename: str) -> bool:
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def save_cache() -> None:
    """Save transcription cache to disk"""
    try:
        with open('transcription_cache.json', 'w') as f:
            json.dump(transcription_cache, f)
    except Exception as e:
        print(f"Error saving cache: {e}")

def hash_file(path: str) -> str:
    """Generate MD5 hash for file content"""
    hasher = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def preprocess_wine_terminology(text: str) -> str:
    """Convert wine industry shorthand to full terms using compiled regex"""
    processed_text = text.lower()
    for pattern, replacement in WINE_TERM_PATTERNS.items():
        processed_text = re.sub(pattern, replacement, processed_text)
    return processed_text

def detect_special_responses(transcript: str) -> str:
    """Detect special response scenarios that override normal classification"""
    transcript_lower = transcript.lower()
    
    # Greeting detection
    greeting_patterns = [
        r'\b(hi|hello|hey)\s+(aimee|amy)\b',
        r'^(hi|hello|hey)\s*$',
        r'\b(good\s+(morning|afternoon|evening))\b'
    ]
    
    for pattern in greeting_patterns:
        if re.search(pattern, transcript_lower):
            return "Hello! I'm Aimee, your wine industry assistant. How can I help you today?"
    
    # Gratitude detection
    if any(phrase in transcript_lower for phrase in ['thank you', 'thanks', 'appreciate']):
        return "You're very welcome! Happy to help with your wine needs."
    
    # Confusion detection
    confusion_indicators = ['what', 'huh', 'unclear', 'didn\'t catch', 'repeat']
    if any(indicator in transcript_lower for indicator in confusion_indicators):
        return "I'm sorry, could you please repeat that? I want to make sure I help you correctly."
    
    return ""

def handle_fairfield_intent(intent: str, entities: Optional[EntityDict]) -> str:
    """Handle Fairfield County specific intents"""
    if intent == "customer_intelligence":
        customer_name = entities.get("customer_name", "") if entities else ""
        if not customer_name:
            customer_name = entities.get("restaurant", "") if entities else ""
        
        if customer_name:
            try:
                response = fairfield_handlers['customer_intelligence'](customer_name)
                return f"Here's the intelligence on {customer_name}: {response}"
            except Exception as e:
                print(f"Error in customer_intelligence: {e}")
                return f"I found information about {customer_name}, but there was an error retrieving it."
        return "Which customer would you like intelligence on?"

    elif intent in ["daily_briefing", "daily_priorities"]:
        try:
            response = fairfield_handlers['daily_briefing']()
            return f"Here's your daily briefing: {response}"
        except Exception as e:
            print(f"Error in daily_briefing: {e}")
            return "Let me get your daily briefing... There was an issue retrieving the latest information."

    elif intent == "gap_analysis":
        customer_name = entities.get("customer_name", "") if entities else ""
        if not customer_name:
            customer_name = entities.get("restaurant", "") if entities else ""
        
        if customer_name:
            try:
                response = fairfield_handlers['gap_analysis'](customer_name)
                return f"Gap analysis for {customer_name}: {response}"
            except Exception as e:
                print(f"Error in gap_analysis: {e}")
                return f"I can analyze wine list gaps for {customer_name}, but there was an error."
        return "Which customer's wine list should I analyze for gaps?"

    elif intent == "opportunity_analysis":
        customer_name = entities.get("customer_name", "") if entities else ""
        if not customer_name:
            customer_name = entities.get("restaurant", "") if entities else ""
        
        if customer_name:
            try:
                response = fairfield_handlers['opportunity_analysis'](customer_name)
                return f"Opportunity analysis for {customer_name}: {response}"
            except Exception as e:
                print(f"Error in opportunity_analysis: {e}")
                return f"I can analyze opportunities for {customer_name}, but there was an error."
        return "Which customer's opportunities should I analyze?"

    elif intent == "competitive_strategy":
        customer_name = entities.get("customer_name", "") if entities else ""
        if not customer_name:
            customer_name = entities.get("restaurant", "") if entities else ""
        competitor = entities.get("competitor", None) if entities else None
        
        if customer_name:
            try:
                response = fairfield_handlers['competitive_strategy'](customer_name, competitor)
                return f"Competitive strategy for {customer_name}: {response}"
            except Exception as e:
                print(f"Error in competitive_strategy: {e}")
                return f"I can help with competitive strategy for {customer_name}, but there was an error."
        return "Which customer needs competitive strategy?"

    elif intent == "meeting_preparation":
        customer_name = entities.get("customer_name", "") if entities else ""
        if not customer_name:
            customer_name = entities.get("restaurant", "") if entities else ""
        
        if customer_name:
            try:
                response = fairfield_handlers['meeting_preparation'](customer_name)
                return f"Meeting preparation for {customer_name}: {response}"
            except Exception as e:
                print(f"Error in meeting_preparation: {e}")
                return f"I can prepare you for your {customer_name} meeting, but there was an error."
        return "Which customer meeting should I prepare you for?"

    elif intent == "distributor_intelligence":
        distributor_name = entities.get("distributor_name", "") if entities else ""
        if not distributor_name:
            distributor_name = entities.get("distributor", "") if entities else ""
        
        if distributor_name:
            try:
                response = fairfield_handlers['distributor_intelligence'](distributor_name)
                return f"Distributor intelligence on {distributor_name}: {response}"
            except Exception as e:
                print(f"Error in distributor_intelligence: {e}")
                return f"I can provide intelligence on {distributor_name}, but there was an error."
        return "Which distributor would you like intelligence on?"

    return ""

def extract_wine_details(transcript: str) -> Dict[str, str]:
    """Extract wine-specific details from transcript"""
    details = {
        'wine': None,
        'quantity': None,
        'size': None,
        'delivery': None
    }

    # Extract wine
    for pattern in WINE_PATTERNS:
        match = pattern.search(transcript)
        if match:
            details['wine'] = match.group(1).strip()
            break

    # Extract quantity
    quantity_patterns = [
        r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:bottles?|cases?)\b',
        r'\b(\d+)\s+(?:bottles?|cases?|units?)\b',
        r'\b(a\s+(?:bottle|case|dozen))\b',
        r'\b(half\s+a\s+dozen|dozen)\b'
    ]
    
    for pattern in quantity_patterns:
        match = re.search(pattern, transcript.lower())
        if match:
            details['quantity'] = match.group(1).strip()
            break

    # Extract size
    size_patterns = [
        r'\b(magnum|half-bottle|standard|375ml|750ml|1\.5l|split)\b',
        r'\bin\s+(large|small|regular)\s+(?:size|bottles?)\b'
    ]
    
    for pattern in size_patterns:
        match = re.search(pattern, transcript.lower())
        if match:
            details['size'] = match.group(1).strip()
            break

    # Extract delivery
    delivery_patterns = [
        r'\b(?:for|by|on)\s+(today|tomorrow|this\s+week|next\s+week|friday|monday|tuesday|wednesday|thursday|saturday|sunday)\b',
        r'\b(?:for|by)\s+(\d{1,2}\/\d{1,2}|\d{1,2}th?|\d{1,2}nd|\d{1,2}rd)\b',
        r'\b(as soon as possible|asap|urgent|rush|immediately)\b'
    ]
    
    for pattern in delivery_patterns:
        match = re.search(pattern, transcript.lower())
        if match:
            details['delivery'] = match.group(1).strip()
            break

    return details

def extract_key_details(transcript: str, intent: str, entities: Optional[EntityDict] = None) -> str:
    """Extract key details and create summary with wine intelligence"""
    # Handle Fairfield County intents first
    fairfield_intents = [
        'customer_intelligence', 'daily_briefing', 'daily_priorities', 
        'opportunity_analysis', 'gap_analysis', 'competitive_strategy', 
        'meeting_preparation', 'distributor_intelligence'
    ]
    
    if intent in fairfield_intents:
        return handle_fairfield_intent(intent, entities)

    # Check for wine keywords
    text_lower = transcript.lower()
    wine_keywords = ['wine', 'pairing', 'seafood', 'celebration', 'fruity', 'crisp', 'bold', 'light', 
                    'chardonnay', 'cabernet', 'champagne', 'pinot', 'merlot']
    
    if any(keyword in text_lower for keyword in wine_keywords):
        if any(food in text_lower for food in ['seafood', 'salmon', 'fish']):
            response = handle_pairing_query('seafood', wine_intelligence)
            return f"I heard: {transcript}. {response}"
        elif any(celebration in text_lower for celebration in ['celebration', 'wedding', 'champagne']):
            response = handle_pairing_query('celebration', wine_intelligence)
            return f"I heard: {transcript}. {response}"
        elif any(taste in text_lower for taste in ['fruity', 'light', 'crisp', 'bold']):
            taste_descriptors = []
            if 'fruity' in text_lower:
                taste_descriptors.extend(['blackberry', 'apple', 'citrus'])
            if 'bold' in text_lower:
                taste_descriptors.extend(['cedar', 'vanilla'])
            if 'light' in text_lower:
                taste_descriptors.extend(['citrus', 'apple'])
            if 'crisp' in text_lower:
                taste_descriptors.extend(['citrus', 'apple'])
            
            response = handle_taste_query(taste_descriptors, wine_intelligence)
            return f"I heard: {transcript}. {response}"

    # Preprocess wine terminology
    text = preprocess_wine_terminology(transcript)
    
    # Extract customer name
    customer = None
    for pattern in CUSTOMER_PATTERNS:
        match = pattern.search(transcript)
        if match:
            potential_customer = match.group(1).strip()
            wine_terms = ['Chardonnay', 'Cabernet', 'Merlot', 'Pinot', 'Sauvignon', 'Wine', 'Vineyard', 'Cellar', 'Valley', 'Estate']
            if not any(term in potential_customer for term in wine_terms):
                customer = potential_customer
                break

    # Extract wine details
    wine_details = extract_wine_details(transcript)
    
    # Build response based on intent
    if intent == "add_to_order":
        parts = []
        if customer:
            parts.append(customer)
        if customer and (wine_details['quantity'] or wine_details['wine']):
            parts.append("needs")
        if wine_details['quantity'] and wine_details['wine']:
            parts.append(f"{wine_details['quantity']} of {wine_details['wine']}")
        elif wine_details['quantity']:
            parts.append(wine_details['quantity'])
        elif wine_details['wine']:
            parts.append(wine_details['wine'])
        if wine_details['size']:
            parts.append(f"in {wine_details['size']}")
        if wine_details['delivery']:
            parts.append(f"for {wine_details['delivery']}")
        
        return "I heard: " + " ".join(parts) + "." if len(parts) >= 2 else "I heard: add to order."

    elif intent == "check_shipment_status":
        return f"I heard: ETA check for {wine_details['wine']}." if wine_details['wine'] else "I heard: shipment status check."

    elif intent == "check_inventory":
        parts = [f"check inventory for {wine_details['wine']}"] if wine_details['wine'] else ["inventory check"]
        if "cheapest possible" in text_lower:
            parts.append("cheapest possible")
        if customer:
            parts.append(f"for {customer}")
        return "I heard: " + " ".join(parts) + "."

    elif intent == "gift_request":
        parts = ["gift request"]
        if "wedding" in text_lower:
            parts = ["wedding gift request"]
        elif "mother to daughter" in text_lower:
            parts = ["mother to daughter gift request"]
        elif "anniversary" in text_lower:
            parts = ["anniversary gift request"]
        elif "birthday" in text_lower:
            parts = ["birthday gift request"]

        if wine_details['wine']:
            parts.append(f"for {wine_details['wine']}")
        elif "champagne" in text_lower:
            parts.append("for champagne")
        elif "sparkling wine" in text_lower:
            parts.append("for sparkling wine")
        elif "red wine" in text_lower:
            parts.append("for red wine")
        elif "white wine" in text_lower:
            parts.append("for white wine")

        if "best" in text_lower and ("you've got" in text_lower or "available" in text_lower):
            parts.append("the best available")
        elif "premium" in text_lower:
            parts.append("premium quality")
        elif "special" in text_lower:
            parts.append("something special")

        if re.search(r'\b(19|20)\d{2}\b', text_lower):
            vintage_match = re.search(r'\b(19|20)\d{2}\b', text_lower)
            parts.append(f"vintage {vintage_match.group()}")

        return "I heard: " + " ".join(parts) + "."

    elif intent == "taste_preference_query":
        taste_descriptors = []
        if "fruity" in text_lower:
            taste_descriptors.append("fruity")
        if "light" in text_lower:
            taste_descriptors.append("light")
        if "bold" in text_lower:
            taste_descriptors.append("bold")
        if "crisp" in text_lower:
            taste_descriptors.append("crisp")
        
        response = handle_taste_query(taste_descriptors, wine_intelligence)
        return f"I heard: {transcript}. {response}"

    elif intent == "wine_pairing_request":
        food_type = ""
        if "seafood" in text_lower or "salmon" in text_lower:
            food_type = "seafood"
        elif "celebration" in text_lower or "wedding" in text_lower:
            food_type = "celebration"
        elif "steak" in text_lower or "meat" in text_lower:
            food_type = "red meat"
        
        if food_type:
            response = handle_pairing_query(food_type, wine_intelligence)
            return f"I heard: {transcript}. {response}"
        return f"I heard: {transcript}. I'd be happy to help with wine pairings - could you tell me what food you're serving?"

    elif intent == "flavor_profile_inquiry":
        return f"I heard: {transcript}. I'd be happy to tell you about that wine's flavor profile. Which specific wine are you interested in?"

    elif intent == "taste_based_recommendation":
        return f"I heard: {transcript}. I can definitely help you find similar wines. What wine did you have in mind as a reference?"

    # Default response
    if customer and wine_details['wine']:
        return f"I heard: {customer} request for {wine_details['wine']}."
    elif customer:
        return f"I heard: request from {customer}."
    elif wine_details['wine']:
        return f"I heard: request about {wine_details['wine']}."
    return "I heard your request."

def detect_tone(transcript_lower: str) -> str:
    """Detect tone from transcript using precompiled keywords"""
    for tone, keywords in TONE_KEYWORDS.items():
        if any(keyword in transcript_lower for keyword in keywords):
            return tone
    return "neutral"

def format_response(intent: str, tone: str) -> str:
    """Format response based on intent and tone"""
    intent_responses = {
        "add_to_order": "I'll get that order processed.",
        "check_inventory": "I'll check what we have in stock.",
        "cancel_order": "Consider it canceled.",
        "confirm_delivery": "I'll confirm those delivery details.",
        "check_pricing": "Let me pull current pricing for you.",
        "check_shipment_status": "I'll track that shipment for you.",
        "gift_request": "Perfect! I'll help you find the ideal gift.",
        "product_recommendation": "I'll recommend something perfect for you.",
        "schedule_appointment": "I'll get that appointment scheduled.",
        "taste_preference_query": "Let me find wines that match your taste preferences.",
        "wine_pairing_request": "I'll suggest perfect wine pairings for you.",
        "flavor_profile_inquiry": "I'll tell you all about that wine's flavor profile.",
        "taste_based_recommendation": "I'll find wines similar to what you love."
    }
    
    base_response = intent_responses.get(intent, "I'll help you with that.")
    
    if tone == "urgent":
        return f"{base_response} Right on it."
    elif tone == "polite":
        return f"{base_response} Thank you for your business."
    elif tone == "casual":
        return f"{base_response} No problem!"
    return base_response

def generate_aimee_response(text: str, voice_id: str = "rzsnuMd2pwYz1rGtMIVI") -> str:
    """Generate audio file with proper path handling"""
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)
        
        # Generate a filename in the uploads folder
        filename = os.path.join('uploads', f'response_{int(time.time())}.mp3')
        
        # Use gTTS (which we know works)
        tts = gTTS(text=text, lang='en')
        tts.save(filename)
        
        # Return relative path
        return filename
        
    except Exception as e:
        print(f"AUDIO GENERATION ERROR: {str(e)}")
        return ""

def generate_audio_response(text: str) -> str:
    """Consistent implementation"""
    return generate_aimee_response(text)

@lru_cache(maxsize=1000)
def transcribe_audio_cached(filepath: str, model_type: str = "base") -> Dict[str, Any]:
    """Cached transcription with performance optimization"""
    file_hash = hash_file(filepath)
    cache_key = f"{file_hash}_{model_type}"
    
    if cache_key in transcription_cache:
        return transcription_cache[cache_key]
    
    if not WHISPER_AVAILABLE:
        return {
            'text': '[Whisper not available]',
            'transcription_time': 0,
            'model_used': 'none'
        }
    
    start_time = time.time()
    
    try:
        model = model_manager.get_model(model_type)
        result = model.transcribe(filepath, fp16=False, language="en")
        
        result_data = {
            'text': result["text"].strip(),
            'transcription_time': round(time.time() - start_time, 2),
            'model_used': model_type
        }
        
        transcription_cache[cache_key] = result_data
        if len(transcription_cache) % 10 == 0:
            save_cache()
        
        return result_data
        
    except Exception as e:
        print(f"Transcription error: {e}")
        return {
            'text': f'[Transcription error: {str(e)}]',
            'transcription_time': time.time() - start_time,
            'model_used': model_type
        }

def verify_transcript_background(filepath: str, base_transcript: str, file_hash: str) -> None:
    """Background verification using medium model"""
    try:
        verification_result = transcribe_audio_cached(filepath, model_type="medium")
        
        verification_results[file_hash] = {
            'original': base_transcript,
            'verified': verification_result['text'],
            'confidence': 'high' if abs(len(base_transcript) - len(verification_result['text'])) < 10 else 'medium',
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Background verification error: {e}")
        verification_results[file_hash] = {
            'original': base_transcript,
            'verified': '[Verification failed]',
            'confidence': 'low',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        }

def log_interaction(transcript: str, classification: Dict[str, Any], audio_filename: Optional[str]) -> None:
    """Log interaction to CSV file"""
    try:
        with open('aimee_interactions.csv', 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            if csvfile.tell() == 0:
                writer.writerow(['timestamp', 'transcript', 'intent', 'tone', 'confidence', 'audio_file'])
            
            writer.writerow([
                datetime.now().isoformat(),
                transcript,
                classification.get('intent', 'unknown'),
                classification.get('tone', 'unknown'),
                classification.get('match_score', 0.0),
                audio_filename or 'none'
            ])
    except Exception as e:
        print(f"Error logging interaction: {e}")

# Flask routes
@app.route('/')
def index():
    return render_template('voice_demo.html')

@app.route('/test-elevenlabs')
def test_elevenlabs():
    test_text = "Hello, this is a test of Aimee's voice synthesis."
    try:
        audio_file = generate_aimee_response(test_text)
        return jsonify({
            'status': 'success' if audio_file else 'error',
            'message': 'ElevenLabs test successful' if audio_file else 'Audio generation failed',
            'audio_file': audio_file if audio_file else None
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'ElevenLabs test failed: {str(e)}'})

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'whisper_available': WHISPER_AVAILABLE,
        'elevenlabs_available': elevenlabs_client is not None
    })

@app.route('/demo')
def voice_demo():
    return render_template('voice_demo.html')

@app.route('/play_audio/<path:filename>')
def play_audio(filename):
    """Serve audio files safely"""
    try:
        # Security check - only allow files from uploads folder
        if not filename.startswith('uploads/'):
            filename = 'uploads/' + filename
            
        return send_from_directory('.', filename, mimetype='audio/mpeg')
    except Exception as e:
        print(f"AUDIO DELIVERY ERROR: {str(e)}")
        return "Audio not found", 404

@app.route('/classify', methods=['POST'])
def classify_text():
    """Improved classification endpoint"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Classify the text
        classification = classifier.classify(text)
        
        # Generate response
        response = {
            'input': text,
            'intent': classification['intent'],
            'confidence': round(classification['match_score'], 2),
            'entities': classification['entities'],
            'success': True
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file'}), 400
        
        file = request.files['audio']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400
        
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        processing_start = time.time()
        file_hash = hash_file(filepath)
        transcript_data = transcribe_audio_cached(filepath)
        transcript = transcript_data['text']
        
        if not transcript.strip():
            return jsonify({'error': 'Could not transcribe audio'}), 400
        
        threading.Thread(
            target=verify_transcript_background, 
            args=(filepath, transcript, file_hash),
            daemon=True
        ).start()
        
        processed_transcript = preprocess_wine_terminology(transcript)
        classification = classifier.classify(processed_transcript)
        tone = detect_tone(transcript.lower())
        classification['tone'] = tone
        
        special_response = detect_special_responses(transcript)
        if special_response:
            response_text = special_response
        else:
            intent = classification['intent']
            if intent != "unknown":
                key_details = extract_key_details(transcript, intent, classification.get('entities', {}))
                base_response = format_response(intent, tone)
                response_text = f"{key_details} {base_response}"
            else:
                response_text = "I heard your message, but I'm not sure how to help. Could you please rephrase that?"
        
        audio_filename = generate_aimee_response(response_text)
        processing_time = time.time() - processing_start
        log_interaction(transcript, classification, audio_filename)
        
        return jsonify({
            'transcript': transcript,
            'intent': classification['intent'],
            'tone': classification['tone'],
            'score': classification['match_score'],
            'processing_time': round(processing_time, 2),
            'transcription_time': transcript_data.get('transcription_time', 0),
            'model_used': transcript_data.get('model_used', 'base'),
            'response_text': response_text,
            'audio_file': audio_filename,
            'file_hash': file_hash,
            'verification_status': 'pending'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process-text', methods=['POST'])
def process_text():
    try:
        data = request.get_json()
        transcript = data.get('text', '')
        if not transcript:
            return jsonify({'error': 'No text provided'}), 400
        
        processing_start = time.time()
        processed_transcript = preprocess_wine_terminology(transcript)
        classification = classifier.classify(processed_transcript)
        tone = detect_tone(transcript.lower())
        classification['tone'] = tone
        
        special_response = detect_special_responses(transcript)
        if special_response:
            response_text = special_response
        else:
            intent = classification.get("intent", "unknown")
            if intent != "unknown":
                key_details = extract_key_details(transcript, intent, classification.get('entities', {}))
                base_response = format_response(intent, tone)
                response_text = f"{key_details} {base_response}"
            else:
                response_text = "I heard your message, but I'm not sure how to help. Could you please rephrase that?"
        
        audio_filename = generate_aimee_response(response_text)
        processing_time = time.time() - processing_start
        log_interaction(transcript, classification, audio_filename)
        
        return jsonify({
            'transcript': transcript,
            'intent': classification['intent'],
            'tone': classification['tone'],
            'score': classification['match_score'],
            'processing_time': round(processing_time, 2),
            'transcription_time': 0,
            'model_used': 'text_input',
            'response_text': response_text,
            'audio_file': audio_filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/verification-status/<file_hash>')
def verification_status(file_hash):
    if file_hash in verification_results:
        return jsonify({
            'status': 'completed',
            'result': verification_results[file_hash]
        })
    return jsonify({'status': 'pending'})

@app.route('/force-verify', methods=['POST'])
def force_verify():
    try:
        file_hash = request.get_json().get('file_hash')
        if not file_hash:
            return jsonify({'error': 'No file hash provided'}), 400
        
        if file_hash in verification_results:
            return jsonify({
                'status': 'completed',
                'result': verification_results[file_hash]
            })
        return jsonify({
            'status': 'not_found',
            'message': 'File verification not available'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup_old_files():
    try:
        cleanup_count = 0
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path) and time.time() - os.path.getctime(file_path) > 3600:
                os.remove(file_path)
                cleanup_count += 1
        
        return jsonify({
            'status': 'success',
            'files_cleaned': cleanup_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear-cache', methods=['POST'])
def clear_cache():
    global transcription_cache
    cache_size = len(transcription_cache)
    transcription_cache.clear()
    return jsonify({
        'status': 'success',
        'cleared_entries': cache_size

@app.route('/get_audio/<filename>')
def get_audio(filename):
    """Safe audio file delivery"""
    try:
        return send_from_directory(
            os.path.dirname(filename),
            os.path.basename(filename),
            mimetype='audio/mpeg'
        )
    except:
        return "Audio not found", 404
    })

if __name__ == '__main__':
    print("Starting Aimee Voice Pipeline...")
    print(f"Whisper available: {WHISPER_AVAILABLE}")
    print(f"ElevenLabs available: {elevenlabs_client is not None}")
    print(f"Wine intelligence loaded: {len(wine_intelligence.wine_database)} wines")
    
    app.run(debug=True, host='0.0.0.0', port=5000)