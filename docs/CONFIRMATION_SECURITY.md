# PlayzAI V2 — Zero-Trust Risk Classification & Confirmation Security

In PlayzAI V2, AI models are treated as **untrusted components**. All PC commands and automation actions pass through an independent, server-enforced risk classification engine before execution.

---

## 1. Risk Taxonomy

### LEVEL 1 — SAFE (Auto-execute when authenticated)
- **Description**: Read-only diagnostics, harmless queries, and standard desktop application launching.
- **Examples**:
  - `get_status`, `pc_status`, `cpu`, `ram`, `storage`, `network`, `system_info`
  - `list_processes`, `list_directory`, `read_log`, `read_file`
  - `open_app` for allowlisted everyday tools (Notepad, Calc, Chrome, Edge, VS Code, Discord, Spotify)
  - `ping`, `ipconfig`, `obs_status`, `minecraft_status`

### LEVEL 2 — MODERATE (Executed with session authorization)
- **Description**: File creation/updates in non-system paths, service restarts, media studio automation.
- **Examples**:
  - `write_file`, `create_file`, `move_file`, `rename_file` in user folders
  - `obs_start`, `obs_stop`, `obs_record_start`, `obs_record_stop`
  - `minecraft_start`, `minecraft_stop`
  - `service_control` (query / restart non-system service)

### LEVEL 3 — HIGH RISK / HEAVY (Strictly Requires Human Confirmation)
- **Description**: Destructive file operations, power state changes, elevated script executions, registry/firewall modifications, disk alterations.
- **Examples**:
  - File/Directory Deletion: `delete_file`, `delete_folder`, `rmdir /s`, `del /s`, `Remove-Item -Recurse`
  - Power State: `shutdown`, `restart`, `reboot`, `Stop-Computer`
  - Privilege & Policy: `Set-ExecutionPolicy`, `net user`, `takeown`, `icacls`, `reg add`, `reg delete`
  - Firewall & Network: `netsh advfirewall`, firewall disable
  - Disk Operations: `format`, `diskpart`
  - System Repairs / Changes: `sfc /scannow`, `dism`, `bcdedit`, `sc delete`
  - Arbitrary PowerShell / CMD scripts

---

## 2. Confirmation Lifecycle

1. **Trigger**: When an operator or AI natural language request triggers a Level 3 action, the backend rejects immediate execution.
2. **Pending Record Created**: A short-lived record is stored in `pending_confirmations` with:
   - `confirmation_id` (unique UUID)
   - `session_id` (cryptographically tied to the active caller session)
   - `device_id` (target device)
   - `action` & `command` (exact script/command string)
   - `risk_level` & `risk_explanation`
   - `expires_at` (5-minute TTL)
   - `consumed = 0`
3. **UI Display**: The Dashboard and Android chat show a prompt with:
   - **ACTION**: What will happen
   - **COMMAND**: The exact script / command to be run
   - **RISK**: Plain explanation of potential consequences
   - Buttons: `[ Confirm & Execute ]` and `[ Cancel ]`
4. **Approval & Consumption**:
   - When confirmed via `POST /api/security/confirmations/{id}/confirm`, the server verifies caller session, expiry, and non-consumed status.
   - The confirmation is marked `consumed = 1, status = 'confirmed'` (single-use policy prevents replay attacks).
   - The command is queued for the Windows PC agent.
5. **AI Cannot Confirm**: An AI model is technically incapable of confirming its own high-risk actions. Only authenticated operator session tokens are accepted.

---

## 3. Immutable Audit Logging

Every execution and confirmation decision is recorded in the `audit_logs` table:
- **Timestamp**
- **User / Session ID**
- **Target Device**
- **Action & Command** (all passwords and API keys scrubbed)
- **Risk Level** (SAFE / MODERATE / HIGH)
- **Confirmation Status** (NONE / CONFIRMED / CANCELLED)
- **Result & Exit Code**
- **Execution Time (ms)**
- **Provider & Model**
