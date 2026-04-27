# DS-160 Agent Quickstart

## Purpose

- `app/intake.html`: collect full dossier data via manual input; export final JSON for execution.
- `app/ds160-assistant.html`: import JSON and autofill DS-160 via local FastAPI + Chrome CDP.

## Runtime Contract

- Python 3.10+
- Chrome/Chromium installed
- macOS or Ubuntu
- FastAPI service: `http://127.0.0.1:8765`
- Chrome remote debugging: `9222`

## Install

macOS / Ubuntu:

```bash
cd /path/to/amercican_visa
bash scripts/install-deps.sh
source .venv/bin/activate
```

Windows PowerShell:

```powershell
cd \path\to\amercican_visa
.\scripts\install-deps.ps1
.\.venv\Scripts\Activate.ps1
```

- If `uv` is installed, the script uses it.
- If `uv` is not installed, the script falls back to `python -m venv` + `pip`.
- Runtime server dependencies are defined in `requirements.txt`.

## Start

macOS / Ubuntu:

```bash
bash scripts/start.sh
```

Windows PowerShell:

```powershell
.\scripts\start.ps1
```

## Stop

macOS / Ubuntu:

```bash
bash scripts/stop.sh
```

Windows PowerShell:

```powershell
.\scripts\stop.ps1
```

## Data Contract

- Intake UI works directly with the full dossier schema.
- Exported/downloaded JSON is a full dossier, e.g. `china-b1b2-dossier.json`.
- Assistant accepts full dossier JSON only.
- Offline intake mode still exports the same full dossier structure locally.

## Happy Path

1. Run start script.
2. Use `app/intake.html`.
3. Fill manually.
4. Export JSON.
5. Open `app/ds160-assistant.html`.
6. Import same JSON.
7. Navigate DS-160 in Chrome.
8. Click fill/save page by page.

## Key Files

- `scripts/install-deps.sh`
- `scripts/install-deps.ps1`
- `scripts/start.sh`
- `scripts/start.ps1`
- `scripts/stop.sh`
- `scripts/stop.ps1`
- `app/intake.js`
- `app/ds160-assistant.js`
- `src/visa_agent/server.py`
- `src/visa_agent/dossier_contract.py`
- `src/visa_agent/browser/live_form_fill.py`
- `docs/dossier.schema.json`
- `sample_data/china_b1b2_fake_test.json`
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
bash scripts/start.sh
```

If autofill fails:

- confirm Chrome is on a supported DS-160 page
- inspect assistant review/blocked fields
- check browser console and server logs
