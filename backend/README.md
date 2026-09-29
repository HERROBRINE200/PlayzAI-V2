# PlayzAI backend

The backend is the only component that talks to an AI provider. The Android APK never contains `AI_API_KEY`.

## Run

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

Use an HTTPS reverse proxy for deployment. Loopback HTTP is only for development. Provider credentials, owner secrets, WhatsApp Cloud credentials, and database configuration remain external.

## Core endpoints

- `GET/POST /health` — database/provider/messaging status without secrets.
- `POST /api/devices/register` and `/api/auth/session` — device enrollment and expiring sessions.
- `GET /api/devices`, `GET /api/security/events`, `GET /api/commands` — authenticated state/history.
- `POST /api/chat` — authenticated AI chat; messages are persisted and provider failures are truthful.
- `POST /api/command` — authenticated allowlisted queue; destructive commands require confirmation.
- `POST /api/pairing/codes` and `/api/pairing/claim` — owner-issued one-time Windows pairing.
- `POST /api/agent/heartbeat`, `GET /api/agent/commands`, and command result POST — Windows agent protocol.
- `POST /api/pcs`, `GET /api/pcs`, and `POST /api/pcs/{pc_id}/wake` — PC metrics/configuration and Wake-on-LAN.
- `POST /api/devices/revoke`, `/api/security/lockdown`, `/api/security/unlock` — owner controls.
- `WS /ws` — authenticated realtime ping/subscription status channel.
- `GET/POST /api/whatsapp/webhook`, `/api/whatsapp/status`, and `/api/whatsapp/send` — official WhatsApp Cloud API architecture only.

No unrestricted shell route exists. The Windows agent receives only queued allowlisted actions and returns results. WhatsApp remains unconfigured until valid official Business Cloud API credentials are supplied.

## Tests

```bash
pytest -q
```
