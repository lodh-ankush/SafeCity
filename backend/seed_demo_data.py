#!/usr/bin/env python3
"""
seed_demo_data.py  –  Generate realistic demo data for SafeCity AI dashboard.

Reads patterns from the original events.csv and generates ~80 fused incidents
spread over the past 60 days with realistic geo-coordinates around Bhubaneswar.

Run:  python seed_demo_data.py
"""
import random
from datetime import datetime, timedelta

from core.db import init_db, log_incident, log_event
from core.schemas import Incident, ModalityResult

# ── Bhubaneswar locations ───────────────────────────────────────────
LOCATIONS = [
    {"name": "KIIT Square",          "lat": 20.3541, "lon": 85.8145},
    {"name": "Patia Chowk",          "lat": 20.3591, "lon": 85.8190},
    {"name": "Chandrasekharpur",     "lat": 20.3267, "lon": 85.8177},
    {"name": "Nandankanan Road",     "lat": 20.3948, "lon": 85.8238},
    {"name": "Bhubaneswar Station",  "lat": 20.2708, "lon": 85.8408},
    {"name": "Master Canteen",       "lat": 20.2871, "lon": 85.8406},
    {"name": "Khandagiri Square",    "lat": 20.2574, "lon": 85.7753},
    {"name": "Jaydev Vihar",         "lat": 20.2966, "lon": 85.8115},
    {"name": "Saheed Nagar",         "lat": 20.2873, "lon": 85.8461},
    {"name": "Vani Vihar",           "lat": 20.3023, "lon": 85.8416},
    {"name": "Kalinga Stadium",      "lat": 20.2896, "lon": 85.8206},
    {"name": "Rasulgarh",            "lat": 20.2933, "lon": 85.8648},
    {"name": "Aiginia Square",       "lat": 20.2683, "lon": 85.8558},
    {"name": "Mancheswar",           "lat": 20.3122, "lon": 85.8512},
    {"name": "Baramunda Bus Stand",  "lat": 20.2756, "lon": 85.8006},
    {"name": "Lingaraj Temple Road", "lat": 20.2384, "lon": 85.8320},
    {"name": "Infocity",             "lat": 20.3342, "lon": 85.8168},
    {"name": "VSS Nagar",            "lat": 20.2815, "lon": 85.8293},
    {"name": "Acharya Vihar",        "lat": 20.2996, "lon": 85.8340},
    {"name": "Sishu Bhawan",         "lat": 20.2745, "lon": 85.8355},
]

# ── Incident templates ──────────────────────────────────────────────
INCIDENT_TEMPLATES = [
    {
        "type": "accident",
        "video_labels": ["car crash", "driving car"],
        "audio_labels": ["Siren", "car horn", "Crash"],
        "text_labels": ["fear", "NEGATIVE"],
        "texts": [
            "Major collision reported on the highway near {loc}.",
            "Two-vehicle accident blocking traffic at {loc}.",
            "Hit-and-run incident near {loc}, ambulance requested.",
            "Bus overturned near {loc} flyover, multiple injuries.",
            "Truck collision with auto-rickshaw at {loc}.",
        ],
        "score_range": (0.65, 0.95),
    },
    {
        "type": "emergency",
        "video_labels": ["running", "driving car"],
        "audio_labels": ["Siren", "police car (siren)", "Ambulance (siren)"],
        "text_labels": ["fear", "NEGATIVE"],
        "texts": [
            "Emergency vehicles rushing towards {loc}.",
            "Multiple sirens heard near {loc}, possible major incident.",
            "Police sirens around {loc} area, road blocked.",
            "Ambulance emergency call from {loc} junction.",
            "Fire brigade dispatched to {loc} area.",
        ],
        "score_range": (0.60, 0.92),
    },
    {
        "type": "fire",
        "video_labels": ["unknown"],
        "audio_labels": ["Siren", "Crackling", "Explosion"],
        "text_labels": ["fear", "NEGATIVE"],
        "texts": [
            "Fire spotted near the market in {loc}.",
            "Smoke rising from building at {loc}.",
            "Electrical fire reported at {loc} transformer station.",
            "Small fire in slum area near {loc}, spreading fast.",
            "Gas leak and fire reported at restaurant in {loc}.",
        ],
        "score_range": (0.70, 0.96),
    },
    {
        "type": "traffic",
        "video_labels": ["driving car", "riding bicycle"],
        "audio_labels": ["car horn", "Traffic noise"],
        "text_labels": ["anger", "NEGATIVE"],
        "texts": [
            "Heavy congestion reported at {loc} crossing.",
            "Traffic signal malfunction at {loc}, causing gridlock.",
            "Road construction blocking lanes near {loc}.",
            "Waterlogging causing traffic jam at {loc}.",
            "Festival procession blocking road near {loc}.",
        ],
        "score_range": (0.40, 0.75),
    },
    {
        "type": "violence_suspected",
        "video_labels": ["running"],
        "audio_labels": ["Gunshot, gunfire", "Screaming", "Shout"],
        "text_labels": ["fear", "anger"],
        "texts": [
            "Aggressive altercation reported near {loc}.",
            "Group fight broke out at {loc} late at night.",
            "Suspicious activity spotted by CCTV at {loc}.",
            "Loud screams and shouting heard near {loc}.",
            "Vandalism reported at {loc}, police alerted.",
        ],
        "score_range": (0.70, 0.94),
    },
]

SUMMARIES = {
    "accident": [
        "Vehicle collision detected via CCTV and audio. Emergency response dispatched.",
        "Multi-vehicle accident confirmed through video classification and audio sirens.",
        "Traffic accident identified. Audio sensors detected collision sounds and sirens.",
        "Road accident confirmed by multimodal analysis. Ambulance en route.",
    ],
    "emergency": [
        "Emergency response activity detected through audio classification and text reports.",
        "Multiple emergency signals confirmed across audio and text modalities.",
        "High-priority emergency event. Sirens and distress reports corroborated.",
        "Emergency situation verified through cross-modal signal fusion.",
    ],
    "fire": [
        "Fire incident detected via text reports and audio crackling. Fire brigade alerted.",
        "Smoke and flames reported. Audio sensors confirm emergency sirens nearby.",
        "Active fire confirmed through multimodal analysis of text and audio data.",
        "Fire hazard identified. Multiple citizen reports corroborate sensor data.",
    ],
    "traffic": [
        "Traffic congestion detected via video feed and citizen reports.",
        "Road blockage confirmed through CCTV analysis and text classification.",
        "High traffic density identified. Signal malfunction suspected.",
        "Traffic disruption verified through multimodal sensor data.",
    ],
    "violence_suspected": [
        "Suspicious activity flagged by audio sensors and text reports. Police alerted.",
        "Potential violent incident detected through audio classification of distress sounds.",
        "Aggressive behavior identified via multimodal analysis. Patrol dispatched.",
        "Security alert generated from correlated audio and text incident reports.",
    ],
}


def jitter(val: float, amount: float = 0.005) -> float:
    """Add small random offset to a coordinate."""
    return round(val + random.uniform(-amount, amount), 6)


def random_datetime(days_back: int = 60) -> datetime:
    """Generate a random datetime within the past N days."""
    now = datetime.now()
    delta = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return now - delta


def generate_events(incidents_data: list) -> list:
    """Generate raw events from incident data (for events.csv)."""
    events = []
    for inc in incidents_data:
        ts = inc["timestamp"]
        # Audio event
        events.append({
            "timestamp": ts,
            "modality": "audio",
            "event": inc["audio_label"],
            "score": round(inc["audio_score"], 4),
        })
        # Text events (1-3 per incident)
        for _ in range(random.randint(1, 3)):
            events.append({
                "timestamp": ts,
                "modality": "text",
                "event": inc["text_label"],
                "score": round(random.uniform(0.6, 0.99), 4),
            })
    return events


def seed():
    """Generate and write demo data."""
    print("🌱 Seeding SafeCity AI demo data...")
    init_db()

    incidents_data = []
    num_incidents = 80

    for i in range(num_incidents):
        template = random.choice(INCIDENT_TEMPLATES)
        loc = random.choice(LOCATIONS)
        dt = random_datetime()
        fused_score = round(random.uniform(*template["score_range"]), 3)

        text_line = random.choice(template["texts"]).format(loc=loc["name"])

        inc = {
            "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "type": template["type"],
            "fused_score": fused_score,
            "video_label": random.choice(template["video_labels"]),
            "video_score": round(random.uniform(0.3, 0.9), 3),
            "audio_label": random.choice(template["audio_labels"]),
            "audio_score": round(random.uniform(0.4, 0.85), 3),
            "text_label": random.choice(template["text_labels"]),
            "text_score": round(random.uniform(0.55, 0.99), 3),
            "raw_text": text_line,
            "lat": jitter(loc["lat"]),
            "lon": jitter(loc["lon"]),
            "summary": random.choice(SUMMARIES[template["type"]]),
        }
        incidents_data.append(inc)

    # Sort by timestamp
    incidents_data.sort(key=lambda x: x["timestamp"])

    # ── Write incidents to SQLite ─────────────────────────────────────
    for inc in incidents_data:
        log_incident(Incident(
            timestamp=inc["timestamp"],
            type=inc["type"],
            fused_score=inc["fused_score"],
            video=ModalityResult(label=inc["video_label"], score=inc["video_score"]),
            audio=ModalityResult(label=inc["audio_label"], score=inc["audio_score"]),
            text=ModalityResult(label=inc["text_label"], score=inc["text_score"]),
            lat=inc["lat"],
            lon=inc["lon"],
            raw_text=[inc["raw_text"]],
            summary=inc["summary"],
        ))

    print(f"   ✅ Wrote {len(incidents_data)} incidents to the database")

    # ── Write raw events to SQLite ────────────────────────────────────
    events = generate_events(incidents_data)
    events.sort(key=lambda x: x["timestamp"])

    for ev in events:
        log_event(ev["timestamp"], ev["modality"], ev["event"], ev["score"])

    print(f"   ✅ Wrote {len(events)} events to the database")
    print("🎉 Demo data seeding complete!")


if __name__ == "__main__":
    seed()
