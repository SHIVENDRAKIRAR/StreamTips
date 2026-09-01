# StreamTips

Real-time tipping platform for streamers — see full plan in `docs/streamtips-project-plan.md`.

## Day 1 status: DB schema + JWT auth + creator profile — DONE
## Day 2 status: Tip page + Razorpay order creation — DONE
## Day 3 status: Webhook verification + idempotency — DONE
## Day 4 status: WebSocket server — DONE
## Day 5 status: OBS overlay page — DONE

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

## Testing the webhook locally (Day 3)

Razorpay's servers can't reach `localhost` directly, so you need a tunnel:

1. Install [ngrok](https://ngrok.com/download) (free tier is fine).
2. With your server running on port 8000, in a separate terminal run:
   ```bash
   ngrok http 8000
   ```
   It gives you a public URL like `https://abcd1234.ngrok-free.app`.
3. In the Razorpay Dashboard → Settings → Webhooks → Add New Webhook:
   - URL: `https://abcd1234.ngrok-free.app/webhooks/razorpay`
   - Active events: check **`payment.captured`**
   - Set a webhook secret — copy it into your `.env` as `RAZORPAY_WEBHOOK_SECRET`, then restart uvicorn so it picks up the new value.
4. Now complete a test payment through `frontend/tip.html` as in Day 2. Within a few seconds, Razorpay should hit your webhook, and you'll see the tip's `status` flip from `pending` to `success` in the `tips` table.

**To verify idempotency actually works:** in the Razorpay Dashboard, find that webhook delivery under Webhooks → Logs, and use "Resend". Confirm the tip stays `success` (not duplicated, no error) and check your server logs for `"Duplicate webhook event ignored"`.

## Try the tip page

1. Sign up a creator via `/docs` (`POST /auth/signup`) — note the `username` you chose.
2. Open `frontend/tip.html` directly in your browser (double-click it, or use VS Code's Live Server extension).
3. Add `?creator=<username>` to the URL, e.g. `tip.html?creator=shivendra`.
4. Enter an amount, click Send Tip — Razorpay's test checkout modal opens.
5. Use Razorpay's [test card numbers](https://razorpay.com/docs/payments/payments/test-card-upi-details/) to simulate a payment.

Note: the tip only shows as `pending` in the DB until Day 3's webhook verification marks it `success`. The frontend "Payment received" message is just Razorpay confirming the checkout succeeded — it is NOT the source of truth for whether the tip is recorded as paid.

## Setting up the real OBS overlay (Day 5)

1. Get your overlay token from `GET /users/me/overlay`.
2. In OBS: Sources → + → Browser Source.
3. URL: `http://localhost:8000/../frontend/overlay.html?token=<your-token>` — or better, serve `frontend/` with a simple static server (`python3 -m http.server 5500` from inside `frontend/`) and use `http://localhost:5500/overlay.html?token=<your-token>`.
4. Set Width/Height to something like 800x400 (it's centered, so exact size just needs to fit the card).
5. Check "Shutdown source when not visible" **OFF** — you want it listening even when the scene isn't active, or you'll miss tips.
6. Fire a real tip through the full flow. The alert should pop in, hold for ~6 seconds, then fade out — background stays transparent over your video the whole time.

The overlay auto-reconnects if OBS reloads the source or the connection drops — no manual refresh needed mid-stream. Tips are queued, so two arriving close together show one after another instead of overlapping.

`frontend/ws_test.html` is kept around as a plain-text fallback for debugging the raw WebSocket feed if the styled overlay ever misbehaves.

## Testing the WebSocket (Day 4)

1. Get your overlay token: call `GET /users/me/overlay` in `/docs` while logged in (or check the `users.overlay_token` column directly in Postgres).
2. Open `frontend/ws_test.html?token=<your-overlay-token>` in a browser. It should say "Connected."
3. Complete a test tip through `frontend/tip.html` as before, and let the webhook process it (via ngrok, as in Day 3).
4. Within a second or two, `ws_test.html` should log the tip event — name, amount, message.

This is a plain diagnostic page, not the real overlay. Day 5 replaces it with the actual styled alert used in OBS.

**Note on scaling:** the connection manager is in-memory, single-process by design (see comments in `app/services/connection_manager.py`) — this is the deliberate "no Redis in V1" cut from the project plan, not an oversight.

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
| 3 | Webhook verification + idempotency + tip creation — **done** |
| 4 | WebSocket server — **done** |
| 5 | Overlay page — **done** |
| 6 | End-to-end wiring + testing |
| 7 | Deploy |
