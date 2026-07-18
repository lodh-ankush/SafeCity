// Talks to the FastAPI backend via the Vite dev-server proxy (see
// vite.config.js: /api and /ws both forward to http://127.0.0.1:8000), so
// relative paths work in dev and in a same-origin production build alike.

async function getJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export function getIncidents({ limit = 100, offset = 0, type, minScore } = {}) {
  const params = new URLSearchParams({ limit, offset });
  if (type) params.set("type", type);
  if (minScore != null) params.set("min_score", minScore);
  return getJSON(`/api/incidents?${params}`);
}

export function getStats() {
  return getJSON("/api/stats");
}

export function getForecast() {
  return getJSON("/api/forecast");
}

export function getMapIncidents() {
  return getJSON("/api/map/incidents");
}

export function getIncidentTypes() {
  return getJSON("/api/config/incident-types");
}

export async function ingestEvent(payload) {
  const res = await fetch("/api/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`/api/ingest -> ${res.status}`);
  return res.json();
}

// A live /ws/alerts push (see backend/api/routes.py's incident_out) is a
// leaner shape than a persisted incident from GET /api/incidents (no id,
// no per-modality labels/scores, no summary, raw_text is an array not a
// joined string). Normalize both to one shape for consistent rendering.
let liveIdCounter = 0;
export function normalizeIncident(incident) {
  const rawText = Array.isArray(incident.raw_text)
    ? incident.raw_text.join(" | ")
    : (incident.raw_text ?? "");
  return {
    id: incident.id ?? `live-${Date.now()}-${liveIdCounter++}`,
    video_label: null,
    audio_label: null,
    text_label: null,
    summary: "",
    ...incident,
    raw_text: rawText,
  };
}

export function wsAlertsUrl() {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/alerts`;
}
