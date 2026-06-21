# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to semantic versioning where practical.

## [Unreleased]

### Added

- Added visual evidence capture for unhealthy DOM drift checks, including CDP screenshots saved under the local `.ds160/visual-evidence/` workspace.
- Added `visa_agent.automation` as a dedicated automation core package.
- Added `DS160AutomationCore` to coordinate browser availability checks, page resolution, page filling, checkpoint updates, and audit logging outside the FastAPI route layer.
- Added a lightweight MaaFramework-inspired task pipeline runtime with `action`, `recognition`, `next`, and `on_error` node flow semantics.
- Added a reusable `VisualEvidenceStore` for future screenshot, OCR, template-match, and failure-evidence workflows.
- Added tests for the automation pipeline, automation core orchestration, CDP screenshot writing, and DOM drift evidence capture.

### Changed

- Refactored `/fill-page` and `/fill-and-continue` server endpoints to delegate DS-160 browser automation to `DS160AutomationCore`.
- Moved visual evidence path generation out of DOM drift detection and into the shared evidence store.
- Reduced fill orchestration responsibilities in `server.py`, leaving FastAPI routes focused on HTTP request/response adaptation.
- Updated frontend drift-check logging to show the saved visual evidence path when selector drift is unhealthy.

### Fixed

- Fixed DOM drift checks calling `find_target_websocket_url` without a URL substring by allowing the CDP target lookup helper to default to any debuggable target.
- Fixed drift warning audit entries to include the saved visual evidence path when available.
