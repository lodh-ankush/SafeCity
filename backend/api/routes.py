# api/routes.py
"""
SafeCity AI – REST API Endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from collections import Counter, defaultdict
from datetime import datetime

from core.db import log_event, log_incident, read_events, read_incidents
from core.forecast import generate_forecast
from core.fusion import fuse
from core.alerts import AlertQueue
from core.utils import get_timestamp
from core.ws_manager import manager
from core.config import INCIDENT_TYPES, DEMO_CENTER_LAT, DEMO_CENTER_LON

router = APIRouter()

# Ranks, dedupes, and suppresses fused incidents for the lifetime of the process.
alert_queue = AlertQueue()


# ── Incidents ────────────────────────────────────────────────────────
@router.get("/incidents")
def get_incidents(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    type: Optional[str] = None,
    min_score: Optional[float] = None,
):
    """List fused incidents with optional filters."""
    incidents = read_incidents()
    if type:
        incidents = [i for i in incidents if i["type"] == type]
    if min_score is not None:
        incidents = [i for i in incidents if i["fused_score"] >= min_score]
    total = len(incidents)
    # Most recent first
    incidents = list(reversed(incidents))
    page = incidents[offset : offset + limit]
    return {"total": total, "offset": offset, "limit": limit, "incidents": page}


@router.get("/incidents/latest")
def get_latest_incidents(n: int = Query(20, ge=1, le=100)):
    """Get the N most recent incidents."""
    incidents = read_incidents()
    latest = list(reversed(incidents))[:n]
    return {"count": len(latest), "incidents": latest}


# ── Events ───────────────────────────────────────────────────────────
@router.get("/events")
def get_events(
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    modality: Optional[str] = None,
):
    """List raw modality events."""
    events = read_events()
    if modality:
        events = [e for e in events if e["modality"] == modality]
    total = len(events)
    events = list(reversed(events))
    page = events[offset : offset + limit]
    return {"total": total, "offset": offset, "limit": limit, "events": page}


# ── Stats ────────────────────────────────────────────────────────────
@router.get("/stats")
def get_stats():
    """Aggregated statistics across all incidents and events."""
    incidents = read_incidents()
    events = read_events()

    # Counts by type
    type_counter = Counter(i["type"] for i in incidents)

    # Average fused_score by type
    score_sums = defaultdict(float)
    score_counts = defaultdict(int)
    for i in incidents:
        score_sums[i["type"]] += i["fused_score"]
        score_counts[i["type"]] += 1
    avg_scores = {
        t: round(score_sums[t] / score_counts[t], 3) for t in score_counts
    }

    # Hourly distribution
    hourly = Counter()
    for i in incidents:
        try:
            dt = datetime.strptime(i["timestamp"], "%Y-%m-%d %H:%M:%S")
            hourly[dt.hour] += 1
        except (ValueError, KeyError):
            pass
    hourly_dist = {str(h): hourly.get(h, 0) for h in range(24)}

    # Severity breakdown
    severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for i in incidents:
        s = i["fused_score"]
        if s >= 0.8:
            severity["critical"] += 1
        elif s >= 0.6:
            severity["high"] += 1
        elif s >= 0.4:
            severity["medium"] += 1
        else:
            severity["low"] += 1

    # Events by modality
    modality_counter = Counter(e["modality"] for e in events)

    # Recent activity (last 7 entries)
    recent = list(reversed(incidents))[:7]

    return {
        "total_incidents": len(incidents),
        "total_events": len(events),
        "incidents_by_type": dict(type_counter),
        "avg_score_by_type": avg_scores,
        "hourly_distribution": hourly_dist,
        "severity_breakdown": severity,
        "events_by_modality": dict(modality_counter),
        "recent_incidents": recent,
        "incident_type_meta": INCIDENT_TYPES,
    }


# ── Forecast ─────────────────────────────────────────────────────────
@router.get("/forecast")
def get_forecast():
    """Time-series based forecasting and risk analysis."""
    return generate_forecast()


# ── Map Data ─────────────────────────────────────────────────────────
@router.get("/map/incidents")
def get_map_incidents():
    """Return geo-tagged incidents for map overlay."""
    incidents = read_incidents()
    geo_incidents = [
        i for i in incidents
        if i.get("lat") is not None and i.get("lon") is not None
    ]
    return {
        "center": {"lat": DEMO_CENTER_LAT, "lon": DEMO_CENTER_LON},
        "zoom": 13,
        "incidents": geo_incidents,
        "total": len(geo_incidents),
    }


# ── Ingestion ────────────────────────────────────────────────────────
class ModalityIn(BaseModel):
    label: str
    score: float


class TextEventIn(BaseModel):
    label: str
    score: float
    text: Optional[str] = None  # raw report content, used for incident-type keyword matching


class IngestRequest(BaseModel):
    video: Optional[ModalityIn] = None
    audio: Optional[ModalityIn] = None
    text: Optional[List[TextEventIn]] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    timestamp: Optional[str] = None  # override "now"; used for replaying historical data


@router.post("/ingest")
async def ingest_event(payload: IngestRequest):
    """
    Accept one bundle of per-modality classification results (whatever a
    video/audio/text pipeline run produced, or a replayed historical event),
    fuse them into a candidate incident, and run it through the alert queue
    (score threshold + dedupe + per-type suppression). Accepted incidents are
    persisted and broadcast live to any /ws/alerts WebSocket clients.
    """
    if not payload.video and not payload.audio and not payload.text:
        raise HTTPException(
            status_code=400,
            detail="At least one of video, audio, or text must be provided",
        )

    ts = payload.timestamp or get_timestamp()
    if payload.video:
        log_event(ts, "video", payload.video.label, payload.video.score)
    if payload.audio:
        log_event(ts, "audio", payload.audio.label, payload.audio.score)
    if payload.text:
        for t in payload.text:
            log_event(ts, "text", t.label, t.score)

    video_res = payload.video.model_dump() if payload.video else None
    audio_res = payload.audio.model_dump() if payload.audio else None
    text_res_list = [t.model_dump() for t in payload.text] if payload.text else None
    raw_text = [t.text for t in payload.text if t.text] if payload.text else []

    incident = fuse(video_res, audio_res, text_res_list, raw_text=raw_text)
    if payload.timestamp:
        incident.timestamp = payload.timestamp  # fuse() always stamps "now"; honor replay timestamps
    incident.lat = payload.lat
    incident.lon = payload.lon

    accepted, reason = alert_queue.push(incident)
    incident_out = {
        "timestamp": incident.timestamp,
        "type": incident.type,
        "fused_score": round(incident.fused_score, 3),
        "lat": incident.lat,
        "lon": incident.lon,
        "raw_text": incident.raw_text,
    }

    if accepted:
        log_incident(incident)
        await manager.broadcast({**incident_out, "is_live": True})

    return {"accepted": accepted, "reason": reason, "incident": incident_out}


# ── Config ───────────────────────────────────────────────────────────
@router.get("/config/incident-types")
def get_incident_types():
    """Return incident type metadata (colors, icons, severity)."""
    return INCIDENT_TYPES
