"""PlayzAI Multi-AI Manager and Dispatcher.

Coordinates:
- Multiple AI provider configurations
- Model discovery & selection
- Secure credential management (API keys masked everywhere)
- Intelligent fallback routing on transient failures
- Natural Language PC automation translation
- Zero-trust risk classification & confirmation enforcement
- Truthful audit logging
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import uuid
from typing import Any

from ai_providers import (
    AIError,
    AIProvider,
    AuthenticationFailed,
    InvalidAPIKey,
    InvalidModel,
    NetworkError,
    ProviderNotConfigured,
    ProviderTimedOut,
    ProviderUnavailable,
    RateLimited,
    get_provider_instance,
    mask_api_key,
)
from confirmation_manager import create_confirmation
from risk_engine import (
    LEVEL_1_SAFE,
    LEVEL_2_MODERATE,
    LEVEL_3_HIGH,
    classify_task,
)

SYSTEM_PROMPT = os.getenv(
    "AI_SYSTEM_PROMPT",
    "You are PlayzAI, a truthful, secure AI assistant and Windows PC automation companion. "
    "Be helpful, direct, and concise. Never fabricate command execution results or PC telemetry.",
)


def init_ai_schema(connection: sqlite3.Connection) -> None:
    """Create AI tables if not present and populate initial defaults."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS ai_providers(
            id TEXT PRIMARY KEY,
            provider_type TEXT NOT NULL,
            display_name TEXT NOT NULL,
            api_key TEXT NOT NULL DEFAULT '',
            base_url TEXT DEFAULT '',
            default_model TEXT DEFAULT '',
            enabled INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 1,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'untested',
            last_tested_at REAL,
            last_error TEXT DEFAULT '',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_models(
            id TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            description TEXT DEFAULT '',
            is_custom INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_settings(
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS pending_confirmations(
            id TEXT PRIMARY KEY,
            session_id TEXT,
            device_id TEXT,
            action TEXT NOT NULL,
            command TEXT DEFAULT '',
            args_json TEXT DEFAULT '{}',
            risk_level TEXT NOT NULL,
            risk_explanation TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            consumed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS audit_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            user_id TEXT DEFAULT '',
            session_id TEXT DEFAULT '',
            device_id TEXT DEFAULT '',
            source_ip TEXT DEFAULT '',
            action TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            command TEXT DEFAULT '',
            confirmation_status TEXT DEFAULT 'NONE',
            result TEXT NOT NULL,
            exit_code INTEGER,
            execution_time_ms REAL DEFAULT 0,
            provider TEXT DEFAULT '',
            model TEXT DEFAULT '',
            detail TEXT DEFAULT ''
        );
        """
    )
    # Ensure default settings exist
    default_settings = {
        "fallback_enabled": "true",
        "default_provider": "gemini",
        "default_model": "gemini-1.5-flash",
        "default_language": "en",
        "pc_control_enabled": "true",
    }
    for k, v in default_settings.items():
        connection.execute(
            "INSERT OR IGNORE INTO ai_settings(key, value) VALUES (?, ?)", (k, v)
        )
    connection.commit()


def sanitize_for_audit(text: str) -> str:
    """Scrub sensitive credentials from commands and details before logging."""
    if not text:
        return ""
    # Redact common key patterns
    scrubbed = re.sub(r"(AIza[0-9A-Za-z-_]{35})", "[REDACTED_GEMINI_KEY]", text)
    scrubbed = re.sub(r"(sk-[0-9A-Za-z-_]{20,})", "[REDACTED_OPENAI_KEY]", scrubbed)
    scrubbed = re.sub(r"(sk-ant-[0-9A-Za-z-_]{20,})", "[REDACTED_CLAUDE_KEY]", scrubbed)
    scrubbed = re.sub(r"(password|secret|token|api_key)\s*[:=]\s*['\"]?[^'\"\s]+", r"\1=[REDACTED]", scrubbed, flags=re.IGNORECASE)
    return scrubbed[:1000]


def record_audit_log(
    connection: sqlite3.Connection,
    action: str,
    risk_level: str,
    result: str,
    user_id: str = "",
    session_id: str = "",
    device_id: str = "",
    source_ip: str = "",
    command: str = "",
    confirmation_status: str = "NONE",
    exit_code: int | None = None,
    execution_time_ms: float = 0,
    provider: str = "",
    model: str = "",
    detail: str = "",
) -> None:
    """Safely append an entry to the audit log."""
    try:
        connection.execute(
            """
            INSERT INTO audit_logs(
                timestamp, user_id, session_id, device_id, source_ip,
                action, risk_level, command, confirmation_status,
                result, exit_code, execution_time_ms, provider, model, detail
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                sanitize_for_audit(user_id),
                sanitize_for_audit(session_id),
                sanitize_for_audit(device_id),
                sanitize_for_audit(source_ip),
                sanitize_for_audit(action),
                risk_level,
                sanitize_for_audit(command),
                confirmation_status,
                result,
                exit_code,
                execution_time_ms,
                provider,
                model,
                sanitize_for_audit(detail),
            ),
        )
        connection.commit()
    except Exception:
        pass


def get_all_providers(
    connection: sqlite3.Connection, include_secrets: bool = False
) -> list[dict[str, Any]]:
    """Retrieve all provider configurations."""
    rows = connection.execute(
        "SELECT * FROM ai_providers ORDER BY priority ASC, created_at ASC"
    ).fetchall()
    providers = []
    for r in rows:
        item = dict(r)
        if not include_secrets:
            raw_key = item.get("api_key") or ""
            item["api_key_masked"] = mask_api_key(raw_key)
            item["has_key"] = bool(raw_key.strip())
            item.pop("api_key", None)
        providers.append(item)
    return providers


def get_provider_by_id(
    connection: sqlite3.Connection, provider_id: str, include_secrets: bool = False
) -> dict[str, Any] | None:
    """Retrieve a single provider configuration."""
    row = connection.execute(
        "SELECT * FROM ai_providers WHERE id = ?", (provider_id,)
    ).fetchone()
    if not row:
        return None
    item = dict(row)
    if not include_secrets:
        raw_key = item.get("api_key") or ""
        item["api_key_masked"] = mask_api_key(raw_key)
        item["has_key"] = bool(raw_key.strip())
        item.pop("api_key", None)
    return item


def save_provider(
    connection: sqlite3.Connection, data: dict[str, Any]
) -> dict[str, Any]:
    """Create or update an AI provider configuration."""
    now_ts = time.time()
    pid = data.get("id") or f"prov_{data.get('provider_type')}_{uuid.uuid4().hex[:6]}"
    ptype = (data.get("provider_type") or "openai").lower().strip()
    dname = data.get("display_name") or f"{ptype.title()} Provider"
    key = (data.get("api_key") or "").strip()
    url = (data.get("base_url") or "").strip()
    model = (data.get("default_model") or "").strip()
    enabled = 1 if data.get("enabled", True) else 0
    priority = int(data.get("priority", 1))
    desc = data.get("description", "")

    existing = connection.execute("SELECT * FROM ai_providers WHERE id = ?", (pid,)).fetchone()
    if existing:
        # If updating and key is empty or masked, retain existing secret key
        if not key or key.startswith("•••") or "••••" in key:
            key = existing["api_key"]
        connection.execute(
            """
            UPDATE ai_providers
            SET provider_type = ?, display_name = ?, api_key = ?, base_url = ?,
                default_model = ?, enabled = ?, priority = ?, description = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (ptype, dname, key, url, model, enabled, priority, desc, now_ts, pid),
        )
    else:
        connection.execute(
            """
            INSERT INTO ai_providers(
                id, provider_type, display_name, api_key, base_url,
                default_model, enabled, priority, description, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'untested', ?, ?)
            """,
            (pid, ptype, dname, key, url, model, enabled, priority, desc, now_ts, now_ts),
        )
    connection.commit()
    return get_provider_by_id(connection, pid, include_secrets=False) or {}


def delete_provider(connection: sqlite3.Connection, provider_id: str) -> bool:
    """Delete a provider configuration."""
    res = connection.execute("DELETE FROM ai_providers WHERE id = ?", (provider_id,))
    connection.execute("DELETE FROM ai_models WHERE provider_id = ?", (provider_id,))
    connection.commit()
    return res.rowcount > 0


async def test_provider_connection(
    connection: sqlite3.Connection, provider_id: str
) -> dict[str, Any]:
    """Perform a REAL live connection and authentication test to the provider endpoint."""
    prov = get_provider_by_id(connection, provider_id, include_secrets=True)
    if not prov:
        return {"ok": False, "error_code": "provider_not_found", "detail": "Provider not found."}

    ptype = prov.get("provider_type", "")
    key = prov.get("api_key", "")
    base_url = prov.get("base_url", "")
    model = prov.get("default_model", "")

    try:
        adapter = get_provider_instance(ptype)
    except Exception as exc:
        return {"ok": False, "error_code": "unsupported_provider", "detail": str(exc)}

    result = await adapter.test_connection(api_key=key, base_url=base_url, model=model)

    # Update provider status in DB
    status_str = "online" if result.get("ok") else "error"
    last_err = result.get("detail") if not result.get("ok") else ""
    connection.execute(
        """
        UPDATE ai_providers
        SET status = ?, last_tested_at = ?, last_error = ?
        WHERE id = ?
        """,
        (status_str, time.time(), last_err, provider_id),
    )
    connection.commit()

    return result


async def discover_provider_models(
    connection: sqlite3.Connection, provider_id: str
) -> list[str]:
    """Query provider API for available model IDs."""
    prov = get_provider_by_id(connection, provider_id, include_secrets=True)
    if not prov:
        return []

    ptype = prov.get("provider_type", "")
    key = prov.get("api_key", "")
    base_url = prov.get("base_url", "")

    try:
        adapter = get_provider_instance(ptype)
        models = await adapter.discover_models(api_key=key, base_url=base_url)
        return models
    except Exception:
        return []


def get_ai_settings(connection: sqlite3.Connection) -> dict[str, str]:
    """Retrieve all AI settings as a dictionary."""
    rows = connection.execute("SELECT key, value FROM ai_settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def update_ai_settings(
    connection: sqlite3.Connection, settings: dict[str, str]
) -> dict[str, str]:
    """Update AI settings."""
    for k, v in settings.items():
        connection.execute(
            """
            INSERT INTO ai_settings(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (k, str(v)),
        )
    connection.commit()
    return get_ai_settings(connection)


def detect_natural_language_pc_task(message: str) -> tuple[str | None, dict[str, Any]]:
    """Detect if the user message describes a PC automation task.

    Returns (action, args) or (None, {}).
    """
    msg = message.strip().lower()

    # Power operations
    if re.search(r"\b(shutdown|turn off my pc|power off)\b", msg):
        return "shutdown", {}
    if re.search(r"\b(restart my pc|reboot my pc|restart computer)\b", msg):
        return "restart", {}
    if re.search(r"\b(lock my pc|lock workstation|lock screen)\b", msg):
        return "lock_pc", {}
    if re.search(r"\b(turn on my pc|wake on lan|wake my pc)\b", msg):
        return "wake_pc", {}

    # Diagnostics / Status / Telemetry
    if re.search(r"\b(is my pc online|pc status|check my pc|check computer)\b", msg):
        return "pc_status", {}
    if re.search(r"\b(check (my )?(ram|memory)|how much ram|memory usage)\b", msg):
        return "ram", {}
    if re.search(r"\b(check (my )?(cpu|processor)|cpu usage)\b", msg):
        return "cpu", {}
    if re.search(r"\b(check (my )?(disk|storage|hard drive)|disk space|storage usage)\b", msg):
        return "storage", {}
    if re.search(r"\b(system info|diagnostics|specs|pc info)\b", msg):
        return "system_info", {}

    # OBS Control
    if re.search(r"\b(start obs recording|start recording)\b", msg):
        return "obs_record_start", {}
    if re.search(r"\b(stop obs recording|stop recording)\b", msg):
        return "obs_record_stop", {}
    if re.search(r"\b(start obs stream|start streaming)\b", msg):
        return "obs_start", {}
    if re.search(r"\b(stop obs stream|stop streaming)\b", msg):
        return "obs_stop", {}
    if re.search(r"\b(is obs running|obs status|check obs)\b", msg):
        return "obs_status", {}
    if re.search(r"\b(start obs|launch obs|open obs)\b", msg):
        return "open_app", {"name": "obs"}

    # Minecraft Control
    if re.search(r"\b(start minecraft|launch minecraft|open minecraft)\b", msg):
        return "open_app", {"name": "minecraft"}
    if re.search(r"\b(check minecraft|minecraft status)\b", msg):
        return "minecraft_status", {}

    # Open App
    match_open = re.search(r"\b(open|launch|start)\s+([a-zA-Z0-9_\-\.\s]+?)(?:\s+app|\s+please|\s+now|$)", msg)
    if match_open:
        target = match_open.group(2).strip()
        if target and target not in ("the", "a", "an", "this", "my", "recording", "stream", "streaming"):
            return "open_app", {"name": target}

    # Close App
    match_close = re.search(r"\b(close|kill|stop|terminate)\s+([a-zA-Z0-9_\-\.\s]+?)(?:\s+app|\s+process|\s+now|$)", msg)
    if match_close:
        target = match_close.group(2).strip()
        if target and target not in ("the", "a", "an", "this", "my", "recording", "stream", "streaming", "pc", "computer"):
            return "close_app", {"name": target}

    # Direct PowerShell or CMD
    match_ps = re.search(r"\b(?:run|execute)\s+(?:this\s+)?powershell\s+(?:command|script)?\s*[:;]?\s*(.+)$", message, re.IGNORECASE)
    if match_ps:
        return "run_powershell", {"command": match_ps.group(1).strip()}

    match_cmd = re.search(r"\b(?:run|execute)\s+(?:this\s+)?(?:cmd|command)\s*[:;]?\s*(.+)$", message, re.IGNORECASE)
    if match_cmd:
        return "run_command", {"command": match_cmd.group(1).strip()}

    # Deletion
    match_del = re.search(r"\b(?:delete|remove)\s+(?:the\s+)?(?:file|folder|directory)\s+([a-zA-Z0-9_\\\/\:\.\-]+)", message, re.IGNORECASE)
    if match_del:
        return "delete_file", {"path": match_del.group(1).strip()}

    return None, {}


async def execute_ai_chat(
    connection: sqlite3.Connection,
    message: str,
    conversation_id: str,
    device_id: str = "web",
    session_id: str = "",
    source_ip: str = "127.0.0.1",
    requested_provider_id: str | None = None,
    requested_model: str | None = None,
    language: str = "en",
    request_id: str = "",
    legacy_env_config: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute authenticated multi-AI chat with tool execution, fallback, and truthful responses."""
    settings = get_ai_settings(connection)
    pc_control_enabled = settings.get("pc_control_enabled", "true").lower() == "true"
    fallback_enabled = settings.get("fallback_enabled", "true").lower() == "true"

    # Step 1: Check for natural language PC automation tasks
    if pc_control_enabled:
        action, args = detect_natural_language_pc_task(message)
        if action:
            risk_level, explanation = classify_task(action, args)
            cmd_str = args.get("command") or json.dumps(args)

            # LEVEL 3 High Risk actions STRICTLY require explicit confirmation
            if risk_level == LEVEL_3_HIGH:
                conf = create_confirmation(
                    connection=connection,
                    session_token_hash=session_id,
                    device_id=device_id,
                    action=action,
                    command=cmd_str,
                    args=args,
                    risk_level=risk_level,
                    risk_explanation=explanation,
                )
                record_audit_log(
                    connection=connection,
                    action=f"PC Task Requested: {action}",
                    risk_level=risk_level,
                    result="CONFIRMATION_REQUIRED",
                    user_id=device_id,
                    session_id=session_id,
                    device_id=device_id,
                    source_ip=source_ip,
                    command=cmd_str,
                    confirmation_status="PENDING",
                    detail=explanation,
                )
                # Format friendly confirmation prompt
                lang_l = (language or "en").lower()
                if lang_l in ("hi", "hindi"):
                    reply_text = (
                        f"⚠️ यह कार्रवाई उच्च जोखिम वाली है (Level 3):\n\n"
                        f"कार्रवाई: {action}\n"
                        f"कमांड: {cmd_str}\n"
                        f"जोखिम: {explanation}\n\n"
                        f"कृपया आगे बढ़ने के लिए नीचे दिए गए 'Confirm' बटन पर क्लिक करें।"
                    )
                elif lang_l in ("hinglish",):
                    reply_text = (
                        f"⚠️ Yeh action high risk category mein aati hai (Level 3):\n\n"
                        f"Action: {action}\n"
                        f"Command: {cmd_str}\n"
                        f"Risk: {explanation}\n\n"
                        f"Execute karne ke liye please neeche 'Confirm' button dabayein."
                    )
                else:
                    reply_text = (
                        f"⚠️ High-risk action detected ({risk_level}):\n\n"
                        f"Action: {action}\n"
                        f"Command: {cmd_str}\n"
                        f"Risk: {explanation}\n\n"
                        f"Please confirm execution using the button below."
                    )

                return {
                    "reply": reply_text,
                    "conversation_id": conversation_id,
                    "provider_used": "system-pc-controller",
                    "model_used": "risk-engine-v2",
                    "fallback_occurred": False,
                    "requires_confirmation": True,
                    "confirmation": conf,
                }

    # Step 2: Fetch candidate AI providers
    providers = get_all_providers(connection, include_secrets=True)
    enabled_providers = [p for p in providers if p.get("enabled", 1) == 1]

    # If requested specific provider
    primary_provider: dict[str, Any] | None = None
    if requested_provider_id:
        primary_provider = next((p for p in providers if p["id"] == requested_provider_id), None)

    if not primary_provider:
        # Default from settings or first enabled provider
        default_pid = settings.get("default_provider")
        if default_pid:
            primary_provider = next((p for p in enabled_providers if p["id"] == default_pid), None)
        if not primary_provider and enabled_providers:
            primary_provider = enabled_providers[0]

    # Step 3: Check legacy environment variables if no DB provider exists
    if not primary_provider and legacy_env_config:
        legacy_key = legacy_env_config.get("api_key", "").strip()
        legacy_url = legacy_env_config.get("base_url", "").strip()
        legacy_model = legacy_env_config.get("model", "").strip()
        if legacy_key and legacy_url and legacy_model:
            primary_provider = {
                "id": "legacy_env",
                "provider_type": "openai_compatible",
                "display_name": "Legacy Configured Provider",
                "api_key": legacy_key,
                "base_url": legacy_url,
                "default_model": legacy_model,
                "enabled": 1,
            }

    if not primary_provider:
        raise ProviderNotConfigured("No AI provider is configured or enabled on the backend.")

    # Step 4: Build candidate execution queue (primary + fallbacks)
    candidates = [primary_provider]
    if fallback_enabled:
        for p in enabled_providers:
            if p["id"] != primary_provider["id"]:
                candidates.append(p)

    # Step 5: Execute with fallback
    last_error: Exception | None = None
    fallback_occurred = False

    # Retrieve recent conversation messages
    history_rows = connection.execute(
        """
        SELECT role, body FROM messages
        WHERE conversation_id = ?
        ORDER BY created ASC LIMIT 10
        """,
        (conversation_id,),
    ).fetchall()
    conversation_history = [{"role": r["role"], "content": r["body"]} for r in history_rows]

    for idx, prov in enumerate(candidates):
        ptype = prov.get("provider_type", "openai")
        key = prov.get("api_key", "")
        base_url = prov.get("base_url", "")
        target_model = requested_model if (idx == 0 and requested_model) else (prov.get("default_model") or "")

        try:
            adapter = get_provider_instance(ptype)
            start_t = time.perf_counter()
            res = await adapter.generate_response(
                message=message,
                conversation_history=conversation_history,
                api_key=key,
                base_url=base_url,
                model=target_model,
                system_prompt=SYSTEM_PROMPT,
                language=language,
                request_id=request_id,
            )
            exec_time_ms = round((time.perf_counter() - start_t) * 1000, 1)

            # Record truthful audit log
            record_audit_log(
                connection=connection,
                action="AI Chat Completion",
                risk_level=LEVEL_1_SAFE,
                result="SUCCESS",
                user_id=device_id,
                session_id=session_id,
                device_id=device_id,
                source_ip=source_ip,
                provider=ptype,
                model=res.get("model", target_model),
                execution_time_ms=exec_time_ms,
                detail=f"Tokens/Status: OK. Fallback: {fallback_occurred}",
            )

            return {
                "reply": res["reply"],
                "conversation_id": conversation_id,
                "provider_used": ptype,
                "model_used": res.get("model", target_model),
                "fallback_occurred": fallback_occurred,
                "request_id": request_id,
            }

        except (RateLimited, ProviderUnavailable, ProviderTimedOut, NetworkError) as transient_err:
            last_error = transient_err
            fallback_occurred = True
            record_audit_log(
                connection=connection,
                action="AI Provider Transient Failure",
                risk_level=LEVEL_1_SAFE,
                result="FALLBACK_TRIGGERED",
                user_id=device_id,
                session_id=session_id,
                device_id=device_id,
                source_ip=source_ip,
                provider=ptype,
                model=target_model,
                detail=f"Error: {transient_err.__class__.__name__}: {str(transient_err)}",
            )
            # Try next provider in fallback queue
            continue

        except (InvalidAPIKey, AuthenticationFailed, InvalidModel) as perm_err:
            # Permanent auth or configuration errors should be reported directly
            record_audit_log(
                connection=connection,
                action="AI Provider Auth/Config Error",
                risk_level=LEVEL_1_SAFE,
                result="FAILED",
                user_id=device_id,
                session_id=session_id,
                device_id=device_id,
                source_ip=source_ip,
                provider=ptype,
                model=target_model,
                detail=f"Error: {perm_err.__class__.__name__}",
            )
            raise perm_err

        except Exception as unk_err:
            last_error = unk_err
            fallback_occurred = True
            continue

    if last_error:
        raise last_error

    raise ProviderUnavailable("All configured AI providers are currently unavailable.")
