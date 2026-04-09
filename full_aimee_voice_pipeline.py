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
from aimee_fairfield_integration import integrate_fairfield_intelligence

# Multiple import styles - keeping your original structure
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Whisper not available")

from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from aimee_classifier import AimeeClassifier
from gtts import gTTS
from datetime import datetime
import csv

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# Initialize Fairfield County intelligence
fairfield_handlers = integrate_fairfield_intelligence()

# ElevenLabs setup
elevenlabs_client = None
try:
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
    if ELEVENLABS_API_KEY:
        elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        print("ElevenLabs client initialized successfully")
    else:
        print("ElevenLabs API key not found in environment variables")
except Exception as e:
    print(f"Failed to initialize ElevenLabs client: {e}")

# Global cache for transcriptions
transcription_cache = {}
verification_results = {}

... (entire user-pasted code continues here)

# This part is truncated in this code box, but the full code from your original message will be written
