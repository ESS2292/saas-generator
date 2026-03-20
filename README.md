# SaaS Generator

`saas-generator` is a prompt-driven app and SaaS generator with a browser-based control panel.

It takes a product idea, classifies it into a supported app family, expands that into a structured manifest, generates a full-stack starter app, verifies the output, and exposes the whole flow through an authenticated web UI.

## What It Does

- Accepts prompts through a web control panel or CLI
- Refines vague prompts into a more structured build brief
- Maps requests into supported product families
- Generates a backend, frontend, schema, and deployment artifacts
- Verifies generated apps with runtime and build checks
- Stores runs, logs, artifacts, quotas, and settings in a control-panel database
- Processes generation jobs through a separate worker service

## Current Product Shape

The repo is split into two main layers:

1. Generator pipeline
- intake and spec refinement
- family-based manifest normalization
- scaffold generation
- deterministic repair
- backend/frontend verification

2. Control panel
- authenticated browser UI
- queued runs
- provider checks
- settings and secrets
- run detail pages
- download/export actions

## Main Entry Points

- Web control panel: [`web_app.py`](./web_app.py)
- Worker service: [`control_panel_worker.py`](./control_panel_worker.py)
- CLI entry: [`main.py`](./main.py)
- Pipeline orchestration: [`engine/pipeline.py`](./engine/pipeline.py)

## Supported App Families

The generator is strongest on business-app and workflow-heavy products such as:

- CRM
- support desk
- project management
- booking platform
- marketplace
- ecommerce
- internal tools
- recruiting
- inventory management
- finance ops
- learning platform
- content platform
- social app

This is not a universal generator for arbitrary software, but it is designed to generate a broad set of family-based SaaS starters reliably.

## Local Setup

### 1. Create and use the virtual environment

This repo expects the checked-in local environment at `agent-env/`.

If you already have it:

```bash
source agent-env/bin/activate
```

### 2. Install dependencies if needed

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a local `.env` file with at least:

```env
OPENAI_API_KEY=your_openai_api_key
```

Optional but recommended for the control panel:

```env
CONTROL_PANEL_SECRET_KEY=replace_this_with_a_real_secret
CONTROL_PANEL_DATABASE_URL=sqlite:///memory/control_panel.db
```

For hosted deployments, `CONTROL_PANEL_DATABASE_URL` should point to Postgres.

## Running The Product Locally

### Control panel web service

```bash
./agent-env/bin/uvicorn web_app:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

### Worker service

Run this in a second terminal:

```bash
./agent-env/bin/python control_panel_worker.py
```

The web service queues jobs. The worker processes them.

### CLI mode

If you want the old terminal flow instead of the browser UI:

```bash
./agent-env/bin/python main.py
```

## Control Panel Features

The browser UI currently includes:

- login and registration
- first-run setup checks
- provider readiness checks
- prompt templates
- starter mode and advanced mode
- queued run creation
- run history with stage summaries
- run detail pages
- artifact and log access
- secret storage
- download/export for generated apps

## Provider Readiness

Before queueing a run, the control panel checks whether OpenAI generation is usable.

This catches common failures early, including:

- missing `OPENAI_API_KEY`
- invalid API key
- quota exhaustion
- provider connection issues

If the provider is not ready, the UI blocks queueing and shows the reason directly.

## Tests

Run the full suite:

```bash
./agent-env/bin/pytest -q
```

The repo includes tests for:

- manifest normalization
- scaffold generation
- family extensions
- repair logic
- runtime verification
- frontend verification
- control-panel behavior
- deployment artifact presence

## Deployment

Control-panel deployment artifacts live in [`deployment/`](./deployment):

- [`deployment/control-panel-docker-compose.yml`](./deployment/control-panel-docker-compose.yml)
- [`deployment/control-panel-render.yaml`](./deployment/control-panel-render.yaml)
- [`deployment/control-panel-railway.json`](./deployment/control-panel-railway.json)
- [`deployment/CONTROL_PANEL.md`](./deployment/CONTROL_PANEL.md)

The hosted architecture is:

- one web service
- one worker service
- one shared control-panel database

## Important Notes

- Generated-app quality depends on a valid OpenAI API key and available quota.
- Verification paths may require Docker and Node/npm locally.
- The control panel is production-shaped, but some infrastructure concerns still belong on the roadmap, such as streaming run updates, stronger secrets management, and richer hosted ops.

## Recommended Next Steps

If you are continuing development, the highest-value areas are:

- live progress streaming in the control panel
- stronger hosted secret management
- deeper family-specific business logic
- richer generated app editing after initial generation
