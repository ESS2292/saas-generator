# SaaS Generator

`saas-generator` is a prompt-driven app generator with a browser-based control panel.

A user signs in, submits a product idea, the system classifies and refines the request, generates a full-stack starter app, verifies it, stores logs and artifacts, and exposes the whole run through an authenticated UI.

For hiring teams, the point of this project is not just "LLM generates code." The stronger signal is the surrounding product and systems work:

- web app + worker separation
- user-scoped runs and auth
- structured manifest generation instead of raw code dumping
- deterministic repair before model retries
- runtime and build verification
- portfolio-ready local product UX

## What This Project Shows

- full-stack product thinking, not just prompt engineering
- job orchestration and background processing
- pragmatic AI product boundaries
- verification and failure handling around generated output
- product UX for a technical workflow

## Demo First

If you want to see the project quickly, use the local demo flow:

```bash
./scripts/start_local_control_panel.sh
```

Then open:

```text
http://127.0.0.1:8000
```

Stop the demo services with:

```bash
./scripts/stop_local_control_panel.sh
```

For a portfolio walkthrough and demo-ready prompts, start here:

- [`PORTFOLIO_DEMO.md`](./PORTFOLIO_DEMO.md)
- [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## Screenshots And Demo Video

This repo is now set up well for portfolio presentation. The next thing to add is media.

Recommended additions:

1. Dashboard screenshot
   Suggested path: `docs/media/dashboard.png`

2. Run detail screenshot
   Suggested path: `docs/media/run-detail.png`

3. Generated app screenshot
   Suggested path: `docs/media/generated-app.png`

4. Short demo video or GIF
   Suggested path: `docs/media/demo.gif` or a linked video in the repo description

Suggested placements once you have them:

- Add the dashboard image near the top of this README
- Add the run detail image under the control panel section
- Add the generated app image under the portfolio demo section
- Add a short linked demo video near the “Demo First” section

## Product Overview

The product has two major layers.

1. Generator pipeline
- intake classification
- spec refinement
- manifest generation
- scaffold rendering
- deterministic repair
- backend/frontend verification

2. Control panel
- authentication
- user-scoped runs
- queued jobs
- provider readiness checks
- run detail pages with logs and artifacts
- live run streaming
- settings and secret storage

## Architecture

For a more detailed system walkthrough, see:

- [`ARCHITECTURE.md`](./ARCHITECTURE.md)

```text
Browser UI
  |
  v
web_app.py
  |
  +--> auth, runs, settings, downloads, readiness, SSE
  |
  v
control_panel_store.py
  |
  +--> users, sessions, runs, jobs, logs, artifacts, secrets
  |
  v
control_panel_worker.py
  |
  v
engine/control_panel_jobs.py
  |
  v
engine/pipeline.py
  |
  +--> intake.py
  +--> spec_refiner.py
  +--> generate_code.py
  +--> manifest.py
  +--> project_builder.py
  +--> repair.py
  +--> runtime_verifier.py
  +--> frontend_verifier.py
  |
  v
generated_apps/<run>
```

## End-To-End Flow

1. A signed-in user submits a prompt from the control panel.
2. The web app checks provider readiness and queues a run.
3. The worker claims the job and starts the generator pipeline.
4. The pipeline classifies the request into a supported app family.
5. The idea is refined into a more structured spec brief.
6. The model produces a strict manifest instead of arbitrary file output.
7. Local templates render the backend, frontend, schema, and deploy artifacts.
8. Deterministic repair rewrites or fixes artifacts before broad model retries.
9. Runtime verification checks the generated backend and frontend.
10. Logs, artifacts, and summary data are persisted for the control panel.
11. The run detail page updates live through SSE while the job is executing.

## Main Entry Points

- Web control panel: [`web_app.py`](./web_app.py)
- Worker service: [`control_panel_worker.py`](./control_panel_worker.py)
- CLI entry: [`main.py`](./main.py)
- Pipeline orchestration: [`engine/pipeline.py`](./engine/pipeline.py)
- Control-panel data layer: [`memory/control_panel_store.py`](./memory/control_panel_store.py)

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

This is intentionally not positioned as a universal app generator for arbitrary software. The product boundary is family-based generation with verification, which is a more credible and maintainable target.

## Engineering Decisions

### 1. Family-based generation instead of “generate anything”

I constrained the generator to supported app families because reliability matters more than broad claims. This makes the output easier to validate, repair, and explain.

### 2. Structured manifest instead of raw file parsing

The model produces a strict manifest that the local renderer consumes. That is more stable than trusting freeform model output to directly write project files.

### 3. Deterministic repair before model retry

The pipeline tries targeted artifact repair before falling back to another LLM pass. That reduces unnecessary churn and makes failures easier to reason about.

### 4. Separate web and worker processes

Queued job execution is isolated from the control panel web process. That is the right shape for a real product and makes the system easier to host and monitor.

### 5. Verification is a first-class part of generation

The project does not stop at “files were generated.” It verifies backend runtime and frontend build/preview before a run is considered successful.

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
- live run streaming
- artifact and log access
- secret storage
- download/export for generated apps

## Local Setup

### 1. Use the local virtual environment

This repo expects the checked-in environment at `agent-env/`.

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

Recommended for the control panel:

```env
CONTROL_PANEL_SECRET_KEY=replace_this_with_a_real_secret
CONTROL_PANEL_DATABASE_URL=sqlite:///memory/control_panel.db
```

For hosted deployment, `CONTROL_PANEL_DATABASE_URL` should point to Postgres.

## Running Locally

### One-command portfolio demo

```bash
./scripts/start_local_control_panel.sh
```

Then open:

```text
http://127.0.0.1:8000
```

### Manual mode

Web app:

```bash
./agent-env/bin/uvicorn web_app:app --host 127.0.0.1 --port 8000
```

Worker:

```bash
./agent-env/bin/python control_panel_worker.py
```

CLI:

```bash
./agent-env/bin/python main.py
```

## Provider Readiness

Before queueing a run, the control panel checks whether OpenAI generation is usable.

This catches common failures early, including:

- missing `OPENAI_API_KEY`
- invalid API key
- quota exhaustion
- provider connection issues

The control panel also exposes readiness and worker heartbeat information so a “web server is up” state is not confused with “the system is actually able to process runs.”

## Tests

Run the full suite:

```bash
./agent-env/bin/pytest -q
```

The repo includes coverage for:

- manifest normalization
- family planners and renderers
- scaffold generation
- deterministic repair
- backend runtime verification
- frontend build and preview verification
- control-panel behavior
- deployment artifact presence

## Deployment

The product is currently best demonstrated locally for portfolio use, but the repo also includes hosted deployment artifacts in [`deployment/`](./deployment):

- [`deployment/control-panel-docker-compose.yml`](./deployment/control-panel-docker-compose.yml)
- [`deployment/control-panel-render.yaml`](./deployment/control-panel-render.yaml)
- [`deployment/control-panel-railway.json`](./deployment/control-panel-railway.json)
- [`deployment/CONTROL_PANEL.md`](./deployment/CONTROL_PANEL.md)

Hosted topology:

- one web service
- one worker service
- one shared control-panel database

## Portfolio Framing

If you are presenting this project to companies, the strongest story is:

- you designed a bounded AI product instead of making unrealistic claims
- you built the surrounding product architecture, not just the model call
- you handled queueing, auth, persistence, verification, repair, and UX
- you made the system demoable and understandable

That is a stronger signal than simply saying “I built an AI app generator.”

## Recommended Next Improvements

If I were continuing this project for portfolio impact, I would prioritize:

- adding screenshots and a short demo video to the repo
- polishing one or two app families more deeply
- improving visual design in the control panel
- adding a lightweight architecture diagram image
- adding a full end-to-end mocked happy-path test
