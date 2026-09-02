# StreamTips

A real-time tipping platform for livestreamers. A viewer pays through Razorpay, the payment is confirmed by a signature-verified webhook, and an animated alert appears live inside the creator's OBS stream within seconds.

![StreamTips alert live in OBS](docs/obs-demo.png)

## How it works

```
Creator signs up (JWT) → gets a public tip page and a private OBS overlay link

Viewer opens the tip page → enters name, message, amount → pays via Razorpay
        │
        ▼
Razorpay confirms payment → sends a signed webhook event
        │
        ▼
Backend verifies the HMAC-SHA256 signature on the raw request body
        │
        ▼
Checks the event hasn't been processed before (DB-enforced idempotency)
        │
        ▼
Tip status flips from "pending" to "success" in PostgreSQL
        │
        ▼
Event is pushed over WebSocket to the creator's connected OBS overlay
        │
        ▼
🎉 Alert renders live on stream
```

**The core design decision:** a tip can only ever be marked successful by a verified webhook event — never by the client. `POST /tips` only ever creates a `pending` row. This closes the obvious attack of a viewer calling the API directly to fake a large donation without paying.

## Stack

- **Backend:** FastAPI, PostgreSQL, SQLAlchemy, Alembic
- **Auth:** JWT + bcrypt
- **Payments:** Razorpay (order creation, signed webhooks)
- **Real-time:** native FastAPI WebSockets
- **Overlay:** plain HTML/CSS/JS, rendered as an OBS Browser Source

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in DATABASE_URL, JWT_SECRET_KEY, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET

# create the database first: CREATE DATABASE streamtips;
alembic upgrade head

uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

### Testing the full flow

1. Sign up a creator via `/docs` (`POST /auth/signup`).
2. Open `frontend/tip.html?creator=<username>` and send a test tip (use [Razorpay's test card numbers](https://razorpay.com/docs/payments/payments/test-card-upi-details/)).
3. Since Razorpay can't reach `localhost` directly, tunnel your server with `ngrok http 8000` and register `https://<ngrok-url>/webhooks/razorpay` in the Razorpay Dashboard under Webhooks (event: `payment.captured`).
4. Get your overlay token from `GET /users/me/overlay`, open `frontend/overlay.html?token=<token>` as an OBS Browser Source (or in a plain browser tab to preview), and watch the alert fire when the webhook lands.

## Security & reliability

| Concern | How it's handled |
|---|---|
| Faking a successful payment | Only the signature-verified webhook can set a tip to `success` — no client-reachable endpoint does |
| Duplicate webhook delivery | Unique DB constraint on `webhook_events.event_id`; a duplicate insert fails and is ignored |
| Tampered webhook payload | HMAC-SHA256 signature checked against the raw request body before anything is trusted |
| Guessing another creator's overlay | 64-char random `overlay_token`, unrelated to username/id, validated before the WebSocket connection is even accepted |
| XSS via tip messages | Viewer-submitted text is HTML-escaped before being rendered in the overlay |
| OBS disconnecting mid-stream | Overlay auto-reconnects on a fixed retry delay, no manual refresh needed |

All of the above were manually tested, including duplicate-webhook resends, concurrent tips, invalid input, and direct attempts to bypass payment verification.

## Scope

**In V1:** JWT auth, creator profiles, Razorpay order + webhook + idempotency, real-time WebSocket alerts, secure OBS overlay tokens.

**Deliberately out of V1:** Redis (no horizontal scaling needed yet), TTS, leaderboards, donation goals, custom themes/sounds, third-party stream integrations. See the code comments in `app/services/connection_manager.py` for the reasoning on the Redis cut specifically.

## Project structure

```
app/
├── core/         # config, database, security, auth dependency
├── models/       # users, tips, webhook_events
├── schemas/      # request/response validation
├── routers/      # auth, users, public, tips, webhooks, websocket
└── services/     # razorpay client, websocket connection manager
frontend/
├── tip.html      # public viewer-facing tip page
├── overlay.html  # OBS Browser Source overlay
└── ws_test.html  # plain-text WebSocket debug page
```

## Development notes

Built day-by-day, each stage tested before moving to the next:

| Day | Focus |
|---|---|
| 1 | DB schema, JWT auth, creator profile CRUD |
| 2 | Razorpay order creation, tip page |
| 3 | Webhook signature verification + idempotency |
| 4 | WebSocket server + connection handling |
| 5 | OBS overlay page (animation, reconnect, alert queueing) |
| 6 | Hardening — duplicate webhooks, invalid input, XSS, concurrency, attack simulation |

Cloud deployment was deliberately skipped in favor of a reliable local demo.

---

### Demo

The screenshot below shows a live tip alert rendering inside OBS via the Browser Source overlay:

![OBS Browser Source showing a live StreamTips alert](docs/obs-demo.png)
