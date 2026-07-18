# core/schemas.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ── Internal dataclasses (used by ML pipelines) ─────────────────────
@dataclass
class ModalityResult:
    label: str
    score: float
    top: Optional[List[Dict]] = None  # optional: top-k from pipeline


@dataclass
class Incident:
    timestamp: str
    type: str                              # normalised e.g. accident / traffic / emergency
    fused_score: float
    video: Optional[ModalityResult] = None
    audio: Optional[ModalityResult] = None
    text:  Optional[ModalityResult] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    raw_text: Optional[List[str]] = field(default_factory=list)
    summary: Optional[str] = None
