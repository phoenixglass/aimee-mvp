from elevenlabs.client import ElevenLabs
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import tempfile
import uuid
import json
import hashlib
import threading
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import time
from datetime import datetime
import csv
# UPDATED IMPORTS - Enhanced wine intelligence with JSONL data + Enhanced Fairfield County intelligence
from enhanced_aimee_wine_intelligence import (
    EnhancedAimeeWineIntelligence, 
    handle_enhanced_taste_query, 
    handle_enhanced_pairing_query,
    handle_wine_recommendation_request
)
from aimee_fairfield_integration import get_customer_intelligence
from aimee_classifier import AimeeClassifier
from salesforce_integration import get_salesforce
from gtts import gTTS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
UPLOAD_FOLDER = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize ElevenLabs client
try:
    elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    print("✅ ElevenLabs client initialized")
except Exception as e:
    elevenlabs_client = None
    print(f"⚠️ ElevenLabs initialization failed: {e}")

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)

# Initialize Whisper
try:
    import whisper
    import torch
    WHISPER_AVAILABLE = True
except ImportError:
    whisper = None
    torch = None
    WHISPER_AVAILABLE = False
    print("⚠️ Whisper/torch not available. Install with: pip install openai-whisper torch")

# UPDATED WINE INTELLIGENCE INITIALIZATION - Enhanced with JSONL data
try:
    wine_intelligence = EnhancedAimeeWineIntelligence()
    print("✅ Enhanced wine intelligence initialized")
    print(f"📊 Wine data stats: {wine_intelligence.get_stats()}")
except Exception as e:
    print(f"⚠️ Enhanced wine intelligence initialization failed: {e}")
    # Fallback to original if enhanced fails
    try:
        from aimee_wine_intelligence import AimeeWineIntelligence
        wine_intelligence = AimeeWineIntelligence()
        print("✅ Fallback wine intelligence initialized")
    except Exception as fallback_error:
        print(f"⚠️ Fallback wine intelligence also failed: {fallback_error}")
        wine_intelligence = None

# Initialize classifier
try:
    print("Loading classifier from aimee_training_data_tagged.json...")
    classifier = AimeeClassifier(data_file="aimee_training_data_tagged.json", threshold=0.2)
    print("✅ Classifier initialized successfully")
    
    # Test the classifier
    test_result = classifier.classify("test")
    print(f"✅ Classifier test successful: {test_result}")
    
except Exception as e:
    print(f"❌ Classifier initialization failed: {e}")
    import traceback
    traceback.print_exc()
    classifier = None

# Persistent transcript cache
CACHE_FILE = "transcript_cache.json"
transcript_cache = {}
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r") as f:
            transcript_cache = json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading cache: {e}")

def save_cache():
    """Save cache to disk asynchronously"""
    def _save():
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(transcript_cache, f)
        except Exception as e:
            print(f"Cache save error: {e}")
    executor.submit(_save)

def hash_file(path: str) -> str:
    """Generate SHA256 hash of file content"""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

class WhisperModelManager:
    """Manage Whisper models with thread-safe loading"""
    def __init__(self):
        self.device = "cuda" if torch and torch.cuda.is_available() else "cpu"
        self.models = {}
        self.lock = threading.Lock()
        
    def load_model(self, model_type: str):
        """Load a Whisper model if not already loaded"""
        with self.lock:
            if model_type not in self.models:
                try:
                    print(f"Loading Whisper {model_type} model...")
                    self.models[model_type] = whisper.load_model(model_type, device=self.device)
                    print(f"✅ Whisper {model_type} model loaded")
                except Exception as e:
                    print(f"❌ Failed to load Whisper {model_type}: {e}")
                    return None
        return self.models.get(model_type)

    def is_available(self, model_type: str) -> bool:
        """Check if model is available"""
        if model_type in self.models:
            return True
        return self.load_model(model_type) is not None

    def transcribe(self, filepath: str, model_type: str = "base") -> dict:
        """Transcribe audio file using specified model"""
        model = self.models.get(model_type)
        if not model:
            raise ValueError(f"Model {model_type} not loaded")
        
        try:
            start_time = time.time()
            result = model.transcribe(filepath)
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "en"),
                "duration": time.time() - start_time
            }
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}")

    def get_model(self, model_type="base"):
        """Get the specified model"""
        if model_type == "medium":
            return self.models.get("medium")
        return self.models.get("base")

# Initialize model manager
model_manager = WhisperModelManager()

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
    """Extract key details from transcript based on intent - enhanced for tactical briefings"""
    print(f"DEBUG - extract_key_details called with intent: {intent}")
    print(f"DEBUG - transcript: '{transcript}'")
    
    text = transcript.lower()
    
    # ENHANCED CUSTOMER EXTRACTION - More precise matching
    customer = None
    
    # First check for exact matches in the transcript
    customers = {
        "spiga": "Spiga Wine Bar",
        "barcelona norwalk": "Barcelona Wine Bar - Norwalk",
        "barcelona fairfield": "Barcelona Wine Bar - Fairfield",
        "barcelona": "Barcelona Wine Bar",
        "elm": "ELM",
        "the cottage": "The Cottage",
        "bin 100": "Bin 100",
        "blackstones grille": "Blackstones Grille",
        "blackstones norwalk": "Blackstones Steakhouse - Norwalk",
        "blackstones stamford": "Blackstones Steakhouse - Stamford",
        "blackstones": "Blackstones",
        "rebecca's": "Rebecca's",
        "99 bottles": "99 Bottles",
        "horseneck": "Horseneck Wine & Spirits",
        "db fine wines": "DB Fine Wines",
        "greens farms": "Greens Farms Spirit Shop",
        "labella's": "LaBella's Fine Wine & Spirits",
        "acme": "Acme Liquors"
    }
    
    # Check for exact matches first
    for cust_key, cust_name in customers.items():
        if cust_key in text:
            customer = cust_name
            break
    
    # If no exact match, look for partial matches
    if not customer:
        partial_matches = {
            "spiga": "Spiga Wine Bar",
            "barcelona": "Barcelona Wine Bar",
            "elm": "ELM",
            "cottage": "The Cottage",
            "bin": "Bin 100",
            "blackstone": "Blackstones",
            "rebecca": "Rebecca's",
            "99": "99 Bottles",
            "horse neck": "Horseneck Wine & Spirits",
            "db": "DB Fine Wines",
            "greens": "Greens Farms Spirit Shop",
            "labella": "LaBella's Fine Wine & Spirits",
            "acme": "Acme Liquors"
        }
        
        for partial, cust_name in partial_matches.items():
            if partial in text:
                customer = cust_name
                break
    
    print(f"DEBUG - Found customer: {customer}")
    
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

    # ENHANCED FAIRFIELD COUNTY INTELLIGENCE HANDLING
    elif intent in ["customer_intelligence", "daily_briefing", "daily_priorities", 
                   "distributor_intelligence", "market_analysis", "gap_analysis", 
                   "opportunity_analysis", "competitive_intelligence", "regional_briefing",
                   "market_strategy", "contact_intelligence", "timing_intelligence", 
                   "product_opportunity", "competitive_strategy", "revenue_analysis", 
                   "distributor_mapping", "program_analysis", "premium_opportunity", 
                   "competitive_positioning", "financial_analysis", "expansion_opportunity", 
                   "timing_strategy", "market_differentiation", "appointment_strategy", 
                   "competitive_landscape", "competitive_comparison", "education_opportunity", 
                   "pricing_strategy", "market_size", "meeting_preparation",
                   "tactical_briefing", "account_intelligence"]:
    if not customer:
            return "I couldn't identify which customer you wanted a briefing on. Please specify the customer name."
        
        print(f"DEBUG - Calling get_customer_intelligence for {customer}")
        try:
            response = get_customer_intelligence(customer)  # Pass just the customer name
            print(f"DEBUG - Got intelligence response: {response[:100]}...")
            return response
        except Exception as e:
            print(f"DEBUG - Customer intelligence error: {e}")
            return f"I couldn't retrieve the tactical briefing for {customer}. Please try again.

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
        
        # UPDATED FUNCTION CALL - Enhanced wine intelligence
        if wine_intelligence:
            response = handle_enhanced_taste_query(taste_descriptors, wine_intelligence)
        else:
            response = "I'd be happy to help you find wines with those characteristics."
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
            # UPDATED FUNCTION CALL - Enhanced wine intelligence
            if wine_intelligence:
                response = handle_enhanced_pairing_query(food_type, wine_intelligence)
            else:
                response = f"I can help you find wines that pair well with {food_type}."
            return f"I heard: {text}. {response}"
        else:
            return f"I heard: {text}. I'd be happy to help with wine pairings - could you tell me what food you're serving?"

    elif intent == "flavor_profile_inquiry":
        return f"I heard: {text}. I'd be happy to tell you about that wine's flavor profile. Which specific wine are you interested in?"

    elif intent == "taste_based_recommendation":
        # NEW ENHANCED RECOMMENDATION HANDLING
        if wine_intelligence and hasattr(wine_intelligence, 'get_wine_recommendations_by_preference'):
            response = handle_wine_recommendation_request(text, wine_intelligence)
            return response
        else:
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

# Precompiled keyword sets for faster lookup
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
        # Enhanced responses for tactical briefings
        "customer_intelligence": "Intelligence ready.",
        "tactical_briefing": "Tactical brief loaded.",
        "daily_briefing": "Priorities briefed.",
        "market_analysis": "Market data processed.",
        "gap_analysis": "Gaps identified.",
        "opportunity_analysis": "Opportunities mapped.",
        "competitive_intelligence": "Competitive edge confirmed.",
        "regional_briefing": "Regional intelligence ready.",
        "distributor_intelligence": "Distributor landscape mapped."
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

def transcribe_audio_cached(filepath: str, model_type: str = "base", priority: str = "speed"):
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

def log_interaction(transcript: str, classification: dict, audio_filename: str):
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
    """Health check endpoint with enhanced intelligence status"""
    return jsonify({
        'status': 'healthy',
        'whisper_base_available': model_manager.is_available("base"),
        'whisper_medium_available': model_manager.is_available("medium"),
        'gpu_available': torch and torch.cuda.is_available() if torch else False,
        'cache_size': len(transcript_cache),
        'device': model_manager.device,
        'elevenlabs_available': elevenlabs_client is not None,
        'enhanced_wine_intelligence': wine_intelligence is not None and hasattr(wine_intelligence, 'get_stats'),
        'wine_data_stats': wine_intelligence.get_stats() if wine_intelligence and hasattr(wine_intelligence, 'get_stats') else {},
        'fairfield_intelligence': True,  # Now always available
        'tactical_briefings_loaded': 17,  # 17 accounts loaded
        'accounts_available': ['Barcelona (2 locations)', 'Spiga', 'ELM', 'The Cottage', 'Bin 100', 'Blackstones (3 locations)', 'Rebecca\'s', '99 Bottles', 'Horseneck', 'DB Fine Wines', 'Greens Farms', 'LaBella\'s', 'Acme'],
        'voice_commands': ['Brief me on [account]', '[Region] accounts', 'Daily priorities', 'Market analysis', 'All Blackstones']
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
        
        # Test enhanced wine intelligence if available
        wine_test_results = {}
        if wine_intelligence and hasattr(wine_intelligence, 'get_wine_recommendations_by_preference'):
            try:
                wine_recs = wine_intelligence.get_wine_recommendations_by_preference(text, limit=3)
                wine_test_results = {
                    'recommendations_found': len(wine_recs),
                    'top_recommendation': wine_recs[0] if wine_recs else None,
                    'wine_stats': wine_intelligence.get_stats()
                }
            except Exception as e:
                wine_test_results = {'error': str(e)}
        
        # Test Fairfield County intelligence
        fairfield_test_results = {}
        try:
            fairfield_response = get_customer_intelligence(text)
            fairfield_test_results = {
                'response_length': len(fairfield_response),
                'response_preview': fairfield_response[:100] + "..." if len(fairfield_response) > 100 else fairfield_response,
                'contains_tactical_data': any(keyword in fairfield_response.lower() for keyword in ['tactical', 'annual volume', 'gaps', 'lead with'])
            }
        except Exception as e:
            fairfield_test_results = {'error': str(e)}
        
        return jsonify({
            'original_text': text,
            'processed_text': processed_text,
            'classification': classification,
            'tone': tone,
            'key_details': key_details,
            'classifier_stats': stats,
            'enhanced_wine_intelligence': wine_test_results,
            'fairfield_intelligence': fairfield_test_results
        })
        
    except Exception as e:
        print(f"Classification test error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test-tactical-briefing', methods=['POST'])
def test_tactical_briefing():
    """Test the tactical briefing system"""
    try:
        data = request.get_json()
        query = data.get('query', 'brief me on spiga')
        
        print(f"=== TACTICAL BRIEFING TEST ===")
        print(f"Query: '{query}'")
        
        # Test Fairfield County intelligence
        response = get_customer_intelligence(query)
        
        # Test various query types
        test_queries = [
            "brief me on spiga",
            "barcelona norwalk",
            "new canaan accounts", 
            "all blackstones",
            "daily priorities",
            "market analysis"
        ]
        
        test_results = {}
        for test_query in test_queries:
            try:
                test_response = get_customer_intelligence(test_query)
                test_results[test_query] = {
                    'response_length': len(test_response),
                    'contains_tactical_data': any(keyword in test_response.lower() for keyword in ['tactical', 'annual', 'gaps', 'lead with', 'opportunity']),
                    'preview': test_response[:100] + "..." if len(test_response) > 100 else test_response
                }
            except Exception as e:
                test_results[test_query] = {'error': str(e)}
        
        return jsonify({
            'query': query,
            'main_response': response,
            'response_length': len(response),
            'test_results': test_results,
            'system_status': {
                'fairfield_intelligence_loaded': True,
                'accounts_loaded': 17,
                'tactical_briefings_available': True
            }
        })
        
    except Exception as e:
        print(f"Tactical briefing test error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test-wine-intelligence', methods=['POST'])
def test_wine_intelligence():
    """Test the enhanced wine intelligence system"""
    try:
        data = request.get_json()
        query = data.get('query', 'fruity wine')
        
        if not wine_intelligence:
            return jsonify({'error': 'Wine intelligence not available'}), 400
        
        if not hasattr(wine_intelligence, 'get_wine_recommendations_by_preference'):
            return jsonify({'error': 'Enhanced wine intelligence not loaded'}), 400
        
        print(f"=== WINE INTELLIGENCE TEST ===")
        print(f"Query: '{query}'")
        
        # Test recommendations
        recommendations = wine_intelligence.get_wine_recommendations_by_preference(query, limit=5)
        
        # Test taste query handling
        taste_descriptors = [word for word in query.lower().split() if word in ['fruity', 'bold', 'crisp', 'smooth', 'light', 'dry']]
        taste_response = wine_intelligence.handle_taste_query(taste_descriptors) if taste_descriptors else "No taste descriptors found"
        
        # Get stats
        stats = wine_intelligence.get_stats()
        
        return jsonify({
            'query': query,
            'recommendations_found': len(recommendations),
            'recommendations': recommendations[:3],  # Top 3
            'taste_descriptors': taste_descriptors,
            'taste_response': taste_response,
            'wine_intelligence_stats': stats
        })
        
    except Exception as e:
        print(f"Wine intelligence test error: {e}")
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
        if classifier is None:
            return jsonify({'error': 'Classifier not available'}), 500

        classification = classifier.classify(processed_transcript)
        
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
            'response_audio': f'/audio/{audio_filename}' if audio_filename else None,
            'enhanced_intelligence': {
                'fairfield_accounts': 17,
                'wine_intelligence': wine_intelligence is not None and hasattr(wine_intelligence, 'get_stats'),
                'tactical_briefings': True
            }
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
                'tts_provider': 'elevenlabs' if elevenlabs_client else 'gtts',
                'enhanced_wine_intelligence': wine_intelligence is not None and hasattr(wine_intelligence, 'get_stats'),
                'enhanced_intelligence': {
                    'fairfield_accounts': 17,
                    'tactical_briefings': True,
                    'wine_intelligence': wine_intelligence is not None,
                    'voice_commands_available': ['Brief me on [account]', '[Region] accounts', 'Daily priorities', 'Market analysis']
                }
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

@app.route('/clear-cache', methods=['POST'])
def clear_cache():
    """Clear transcript cache"""
    global transcript_cache
    transcript_cache.clear()
    save_cache()
    return jsonify({'message': 'Cache cleared successfully'})


# ─────────────────────────────────────────────────────────────────────────────
# Salesforce endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/salesforce/health', methods=['GET'])
def salesforce_health():
    """Check Salesforce connectivity."""
    sf = get_salesforce()
    result = sf.health_check()
    status = 200 if result.get("connected") else 503
    return jsonify(result), status


@app.route('/salesforce/account', methods=['POST'])
def salesforce_get_account():
    """
    Pull account information from Salesforce.
    Body: {"account_name": "Barcelona Wine Bar"}
    Returns the account record plus a voice-ready summary.
    """
    data = request.get_json(silent=True) or {}
    account_name = (data.get("account_name") or "").strip()
    if not account_name:
        return jsonify({"success": False, "error": "account_name is required"}), 400

    sf = get_salesforce()
    result = sf.get_account(account_name)
    if not result:
        return jsonify({"success": False, "error": "Salesforce unavailable"}), 503

    if result.get("success"):
        result["voice_summary"] = sf.get_account_summary(account_name)
    return jsonify(result), 200 if result.get("success") else 404


@app.route('/salesforce/opportunities', methods=['POST'])
def salesforce_get_opportunities():
    """
    Return open opportunities for an account.
    Body: {"account_name": "Barcelona Wine Bar"}
    """
    data = request.get_json(silent=True) or {}
    account_name = (data.get("account_name") or "").strip()
    if not account_name:
        return jsonify({"success": False, "error": "account_name is required"}), 400

    sf = get_salesforce()
    result = sf.get_opportunities(account_name)
    if not result:
        return jsonify({"success": False, "error": "Salesforce unavailable"}), 503

    if result.get("success"):
        result["voice_summary"] = sf.get_opportunity_summary(account_name)
    return jsonify(result), 200 if result.get("success") else 404


@app.route('/salesforce/log-call', methods=['POST'])
def salesforce_log_call():
    """
    Log a call note as a completed Task on a Salesforce Account.
    Body: {
        "account_name": "Barcelona Wine Bar",
        "subject": "Follow-up call",
        "description": "Discussed Rioja allocation and summer menu.",
        "duration_minutes": 10,        (optional)
        "contact_name": "Chef Misha"   (optional)
    }
    """
    data = request.get_json(silent=True) or {}
    account_name = (data.get("account_name") or "").strip()
    subject = (data.get("subject") or "").strip()
    description = (data.get("description") or "").strip()
    duration = int(data.get("duration_minutes") or 0)
    contact_name = (data.get("contact_name") or "").strip() or None

    if not account_name:
        return jsonify({"success": False, "error": "account_name is required"}), 400
    if not description:
        return jsonify({"success": False, "error": "description is required"}), 400

    sf = get_salesforce()
    result = sf.log_call_note(account_name, subject, description, duration, contact_name)
    if not result:
        return jsonify({"success": False, "error": "Salesforce unavailable"}), 503

    if result.get("success"):
        result["voice_summary"] = f"Call note logged for {result['account']}."
    return jsonify(result), 200 if result.get("success") else 400


@app.route('/salesforce/update-account', methods=['POST'])
def salesforce_update_account():
    """
    Update fields on a Salesforce Account record.
    Body: {
        "account_name": "Barcelona Wine Bar",
        "fields": {
            "Phone": "203-555-1234",
            "Description": "Key Rioja account, Chef Misha contact."
        }
    }
    """
    data = request.get_json(silent=True) or {}
    account_name = (data.get("account_name") or "").strip()
    fields = data.get("fields") or {}

    if not account_name:
        return jsonify({"success": False, "error": "account_name is required"}), 400
    if not fields or not isinstance(fields, dict):
        return jsonify({"success": False, "error": "fields dict is required"}), 400

    sf = get_salesforce()
    result = sf.update_account(account_name, fields)
    if not result:
        return jsonify({"success": False, "error": "Salesforce unavailable"}), 503

    if result.get("success"):
        result["voice_summary"] = sf.update_account_voice_summary(account_name, fields)
    return jsonify(result), 200 if result.get("success") else 400


@app.route('/salesforce/recent-activity', methods=['POST'])
def salesforce_recent_activity():
    """
    Return recent activity (Tasks) for an account.
    Body: {"account_name": "Barcelona Wine Bar"}
    """
    data = request.get_json(silent=True) or {}
    account_name = (data.get("account_name") or "").strip()
    if not account_name:
        return jsonify({"success": False, "error": "account_name is required"}), 400

    sf = get_salesforce()
    result = sf.get_recent_activity(account_name)
    if not result:
        return jsonify({"success": False, "error": "Salesforce unavailable"}), 503

    if result.get("success"):
        result["voice_summary"] = sf.get_recent_activity_summary(account_name)
    return jsonify(result), 200 if result.get("success") else 404

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

if __name__ == '__main__':
    print("\n=== AIMEE ENHANCED WITH TACTICAL BRIEFINGS STARTUP ===")
    print(f"Device: {model_manager.device}")
    print(f"Whisper: {'✅ Available' if WHISPER_AVAILABLE else '❌ Not available'}")
    print(f"ElevenLabs: {'✅ Available' if elevenlabs_client else '❌ Not available'}")
    print(f"Enhanced Wine Intelligence: {'✅ Ready' if wine_intelligence and hasattr(wine_intelligence, 'get_stats') else '❌ Not available'}")
    
    if wine_intelligence and hasattr(wine_intelligence, 'get_stats'):
        stats = wine_intelligence.get_stats()
        print(f"Wine Data Stats: {stats}")
    
    print(f"Classifier: {'✅ Ready' if classifier else '❌ Not available'}")
    sf_status = get_salesforce().health_check()
    print(f"Salesforce: {'✅ Connected — ' + str(sf_status.get('instance_url','')) if sf_status.get('connected') else '⚠️  Not connected — set SF_* vars in .env'}")
    print(f"Fairfield County Intelligence: ✅ Ready - 17 tactical briefings loaded")
    print(f"Accounts: Barcelona (2), Spiga, ELM, The Cottage, Bin 100, Blackstones (3), Rebecca's, 99 Bottles, Horseneck, DB Fine Wines, Greens Farms, LaBella's, Acme")
    print(f"Voice Commands: 'Brief me on [account]', '[Region] accounts', 'Daily priorities', 'Market analysis'")
    
    # Preload models
    if WHISPER_AVAILABLE:
        model_manager.load_model("base")
        model_manager.load_model("medium")
    
    # Clean up old files
    cleanup_old_files()
    
    print("🍷 Aimee Enhanced with 17 Tactical Briefings Ready!")
    print("🎯 Try: 'Brief me on Spiga', 'New Canaan accounts', 'Daily priorities'")
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)