# Portfolio Demo Guide

This project is easiest to present as a local product demo rather than a hosted SaaS.

## Recommended Demo Flow

1. Start the control panel:

```bash
./scripts/start_local_control_panel.sh
```

2. Open:

```text
http://127.0.0.1:8000
```

3. Register a fresh account.

4. Show the setup and readiness checks.

5. Run one of the prompts below.

6. Open the run detail page and show:

- stage timeline
- live log updates
- artifact list
- generated app download

7. Stop the demo services:

```bash
./scripts/stop_local_control_panel.sh
```

## Best Demo Prompts

### CRM

```text
Build a CRM for a small sales team that needs leads, deals, account notes, follow-up tasks, and weekly pipeline reviews.
```

Why this works:
- easy to understand quickly
- strong fit for the generator
- good entity/workflow coverage

### Booking Platform

```text
Build a booking platform for personal trainers with client profiles, session scheduling, package tracking, and availability views.
```

Why this works:
- visually clear family-specific behavior
- shows scheduling-focused generation

### Support Desk

```text
Build a support desk for a SaaS company that needs tickets, escalations, SLA tracking, customer updates, and agent workload views.
```

Why this works:
- strong workflow language
- easy to narrate in a portfolio review

### Recruiting Platform

```text
Build a recruiting platform for a startup hiring team with candidates, interview stages, feedback tracking, and offer pipeline visibility.
```

Why this works:
- demonstrates a different domain pack
- good for showing family-specific business actions

## Portfolio Tips

- Keep one funded `OPENAI_API_KEY` ready before the demo.
- Prefer one polished prompt over many weak ones.
- Record a short screen capture after a successful run.
- Include screenshots of:
  - login/dashboard
  - run detail page
  - generated app output

## Demo Checklist

- `OPENAI_API_KEY` is valid and funded
- no old web/worker process is still bound
- browser opens `http://127.0.0.1:8000`
- one reliable prompt is copied and ready
- logs are visible in case the interviewer asks how failures are handled
