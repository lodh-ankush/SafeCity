# core/config.py
import os

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

DB_PATH = os.path.join(BASE_DIR, "safecity.db")

# ── Per-modality confidence thresholds ───────────────────────────────
VIDEO_MIN = 0.30
AUDIO_MIN = 0.30
TEXT_MIN  = 0.50   # text can be noisy; keep higher

# ── Fusion weights (tune later) ─────────────────────────────────────
W_VIDEO = 0.45
W_AUDIO = 0.35
W_TEXT  = 0.20

# ── Global alert threshold (after fusion) ────────────────────────────
ALERT_MIN = 0.55

# ── Dedupe / suppression settings ────────────────────────────────────
DEDUP_TIME_WINDOW_SEC = 90
DEDUP_DISTANCE_M      = 60
SUPPRESS_REPEAT_SEC   = 120

# ── Label normalisation maps ────────────────────────────────────────
# Keys must be labels the underlying model can actually output — verified
# against MCG-NJU/videomae-base-finetuned-kinetics' real 400-class Kinetics
# vocabulary (`AutoConfig.from_pretrained(...).id2label`), since matching is
# substring-based (`normalize_label` in fusion.py) and a key that's a
# substring of an unrelated real label will misfire (e.g. "wrestling" would
# also match "arm wrestling" — excluded for that reason).
#
# Kinetics-400 is a general human-action dataset, not an incident/hazard
# classifier: it has no "car crash"/"collision"/"accident" class at all, so
# "accident" and "emergency" are not currently reachable via video no matter
# what footage is supplied. "fire" is reachable only via "extinguishing
# fire" (the one genuinely fire-adjacent class); "violence_suspected" is
# proxied by real physical-altercation-resembling actions, since Kinetics-400
# has no "assault"/"fight" class either.
VIDEO_LABEL_MAP = {
    "driving car": "traffic",
    "riding a bike": "traffic",
    "riding mountain bike": "traffic",
    "riding scooter": "traffic",
    "motorcycling": "traffic",
    "extinguishing fire": "fire",
    "punching person": "violence_suspected",
    "sword fighting": "violence_suspected",
    "slapping": "violence_suspected",
    "headbutting": "violence_suspected",
}

AUDIO_LABEL_MAP = {
    "siren": "emergency",
    "police car (siren)": "emergency",
    "car horn": "traffic",
    "gunshot": "violence_suspected",
}

TEXT_KEYWORDS = {
    "accident": "accident",
    "crash": "accident",
    "pileup": "accident",
    "fire": "fire",
    "smoke": "fire",
    "gunshot": "violence_suspected",
    "fight": "violence_suspected",
    "congestion": "traffic",
    "traffic": "traffic",
    "siren": "emergency",
}

# ── Incident type display metadata ──────────────────────────────────
# Colors are the frontend's validated categorical palette (light-mode hex —
# see frontend/src/theme.js for the dark-mode step of each and the CVD/
# contrast validation). Only 4 hues clear the all-pairs CVD check the map
# view needs (see CLAUDE.md); violence_suspected/unknown share a muted gray
# and are distinguished by icon, not color.
INCIDENT_TYPES = {
    "accident":           {"color": "#2a78d6", "icon": "🚗", "severity_base": 0.80},
    "emergency":          {"color": "#008300", "icon": "🚨", "severity_base": 0.90},
    "fire":               {"color": "#e87ba4", "icon": "🔥", "severity_base": 0.85},
    "traffic":            {"color": "#eda100", "icon": "🚦", "severity_base": 0.40},
    "violence_suspected": {"color": "#898781", "icon": "⚠️",  "severity_base": 0.90},
    "unknown":            {"color": "#898781", "icon": "❓", "severity_base": 0.30},
}

# ── Demo geo centre (Bhubaneswar, India) ────────────────────────────
DEMO_CENTER_LAT = 20.2961
DEMO_CENTER_LON = 85.8245
