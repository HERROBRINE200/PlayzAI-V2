# PlayzAI V2 — Multi-AI Assistant & Windows Automation Platform

A complete, enterprise-grade, multi-provider AI assistant and Windows PC automation platform with zero-trust risk classification, real-time telemetry, and multi-language support (English, Hindi, and Indian Hinglish).

---

## What's New in V2

- **True Multi-Provider AI Architecture**: Native support for Google Gemini, OpenAI (Official), Anthropic Claude, OpenAI-Compatible providers (Groq, Together, DeepSeek, Ollama, OpenRouter, vLLM), and Custom AI Endpoints.
- **Dynamic Fallback Routing**: Automatic failover across priority-ranked providers during rate-limiting or provider downtime without silent error swallowing.
- **Zero-Trust Risk Engine**: Classification of all PC automation tasks into Level 1 (Safe), Level 2 (Moderate), and Level 3 (High Risk).
- **Cryptographic Operator Confirmations**: High-risk operations (file deletion, power state, elevated PowerShell/CMD, registry/firewall alterations) generate single-use, session-tied confirmation tokens requiring explicit operator approval.
- **Enhanced Windows PC Agent**: Real-time CPU, RAM, Disk, and Network telemetry; application launcher; OBS Studio & Minecraft automation; PowerShell and CMD execution runner.
- **Multi-Language Voice Support**: English, Hindi (Devanagari script), and Indian Hinglish with voice gender selection (Default, Male, Female) and rate/pitch controls.
- **Immutable Audit Logging**: Sanitized audit trail recording all AI interactions, tool calls, exit codes, and confirmation decisions.

---

## Repository Structure

```
.
├── backend/                  # FastAPI Python backend (Multi-AI routing, Risk Engine, Confirmations, Database)
│   ├── ai_providers.py       # Gemini, OpenAI, Claude, OpenAI-Compatible adapters
│   ├── ai_manager.py         # Multi-AI coordinator, fallback dispatcher, audit logger
│   ├── risk_engine.py        # PC task risk classification (Level 1, 2, 3)
│   ├── confirmation_manager.py # Zero-trust confirmation lifecycle
│   ├── main.py               # REST API, WebSocket realtime channel, WhatsApp webhook
│   ├── test_main.py          # Core API test suite
│   ├── test_v2_features.py   # Multi-AI, Fallback, Confirmation, and Audit test suite
│   └── requirements.txt      # Python dependencies
├── src/                      # React + TypeScript + Vite Dashboard frontend
│   ├── App.tsx               # Main Dashboard application & UI views
│   ├── api.ts                # TypeScript PlayzApi client
│   ├── types.ts              # System types & data structures
│   └── styles.css            # Dark/light theme visual system
├── agent/                    # Windows PC Automation Agent
│   ├── agent.py              # Telemetry, app launcher, OBS/Minecraft, CMD/PowerShell runner
│   ├── test_agent.py         # Agent test suite
│   └── requirements.txt      # Agent dependencies
├── android/                  # Android Jetpack Compose application
│   ├── app/src/main/         # Kotlin source code, models, stores, services, UI
│   └── build.gradle.kts      # Android build configuration
├── docs/                     # Architectural & setup guides
│   ├── AI_PROVIDERS.md       # Multi-AI setup, model discovery, fallback
│   ├── PC_AUTOMATION.md      # Windows Agent capabilities and architecture
│   ├── CONFIRMATION_SECURITY.md # Risk classification and confirmation workflow
│   └── SETUP_GUIDE.md        # Full installation and deployment instructions
├── package.json              # Dashboard dependencies and build scripts
└── vite.config.ts            # Vite configuration
```

---

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

Run tests:
```bash
pytest backend/ -v
```

### 2. Dashboard

```bash
npm install
npm test
npm run typecheck
npm run lint
npm run build
npm run dev
```

### 3. Windows Agent

```bash
cd agent
pip install -r requirements.txt
python agent.py
```

Run tests:
```bash
pytest agent/ -v
```

---

## Security & Privacy Guarantee

- **API Keys**: Stored exclusively on the backend. Never exposed to frontends, never bundled in the Android APK, and masked in all API responses.
- **Zero-Trust Boundary**: AI models are untrusted. The backend independently verifies authentication, risk level, permissions, and operator confirmation before dispatching commands to the Windows Agent.
