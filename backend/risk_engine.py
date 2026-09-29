"""PlayzAI PC Task Risk Classification Engine.

Classifies all PC automation tasks and commands into:
- LEVEL 1 — SAFE: No confirmation required when authenticated.
- LEVEL 2 — MODERATE: Low-to-moderate impact actions.
- LEVEL 3 — HIGH RISK / HEAVY: Elevated, destructive, or system-altering actions that STRICTLY require explicit user confirmation.
"""

from __future__ import annotations

import re
from typing import Any

LEVEL_1_SAFE = "LEVEL 1 — SAFE"
LEVEL_2_MODERATE = "LEVEL 2 — MODERATE"
LEVEL_3_HIGH = "LEVEL 3 — HIGH RISK / HEAVY"

SAFE_ACTIONS: set[str] = {
    "heartbeat",
    "get_status",
    "pc_status",
    "cpu",
    "ram",
    "storage",
    "network",
    "system_info",
    "diagnostics",
    "list_processes",
    "list_directory",
    "read_log",
    "read_file",
    "obs_status",
    "minecraft_status",
    "notify",
    "ping",
    "ipconfig",
}

SAFE_APPS: set[str] = {
    "notepad",
    "calc",
    "calculator",
    "chrome",
    "firefox",
    "msedge",
    "edge",
    "code",
    "vscode",
    "spotify",
    "discord",
    "explorer",
    "taskmgr",
    "obs",
    "obs64",
    "paint",
    "mspaint",
}

# Regex patterns that indicate Level 3 destructive or elevated operations
HIGH_RISK_PATTERNS = [
    # Deletion and format
    r"\b(rmdir|rd|del|erase|Remove-Item|rm)\b.*\b(-r|-recurse|/s|/q|\*)\b",
    r"\b(format|diskpart|mkfs|fdisk|dd)\b",
    # Reboot and shutdown
    r"\b(shutdown|Stop-Computer|Restart-Computer|reboot|poweroff|init 0|init 6)\b",
    # Security, firewall, elevation, users
    r"\b(Set-ExecutionPolicy|netsh\s+advfirewall|reg\s+(delete|add)|Remove-ItemProperty)\b",
    r"\b(net\s+user|net\s+localgroup|takeown|icacls|chmod\s+-R\s+777)\b",
    r"\b(sfc\s+/scannow|dism|bcdedit|vssadmin)\b",
    # Destructive service or process kills
    r"\b(sc\s+(delete|stop)|Stop-Service|kill\s+-9|taskkill\s+/f\s+/im\s+(explorer|lsass|csrss|winlogon|svchost)\.exe)\b",
    # Dangerous uninstallation
    r"\b(uninstall|remove-package|winget\s+uninstall|choco\s+uninstall)\b",
]

MODERATE_PATTERNS = [
    r"\b(New-Item|Set-Content|Add-Content|Out-File|copy|move|ren|rename|Copy-Item|Move-Item|Rename-Item)\b",
    r"\b(Restart-Service|Start-Service|taskkill)\b",
    r"\b(pip\s+install|npm\s+install|winget\s+install)\b",
]


def classify_command_text(command_text: str) -> tuple[str, str]:
    """Classify risk level of a raw command string or PowerShell snippet."""
    if not command_text or not command_text.strip():
        return LEVEL_1_SAFE, "Empty command query."

    cmd = command_text.strip()

    # Check high risk patterns
    for pattern in HIGH_RISK_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return (
                LEVEL_3_HIGH,
                f"Command contains potentially destructive, elevated, or system-altering operation matching pattern '{pattern}'.",
            )

    # Check moderate patterns
    for pattern in MODERATE_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return (
                LEVEL_2_MODERATE,
                "Command creates/modifies files, services, or packages.",
            )

    # Safe diagnostic read-only commands
    if re.match(r"^(dir|ls|Get-Process|Get-Service|Get-ComputerInfo|Get-Volume|ipconfig|ping|tracert|systeminfo|whoami|echo|hostname|tasklist)\b", cmd, re.IGNORECASE):
        return LEVEL_1_SAFE, "Standard diagnostic or read-only system command."

    # Unknown custom PowerShell or CMD command defaults to Level 3 for safety
    return (
        LEVEL_3_HIGH,
        "Custom shell or PowerShell script execution requires explicit confirmation.",
    )


def classify_task(action: str, args: dict[str, Any] | None = None) -> tuple[str, str]:
    """Classify any PlayzAI PC task into (risk_level, explanation)."""
    action_clean = (action or "").strip().lower()
    args_dict = args or {}

    # Standard safe queries
    if action_clean in SAFE_ACTIONS:
        return LEVEL_1_SAFE, f"Safe diagnostic or read-only action '{action_clean}'."

    # Application launch
    if action_clean == "open_app":
        app_name = str(args_dict.get("name") or args_dict.get("app") or "").lower().strip()
        if not app_name:
            return LEVEL_1_SAFE, "Open default application."
        if app_name in SAFE_APPS or any(safe in app_name for safe in SAFE_APPS):
            return LEVEL_1_SAFE, f"Launch standard user application: {app_name}."
        return LEVEL_2_MODERATE, f"Launch custom or unallowlisted application: {app_name}."

    if action_clean == "close_app":
        app_name = str(args_dict.get("name") or args_dict.get("app") or "").lower().strip()
        if app_name in ("csrss", "lsass", "explorer", "winlogon", "system"):
            return LEVEL_3_HIGH, f"Terminating critical system process '{app_name}' is high risk."
        return LEVEL_2_MODERATE, f"Close application: {app_name}."

    # OBS & Minecraft control
    if action_clean in ("obs_start", "obs_stop", "obs_record_start", "obs_record_stop", "obs_scene", "obs_control"):
        return LEVEL_2_MODERATE, f"OBS Studio automation action '{action_clean}'."

    if action_clean in ("minecraft_start", "minecraft_stop", "minecraft_command", "minecraft_control"):
        return LEVEL_2_MODERATE, f"Minecraft server/client automation action '{action_clean}'."

    # File operations
    if action_clean in ("read_file", "list_dir", "list_files", "file_exists"):
        return LEVEL_1_SAFE, "Read-only file system inspection."

    if action_clean in ("write_file", "create_file", "move_file", "rename_file", "copy_file"):
        path = str(args_dict.get("path") or args_dict.get("destination") or "")
        if any(crit in path.lower() for crit in ("windows", "system32", "program files", "boot", "etc")):
            return LEVEL_3_HIGH, f"Modifying files in system directory '{path}' is high risk."
        return LEVEL_2_MODERATE, f"File modification: {action_clean} on '{path}'."

    if action_clean in ("delete_file", "delete_folder", "remove_directory"):
        path = str(args_dict.get("path") or args_dict.get("file") or "")
        return LEVEL_3_HIGH, f"File or folder deletion on '{path}' is destructive and irreversible."

    # Power & Lockdown
    if action_clean in ("shutdown", "restart", "reboot", "sleep_pc"):
        return LEVEL_3_HIGH, f"PC power state operation '{action_clean}' requires explicit confirmation."

    if action_clean in ("lock_pc", "lockdown", "unlock"):
        return LEVEL_2_MODERATE, f"Security lock operation '{action_clean}'."

    # Direct Command & PowerShell execution
    if action_clean in ("run_command", "cmd", "run_powershell", "powershell", "execute_script"):
        cmd_str = str(args_dict.get("command") or args_dict.get("script") or "")
        return classify_command_text(cmd_str)

    # Service operations
    if action_clean == "service_control":
        subaction = str(args_dict.get("subaction") or "").lower()
        service_name = str(args_dict.get("service") or "").lower()
        if subaction in ("status", "query"):
            return LEVEL_1_SAFE, f"Query status of service '{service_name}'."
        if subaction in ("stop", "disable", "delete"):
            return LEVEL_3_HIGH, f"Stopping or disabling Windows service '{service_name}' may affect stability."
        return LEVEL_2_MODERATE, f"Service action '{subaction}' on '{service_name}'."

    # Default fallback: unknown action requires Level 3 confirmation
    return LEVEL_3_HIGH, f"Unrecognized PC action '{action_clean}' requires explicit confirmation."
