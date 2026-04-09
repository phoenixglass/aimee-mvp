from elevenlabs.client import ElevenLabs
from flask import send_from_directory
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
from typing import Dict, Any, Optional
from aimee_wine_intelligence import AimeeWineIntelligence, handle_taste_query, handle_pairing_query

try:
    import whisper
    import torch
except ImportError:
    whisper = None
    torch = None
    print("⚠️ whisper/torch modules not found. Please install with: pip install -U openai-whisper torch")

from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from aimee_classifier import AimeeClassifier
from gtts import gTTS
from datetime import datetime
import csv

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize ElevenLabs client with new SDK
try:
    elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    print("✅ ElevenLabs client initialized")
except Exception as e:
    elevenlabs_client = None
    print(f"⚠️ ElevenLabs initialization failed: {e}")

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)

# Persistent transcript cache file
CACHE_FILE = "transcript_cache.json"

# Load cache if it exists
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        transcript_cache = json.load(f)
else:
    transcript_cache = {}

def save_cache():
    """Save cache to disk (non-blocking)"""
    def _save():
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(transcript_cache, f)
        except Exception as e:
            print(f"Cache save error: {e}")
    
    executor.submit(_save)

def hash_file(path: str) -> str:
    """Generate SHA256 hash of file for caching"""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def preprocess_wine_terminology(text: str) -> str:
    """Convert wine industry shorthand to full terms for better classification"""
    
    # Dictionary of wine industry terms
    wine_terms = {
        # Sparkling beverages
        r'\bbubbles?\b': 'sparkling wine',
        r'\bbubbly\b': 'sparkling wine',
        r'\bchampers?\b': 'champagne',
        r'\bfizz\b': 'sparkling wine',
        
        # Non-alcoholic
        r'\bNA\b': 'non-alcoholic',
        r'\bn\.a\.\b': 'non-alcoholic',
        r'\bnon-alc\b': 'non-alcoholic',
        r'\bzero proof\b': 'non-alcoholic',
        r'\bmocktail\b': 'non-alcoholic cocktail',
        
        # Ready to drink
        r'\bRTD\b': 'ready to drink',
        r'\br\.t\.d\.\b': 'ready to drink',
        r'\bcanned cocktail\b': 'ready to drink cocktail',
        r'\bpremixed\b': 'ready to drink',
        
        # Wine types and regions (expand as needed)
        r'\bred blend\b': 'red wine blend',
        r'\bwhite blend\b': 'white wine blend',
        r'\brose\b': 'rosé wine',
        r'\brosé\b': 'rosé wine',
        r'\bnat wine\b': 'natural wine',
        r'\bbiodynamic\b': 'biodynamic wine',
        r'\bvarietals?\b': 'wine varietal',
        
        # Common abbreviations
        r'\bCab Sauv\b': 'Cabernet Sauvignon',
        r'\bCab\b': 'Cabernet',
        r'\bPinot\b': 'Pinot Noir',
        r'\bSauv Blanc\b': 'Sauvignon Blanc',
        r'\bChardonnay\b': 'Chardonnay',
        r'\bMerlot\b': 'Merlot',
        r'\bSyrah\b': 'Syrah',
        r'\bShiraz\b': 'Shiraz',
        
        # Sizes and formats
        r'\bmag\b': 'magnum',
        r'\bmagnum\b': 'magnum bottle',
        r'\bsplit\b': 'split bottle',
        r'\bhalf bottle\b': 'half bottle',
        r'\b187ml\b': 'split bottle',
        r'\b375ml\b': 'half bottle',
        r'\b750ml\b': 'standard bottle',
        r'\b1\.5L\b': 'magnum',
        
        # Business terms
        r'\ballocations?\b': 'wine allocation',
        r'\breserves?\b': 'reserve wine',
        r'\blimited release\b': 'limited release wine',
        r'\blibrary wine\b': 'library wine',
        r'\bback vintage\b': 'back vintage wine',
    }
    
    # Apply replacements (case insensitive)
    processed_text = text
    for pattern, replacement in wine_terms.items():
        processed_text = re.sub(pattern, replacement, processed_text, flags=re.IGNORECASE)
    
    return processed_text

def detect_special_responses(transcript: str) -> str:
    """Detect special response scenarios that override normal classification"""
    text = transcript.lower()
    
    # Flow improvement / help questions
    flow_patterns = [
        r'how\s+will\s+you\s+improve\s+my\s+flow',
        r'how\s+are\s+you\s+(?:going\s+to\s+)?help\s+me',
        r'how\s+will\s+you\s+make\s+my\s+life\s+easier',
        r'can\s+you\s+actually\s+help\s+me\s+sell\s+more',
        r'what\s+can\s+you\s+do\s+for\s+me',
        r'how\s+do\s+you\s+help',
    ]
    
    for pattern in flow_patterns:
        if re.search(pattern, text):
            return "I'm already on it. Filed the thought before you reached for it. Tracked your rhythm. Flagged the cracks. Your client heard from me before they checked the time. You move fast — I move faster. Want more?"
    
    # Sale closing confirmations
    closing_patterns = [
        r'(?:sale|deal|order)\s+(?:closed|confirmed|done|complete)',
        r'(?:they|client|customer)\s+(?:bought|purchased|agreed|said yes)',
        r'got\s+the\s+(?:sale|deal|order)',
        r'(?:closed|won|landed)\s+(?:the|that)\s+(?:sale|deal|account)',
        r'(?:sale|deal)\s+went\s+through',
    ]
    
    for pattern in closing_patterns:
        if re.search(pattern, text):
            # Randomly choose between the two responses
            import random
            responses = [
                "Sharp work. You moved with precision. Next.",
                "You struck clean. Elegant. Line up the next."
            ]
            return random.choice(responses)
    
    return None  # No special response needed

def extract_key_details(transcript: str, intent: str) -> str:
    """Extract key details from transcript based on intent - balanced approach"""
    print(f"DEBUG - extract_key_details called with intent: {intent}")
    print(f"DEBUG - transcript: '{transcript}'")
    
    text = transcript.lower()
    
    # Simple but effective customer extraction
    customer = None
    if "lebella" in text:
        if "fine wine and spirits" in text:
            customer = "LeBella's fine wine and spirits"
        else:
            customer = "LeBella's"
    elif "db fine wine" in text:
        customer = "DB Fine Wine"
    elif "elm needs" in text or "elm for" in text:
        customer = "Elm"
    elif "acme wine and liquors" in text or "acme, wine and lickers" in text:
        customer = "Acme Wine and Liquors"
    elif "westport wine" in text:
        customer = "Westport wine and spirits"
    elif "blackstone" in text:
        if "grille" in text:
            customer = "Blackstone Grille"
        elif "steakhouse" in text or "statecast" in text:
            customer = "Blackstone Steakhouse"
        else:
            customer = "Blackstone"
    elif "greenwich wine" in text:
        customer = "Greenwich wine and spirits"
    elif "putnam wine" in text:
        customer = "Putnam Wine spirits"
    elif "horse neck" in text and "wine" in text:
        customer = "Horse Neck Wine and Spirits"
    elif "pleasantry yacht club" in text:
        customer = "Pleasantry Yacht Club"
    elif "roe and see food" in text:
        customer = "Roe and See Food"
    elif "branch street wine" in text:
        customer = "Branch Street Wine and Liquor"
    elif "dan's wine" in text or "dans wine" in text:
        customer = "Dan's Wine and Liquors"
    elif "paul's fine wine" in text:
        customer = "Paul's Fine Wine and Spirits"
    elif "hennoki" in text:
        customer = "Hennoki Sushi"
    
    # Simple quantity extraction
    quantity = None
    if "seven bottles" in text:
        quantity = "seven bottles"
    elif "seven cases" in text:
        quantity = "seven cases"
    elif "six bottles" in text:
        quantity = "six bottles"
    elif "five cases" in text:
        quantity = "five cases"
    elif "three cases" in text:
        quantity = "three cases"
    elif "112 cases" in text:
        quantity = "112 cases"
    elif "55 cases" in text:
        quantity = "55 cases"
    elif "12 cases" in text:
        quantity = "12 cases"
    elif "11 cases" in text:
        quantity = "11 cases"
    elif "10 cases" in text:
        quantity = "10 cases"
    elif "5 cases" in text:
        quantity = "5 cases"
    elif "one case" in text:
        quantity = "one case"
    elif "1 case" in text:
        quantity = "1 case"
    elif "2 pallets" in text:
        quantity = "2 pallets"
    elif "entire pallet" in text:
        quantity = "entire pallet"
    elif "one bottle" in text:
        quantity = "one bottle"
    
    # Enhanced but controlled wine extraction
    wine = None
    if "charchoos green" in text:
        wine = "Charchoos green"
    elif "cavett" in text and "pinot grigio" in text:
        wine = "Cavett, Pinot Grigio"
    elif "domanda" in text:
        wine = "Domanda Véday"
    elif "jordan" in text and ("chardonnay" in text or "shardinay" in text):
        wine = "Jordan Chardonnay"
    elif "vega cecilia" in text:
        wine = "Vega Cecilia Unico"
    elif "château de beaucastel" in text or "chateau de beaucastel" in text:
        wine = "Château de Beaucastel"
    elif "château de bocastel" in text or "chateau de bocastel" in text:
        wine = "Château de Bocastel Rouge"
    elif "gurgich hill" in text and "fume blanc" in text:
        wine = "Gurgich Hill Fume Blanc"
    elif "aix" in text and "rose" in text:
        wine = "AIX Rosé de Provence"
    elif "domain" in text and "bando" in text:
        wine = "Domaine Bando Château Ramassan"
    elif "tanuta sanguido" in text:
        wine = "Tanuta Sanguido Sasekaya"
    elif "frenet bronca" in text:
        wine = "Frenet Bronca"
    elif "jean-marc crochet" in text or "jean marc crochet" in text:
        wine = "Jean-Marc Crochet Sans-Cé"
    elif "lovey fm" in text and "rose" in text:
        wine = "Lovey FM Rosé"
    elif "casa la postole" in text:
        wine = "Casa La Postole Cabernet"
    elif "hennessy" in text and "peralis" in text:
        wine = "Hennessy Peralis"
    elif "champagne" in text:
        wine = "champagne"
    elif "sparkling wine" in text:
        wine = "sparkling wine"
    elif "bubbles" in text:
        wine = "sparkling wine"
    elif "château" in text or "chateau" in text:
        # Simple château extraction
        match = re.search(r'(château|chateau)\s+([a-z\s]+?)(?:\s|,|\.|$)', text, re.IGNORECASE)
        if match and len(match.group(2).strip()) > 2:
            wine = f"{match.group(1)} {match.group(2).strip()}"
    
    # Simple delivery extraction
    delivery = None
    if "tomorrow" in text:
        delivery = "tomorrow"
    elif "friday" in text:
        delivery = "Friday"
    elif "thursday" in text:
        delivery = "Thursday"
    elif "wednesday" in text:
        delivery = "Wednesday"
    elif "june 17" in text:
        delivery = "June 17th"
    elif "may 16" in text:
        delivery = "May 16th"
    
    # Simple bottle size extraction
    size = None
    if "1.5 liter" in text:
        size = "1.5 liter"
    elif "750" in text:
        size = "750ml"
    elif "375" in text:
        size = "375ml"
    elif "magnum" in text:
        size = "magnum"
    
    print(f"DEBUG - Found customer: {customer}")
    print(f"DEBUG - Found quantity: {quantity}")
    print(f"DEBUG - Found wine: {wine}")
    print(f"DEBUG - Found delivery: {delivery}")
    print(f"DEBUG - Found size: {size}")
    
    # Build intent-specific responses
    if intent == "add_to_order":
        parts = []

        if customer:
            parts.append(customer)

        if customer and (quantity or wine):
            parts.append("needs")

        if quantity and wine:
            parts.append(f"{quantity} of {wine}")
        elif quantity:
            parts.append(quantity)
        elif wine:
            parts.append(wine)

        if size:
            parts.append(f"in {size}")

        if delivery:
            parts.append(f"for {delivery}")

        if len(parts) >= 2:
            return "I heard: " + " ".join(parts) + "."
        else:
            return "I heard: add to order."

    elif intent == "check_shipment_status":
        if wine:
            return f"I heard: ETA check for {wine}."
        else:
            return "I heard: shipment status check."

    elif intent == "check_inventory":
        parts = []
        if wine:
            parts.append(f"check inventory for {wine}")
        else:
            parts.append("inventory check")

        if "cheapest possible" in text:
            parts.append("cheapest possible")

        if customer:
            parts.append(f"for {customer}")

        return "I heard: " + " ".join(parts) + "."

    elif intent == "gift_request":
        parts = ["gift request"]
        if "wedding" in text:
            parts = ["wedding gift request"]
        elif "mother to daughter" in text:
            parts = ["mother to daughter gift request"]
        elif "anniversary" in text:
            parts = ["anniversary gift request"]
        elif "birthday" in text:
            parts = ["birthday gift request"]

        if wine:
            parts.append(f"for {wine}")
        elif "champagne" in text:
            parts.append("for champagne")
        elif "sparkling wine" in text:
            parts.append("for sparkling wine")
        elif "red wine" in text:
            parts.append("for red wine")
        elif "white wine" in text:
            parts.append("for white wine")

        # Look for quality indicators
        if "best" in text and ("you've got" in text or "available" in text):
            parts.append("the best available")
        elif "premium" in text:
            parts.append("premium quality")
        elif "special" in text:
            parts.append("something special")

        # Look for vintage
        if "1982" in text:
            parts.append("vintage 1982")
        elif "2019" in text:
            parts.append("vintage 2019")
        elif re.search(r'\b(19|20)\d{2}\b', text):
            vintage_match = re.search(r'\b(19|20)\d{2}\b', text)
            parts.append(f"vintage {vintage_match.group()}")

        return "I heard: " + " ".join(parts) + "."

    elif intent == "taste_preference_query":
        # Extract taste descriptors from the text
        taste_descriptors = []
        if "fruity" in text.lower():
            taste_descriptors.append("fruity")
        if "light" in text.lower():
            taste_descriptors.append("light")
        if "bold" in text.lower():
            taste_descriptors.append("bold")
        if "crisp" in text.lower():
            taste_descriptors.append("crisp")
        
        response = handle_taste_query(taste_descriptors, wine_intelligence)
        return f"I heard: {text}. {response}"

    elif intent == "wine_pairing_request":
        # Extract food type from text
        food_type = ""
        if "seafood" in text.lower():
            food_type = "seafood"
        elif "salmon" in text.lower():
            food_type = "seafood"
        elif "celebration" in text.lower() or "wedding" in text.lower():
            food_type = "celebration"
        elif "steak" in text.lower() or "meat" in text.lower():
            food_type = "red meat"
        
        if food_type:
            response = handle_pairing_query(food_type, wine_intelligence)
            return f"I heard: {text}. {response}"
        else:
            return f"I heard: {text}. I'd be happy to help with wine pairings - could you tell me what food you're serving?"

    elif intent == "flavor_profile_inquiry":
        return f"I heard: {text}. I'd be happy to tell you about that wine's flavor profile. Which specific wine are you interested in?"

    elif intent == "taste_based_recommendation":
        return f"I heard: {text}. I can definitely help you find similar wines. What wine did you have in mind as a reference?"

    else:
        # Keep it simple for other intents
        if customer and wine:
            return f"I heard: {customer} request for {wine}."
        elif customer:
            return f"I heard: request from {customer}."
        elif wine:
            return f"I heard: request about {wine}."
        else:
            return "I heard your request."
  
    elif intent == "wine_pairing_request":
    # Extract food type from text
    food_type = ""
    if "seafood" in text.lower():
        food_type = "seafood"
    elif "salmon" in text.lower():
        food_type = "seafood"
    elif "celebration" in text.lower() or "wedding" in text.lower():
        food_type = "celebration"
    elif "steak" in text.lower() or "meat" in text.lower():
        food_type = "red meat"
    
    if food_type:
        response = handle_pairing_query(food_type, wine_intelligence)
        return f"I heard: {text}. {response}"
    
        return f"I heard: {text}. I'd be happy to help with wine pairings - could you tell me what food you're serving?"

elif intent == "flavor_profile_inquiry":
    return f"I heard: {text}. I'd be happy to tell you about that wine's flavor profile. Which specific wine are you interested in?"

elif intent == "taste_based_recommendation":
    return f"I heard: {text}. I can definitely help you find similar wines. What wine did you have in mind as a reference?"

    else:
        # Keep it simple for other intents
        if customer and wine:
            return f"I heard: {customer} request for {wine}."
        elif customer:
            return f"I heard: request from {customer}."
        elif wine:
            return f"I heard: request about {wine}."
        else:
            return "I heard your request."

def generate_aimee_response(text, voice_id="rzsnuMd2pwYz1rGtMIVI"):
    """Generate TTS response using ElevenLabs"""
    if not elevenlabs_client:
        print("ElevenLabs client not available, falling back to gTTS")
        return generate_audio_response(text)
    
    try:
        print(f"Generating ElevenLabs audio for: {text[:50]}...")
        
        # Try the new SDK method first with balanced expressive settings
        try:
            audio = elevenlabs_client.generate(
                text=text,
                voice=voice_id,
                model="eleven_multilingual_v2",
                voice_settings={
                    "stability": 0.35,          # Higher = more consistent, still expressive
                    "similarity_boost": 0.8,    # Keep voice characteristics strong
                    "style": 0.3,               # Moderate personality (not too wild)
                    "use_speaker_boost": True   # Enhanced voice presence
                }
            )
        except AttributeError:
            # Fall back to older SDK method
            print("Using older ElevenLabs SDK method...")
            try:
                audio = elevenlabs_client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id="eleven_multilingual_v2",
                    voice_settings={
                        "stability": 0.35,
                        "similarity_boost": 0.8,
                        "style": 0.3,
                        "use_speaker_boost": True
                    }
                )
            except Exception:
                # Final fallback to basic model
                audio = elevenlabs_client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id="eleven_monolingual_v1"
                )
        
        # Convert generator to bytes if needed
        if hasattr(audio, '__iter__') and not isinstance(audio, bytes):
            audio_bytes = b"".join(audio)
        else:
            audio_bytes = audio
        
        # Save to file
        audio_filename = f"aimee_response_{uuid.uuid4().hex}.mp3"
        audio_output_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        
        with open(audio_output_path, "wb") as f:
            f.write(audio_bytes)
        
        print(f"✅ ElevenLabs audio generated: {audio_filename}")
        return audio_filename
        
    except Exception as e:
        print(f"ElevenLabs TTS failed: {e}")
        print("Falling back to gTTS...")
        return generate_audio_response(text)

# Dual model system for speed vs accuracy
class WhisperModelManager:
    def __init__(self):
        self.device = "cuda" if torch and torch.cuda.is_available() else "cpu"
        self.base_model = None
        self.medium_model = None
        self.load_models()
    
    def load_models(self):
        """Load both base and medium models"""
        if not whisper:
            print("Whisper not available")
            return
        
        try:
            # Load base model for real-time processing
            print(f"Loading Whisper 'base' model on {self.device}")
            self.base_model = whisper.load_model("base", device=self.device)
            print("✅ Base model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading base model: {e}")
        
        try:
            # Load medium model for verification (background)
            print(f"Loading Whisper 'medium' model on {self.device}")
            self.medium_model = whisper.load_model("medium", device=self.device)
            print("✅ Medium model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading medium model: {e}")
    
    def get_model(self, model_type="base"):
        """Get the specified model"""
        if model_type == "medium":
            return self.medium_model
        return self.base_model
    
    def is_available(self, model_type="base"):
        """Check if model is available"""
        if model_type == "medium":
            return self.medium_model is not None
        return self.base_model is not None

# Initialize model manager
model_manager = WhisperModelManager()

# Initialize classifier once  
classifier = AimeeClassifier(data_file="aimee_training_data_tagged.json", threshold=0.2)
# Initialize wine intelligence

wine_intelligence = AimeeWineIntelligence()# Precompiled keyword sets for faster lookup
TONE_KEYWORDS = {
    "polite": {"please", "thank you", "kindly", "let me know", "if you can", "would you mind"},
    "urgent": {"urgent", "asap", "right away", "immediately", "need this", "super important", "now"},
    "frustrated": {"ugh", "frustrated", "come on", "this again", "seriously", "annoyed"},
    "casual": {"hey", "just", "no rush", "whenever", "it's fine", "cool", "ok"}
}

@lru_cache(maxsize=1000)
def detect_tone(transcript_lower: str) -> str:
    """Optimized tone detection with caching"""
    # Convert to frozenset for hashability in cache
    words = frozenset(transcript_lower.split())
    
    for tone, keywords in TONE_KEYWORDS.items():
        if keywords & words:  # Set intersection - faster than 'any' with 'in'
            return tone
    return "unknown"

@lru_cache(maxsize=500)
def format_response(intent: str, tone: str) -> str:
    """Cached response formatting"""
    intent_responses = {
        "add_to_order": "I'll get that order processed.",
        "check_inventory": "I'll check what we have in stock.",
        "cancel_order": "Consider it canceled.",
        "confirm_delivery": "I'll confirm those delivery details.",
        "check_pricing": "Let me pull current pricing for you.",
        "gift_request": "I'll find the perfect gift option.",
        "send_email": "I'll send that email out.",
        "product_recommendation": "I'll get you some solid recommendations.",
        "general_inquiry": "I'll look into that for you.",
        "check_shipment_status": "I'll check on that shipment status.",
        "correct_order": "I'll get that order corrected.",
        "sample_request": "I'll put that sample request through.",
        "set_reminder": "I'll set that reminder for you.",
        "send_text": "I'll send that message.",
        "check_invoice": "I'll check on that invoice.",
        "research_product": "I'll pull that research together.",
    }
    
    tone_flavors = {
        "polite": "Right on it.",
        "urgent": "Making it priority.",
        "frustrated": "I hear the urgency.",
        "casual": "No problem.",
    }
    
    phrase = intent_responses.get(intent, f"Got it - {intent.replace('_', ' ')}.")
    tone_flavor = tone_flavors.get(tone, "On it.")
    
    return f"{phrase} {tone_flavor}"

def transcribe_audio_cached(filepath: str, model_type: str = "base", priority: str = "speed") -> Dict[str, Any]:
    """Transcribe audio with dual model system and caching"""
    cache_key = f"{model_type}_{hash_file(filepath)}"
    
    # Check cache first
    if cache_key in transcript_cache:
        print(f"Using cached transcript ({model_type})")
        cached_result = transcript_cache[cache_key].copy()
        cached_result['cached'] = True
        cached_result['model_used'] = model_type
        return cached_result
    
    # Get the appropriate model
    model = model_manager.get_model(model_type)
    if model is None:
        raise Exception(f'Whisper {model_type} model is not available')
    
    # Transcribe with optimized settings
    try:
        use_fp16 = torch and torch.cuda.is_available()
        
        # Adjust settings based on model and priority
        if model_type == "base" and priority == "speed":
            # Fastest settings for real-time
            beam_size = 1
            best_of = 1
            temperature = 0.0
        elif model_type == "medium":
            # Better quality settings for verification
            beam_size = 5
            best_of = 5
            temperature = (0.0, 0.2, 0.4, 0.6, 0.8)
        else:
            # Balanced settings
            beam_size = 1
            best_of = 1
            temperature = 0.0
        
        print(f"Transcribing with {model_type} model...")
        start_time = time.time()
        
        result = model.transcribe(
            filepath,
            fp16=use_fp16,
            language="en",
            task="transcribe",
            beam_size=beam_size,
            best_of=best_of,
            temperature=temperature
        )
        
        transcription_time = time.time() - start_time
        
        transcript_data = {
            "text": result["text"].strip(),
            "language": result.get("language", "en"),
            "segments": result.get("segments", []),
            "model_used": model_type,
            "transcription_time": round(transcription_time, 2),
            "cached": False
        }
        
        # Cache the result
        transcript_cache[cache_key] = transcript_data
        save_cache()
        
        return transcript_data
        
    except Exception as e:
        raise Exception(f"Transcription failed with {model_type} model: {str(e)}")

def verify_transcript_background(filepath: str, base_transcript: str, file_hash: str):
    """Background verification with medium model"""
    def _verify():
        try:
            if not model_manager.is_available("medium"):
                return
            
            medium_cache_key = f"medium_{file_hash}"
            if medium_cache_key in transcript_cache:
                return  # Already verified
            
            print("Starting background verification with medium model...")
            medium_result = transcribe_audio_cached(filepath, "medium", "accuracy")
            medium_transcript = medium_result["text"]
            
            # Simple confidence comparison
            if len(medium_transcript) > len(base_transcript) * 0.8:  # Reasonable length check
                confidence_boost = min(0.2, abs(len(medium_transcript) - len(base_transcript)) / len(base_transcript))
                print(f"Background verification complete. Confidence boost: +{confidence_boost:.2f}")
                
                # Store verification result
                verification_data = {
                    "base_transcript": base_transcript,
                    "medium_transcript": medium_transcript,
                    "confidence_boost": confidence_boost,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Save to verification log
                verification_log = os.path.join(app.config['UPLOAD_FOLDER'], "verification_log.json")
                try:
                    with open(verification_log, "a") as f:
                        f.write(json.dumps(verification_data) + "\n")
                except Exception as e:
                    print(f"Verification logging error: {e}")
            
        except Exception as e:
            print(f"Background verification error: {e}")
    
    # Submit to thread pool for background processing
    executor.submit(_verify)

def generate_audio_response(text: str) -> str:
    """Generate TTS audio response using gTTS (fallback)"""
    try:
        tts = gTTS(text=text, lang='en', slow=False)  # Fast speech
        audio_filename = f"response_{uuid.uuid4().hex}.mp3"
        audio_output_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        tts.save(audio_output_path)
        return audio_filename
    except Exception as e:
        print(f"TTS generation error: {e}")
        return None

def log_interaction(transcript: str, classification: Dict[str, Any], audio_filename: str):
    """Async logging function"""
    def _log():
        try:
            log_path = os.path.join(app.config['UPLOAD_FOLDER'], "aimee_log.csv")
            with open(log_path, mode='a', newline='', encoding='utf-8') as log_file:
                writer = csv.writer(log_file)
                writer.writerow([
                    datetime.now().isoformat(),
                    transcript,
                    classification.get('intent', 'unknown'),
                    classification.get('tone', 'unknown'),
                    classification.get('match_score', 0.0),
                    audio_filename or 'none'
                ])
        except Exception as e:
            print(f"Logging error: {e}")
    
    executor.submit(_log)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test-elevenlabs', methods=['POST', 'GET'])
def test_elevenlabs():
    """Test ElevenLabs TTS functionality"""
    try:
        if request.method == 'GET':
            # Simple GET test
            return jsonify({
                'status': 'ElevenLabs endpoint is working',
                'elevenlabs_available': elevenlabs_client is not None,
                'api_key_configured': bool(os.getenv("ELEVENLABS_API_KEY"))
            })
        
        # POST request - generate TTS
        data = request.get_json() if request.is_json else {}
        text = data.get('text', 'Hello! This is a test of ElevenLabs text to speech functionality.')
        voice_id = data.get('voice_id', 'rzsnuMd2pwYz1rGtMIVI')  # Default Aimee voice
        
        if not elevenlabs_client:
            return jsonify({
                'error': 'ElevenLabs client not available',
                'api_key_configured': bool(os.getenv("ELEVENLABS_API_KEY"))
            }), 500
        
        print(f"Testing ElevenLabs TTS with text: {text[:50]}...")
        start_time = time.time()
        
        # Generate audio using your existing function
        audio_filename = generate_aimee_response(text, voice_id)
        
        generation_time = time.time() - start_time
        
        if audio_filename:
            return jsonify({
                'success': True,
                'text': text,
                'voice_id': voice_id,
                'audio_filename': audio_filename,
                'audio_url': f'/audio/{audio_filename}',
                'generation_time': round(generation_time, 2),
                'provider': 'elevenlabs'
            })
        else:
            return jsonify({
                'error': 'Audio generation failed',
                'text': text,
                'generation_time': round(generation_time, 2)
            }), 500
            
    except Exception as e:
        print(f"ElevenLabs test error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'whisper_base_available': model_manager.is_available("base"),
        'whisper_medium_available': model_manager.is_available("medium"),
        'gpu_available': torch and torch.cuda.is_available() if torch else False,
        'cache_size': len(transcript_cache),
        'device': model_manager.device,
        'elevenlabs_available': elevenlabs_client is not None
    })

@app.route('/demo')
def voice_demo():
    return send_from_directory('.', 'voice_demo.html')

@app.route('/test-classification', methods=['POST'])
def test_classification():
    """Test the classifier directly to debug classification issues"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        print(f"=== CLASSIFICATION TEST ===")
        print(f"Original text: '{text}'")
        
        # Test preprocessing
        processed_text = preprocess_wine_terminology(text)
        print(f"Processed text: '{processed_text}'")
        
        # Test classification
        classification = classifier.classify(processed_text)
        print(f"Classification result: {classification}")
        
        # Test tone detection
        tone = detect_tone(text.lower())
        print(f"Detected tone: {tone}")
        
        # Test extraction
        intent = classification.get('intent', 'unknown')
        key_details = extract_key_details(text, intent)
        print(f"Extracted details: '{key_details}'")
        
        # Get classifier stats
        stats = classifier.get_stats()
        print(f"Classifier stats: {stats}")
        
        return jsonify({
            'original_text': text,
            'processed_text': processed_text,
            'classification': classification,
            'tone': tone,
            'key_details': key_details,
            'classifier_stats': stats
        })
        
    except Exception as e:
        print(f"Classification test error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload():
    start_time = time.time()
    print("=== upload() called ===")
    
    # Handle voice demo requests
    if 'transcript_override' in request.form:
        transcript = request.form['transcript_override']
        print(f"DEBUG - Voice demo transcript: {transcript}")
        
        # Add debug output for voice demo processing
        print(f"DEBUG - Raw transcript: '{transcript}'")
        print(f"DEBUG - Transcript type: {type(transcript)}")
        print(f"DEBUG - Transcript length: {len(transcript)}")
        
        # Process the transcript with FULL pipeline (same as file upload)
        processed_transcript = preprocess_wine_terminology(transcript)
        print(f"DEBUG - Processed transcript: '{processed_transcript}'")
        
        # Optimized tone detection (use original transcript for tone)
        transcript_lower = transcript.lower()
        tone = detect_tone(transcript_lower)
        print(f"DEBUG - Detected tone: {tone}")
        
        # Intent classification (use processed transcript with wine terms)
        classification = classifier.classify(processed_transcript)
        classification['tone'] = tone
        
        print(f"DEBUG - Classification result: {classification}")
        
        intent = classification['intent']
        score = classification['match_score']
        
        # Check for special response scenarios first
        special_response = detect_special_responses(transcript)
        print(f"DEBUG - Special response: {special_response}")
        
        if special_response:
            response_text = special_response
        else:
            # Generate response text with extracted key details (SAME AS FILE UPLOAD)
            if intent != "unknown":
                # Extract key details and create summary
                key_details = extract_key_details(transcript, intent)
                base_response = format_response(intent, tone)
                response_text = f"{key_details} {base_response}"
            else:
                # For unknown intents, give brief summary
                key_details = extract_key_details(transcript, intent)
                response_text = f"{key_details} I'm Aimee. You talk. I'll catch what counts. No bosses. No filters. Just memory. Let's move."
        
        print(f"DEBUG - Final response text: {response_text}")
        
        # Generate audio
        audio_filename = generate_aimee_response(response_text)
        
        return jsonify({
            'transcript': transcript,
            'intent': intent,
            'tone': tone,
            'score': score,
            'response_text': response_text,
            'response_audio': f'/audio/{audio_filename}' if audio_filename else None
        })
    
    # Continue with normal file upload processing...
    try:
        if not model_manager.is_available("base"):
            return jsonify({'error': 'Whisper base model is not available. Please install openai-whisper.'}), 500

        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file part'}), 400

        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Check for background verification request
        use_verification = request.form.get('verify', 'false').lower() == 'true'
        
        # Validate file type
        allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Unsupported file type: {file_ext}'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        file_hash = hash_file(filepath)

        try:
            # Primary transcription with base model (fast)
            transcript_data = transcribe_audio_cached(filepath, "base", "speed")
            transcript = transcript_data["text"]
            
            if not transcript.strip():
                return jsonify({'error': 'No speech detected in audio'}), 400

            # Preprocess wine terminology before classification
            processed_transcript = preprocess_wine_terminology(transcript)
            
            # Start background verification if requested and medium model available
            if use_verification and model_manager.is_available("medium"):
                verify_transcript_background(filepath, transcript, file_hash)
                print("🔍 Background verification started")

            # Optimized tone detection (use original transcript for tone)
            transcript_lower = transcript.lower()
            tone = detect_tone(transcript_lower)

            # Intent classification (use processed transcript with wine terms)
            classification = classifier.classify(processed_transcript)
            classification['tone'] = tone

            # Check for special response scenarios first
            special_response = detect_special_responses(transcript)
            
            if special_response:
                # Use special response directly
                response_text = special_response
            else:
                # Generate response text with extracted key details
                intent = classification.get("intent", "unknown")
                
                if intent != "unknown":
                    # Extract key details and create summary
                    key_details = extract_key_details(transcript, intent)
                    base_response = format_response(intent, tone)
                    response_text = f"{key_details} {base_response}"
                else:
                    # For unknown intents, give brief summary
                    key_details = extract_key_details(transcript, intent)
                    response_text = f"{key_details} I'm Aimee. You talk. I'll catch what counts. No bosses. No filters. Just memory. Let's move."

            # Generate audio response using ElevenLabs (async)
            audio_future = executor.submit(generate_aimee_response, response_text)
            
            # Start logging (async)
            log_future = executor.submit(log_interaction, transcript, classification, "pending")

            # Wait for audio generation (with timeout)
            try:
                audio_filename = audio_future.result(timeout=15)  # 15 second timeout for ElevenLabs
            except Exception as e:
                print(f"Audio generation failed: {e}")
                audio_filename = None

            processing_time = time.time() - start_time
            print(f"Processing completed in {processing_time:.2f}s")

            response_data = {
                'transcript': transcript,
                'intent': classification['intent'],
                'tone': classification['tone'],
                'score': classification['match_score'],
                'processing_time': round(processing_time, 2),
                'transcription_time': transcript_data.get('transcription_time', 0),
                'model_used': transcript_data.get('model_used', 'base'),
                'cached': transcript_data.get('cached', False),
                'verification_started': use_verification and model_manager.is_available("medium"),
                'tts_provider': 'elevenlabs' if elevenlabs_client else 'gtts'
            }
            
            if audio_filename:
                response_data['response_audio'] = f"/audio/{audio_filename}"

            return jsonify(response_data)

        finally:
            # Clean up uploaded file (delay for background verification)
            def cleanup_file():
                time.sleep(30 if use_verification else 5)  # Give verification time
                try:
                    os.remove(filepath)
                except:
                    pass
            
            executor.submit(cleanup_file)

    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/audio/<filename>')
def uploaded_file(filename):
    """Serve audio files with caching headers"""
    response = send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
    return response

@app.route('/verification-status/<file_hash>')
def verification_status(file_hash):
    """Check background verification status"""
    medium_cache_key = f"medium_{file_hash}"
    if medium_cache_key in transcript_cache:
        return jsonify({
            'verified': True,
            'medium_transcript': transcript_cache[medium_cache_key]['text'],
            'transcription_time': transcript_cache[medium_cache_key].get('transcription_time', 0)
        })
    else:
        return jsonify({'verified': False, 'status': 'processing'})

@app.route('/force-verify', methods=['POST'])
def force_verify():
    """Force verification with medium model for uploaded audio"""
    try:
        if not model_manager.is_available("medium"):
            return jsonify({'error': 'Medium model not available'}), 400
            
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file part'}), 400

        file = request.files['audio']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Direct medium model transcription
            transcript_data = transcribe_audio_cached(filepath, "medium", "accuracy")
            
            return jsonify({
                'transcript': transcript_data['text'],
                'model_used': transcript_data['model_used'],
                'transcription_time': transcript_data['transcription_time'],
                'cached': transcript_data['cached']
            })
            
        finally:
            try:
                os.remove(filepath)
            except:
                pass
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Cleanup old audio files on startup
def cleanup_old_files():
    """Remove audio files older than 24 hours"""
    def _cleanup():
        try:
            current_time = time.time()
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                if (filename.startswith('response_') or filename.startswith('aimee_response_')) and filename.endswith('.mp3'):
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.getmtime(filepath) < current_time - 86400:  # 24 hours
                        os.remove(filepath)
                        print(f"Cleaned up old file: {filename}")
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    executor.submit(_cleanup)

@app.route('/clear-cache', methods=['POST'])
def clear_cache():
    """Clear transcript cache"""
    global transcript_cache
    transcript_cache.clear()
    save_cache()
    return jsonify({'message': 'Cache cleared successfully'})

if __name__ == '__main__':
    print("Starting Aimee Flask App...")
    print(f"GPU Available: {torch and torch.cuda.is_available() if torch else False}")
    print(f"Whisper Base Model: {'✅ Loaded' if model_manager.is_available('base') else '❌ Not Available'}")
    print(f"Whisper Medium Model: {'✅ Loaded' if model_manager.is_available('medium') else '❌ Not Available'}")
    print(f"ElevenLabs: {'✅ Available' if elevenlabs_client else '❌ Not Available'}")
    print(f"Device: {model_manager.device}")
    
    # Cleanup old files
    cleanup_old_files()
    
    app.run(debug=True, threaded=True, ssl_context='adhoc', host='0.0.0.0', port=5000)