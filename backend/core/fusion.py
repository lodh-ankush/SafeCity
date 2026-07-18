# core/fusion.py
from typing import Optional, List, Dict
from core.config import (
    W_VIDEO, W_AUDIO, W_TEXT,
    VIDEO_MIN, AUDIO_MIN, TEXT_MIN,
    ALERT_MIN,
    VIDEO_LABEL_MAP, AUDIO_LABEL_MAP, TEXT_KEYWORDS,
)
from core.schemas import ModalityResult, Incident
from core.utils import get_timestamp, normalize_conf


def normalize_label(label: str, modality: str, text_content: str = None) -> str:
    if modality == "text":
        # Text has no fixed label vocabulary to map (the classifier output is
        # an emotion, e.g. "fear"/"anger", not an incident category) — scan the
        # raw report content itself for incident keywords instead.
        content = (text_content or "").lower()
        if not content:
            return "unknown"
        for k, v in TEXT_KEYWORDS.items():
            if k in content:
                return v
        return "unknown"

    l = (label or "").lower()
    if modality == "video":
        for k, v in VIDEO_LABEL_MAP.items():
            if k in l:
                return v
        return "unknown"
    if modality == "audio":
        for k, v in AUDIO_LABEL_MAP.items():
            if k in l:
                return v
        return "unknown"
    return "unknown"


def to_modality_result(res: Dict) -> Optional[ModalityResult]:
    if not res:
        return None
    return ModalityResult(
        label=res.get("label", "unknown"),
        score=float(res.get("score", 0.0)),
        top=res.get("top"),
    )


def fuse(
    video_res: Optional[Dict],
    audio_res: Optional[Dict],
    text_res_list: Optional[List[Dict]] = None,
    raw_text: Optional[List[str]] = None,
) -> Incident:
    """
    Accepts outputs from pipelines and returns a fused Incident.
    text_res_list: you might have multiple lines; we pick the highest.
    """
    # Pick top text line
    text_best = None
    if text_res_list:
        text_best = max(text_res_list, key=lambda x: x.get("score", 0.0))

    v = to_modality_result(video_res)
    a = to_modality_result(audio_res)
    t = to_modality_result(text_best)

    # Apply per-modality thresholds
    v_conf = normalize_conf(v.score) if (v and v.score >= VIDEO_MIN) else 0.0
    a_conf = normalize_conf(a.score) if (a and a.score >= AUDIO_MIN) else 0.0
    t_conf = normalize_conf(t.score) if (t and t.score >= TEXT_MIN) else 0.0

    # Vote for incident type (simple weighted majority)
    votes = {}
    if v and v_conf > 0:
        key = normalize_label(v.label, "video")
        votes[key] = votes.get(key, 0) + W_VIDEO * v_conf
    if a and a_conf > 0:
        key = normalize_label(a.label, "audio")
        votes[key] = votes.get(key, 0) + W_AUDIO * a_conf
    if t and t_conf > 0:
        text_content = text_best.get("text") if text_best else None
        key = normalize_label(t.label, "text", text_content=text_content)
        votes[key] = votes.get(key, 0) + W_TEXT * t_conf

    if not votes:
        fused_type = "unknown"
        fused_score = 0.0
    else:
        fused_type, fused_score = max(votes.items(), key=lambda kv: kv[1])

    # Ensure minimum for alerting
    if fused_score < ALERT_MIN:
        alt_score = max(v_conf * W_VIDEO, a_conf * W_AUDIO, t_conf * W_TEXT, fused_score)
        fused_score = alt_score

    return Incident(
        timestamp=get_timestamp(),
        type=fused_type,
        fused_score=float(fused_score),
        video=v,
        audio=a,
        text=t,
        raw_text=raw_text or [],
    )
