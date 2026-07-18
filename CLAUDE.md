# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

SafeCity AI has two active parts: a Python/FastAPI backend (`backend/`) and
a React+Vite dashboard frontend (`frontend/`). The `safecity_env/` directory
at the repo root is a Python virtualenv that *also* happens to contain an
earlier, superseded draft of this project (its own `core/`, `pipelines/`,
`safecity_pipeline.py`, plus `safecity_env/events.csv` and real sample media
under `safecity_env/data/`). Treat `safecity_env/` as legacy/scratch and
`backend/` as the source of truth — but note `safecity_env/data/audio/siren.wav`,
`safecity_env/data/sample_videos/traffic.mp4`, and
`safecity_env/data/text/sample_reports.txt` are currently the *only* real
sample media files in the repo (nothing equivalent exists under `backend/`),
and `safecity_env/events.csv` is real historical output from the legacy
pipeline, replayable via `backend/scripts/replay_events_csv.py` (see below).

There is no git repository initialized here yet (a root `.gitignore` is
already in place for when one is).

## Commands

Activate the venv first (Windows):
```
safecity_env\Scripts\activate.bat
```

Install deps (from `backend/`):
```
pip install -r backend/requirements.txt
```
Note: `requirements.txt` lists `websockets`, but it was not actually
installed in this venv until the ingestion work — without it uvicorn cannot
serve `/ws/alerts` at all (it fails silently at the transport level, not at
import time). If WebSocket connections don't work, `pip install websockets`.

Run the FastAPI backend:
```
cd backend
python main.py
```
Serves on `http://0.0.0.0:8000`, interactive docs at `/docs`, WebSocket at
`/ws/alerts`. On startup `init_db()` creates `backend/safecity.db` (SQLite,
WAL mode) with `events` and `incidents` tables if it doesn't exist yet.

Populate demo data (synthetic, not model-derived) so the API/dashboard has
something to show:
```
cd backend
python seed_demo_data.py
```
Inserts ~80 generated incidents (and their underlying events) around
Bhubaneswar directly into `safecity.db` via `core/db.py`.

**Windows console gotcha:** several scripts print emoji (`🌱`, `🚦`, ...).
On a plain Windows terminal using the legacy `cp1252` codepage this raises
`UnicodeEncodeError` on `seed_demo_data.py` and the pipeline scripts. Fix by
running with `set PYTHONIOENCODING=utf-8` first (or `$env:PYTHONIOENCODING="utf-8"`
in PowerShell), or use a UTF-8-capable terminal (Windows Terminal).

Ingest a real incident (video/audio/text classification results, whatever
subset you have) into fusion + alerting + storage + live broadcast:
```
POST /api/ingest
{
  "video": {"label": "car crash", "score": 0.9},
  "audio": {"label": "Siren", "score": 0.7},
  "text": [{"label": "fear", "score": 0.9, "text": "Major accident near KIIT Square"}],
  "lat": 20.3541, "lon": 85.8145
}
```
`video`/`audio`/`text` are all optional but at least one is required. `text[].text`
is the raw report sentence — it's what incident-type keyword matching
actually scans (see Architecture). Returns `{"accepted": bool, "reason": str,
"incident": {...}}`; accepted incidents are persisted and broadcast to all
`/ws/alerts` clients.

Dry-run the ingestion pipeline against real historical data (with the server
running):
```
cd backend
python scripts/replay_events_csv.py
```
Reads `safecity_env/events.csv`, groups its audio/text rows into incident
bundles, and POSTs each one to `/api/ingest`, printing accept/reject/dedupe
outcomes. See the caveats in that script's docstring and in the Architecture
section below about why this particular dataset structurally cannot produce
an accepted incident under the current `ALERT_MIN`/weight configuration.

Run an individual ML pipeline script standalone (each downloads its
HuggingFace model on first run if not already cached; video/audio/text-emotion
models were already cached locally as of this writing, BART for
summarization was not):
```
cd backend
python pipelines/video_pipeline.py
python pipelines/audio_pipeline.py
python pipelines/text_pipeline.py
```
These default to relative sample paths (e.g. `data/sample_videos/traffic.mp4`)
that do **not** exist under `backend/` — there is no `backend/data/`. Either
pass an explicit path as the function argument or point at
`safecity_env/data/...`. These scripts are standalone utilities for
producing a `{label, score}` result you could feed into `/api/ingest` — they
are not called by the API itself (see Architecture).

Run the frontend dashboard (needs the backend running first — it proxies
`/api` and `/ws` to it):
```
cd frontend
npm install   # first time only
npm run dev
```
Serves on `http://localhost:5173`. `vite.config.js` proxies `/api/*` and
`/ws/*` to `http://127.0.0.1:8000`, so the frontend code uses relative paths
(`fetch("/api/stats")`, `ws://<host>/ws/alerts`) and works unchanged in dev
and in a same-origin production build — no CORS juggling, no hardcoded
backend URL to update per environment.

```
npm run build   # production build to frontend/dist/ (not wired to the backend to serve statically)
npm run lint    # oxlint
```

There are no tests, no linter/formatter config, and no CI for the backend.

## Architecture

**`POST /api/ingest` (`backend/api/routes.py`) is the seam that connects
everything.** It accepts a bundle of already-classified per-modality results
— the `{label, score}` shape every pipeline script in `backend/pipelines/`
produces — rather than raw media files; nothing in the API process itself
loads a HuggingFace model. Given a bundle it:

1. Logs each modality result as a row via `core/db.log_event()`.
2. Calls `core/fusion.fuse()` to produce a single candidate `Incident`.
3. Runs it through a process-lifetime `core/alerts.AlertQueue` (module-level
   singleton in `api/routes.py`) for threshold/dedupe/suppression.
4. If accepted: persists via `core/db.log_incident()` and broadcasts the
   incident to every connected `/ws/alerts` client via the shared
   `core/ws_manager.manager`.

The `backend/pipelines/*.py` scripts (video/audio/text classification) are
still standalone, single-file CLI utilities — nothing calls them
automatically. The intended flow is: run a pipeline script (or the legacy
`safecity_env/safecity_pipeline.py` orchestrator) to get a `{label, score}`
result, then `POST` it to `/api/ingest`. `backend/scripts/replay_events_csv.py`
does exactly this against historical data instead of live model output.

**Fusion voting has a real structural ceiling worth understanding before
tuning `core/config.py`.** `core/fusion.fuse()` splits votes *by normalized
type*: each modality's confidence (sigmoid-calibrated via
`core/utils.normalize_conf`, which saturates around ~0.88 even at a raw
score of 1.0) is weighted by `W_VIDEO=0.45` / `W_AUDIO=0.35` / `W_TEXT=0.20`
and added to whichever incident-type bucket its label maps to. A single
modality voting alone can never clear `ALERT_MIN=0.55` (max possible is
`0.45 * ~0.88 ≈ 0.40`). Two modalities only reinforce each other if they map
to the *same* normalized type — and **no audio label maps to `"fire"` or
`"accident"`, and no video label maps to `"accident"` or `"emergency"`** in
`AUDIO_LABEL_MAP`/`VIDEO_LABEL_MAP` (`core/config.py`), while audio+text
combined tops out at `(0.35+0.20) * ~0.88 ≈ 0.48` — still under threshold.
In practice, **only video+audio, video+text, or all three agreeing on the
same type can ever trigger an accepted alert** under the current
weights/threshold; audio+text alone (which is exactly the shape of
`safecity_env/events.csv`, since it has no video rows) structurally cannot.
This was confirmed empirically by replaying `events.csv` through
`/api/ingest` — every bundle was rejected `below_threshold`.

**`VIDEO_LABEL_MAP` was fixed to only use labels the video model can
actually output.** Matching is substring-based, and two of the original
four entries were unreachable on *any* video: `"car crash"` isn't a real
class in `MCG-NJU/videomae-base-finetuned-kinetics`'s 400-label Kinetics
vocabulary at all (verified via `AutoConfig.from_pretrained(...).id2label`)
— Kinetics-400 is a general human-action dataset (sports, daily
activities), not an incident/hazard classifier, and has no
crash/collision/accident concept — and `"riding bicycle"` didn't match
either of the model's real labels (`"riding a bike"` / `"riding mountain
bike"`). The map now uses only verified-reachable labels:
`"driving car"`/`"riding a bike"`/`"riding mountain bike"`/`"riding
scooter"`/`"motorcycling"` → `traffic`, `"extinguishing fire"` → `fire`
(the one genuinely fire-adjacent class in Kinetics-400 — so `fire` *is*
reachable via video, just only through that one specific action), and
`"punching person"`/`"sword fighting"`/`"slapping"`/`"headbutting"` →
`violence_suspected` (proxied by physical-altercation-resembling actions,
since there's no `"assault"`/`"fight"` class either). Each key was checked
programmatically against the full label list for unintended substring
collisions — e.g. `"wrestling"` was deliberately excluded, since it would
have also matched the unrelated `"arm wrestling"`. **`"accident"` and
`"emergency"` remain unreachable via video** no matter what footage is
supplied — Kinetics-400 has no class for either concept, so reaching them
would need a different or additional video model, not new sample footage.
`seed_demo_data.py`'s cosmetic `video_labels` lists (e.g. `"car crash"`)
still reference the old, unreachable label — harmless since seeding sets
`type` directly and never runs it through `fuse()`, but worth knowing it's
no longer representative of what the real model would say.

**Text-modality voting was fixed to match keywords against the raw report
text, not the emotion label.** `TEXT_KEYWORDS` (`"fire"`, `"gunshot"`,
`"accident"`, ...) are words that appear in a citizen report's *content* —
but `fuse()` used to match them against the text classifier's *emotion*
label (`"fear"`, `"anger"`, `"NEGATIVE"`, ...), which never contains those
words, so text was effectively a non-contributing modality. `core/fusion.normalize_label()`
now takes an explicit `text_content` parameter and matches `TEXT_KEYWORDS`
against that when provided (via `IngestRequest.text[].text` /
`TextEventIn.text`); it returns `"unknown"` if no raw text is given. This is
why `/api/ingest` accepts an optional `text` field per text entry, separate
from `label`.

**Storage is SQLite** (`backend/safecity.db`, WAL mode) via `core/db.py` —
two tables, `events` and `incidents`, mirroring the old CSV columns exactly.
`read_incidents()`/`read_events()` return the same dict shapes the API and
`core/forecast.py` always expected, so `api/routes.py` didn't need to
change. This replaced flat CSV files specifically because `/api/ingest` is a
real concurrent writer now (API requests) alongside reads from other
requests — CSV had no locking.

`backend/core/forecast.py`'s `generate_forecast()` is rule-based descriptive
statistics over the incidents table (hour-of-day histogram, day-of-week
averages, a two-half rate comparison for trend direction, lat/lon rounding
for geo clusters) — there is no trained/learned forecasting model.

`backend/pipelines/summarization_pipeline.py` (BART-large-CNN, lazily loaded
so importing it doesn't force a model download) is still not called from
anywhere else in the codebase — the `summary` field on ingested incidents is
currently always empty; only `seed_demo_data.py`'s canned per-type text
populates it. Wiring BART into `/api/ingest` is a follow-up, not yet done —
it requires downloading the ~1.6GB model on first use.

`backend/core/config.py` is the single place for all tunables: per-modality
thresholds, fusion weights, alert threshold, dedupe/suppression windows,
label-normalization maps, incident-type display metadata (color/icon used
by the API), and the demo map center (Bhubaneswar, India). When adjusting
fusion/alerting behavior — including the structural ceiling described above
— this is the file to change; `fusion.py` and `alerts.py` are otherwise
mechanical.

`backend/core/schemas.py` defines the two dataclasses (`ModalityResult`,
`Incident`) that flow through fusion/alerting in memory before
`core/db.log_incident()` flattens them into a SQLite row.

`core/ws_manager.py` holds the `ConnectionManager`/`manager` singleton used
by both `main.py` (the `/ws/alerts` WebSocket route, which just registers
the connection and blocks on `receive_text()` to detect disconnects — it no
longer generates any traffic itself) and `api/routes.py` (which calls
`manager.broadcast()` after an accepted ingest). It's a separate module
specifically to avoid a circular import, since `main.py` imports the router
from `api.routes`.

## Frontend (`frontend/`)

Plain Vite+React (no router, no state library — the whole app is small
enough that `App.jsx` owns all state and passes it down as props).
`src/api.js` is the only place that talks to the backend (REST via `fetch`
against relative `/api/...` paths, resolved by the Vite proxy — see
Commands). `src/hooks/useLiveAlerts.js` opens `/ws/alerts` and
auto-reconnects (3s backoff) if the backend restarts.

**A live WebSocket push and a persisted incident from `GET /api/incidents`
are two different shapes** — the live push is `api/routes.py`'s lean
`incident_out` (no `id`, no per-modality labels, `raw_text` as an array),
while a DB row has all of that (`raw_text` as a joined string). `api.js`'s
`normalizeIncident()` reconciles both into one shape before they hit any
component; live-origin incidents get a synthetic `id` prefixed `live-`,
which `IncidentFeed.jsx` uses to decide whether to play the "just arrived"
flash animation.

`App.jsx` refetches `/api/stats` and `/api/forecast` on every live incident
(no debouncing — fine at demo-data volumes, would want throttling under
real load) and prepends live incidents to the feed/map lists directly rather
than refetching those.

**Color decisions came from the `dataviz` skill's method, not eyeballing** —
run `node <dataviz-skill>/scripts/validate_palette.js "<hexes>" --mode
light|dark --pairs all` before trusting any categorical color set (see that
skill for the full six-check method). Two things that came out of actually
running the validator here, both in `src/theme.js` /
`backend/core/config.py`'s `INCIDENT_TYPES`:
- **Only 4 hues (blue/green/magenta/yellow) pass the all-pairs CVD check**
  the map view needs (markers can sit anywhere next to any other marker, so
  it's an all-pairs context, not adjacent-only like a bar chart). Every
  5-hue combination tried — including semantically "intuitive" ones like
  red-for-fire — failed the normal-vision floor. `accident`/`emergency`/
  `fire`/`traffic` get the 4 safe hues; `violence_suspected`/`unknown`
  share a muted gray and rely on their emoji icon (rendered directly in the
  Leaflet `DivIcon`, not just a color dot) for identity instead.
- Severity (`critical`/`high`/`medium`/`low`) uses the fixed **status**
  palette, never the categorical one — type (identity) and severity
  (state) are deliberately two different color channels so a bar's color
  never has to do double duty.
- The hourly-distribution chart is a single metric (count) over an ordered
  axis, so it's sequential-blue, not categorical — and deliberately plots
  only `actual_count`, not `predicted_count`, since the latter is literally
  `actual_count * 1.05` (see `core/forecast.py`) and showing it as a second
  series would imply forecasting precision that doesn't exist.

Light/dark theming follows the dataviz skill's convention: CSS custom
properties in `index.css` under `:root`, a `@media (prefers-color-scheme:
dark)` block, and a `:root[data-theme="dark"]` override for a future manual
toggle (not built — there's no toggle UI yet, only OS-level dark mode is
wired up). The Leaflet base tiles switch between CartoDB's `light_all`/
`dark_all` tile sets based on the same `prefers-color-scheme` signal
(`MapView.jsx`'s `useIsDark`).
