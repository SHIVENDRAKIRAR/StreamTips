# StreamTips

Real-time tipping platform for streamers — see full plan in `docs/streamtips-project-plan.md`.

## Day 1 status: DB schema + JWT auth + creator profile — DONE
## Day 2 status: Tip page + Razorpay order creation — DONE

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DATABASE_URL, JWT_SECRET_KEY, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET

# create the database first (in psql): CREATE DATABASE streamtips;
alembic revision --autogenerate -m "initial schema"
alembic upgrade head

uvicorn app.main:app --reload
```

Then visit http://localhost:8000/docs for interactive API docs.

## Try the tip page

1. Sign up a creator via `/docs` (`POST /auth/signup`) — note the `username` you chose.
2. Open `frontend/tip.html` directly in your browser (double-click it, or use VS Code's Live Server extension).
3. Add `?creator=<username>` to the URL, e.g. `tip.html?creator=shivendra`.
4. Enter an amount, click Send Tip — Razorpay's test checkout modal opens.
5. Use Razorpay's [test card numbers](https://razorpay.com/docs/payments/payments/test-card-upi-details/) to simulate a payment.

Note: the tip only shows as `pending` in the DB until Day 3's webhook verification marks it `success`. The frontend "Payment received" message is just Razorpay confirming the checkout succeeded — it is NOT the source of truth for whether the tip is recorded as paid.

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
| 2 | Tip page + Razorpay order creation — **done** |
| 3 | Webhook verification + idempotency + tip creation |
| 4 | WebSocket server |
| 5 | Overlay page |
| 6 | End-to-end wiring + testing |
| 7 | Deploy |
