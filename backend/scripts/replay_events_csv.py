#!/usr/bin/env python3
"""
replay_events_csv.py – Dry-run the ingestion pipeline against historical data.

Reads safecity_env/events.csv (raw per-modality events logged by the original
draft pipeline: timestamp, modality, event, score — audio and text only, no
video rows), groups rows that were logged together into incident bundles, and
POSTs each bundle to POST /api/ingest on a running SafeCity AI server. This
exercises fusion + alert dedupe/suppression + persistence + WebSocket
broadcast end-to-end without needing to re-run any ML models.

Caveat: events.csv only ever stored the emotion classifier's label for text
rows (e.g. "fear", "NEGATIVE"), never the raw report sentence. The fused
"text" field of TEXT_KEYWORDS matches against raw report content, so replayed
text here will normalize to "unknown" — that's a limitation of this
historical data, not the fusion logic (see core/fusion.py normalize_label).

Usage (with the API server already running via `python main.py`):
    python scripts/replay_events_csv.py
"""
import csv
import os
from datetime import datetime, timedelta

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
EVENTS_CSV = os.path.join(REPO_ROOT, "safecity_env", "events.csv")

API_BASE = os.environ.get("SAFECITY_API_BASE", "http://127.0.0.1:8000")
GROUP_WINDOW = timedelta(seconds=5)  # events within this window of an audio row belong to it


def load_rows():
    with open(EVENTS_CSV, newline="") as f:
        rows = []
        for r in csv.DictReader(f):
            r["timestamp"] = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
            r["score"] = float(r["score"])
            rows.append(r)
    return rows


def group_rows(rows):
    """Anchor each group on an audio row; attach nearby text rows to it."""
    groups = []
    current = None
    for row in rows:
        if row["modality"] == "audio":
            current = {"timestamp": row["timestamp"], "audio": row, "text": []}
            groups.append(current)
        elif row["modality"] == "text":
            if current and (row["timestamp"] - current["timestamp"]) <= GROUP_WINDOW:
                current["text"].append(row)
            else:
                groups.append({"timestamp": row["timestamp"], "audio": None, "text": [row]})
        elif row["modality"] == "video":
            groups.append({"timestamp": row["timestamp"], "audio": None, "text": [], "video": row})
    return groups


def build_payload(group):
    payload = {"timestamp": group["timestamp"].strftime("%Y-%m-%d %H:%M:%S")}
    if group.get("video"):
        payload["video"] = {"label": group["video"]["event"], "score": group["video"]["score"]}
    if group.get("audio"):
        payload["audio"] = {"label": group["audio"]["event"], "score": group["audio"]["score"]}
    if group.get("text"):
        payload["text"] = [
            {"label": t["event"], "score": t["score"], "text": t["event"]}
            for t in group["text"]
        ]
    return payload


def main():
    rows = load_rows()
    groups = group_rows(rows)
    print(f"Loaded {len(rows)} raw events from {EVENTS_CSV}")
    print(f"Grouped into {len(groups)} incident bundles, replaying against {API_BASE} ...\n")

    accepted = duplicate = suppressed = below = errors = 0
    for g in groups:
        payload = build_payload(g)
        try:
            resp = requests.post(f"{API_BASE}/api/ingest", json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.ConnectionError:
            print(f"Could not reach {API_BASE} — is `python main.py` running? Aborting.")
            return
        except Exception as e:
            print(f"  ERROR posting group at {payload['timestamp']}: {e}")
            errors += 1
            continue

        reason = data["reason"]
        if data["accepted"]:
            accepted += 1
        elif reason == "duplicate":
            duplicate += 1
        elif reason == "suppressed":
            suppressed += 1
        elif reason.startswith("below_threshold"):
            below += 1

        inc = data["incident"]
        print(f"  [{payload['timestamp']}] type={inc['type']:<20} score={inc['fused_score']:.2f}  -> {reason}")

    print(
        f"\nSummary: {len(groups)} groups replayed | "
        f"accepted={accepted} duplicate={duplicate} suppressed={suppressed} "
        f"below_threshold={below} errors={errors}"
    )


if __name__ == "__main__":
    main()
