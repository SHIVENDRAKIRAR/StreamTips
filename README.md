# StreamTips

Real-time tipping platform for streamers — see full plan in `docs/streamtips-project-plan.md`.

## Day 1 status: DB schema + JWT auth + creator profile — DONE

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env

# Configure .env

alembic upgrade head

uvicorn app.main:app --reload
```

Then visit http://localhost:8000/docs for interactive API docs.

## V1 scope

**IN:** JWT auth, creator profile, Razorpay order+webhook+idempotency, WebSocket alert to OBS overlay via secure token.

**OUT (deliberately):** Redis, TTS, leaderboards, donation goals, themes, custom sounds, third-party integrations, mobile app.

## Architecture decision

The Razorpay **webhook** is the sole source of truth for a successful tip.
A client can never directly mark a tip as paid — only a verified webhook event can.

## Day-by-day plan

| Day | Task |
|---|---|
| 1 | DB schema + auth + profile CRUD — **done** |
| 2 | Tip page + Razorpay order creation |
| 3 | Webhook verification + idempotency + tip creation |
| 4 | WebSocket server |
| 5 | Overlay page |
| 6 | End-to-end wiring + testing |
| 7 | Deploy |
