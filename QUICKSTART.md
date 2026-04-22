# DS-160 Agent Quickstart

## Purpose

- `app/intake.html`: collect intake data from images/manual input; export final JSON for execution.
- `app/ds160-assistant.html`: import JSON and autofill DS-160 via local FastAPI + Chrome CDP.

## Runtime Contract

- Python 3.10+
- Chrome/Chromium installed
- macOS or Ubuntu
- FastAPI service: `http://127.0.0.1:8765`
- Chrome remote debugging: `9222`

## Install

```bash
cd /path/to/amercican_visa
uv venv && source .venv/bin/activate && uv pip install fastapi uvicorn
```

Optional for vision intake:

```bash
export VISION_MODEL_API_KEY=...
export VISION_MODEL_NAME=...
export VISION_MODEL_BASE_URL=...
```

## Start

macOS:

```bash
bash scripts/start-mac.sh
```

Ubuntu:

```bash
bash scripts/start-ubuntu.sh
```

Server only:

```bash
bash scripts/start-server.sh
```

Manual split:

```bash
bash scripts/start-chrome-debug.sh
bash scripts/start-server.sh
```

Ubuntu manual Chrome:

```bash
bash scripts/start-chrome-debug-ubuntu.sh
```

Stop macOS local processes:

```bash
bash scripts/stop-mac.sh
```

## Data Contract

- Intake UI internally works with `intake-v1` fields.
- Exported/downloaded JSON is dossier-shaped by default, e.g. `china-b1b2-dossier.json`.
- Assistant accepts both:
  - `intake-v1` JSON
  - full dossier JSON
- If assistant receives `intake-v1`, backend converts it to dossier before building draft bundle.
- Offline intake mode still exports dossier-shaped JSON locally.

## Happy Path

1. Run start script.
2. Use `app/intake.html`.
3. Upload docs or fill manually.
4. Export JSON.
5. Open `app/ds160-assistant.html`.
6. Import same JSON.
7. Navigate DS-160 in Chrome.
8. Click fill/save page by page.

## Key Files

- `scripts/start-mac.sh`
- `scripts/start-ubuntu.sh`
- `scripts/start-server.sh`
- `scripts/start-chrome-debug.sh`
- `scripts/start-chrome-debug-ubuntu.sh`
- `app/intake.js`
- `app/ds160-assistant.js`
- `src/visa_agent/server.py`
- `src/visa_agent/intake.py`
- `src/visa_agent/browser/live_form_fill.py`
- `sample_data/intake_v1_sample.json`
- `sample_data/china_b1b2_sample.json`

## Verify

Service up:

```bash
curl http://127.0.0.1:8765/status
```

Tests:

```bash
PYTHONPATH=src python -m pytest tests/test_intake.py tests/test_mapping.py tests/test_draft_bundle.py
```

## Troubleshooting

CDP not reachable:

```bash
lsof -i :9222
pkill -f "remote-debugging-port=9222"
```

Server not reachable:

```bash
lsof -i :8765
bash scripts/start-server.sh
```

If autofill fails:

- confirm Chrome is on a supported DS-160 page
- inspect assistant review/blocked fields
- check browser console and server logs
