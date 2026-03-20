# Control Panel Deployment

This repository now ships a hosted control-panel service on top of the generator pipeline.
The hosted topology is:

- `web_app.py` as the authenticated web/API surface
- `control_panel_worker.py` as the background run processor
- Postgres as the shared control-panel database

## Local Docker

```bash
docker compose -f deployment/control-panel-docker-compose.yml up --build
```

The app will be available at `http://127.0.0.1:8000`.

## Required Environment Variables

- `CONTROL_PANEL_SECRET_KEY`: master key for encrypting stored provider and deploy secrets
- `CONTROL_PANEL_DATABASE_URL`: SQLAlchemy database URL. In hosted environments this should point to Postgres.
- `OPENAI_API_KEY`: required for live generation runs

## Render

Use [`deployment/control-panel-render.yaml`](./control-panel-render.yaml) as the service blueprint. It provisions:

- one web service
- one worker service
- one Postgres database

## Railway

Use [`deployment/control-panel-railway.json`](./control-panel-railway.json) as the deployment manifest and add a second Railway service that runs:

```bash
python control_panel_worker.py
```
