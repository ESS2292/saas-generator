# Architecture

This document explains the current system shape of `saas-generator` at a level that is useful for demos, code reviews, and hiring conversations.

## High-Level Goal

The product takes a user prompt and turns it into a verified, downloadable full-stack starter app.

It is intentionally not a raw “LLM writes arbitrary files” system. The architecture is built around:

- controlled app-family classification
- structured manifest generation
- deterministic scaffold rendering
- targeted repair
- runtime verification
- authenticated product UX around the generation workflow

## System Shape

```text
User Browser
  |
  v
FastAPI Control Panel (web_app.py)
  |
  +--> auth/session handling
  +--> run creation and status APIs
  +--> settings, secrets, downloads
  +--> readiness and provider checks
  +--> SSE run streaming
  |
  v
Control Panel Store (memory/control_panel_store.py)
  |
  +--> users
  +--> sessions
  +--> runs
  +--> jobs
  +--> logs
  +--> artifacts
  +--> secrets
  +--> worker heartbeats
  |
  v
Worker Process (control_panel_worker.py)
  |
  v
Job Runner (engine/control_panel_jobs.py)
  |
  v
Generation Pipeline (engine/pipeline.py)
  |
  +--> intake analysis
  +--> spec refinement
  +--> plan/code generation
  +--> manifest normalization
  +--> project building
  +--> targeted repair
  +--> backend runtime verification
  +--> frontend build/preview verification
  |
  v
generated_apps/<run_id or prompt-derived folder>
```

## Main Components

### 1. Control Panel

Primary files:

- [`web_app.py`](./web_app.py)
- [`memory/control_panel_store.py`](./memory/control_panel_store.py)
- [`control_panel_worker.py`](./control_panel_worker.py)
- [`engine/control_panel_jobs.py`](./engine/control_panel_jobs.py)

Responsibilities:

- authenticate users
- create and track runs
- store logs and artifacts
- show readiness status
- stream run updates live
- expose generated-app downloads

Why it matters:

This turns the generator from a script into a product-shaped system.

### 2. Intake and Spec Layer

Primary files:

- [`engine/intake.py`](./engine/intake.py)
- [`engine/spec_refiner.py`](./engine/spec_refiner.py)

Responsibilities:

- classify the prompt into a supported app family
- determine support tier and closest family
- expand vague product ideas into a more useful build brief

Why it matters:

This reduces ambiguity before generation and makes the system more reliable than direct prompt-to-code output.

### 3. Manifest Layer

Primary files:

- [`engine/generate_code.py`](./engine/generate_code.py)
- [`engine/manifest.py`](./engine/manifest.py)
- [`templates/families.py`](./templates/families.py)

Responsibilities:

- ask the model for a strict manifest
- normalize and validate the manifest
- apply family defaults and planners
- enforce product boundaries

Why it matters:

The manifest is the contract between model output and deterministic code generation.

### 4. Rendering Layer

Primary files:

- [`engine/project_builder.py`](./engine/project_builder.py)
- [`templates/scaffold.py`](./templates/scaffold.py)
- [`templates/renderers.py`](./templates/renderers.py)
- [`templates/family_extensions/`](./templates/family_extensions)

Responsibilities:

- turn the manifest into backend/frontend files
- emit shared modules and family-specific modules
- generate deployment artifacts

Why it matters:

This keeps the output template-driven and testable instead of trusting raw model codegen for every file.

### 5. Repair and Verification Layer

Primary files:

- [`engine/repair.py`](./engine/repair.py)
- [`engine/runtime_verifier.py`](./engine/runtime_verifier.py)
- [`engine/frontend_verifier.py`](./engine/frontend_verifier.py)
- [`engine/provider_health.py`](./engine/provider_health.py)

Responsibilities:

- perform deterministic artifact repair
- verify generated backend runtime
- verify generated frontend build and preview/static output
- fail early when provider access is not usable

Why it matters:

This is where the project moves beyond “generation worked” into “generated output is at least minimally credible.”

## Request Lifecycle

1. User logs into the control panel.
2. User submits a prompt.
3. Web app checks provider readiness.
4. Run and job are persisted.
5. Worker claims the job.
6. Intake and spec refinement shape the request.
7. Model produces a strict manifest.
8. Manifest is normalized and expanded.
9. Renderer emits a generated app.
10. Repair layer rewrites broken or missing artifacts if needed.
11. Verification runs against generated output.
12. Logs, artifacts, and summary are stored for the run detail page.

## Data Model

The control panel store currently tracks:

- users
- sessions
- stored secrets
- runs
- jobs
- run logs
- run artifacts
- worker heartbeats

Backends:

- local default: SQLite
- hosted-ready option: Postgres

## Why The System Is Split Into Web And Worker

The web app is responsible for:

- user interaction
- auth
- queueing
- status visibility

The worker is responsible for:

- CPU/time-heavy generation flow
- file generation
- verification
- long-running tasks

This separation avoids tying job execution to request/response lifecycle and is closer to a real product architecture.

## Known Boundaries

This is a strong family-based app generator, not a universal software compiler.

It is best at:

- business apps
- workflow-heavy internal tools
- CRUD-heavy SaaS starters
- role-aware dashboards

It is not yet best at:

- highly bespoke consumer apps
- deeply real-time systems
- infra-heavy multi-service platforms
- arbitrary one-shot product generation with no family fit

## What To Show In A Demo

If you are presenting the architecture, focus on:

- why the manifest layer exists
- why repair happens before retry
- why the control panel is separated from the worker
- how verification protects against obviously broken generated output

That tells a much stronger engineering story than simply saying “an LLM builds apps.”
