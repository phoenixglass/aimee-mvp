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

# ... [TRUNCATED FOR BREVITY IN THIS PREVIEW - FULL CONTENT CONTINUES]
