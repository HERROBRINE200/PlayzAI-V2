# PlayzAI V2 — Complete Setup & Deployment Guide

This guide details how to install and run the PlayzAI V2 Backend, Web Dashboard, Windows PC Agent, and Android Application.

---

## 1. Prerequisites

- **Python**: 3.10, 3.11, or 3.12
- **Node.js**: 20.x or 22.x LTS (with `npm`)
- **Git**

---

## 2. Backend Setup

1. Open a terminal in `backend/`:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Create your configuration from `.env.example`:
   ```bash
   cp .env.example .env
   ```
3. Start the FastAPI development server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
4. Verify backend health:
   ```bash
   curl http://127.0.0.1:8000/health
   ```

---

## 3. Web Dashboard Setup

1. In the project root:
   ```bash
   npm install
   npm run build
   ```
2. Start the Vite development preview:
   ```bash
   npm run dev -- --host 0.0.0.0
   ```
3. Open the Dashboard in your browser (`http://localhost:5173`).
4. Register your admin device or enter the backend URL and credentials on the login screen.

---

## 4. Windows PC Agent Setup

1. In the Dashboard under **Devices & Pairing**, click **Generate Pairing Code**.
2. On your Windows machine, open PowerShell or Command Prompt:
   ```cmd
   cd agent
   set PLAYZAI_API=http://<BACKEND_HOST>:8000
   set PLAYZAI_DEVICE_ID=my-windows-desktop
   set PLAYZAI_API_KEY=plz_pc_<YOUR_CLAIMED_KEY>
   python agent.py
   ```
3. The PC will appear as **Online** in the Dashboard, with real-time CPU, RAM, and Disk metrics.

---

## 5. Android Application

1. Open the `android/` directory in Android Studio (Giraffe / Hedgehog / Iguana / Jellyfish or newer).
2. Sync with Gradle files (`build.gradle.kts`).
3. Set your backend URL in `SettingsStore` or in the in-app Settings screen.
4. Run on an Android device or emulator (Android 8.0+ / API 26+).
5. Supports voice interaction in English, Hindi (Devanagari), and Indian Hinglish.
