# PlayzAI V2 — PC Control & Windows Automation Guide

PlayzAI V2 connects your mobile and web interfaces directly to your Windows desktop with zero-trust execution.

---

## 1. Capabilities

### 1.1 Hardware Telemetry & Diagnostics
- **CPU Utilization (%)**
- **RAM Utilization (%)**
- **Storage / Disk Usage (Total, Free, %)**
- **Network Interface & Status**
- **Platform & Hostname**

### 1.2 Application Management
- **Launch allowlisted & custom applications**:
  - Everyday apps: Notepad, Google Chrome, Microsoft Edge, Mozilla Firefox, VS Code, Spotify, Discord, Task Manager, File Explorer, Calculator, MSPaint.
- **Process Termination**:
  - Graceful and forced process termination with safety blocks against terminating core Windows processes (`csrss`, `lsass`, `winlogon`, `system`).

### 1.3 OBS Studio Automation
- **Start / Stop Recording**
- **Start / Stop Streaming**
- **Check OBS Process & Streaming Status**
- **Scene Switching & Control**

### 1.4 Minecraft Automation
- **Server Start & Stop**
- **Console Command Dispatch**
- **Player & Server Status Query**

### 1.5 File System Operations
- **List Directory Entries** (files, directories, sizes)
- **Read File Content** (UTF-8, bounded byte length)
- **Create / Edit Files** (creates parent directories safely)
- **Delete Files & Folders** (Protected by Level 3 Confirmation)

### 1.6 PowerShell & CMD Command Runner
- **Command Execution** (`subprocess.run` with customizable timeouts)
- **Execution Metadata**: captures `exit_code`, `stdout`, `stderr`, and `execution_time_ms`.
- **Zero-Trust Safety**: Dangerous syntax and destructive commands automatically require human operator sign-off.

---

## 2. Windows Agent Architecture

```
Web Dashboard / Android App
            ↓ (REST / WebSocket)
   FastAPI Secure Backend
            ↓ (Risk Engine & Confirmation Check)
     Command Queue (`/api/agent/commands`)
            ↓ (Long Poll / WebSocket)
      Windows PC Agent (`agent.py`)
            ↓ (Subprocess Execution)
   Windows OS / OBS / Minecraft / PowerShell
            ↓ (Result: exit_code, stdout, stderr)
      POST `/api/agent/commands/{id}/result`
            ↓
       Immutable Audit Trail
```

---

## 3. Running the Windows Agent

1. Install Python 3.10+ on the Windows machine.
2. In the `agent/` folder:
   ```cmd
   pip install -r requirements.txt
   set PLAYZAI_API=https://your-backend-domain.com
   set PLAYZAI_DEVICE_ID=my-windows-pc
   set PLAYZAI_API_KEY=plz_pc_your_enrolled_key
   python agent.py
   ```
3. The agent registers its heartbeat and begins polling for tasks immediately.
