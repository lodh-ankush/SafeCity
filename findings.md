# SafeCity AI — Project Findings (analysis reference)

Date: 2026-07-19. No git repo exists yet (`git init` not run). This file is a
working analysis document, not user-facing documentation — see `CLAUDE.md`
for the file meant to guide future coding work.

> **Update (same day, later session):** the gaps below — no ingestion API,
> CSV storage, dead text-modality voting — were closed. See "2026-07-19
> update: ingestion wired end-to-end" at the bottom of this file for what
> changed and what was verified by actually running it. The sections below
> are kept as-written (historical record of the state before that work).

## What actually exists today

**Only a Python backend exists.** No frontend, no `package.json`, no
`/frontend` — confirmed with the user this is simply not built yet (not
missing/misplaced).

```
backend/
  main.py                       FastAPI app + WebSocket alert stream
  api/routes.py                 REST endpoints (all read-only, CSV-backed)
  core/
    config.py                   thresholds, fusion weights, label maps, paths
    db.py                       CSV read/write helpers (the only "database")
    schemas.py                  ModalityResult / Incident dataclasses
    fusion.py                   weighted multimodal voting -> Incident
    alerts.py                   AlertQueue: threshold + dedupe + suppression
    forecast.py                 stats over incidents_fused.csv (no real ML)
    utils.py                    timestamp, sigmoid calibration, jaccard, haversine
  pipelines/
    video_pipeline.py           HF video-classification (videomae-kinetics)
    audio_pipeline.py           HF audio-classification (AST audioset)
    text_pipeline.py            HF text-classification (bert emotion model)
    summarization_pipeline.py   HF summarization (bart-large-cnn), lazy-loaded
  seed_demo_data.py             generates ~80 synthetic incidents around
                                 Bhubaneswar for events.csv / incidents_fused.csv
  requirements.txt

safecity_env/                   Python 3.13 venv (Scripts/, Lib/site-packages/)
                                 ALSO contains the pre-refactor first draft:
                                 core/, pipelines/, safecity_pipeline.py,
                                 events.csv, incidents_fused.csv, and the only
                                 real sample data files (data/audio/siren.wav,
                                 data/sample_videos/traffic.mp4,
                                 data/text/sample_reports.txt).
                                 Confirmed with user: legacy/scratch, backend/
                                 is the current source of truth. Its data/
                                 files are still the only real sample inputs
                                 in the repo — nothing under backend/ has
                                 sample media.

run_safecity.bat                activates safecity_env and runs the OLD
                                 safecity_env/safecity_pipeline.py — this
                                 script targets the legacy tree, not backend/.
```

## Architecture as it actually works (not as diagrams would suggest)

Two pieces exist, and **they are not wired together**:

1. **Offline/batch ML pipeline** (`safecity_pipeline.py` in the legacy tree,
   mirrored conceptually by `backend/pipelines/*`): loads three separate
   HuggingFace pipelines (video/audio/text), runs each once against a
   hardcoded sample file, fuses the three results via `core/fusion.py`
   (weighted vote by label, confidence gated per-modality, sigmoid-calibrated),
   pushes through `core/alerts.py` (score threshold + time/type dedupe via
   Jaccard text similarity + per-type cooldown), and appends accepted
   incidents to `incidents_fused.csv` via `core/db.py`.

2. **FastAPI dashboard backend** (`backend/main.py` + `backend/api/routes.py`):
   purely reads `events.csv` / `incidents_fused.csv` and serves aggregates
   (`/api/stats`, `/api/forecast`, `/api/map/incidents`, etc.) plus a
   WebSocket (`/ws/alerts`) that **replays existing CSV rows on a random
   8–20s timer** relabeled `is_live: true` — it does not consume a live
   pipeline. There is no POST/ingest endpoint anywhere; the API is read-only.

**The two halves currently connect only through shared CSV files on disk.**
`backend/pipelines/*.py` (video/audio/text) are standalone scripts with
`if __name__ == "__main__"` blocks — nothing in `backend/main.py` or
`api/routes.py` imports or calls them. They are not run by the FastAPI app,
not scheduled, and not triggered by any request.

**In practice, the demo runs entirely on `seed_demo_data.py` output** — the
80 synthetic incidents — not on real model inference. That's the only way
`backend/incidents_fused.csv` gets populated today, since `backend/` has no
`data/` directory (the sample media only exists under `safecity_env/data/`,
and the pipeline scripts default to relative paths like
`"data/sample_videos/traffic.mp4"` that don't resolve from `backend/`).

## Notable gaps / things a future contributor should know

- **No orchestration layer.** Nothing calls `fuse()` + `AlertQueue.push()` +
  `log_incident()` in response to new video/audio/text input arriving. The
  legacy `safecity_pipeline.py` does this once, synchronously, for one
  hardcoded file per modality, then exits.
- **No ingestion API.** No endpoint accepts an uploaded video/audio file or
  text report and runs it through the pipelines. `python-multipart` is in
  `requirements.txt` (implies file upload was planned) but no route uses it.
- **"Forecasting" (`core/forecast.py`) is descriptive statistics**, not a
  trained/learned time-series model: hour-of-day histograms, day-of-week
  averages, a two-half rate comparison for trend direction, and geo
  rounding-based clustering for "risk zones." No ML.
- **No persistent database.** `core/db.py` is CSV append/read. No
  concurrency control — `main.py`'s WebSocket loop and any future
  ingest-triggered writes would race on the same file with no locking.
- **No tests, no linter config, no CI.** Nothing to run beyond manually
  exercising the scripts/API.
- **`backend/pipelines/*.py` reference relative sample paths** that don't
  exist under `backend/` — running them as-is (`python pipelines/video_pipeline.py`
  from `backend/`) will fail to find `data/sample_videos/traffic.mp4` unless
  a `backend/data/` tree is created (e.g. copied from `safecity_env/data/`)
  or the path argument is overridden.
- **`safecity_env/` (the venv + legacy draft) is currently sitting inside the
  project folder with no `.gitignore` at the repo root** — since there's no
  git repo yet, nothing is tracked either way, but this is worth deciding on
  before `git init` (the venv alone is large: torch, transformers, torchvision
  etc.).

## Relation to the phased plan the user shared

(Recorded as context only, per the user's instruction not to treat it as a
command.)

- **Phase 1 (ingestion pipeline + baseline classification)**: partially
  present as three independent HF `pipeline()` scripts per modality, but
  each processes exactly one hardcoded file and there's no real "ingestion"
  (no API, no folder-watch, no queue).
- **Phase 2 (multimodal fusion + real-time alert ranking)**: the fusion
  math and `AlertQueue` ranking/dedupe logic exist and look reasonably
  thought-out (weighted vote, sigmoid calibration, Jaccard-based dedupe,
  per-type cooldown) — but it's exercised only by the legacy one-shot
  script, not by anything real-time.
- **Phase 3 (dashboard: incident feed, map overlay, summarization)**: the
  *API surface* for this exists (`/api/incidents`, `/api/map/incidents`,
  `/api/stats`, a summarization pipeline module) but confirmed with the user
  there is **no dashboard/frontend built** — Phase 3's consuming UI doesn't
  exist in this repo yet. Also, `summarization_pipeline.py` is written but
  not called anywhere (not from fusion, not from any route) — incidents'
  `summary` field is currently only populated by `seed_demo_data.py`'s
  canned text, not by the BART summarizer.
- **Phase 4 (forecasting + demo polish)**: `/api/forecast` exists and is
  wired into the API; as noted above it's rule-based statistics rather than
  a trained forecasting model, which may be fine for an MVP demo but is
  worth naming accurately rather than calling it "forecasting."

## Open questions / decisions still needed (not yet asked or already resolved)

Resolved with user already:
- No frontend exists yet — confirmed not-started, not missing.
- `safecity_env`'s core/pipelines/safecity_pipeline.py is legacy/scratch;
  `backend/` is the source of truth.

Still open (not yet raised with user, worth asking before deeper work):
- Should `backend/pipelines/*` be wired into an ingestion API (accepting
  uploads and running fuse+alert+log synchronously or via a background
  task), or is the CSV-seeded read-only dashboard the actual near-term
  target?
- Is CSV intended to remain the storage layer, or is a real DB (SQLite/etc.)
  in scope soon — relevant because of the write-concurrency gap noted above.
- Should `safecity_env/data/*` sample files be copied into `backend/data/`
  so the pipeline scripts are actually runnable from the current codebase?

---

## 2026-07-19 update: ingestion wired end-to-end

Resolved via `AskUserQuestion` before implementing (answers baked into the
design below): ingestion accepts **precomputed per-modality scores** (not
raw file uploads — pipeline scripts stay standalone, feeding this endpoint);
`events.csv` dry-run replays as-is (video just won't contribute, since the
file has no video rows); accepted incidents **broadcast live** on
`/ws/alerts`, replacing the old fake random-replay simulation; storage
**moved to SQLite**; BART summarization wiring was left out for now (not
explicitly requested).

### What changed

- `backend/core/db.py` rewritten around `sqlite3` (`backend/safecity.db`,
  WAL mode) instead of CSV — same dict shapes returned, so `api/routes.py`
  needed no changes to its existing read logic.
- `backend/core/forecast.py` now reads via `core/db.read_incidents()`/
  `read_events()` instead of opening the CSVs directly.
- `backend/seed_demo_data.py` now inserts into SQLite via `core/db.py`
  instead of writing CSV files.
- `backend/core/fusion.py`: fixed a real bug — `normalize_label()` for text
  was matching `TEXT_KEYWORDS` (content words like `"fire"`, `"gunshot"`)
  against the **emotion classifier's label** (`"fear"`, `"NEGATIVE"`, ...)
  instead of the raw report text, so text could never contribute anything
  but `"unknown"` to fusion voting. Confirmed with the user before fixing:
  it now takes an explicit `text_content` argument and matches against that,
  falling back to `"unknown"` when no raw text is supplied.
- `backend/core/ws_manager.py` (new): `ConnectionManager` moved out of
  `main.py` so `api/routes.py` can broadcast to it too, without a circular
  import.
- `backend/api/routes.py`: new `POST /api/ingest` — accepts a
  `{video?, audio?, text?, lat?, lon?, timestamp?}` bundle, runs
  `fuse()` → `AlertQueue.push()` (module-level singleton, persists for the
  process lifetime) → `log_incident()`/`log_event()`, and broadcasts
  accepted incidents to `manager`.
- `backend/main.py`: `/ws/alerts` no longer replays historical CSV rows on
  a random timer pretending to be live — it just holds the connection open;
  all traffic now comes from real `/api/ingest` broadcasts.
- `backend/scripts/replay_events_csv.py` (new): groups `safecity_env/events.csv`
  rows into incident bundles by timestamp proximity and POSTs them to a
  running server's `/api/ingest`, for exercising the pipeline against real
  historical data without needing model weights.
- Root `.gitignore` added (venv, `__pycache__`, `*.db*`, `*.log`) since the
  app now generates real local state.

### A structural finding from actually running it (not a bug fix — a config fact)

Replaying `safecity_env/events.csv` end-to-end produced **zero accepted
incidents** — all 9 grouped bundles came back `below_threshold`. This isn't
a wiring problem; it's math. `fuse()` splits votes by normalized type, each
modality's sigmoid-calibrated confidence saturates around ~0.88 even at a
raw score of 1.0, and weights are `W_VIDEO=0.45 / W_AUDIO=0.35 / W_TEXT=0.20`
against `ALERT_MIN=0.55`. Consequences, confirmed by manual `/api/ingest`
tests with synthetic payloads:

- No single modality can ever clear `ALERT_MIN` alone (max ≈ `0.45×0.88 = 0.40`).
- Audio+text alone — the *only* combination `events.csv` can ever produce,
  since it has no video rows — tops out at ≈ `(0.35+0.20)×0.88 = 0.48`,
  **structurally always under threshold**, regardless of how confident the
  classifiers are.
- Only video+audio, video+text, or all three agreeing on the same
  normalized type can clear 0.55. Verified: video `"car crash"` (0.99) +
  text containing `"accident"` (0.99) → accepted at `fused_score=0.57`.
  Verified duplicate suppression on immediate replay of the same payload.
  Verified video `"driving car"` + audio `"car horn"` (both → `"traffic"`)
  → accepted at `0.666`, and the WebSocket client received the live
  broadcast within the same request/response cycle.
- Separately: **no audio or video label maps to `"fire"`** in
  `AUDIO_LABEL_MAP`/`VIDEO_LABEL_MAP` (`core/config.py`) — only
  `TEXT_KEYWORDS` can produce `"fire"`, and text alone can never reach
  threshold. So `"fire"` — which has full display metadata in
  `INCIDENT_TYPES` (color, icon, severity) — is currently **unreachable**
  as an accepted incident type under any input, not just this dataset.

This is a real design tension between `ALERT_MIN`/weights and what
`INCIDENT_TYPES` promises the dashboard can show. Flagged for the user;
not changed unilaterally, since threshold/weight tuning is a product
decision (the config file's own comment says "tune later").

### Also discovered while testing (environment, not code)

- `websockets` was listed in `requirements.txt` but never actually
  installed in `safecity_env` — `/ws/alerts` would fail at the transport
  level (not an import error) until it was installed. Now installed.
- `seed_demo_data.py` (and the pipeline scripts) print emoji, which raises
  `UnicodeEncodeError` on a default Windows `cp1252` console. Workaround:
  `PYTHONIOENCODING=utf-8`. Not fixed in source (cosmetic, out of scope of
  the ingestion work), just documented in `CLAUDE.md`.

### Verified end-to-end (this session)

Server started cleanly (`python main.py`, no heavy ML imports at
startup/request time since ingest takes precomputed scores) → seeded 80
demo incidents into SQLite → `/api/stats`, `/api/forecast`,
`/api/map/incidents`, `/api/incidents` all reflected seeded data correctly
→ reset DB → replayed `events.csv` (all correctly rejected, as explained
above) → manually POSTed synthetic payloads through all `AlertQueue` paths
(accept / below_threshold / duplicate) → confirmed live WebSocket delivery
on acceptance. Test artifacts (log files, temporary `safecity.db`) cleaned
up; a demo-seeded `safecity.db` was left in place as the ready-to-explore
state.

---

## 2026-07-19 update: VIDEO_LABEL_MAP had unreachable entries

User asked whether swapping in a newer/better sample video would help clear
`ALERT_MIN` without retuning weights. Rather than speculate, ran the real
video model (`MCG-NJU/videomae-base-finetuned-kinetics`, already cached) on
the actual sample (`safecity_env/data/sample_videos/traffic.mp4`) and pulled
its full label vocabulary via `AutoConfig.from_pretrained(...).id2label`.

Findings:
- The sample classifies confidently as `"driving car"` (57.3%), which *does*
  map correctly to `traffic`.
- But `VIDEO_LABEL_MAP` (`core/config.py`) had two entries that can **never**
  match, on any video, because the strings aren't in the model's actual
  400-class Kinetics vocabulary at all: `"car crash"` (Kinetics-400 has no
  crash/collision/accident class whatsoever — it's a general human-action
  dataset, not a hazard classifier) and `"riding bicycle"` (real classes are
  `"riding a bike"` / `"riding mountain bike"`, neither contains that
  substring). So no new sample video, however good, could ever make
  `"accident"` reachable via video — that's a config bug, not a data
  quality problem.
- Checked the full 400-label list for genuinely usable alternatives instead
  of forcing weak proxies. Found one real fire-adjacent class,
  `"extinguishing fire"`, worth mapping to `fire` — this is the first path
  by which `fire` becomes reachable at all (previously only `TEXT_KEYWORDS`
  could produce it, and text alone can never clear `ALERT_MIN`). For
  `violence_suspected`, replaced the misleading `"running"` (only matches
  `"running on treadmill"` — a gym activity, not violence) with actual
  altercation-resembling actions: `"punching person"`, `"sword fighting"`,
  `"slapping"`, `"headbutting"`.
- Deliberately excluded `"wrestling"` despite being a real class, because
  the matching in `fusion.normalize_label()` is substring-based and
  `"wrestling"` is *also* a substring of the unrelated real class `"arm
  wrestling"` — would have caused a friendly game to register as a
  violence signal. Verified this and every other key programmatically
  against the full label list (each now matches exactly one real label,
  1:1) rather than trusting manual inspection.
- `"accident"` and `"emergency"` remain structurally unreachable via video
  — not something fixable by better footage; would need a different model
  trained on hazard/incident concepts, which Kinetics-400 (built for
  general action recognition — sports, chores, daily activities) simply
  isn't.
- Not yet touched: `seed_demo_data.py`'s cosmetic `video_labels` lists
  still contain `"car crash"`/`"riding bicycle"` as flavor text for the
  synthetic demo. Harmless (seeding sets `type` directly, bypassing
  `fuse()` entirely) but now inconsistent with what the real pipeline could
  ever produce — flagged, not fixed, since it doesn't affect functional
  correctness and wasn't asked for.

---

## 2026-07-19 update: frontend built, both servers running end-to-end

User asked to "turn on the backend and frontend respectively and implement
it" — no frontend existed yet (confirmed earlier in this file), so this was
building Phase 3 (incident feed, map overlay) from scratch, not turning on
something already there. Asked two clarifying questions first: stack (chose
React+Vite over a no-build static page) and map library (chose Leaflet+OSM
over Google Maps/Mapbox, since no API key exists anywhere in the project).

**Backend color config changed as a side effect of building the frontend.**
`INCIDENT_TYPES` in `core/config.py` (color field) previously held arbitrary
hex values never validated for colorblind-safety. Building the map view
required picking real colors, so ran them through the `dataviz` skill's
`validate_palette.js` rather than eyeballing — see the CLAUDE.md "Frontend"
section for the actual results (4 hues pass the map's all-pairs CVD check,
not 5; semantically "obvious" choices like red-for-fire failed the
normal-vision floor). Updated backend's `INCIDENT_TYPES` hex values to match
what the frontend actually renders, so the API and the UI tell the same
story instead of the color field being a vestigial, ignored duplicate.

**Verified end-to-end without `claude-in-chrome`** (user had started
installing it but deferred; harness confirmed not to suggest it again this
session). Fell back to: `npm run build` + `npm run lint` (clean) to catch
compile/import errors, then installed Playwright's Chromium headless shell
(`npx playwright install chromium`, ~115MB, network already confirmed
working) for actual rendered screenshots — light mode, dark mode (OS
`prefers-color-scheme` switch confirmed working, including the Leaflet tile
layer swapping to CartoDB dark tiles), and a live-update test: opened the
page, POSTed a real `/api/ingest` payload (`extinguishing fire` video +
text containing `"fire"`/`"smoke"` — deliberately chosen to exercise the
`VIDEO_LABEL_MAP` fix from the previous session) from outside the browser
context, and confirmed the stat tiles, incidents-by-type chart, and feed all
updated live with no page refresh — first real end-to-end proof that a
`fire`-type incident can be accepted (`fused_score=0.558`), not just a
theoretical consequence of the earlier config fix.

Also confirmed: `websockets` connection auto-reconnects on backend restart
(3s backoff in `useLiveAlerts.js`) — relevant since dev workflow restarts
the backend frequently.

Both dev servers were left running (backend :8000, frontend :5173) per the
literal "turn on" ask, rather than stopped after verification like prior
sessions' test servers.
