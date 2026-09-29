from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import socket
import sqlite3
import time
import uuid
from collections import defaultdict, deque
from contextlib import closing
from typing import Any, Callable

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, ConfigDict, Field

from ai_manager import (
    SYSTEM_PROMPT,
    delete_provider,
    discover_provider_models,
    execute_ai_chat,
    get_ai_settings,
    get_all_providers,
    get_provider_by_id,
    init_ai_schema,
    record_audit_log,
    save_provider,
    test_provider_connection,
    update_ai_settings,
)
from ai_providers import (
    AIError,
    AuthenticationFailed,
    InvalidAPIKey,
    InvalidModel,
    NetworkError,
    ProviderNotConfigured,
    ProviderRejected,
    ProviderTimedOut,
    ProviderUnavailable,
    RateLimited,
)
from confirmation_manager import (
    cancel_action,
    confirm_action,
    create_confirmation,
    list_pending_confirmations,
)
from risk_engine import (
    LEVEL_1_SAFE,
    LEVEL_2_MODERATE,
    LEVEL_3_HIGH,
    SAFE_ACTIONS,
    classify_task,
)

load_dotenv()

API_VERSION = "2.0.0"
DB = os.getenv("PLAYZAI_DB", "playzai.db")
AUTH_SECRET = os.getenv("AUTH_SECRET", "playzai-hardened-default-secret-change-in-prod")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "86400"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
AUTH_RATE_LIMIT_PER_MINUTE = int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "10"))
MAX_AUTH_FAILURES = int(os.getenv("MAX_AUTH_FAILURES", "5"))
AUTH_BLOCK_SECONDS = int(os.getenv("AUTH_BLOCK_SECONDS", "300"))
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "20"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "800"))
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
AI_BASE_URL = os.getenv("AI_BASE_URL", "").strip().rstrip("/")
AI_MODEL = os.getenv("AI_MODEL", "").strip()

ENROLLMENT_SECRET = os.getenv("PLAYZAI_ENROLLMENT_SECRET", "").strip()
MASTER_KEY = os.getenv("PLAYZAI_MASTER_KEY", "").strip()

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0").strip()

lockdown_active = False

DANGEROUS_ACTIONS = {
    "shutdown",
    "restart",
    "sleep_pc",
    "lock_pc",
    "delete_file",
    "delete_folder",
    "run_command",
    "run_powershell",
    "service_control",
}


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self.windows: dict[str, deque[float]] = defaultdict(deque)

    def clear(self) -> None:
        self.windows.clear()

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        current = time.time()
        bucket = self.windows[key]
        boundary = current - window_seconds
        while bucket and bucket[0] <= boundary:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (current - bucket[0])))
            return False, retry_after
        bucket.append(current)
        return True, 0


limiter = SlidingWindowLimiter()


def now() -> float:
    return time.time()


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "req-unknown")


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def hash_credential(value: str) -> str:
    return hmac.new(AUTH_SECRET.encode(), value.strip().encode(), hashlib.sha256).hexdigest()


def safe_detail(value: str, max_length: int = 240) -> str:
    sanitized = value.replace("\r", " ").replace("\n", " ").strip()
    return sanitized[:max_length]


def database() -> sqlite3.Connection:
    conn = sqlite3.connect(DB, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with closing(database()) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices(
                id TEXT PRIMARY KEY, name TEXT NOT NULL, key_hash TEXT NOT NULL,
                created REAL NOT NULL, last_seen REAL, blocked_until REAL DEFAULT 0,
                failed_attempts INTEGER DEFAULT 0, failed_window_start REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, source TEXT NOT NULL,
                ip TEXT NOT NULL, event TEXT NOT NULL, detail TEXT DEFAULT '', request_id TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS sessions(
                id TEXT PRIMARY KEY, device_id TEXT NOT NULL, token_hash TEXT NOT NULL,
                created REAL NOT NULL, expires_at REAL NOT NULL, revoked INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS conversations(
                id TEXT PRIMARY KEY, owner_device_id TEXT NOT NULL, title TEXT NOT NULL,
                created REAL NOT NULL, updated REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages(
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, device_id TEXT NOT NULL,
                role TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS commands(
                id TEXT PRIMARY KEY, target_device_id TEXT NOT NULL, requested_by TEXT NOT NULL,
                action TEXT NOT NULL, args_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'queued',
                confirmation INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL, updated REAL NOT NULL, result_json TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS pcs(
                id TEXT PRIMARY KEY, device_id TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
                mac_address TEXT DEFAULT '', broadcast_address TEXT DEFAULT '255.255.255.255',
                agent_version TEXT DEFAULT '', status TEXT DEFAULT 'unknown', last_seen REAL,
                cpu_percent REAL, ram_percent REAL, storage_percent REAL, network_status TEXT DEFAULT 'unknown',
                wol_enabled INTEGER DEFAULT 0, updated REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS whatsapp_messages(
                id TEXT PRIMARY KEY, provider_message_id TEXT UNIQUE, sender TEXT NOT NULL,
                message_type TEXT NOT NULL, body TEXT DEFAULT '', status TEXT NOT NULL,
                created REAL NOT NULL, detail TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS pairing_codes(
                code_hash TEXT PRIMARY KEY, owner_device_id TEXT NOT NULL, pc_name TEXT NOT NULL,
                created REAL NOT NULL, expires_at REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(events)").fetchall()}
        if "request_id" not in columns:
            connection.execute("ALTER TABLE events ADD COLUMN request_id TEXT DEFAULT ''")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(devices)").fetchall()}
        if "failed_attempts" not in columns:
            connection.execute("ALTER TABLE devices ADD COLUMN failed_attempts INTEGER DEFAULT 0")
        if "failed_window_start" not in columns:
            connection.execute("ALTER TABLE devices ADD COLUMN failed_window_start REAL DEFAULT 0")
        connection.commit()

        # Initialize AI schema and audit logging tables
        init_ai_schema(connection)


init_db()


def audit(source: str, ip: str, event: str, detail: str = "", req_id: str = "") -> None:
    try:
        with closing(database()) as connection:
            connection.execute(
                "INSERT INTO events(ts, source, ip, event, detail, request_id) VALUES (?, ?, ?, ?, ?, ?)",
                (now(), source[:64], ip[:64], event[:64], safe_detail(detail), req_id[:128]),
            )
            connection.commit()
    except sqlite3.Error:
        pass


def api_error(request: Request, code: str, message: str, status_code: int, extra_headers: dict[str, str] | None = None) -> JSONResponse:
    headers = {"X-Request-ID": request_id(request)}
    if extra_headers:
        headers.update(extra_headers)
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}, "request_id": request_id(request)},
        headers=headers,
    )


def raise_api(code: str, message: str, status_code: int) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})


def enforce_rate_limit(request: Request, key_suffix: str, limit: int | None = None, window_seconds: int = 60) -> None:
    effective_limit = limit or RATE_LIMIT_PER_MINUTE
    key = f"{client_ip(request)}:{key_suffix}"
    allowed, retry_after = limiter.allow(key, effective_limit, window_seconds)
    if not allowed:
        audit("rate_limit", client_ip(request), "limit_exceeded", f"key={key} retry_after={retry_after}", request_id(request))
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"code": "rate_limited", "message": f"Rate limit exceeded. Try again in {retry_after} seconds."}, headers={"Retry-After": str(retry_after)})


def require_enrollment(request: Request, supplied: str) -> None:
    if ENROLLMENT_SECRET and not hmac.compare_digest(ENROLLMENT_SECRET, supplied):
        audit("enrollment", client_ip(request), "invalid_enrollment_secret", "", request_id(request))
        raise_api("enrollment_rejected", "Invalid enrollment secret.", 403)


def find_device(device_id: str) -> sqlite3.Row | None:
    with closing(database()) as connection:
        return connection.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()


def record_auth_failure(device_id: str, ip: str, req_id: str, detail: str) -> None:
    audit(device_id or "unknown", ip, "auth_failed", detail, req_id)
    if not device_id:
        return
    with closing(database()) as connection:
        device = connection.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        if not device:
            return
        current = now()
        failed_window = device["failed_window_start"] or 0
        attempts = device["failed_attempts"] or 0
        if current - failed_window > 60:
            attempts = 1
            failed_window = current
        else:
            attempts += 1
        blocked_until = current + AUTH_BLOCK_SECONDS if attempts >= MAX_AUTH_FAILURES else 0
        connection.execute("UPDATE devices SET failed_attempts = ?, failed_window_start = ?, blocked_until = ? WHERE id = ?", (attempts, failed_window, blocked_until, device_id))
        connection.commit()


def authenticate(request: Request, device_id: str | None, api_key: str, session_token: str) -> str:
    req_id = request_id(request)
    ip = client_ip(request)
    if lockdown_active:
        audit(device_id or "unknown", ip, "lockdown_rejected", "", req_id)
        raise_api("lockdown_active", "System is currently locked down.", 403)

    enforce_rate_limit(request, f"auth:{device_id or 'anonymous'}", AUTH_RATE_LIMIT_PER_MINUTE)

    if session_token:
        with closing(database()) as connection:
            session = connection.execute("SELECT * FROM sessions WHERE token_hash = ? AND revoked = 0", (hash_credential(session_token),)).fetchone()
            if not session:
                record_auth_failure(device_id or "", ip, req_id, "invalid_session")
                raise_api("invalid_authentication", "Authentication credentials are invalid.", 401)
            if session["expires_at"] < now():
                audit(session["device_id"], ip, "session_expired", "", req_id)
                raise_api("session_expired", "The authenticated session has expired.", 401)
            return session["device_id"]

    if not device_id or not api_key:
        record_auth_failure(device_id or "", ip, req_id, "missing_credentials")
        raise_api("missing_authentication", "Authentication credentials are required.", 401)

    device = find_device(device_id)
    if not device:
        record_auth_failure(device_id, ip, req_id, "device_not_found")
        raise_api("invalid_authentication", "Authentication credentials are invalid.", 401)
    if device["blocked_until"] and device["blocked_until"] > now():
        audit(device_id, ip, "device_blocked", "", req_id)
        raise_api("device_blocked", "Too many authentication failures. Try again later.", 403)
    if not hmac.compare_digest(device["key_hash"], hash_credential(api_key)):
        record_auth_failure(device_id, ip, req_id, "invalid_key")
        raise_api("invalid_authentication", "Authentication credentials are invalid.", 401)

    with closing(database()) as connection:
        connection.execute("UPDATE devices SET last_seen = ?, failed_attempts = 0, blocked_until = 0 WHERE id = ?", (now(), device_id))
        connection.commit()
    return device_id


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(StrictModel):
    device_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    enrollment_secret: str = Field(default="", max_length=256)


class SessionRequest(StrictModel):
    device_id: str = Field(default="", max_length=128)


class ChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str = Field(default_factory=lambda: f"conv-{uuid.uuid4().hex[:12]}", max_length=128)
    provider_id: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    language: str = Field(default="en", max_length=20)


class CommandRequest(StrictModel):
    device_id: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=100)
    args: dict[str, Any] = Field(default_factory=dict)
    confirmation: bool = Field(default=False)


class RevokeDeviceRequest(StrictModel):
    device_id: str = Field(min_length=1, max_length=128)
    confirmation: bool = Field(default=False)


class AgentHeartbeatRequest(StrictModel):
    agent_version: str = Field(default="1.0.0", max_length=32)
    pc_name: str = Field(min_length=1, max_length=100)
    mac_address: str = Field(default="", max_length=32)
    broadcast_address: str = Field(default="255.255.255.255", max_length=64)
    cpu_percent: float | None = Field(default=None, ge=0, le=100)
    ram_percent: float | None = Field(default=None, ge=0, le=100)
    storage_percent: float | None = Field(default=None, ge=0, le=100)
    network_status: str = Field(default="unknown", max_length=64)


class CommandResultRequest(StrictModel):
    ok: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = Field(default="", max_length=500)


class PcConfigRequest(StrictModel):
    pc_id: str = Field(min_length=1, max_length=128)
    device_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    mac_address: str = Field(default="", max_length=32)
    broadcast_address: str = Field(default="255.255.255.255", max_length=64)


class WakeRequest(StrictModel):
    confirmation: bool = Field(default=False)


class WhatsAppSendRequest(StrictModel):
    to: str = Field(min_length=5, max_length=32)
    message: str = Field(min_length=1, max_length=4000)


class PairingCodeRequest(StrictModel):
    pc_name: str = Field(min_length=1, max_length=100)


class PairingClaimRequest(StrictModel):
    code: str = Field(min_length=4, max_length=32)
    device_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class AIProviderCreateRequest(StrictModel):
    provider_type: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(default="", max_length=500)
    base_url: str = Field(default="", max_length=500)
    default_model: str = Field(default="", max_length=100)
    enabled: bool = True
    priority: int = Field(default=1, ge=1, le=100)
    description: str = Field(default="", max_length=500)


class AIProviderUpdateRequest(StrictModel):
    provider_type: str | None = None
    display_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    default_model: str | None = None
    enabled: bool | None = None
    priority: int | None = None
    description: str | None = None


class AIModelCreateRequest(StrictModel):
    provider_id: str = Field(..., min_length=1, max_length=100)
    model_name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=500)


class AISettingsUpdateRequest(StrictModel):
    fallback_enabled: bool | None = None
    default_provider: str | None = None
    default_model: str | None = None
    default_language: str | None = None
    pc_control_enabled: bool | None = None


class PcTaskExecuteRequest(StrictModel):
    device_id: str = Field(..., min_length=1, max_length=128)
    action: str = Field(..., min_length=1, max_length=100)
    args: dict[str, Any] = Field(default_factory=dict)
    confirmation_id: str | None = None


async def call_ai_provider(message: str, conversation_id: str, req_id: str) -> str:
    """Core AI dispatch helper."""
    with closing(database()) as connection:
        legacy_cfg = {
            "api_key": AI_API_KEY,
            "base_url": AI_BASE_URL,
            "model": AI_MODEL,
        }
        res = await execute_ai_chat(
            connection=connection,
            message=message,
            conversation_id=conversation_id,
            device_id="caller",
            requested_provider_id=None,
            requested_model=None,
            language="en",
            request_id=req_id,
            legacy_env_config=legacy_cfg,
        )
        return res["reply"]


def persist_message(conversation_id: str, device_id: str, role: str, body: str) -> None:
    timestamp = now()
    with closing(database()) as connection:
        connection.execute("INSERT INTO conversations(id, owner_device_id, title, created, updated) VALUES(?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET updated = excluded.updated", (conversation_id, device_id, body[:32] or "Conversation", timestamp, timestamp))
        connection.execute("INSERT INTO messages(id, conversation_id, device_id, role, body, created) VALUES(?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), conversation_id, device_id, role, body, timestamp))
        connection.commit()


def validate_mac(value: str) -> str:
    cleaned = value.replace("-", ":").replace(".", ":").upper().strip()
    parts = cleaned.split(":")
    if len(parts) == 6 and all(len(p) == 2 and all(c in "0123456789ABCDEF" for c in p) for p in parts):
        return ":".join(parts)
    raw = "".join(c for c in cleaned if c in "0123456789ABCDEF")
    if len(raw) == 12:
        return ":".join(raw[i:i + 2] for i in range(0, 12, 2))
    raise ValueError("Invalid MAC address format.")


def validate_broadcast(value: str) -> str:
    candidate = value.strip()
    try:
        socket.inet_aton(candidate)
        return candidate
    except OSError:
        pass
    raise ValueError("Invalid IPv4 broadcast address.")


def send_wake_on_lan(mac_address: str, broadcast_address: str) -> None:
    mac_bytes = bytes.fromhex(validate_mac(mac_address).replace(":", ""))
    packet = (b"\xFF" * 6) + (mac_bytes * 16)
    target_ip = validate_broadcast(broadcast_address)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (target_ip, 9))


async def send_official_whatsapp_message(to: str, message: str) -> dict[str, Any]:
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        raise RuntimeError("Official WhatsApp Cloud API credentials are not configured.")
    endpoint = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(endpoint, headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}, json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}})
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError("The official WhatsApp Cloud API rejected the message.")
    return response.json()


app = FastAPI(title="PlayzAI Secure Multi-AI & PC Control Backend", version=API_VERSION)


@app.middleware("http")
async def request_context(request: Request, call_next: Callable[..., Any]) -> JSONResponse:
    supplied = request.headers.get("X-Request-ID", "").strip()
    request.state.request_id = supplied[:128] if supplied else str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception as exc:
        audit("server", client_ip(request), "unhandled_error", f"{request.url.path}: {exc}", request_id(request))
        response = api_error(request, "internal_error", "The server could not complete the request.", 500)
    response.headers["X-Request-ID"] = request_id(request)
    audit("http", client_ip(request), "request", f"{request.method} {request.url.path} status={response.status_code}", request_id(request))
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "request_failed", "message": str(exc.detail)}
    return api_error(request, str(detail.get("code", "request_failed")), str(detail.get("message", "Request failed.")), exc.status_code, exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [".".join(str(part) for part in error.get("loc", ())) for error in exc.errors()]
    return api_error(request, "malformed_request", "Malformed request" + (f"; check {', '.join(fields[:4])}." if fields else "."), 422)


@app.exception_handler(sqlite3.Error)
async def database_exception_handler(request: Request, exc: sqlite3.Error) -> JSONResponse:
    audit("database", client_ip(request), "database_error", type(exc).__name__, request_id(request))
    return api_error(request, "database_unavailable", "The database could not complete the request.", 503)


async def health_response(request: Request) -> dict[str, Any]:
    db_status = "ok"
    has_providers = bool(AI_API_KEY and AI_BASE_URL and AI_MODEL)
    try:
        with closing(database()) as connection:
            connection.execute("SELECT 1").fetchone()
            prov_count = connection.execute("SELECT count(*) FROM ai_providers WHERE enabled = 1").fetchone()[0]
            if prov_count > 0:
                has_providers = True
    except sqlite3.Error:
        db_status = "unavailable"
    return {
        "ok": db_status == "ok",
        "service": "PlayzAI",
        "version": API_VERSION,
        "request_id": request_id(request),
        "database_status": db_status,
        "provider_configured": has_providers,
        "whatsapp_configured": bool(WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_VERIFY_TOKEN),
        "authenticated_api_enabled": bool(AUTH_SECRET or os.getenv("PLAYZAI_ENV", "development") != "production"),
    }


@app.get("/health")
async def health(request: Request) -> dict[str, Any]:
    return await health_response(request)


@app.post("/health")
async def health_post(request: Request) -> dict[str, Any]:
    return await health_response(request)


@app.get("/download/PlayzAI-V2-Complete.zip")
@app.get("/download/zip")
@app.get("/api/download/zip")
async def download_complete_zip():
    zip_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "PlayzAI-V2-Complete.zip"))
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="ZIP file not found.")
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename="PlayzAI-V2-Complete.zip",
        headers={"Content-Disposition": "attachment; filename=\"PlayzAI-V2-Complete.zip\""}
    )



@app.post("/api/devices/register")
@app.post("/v1/devices/register")
async def register_device(payload: RegisterRequest, request: Request) -> dict[str, Any]:
    require_enrollment(request, payload.enrollment_secret)
    enforce_rate_limit(request, "register", 10)
    api_key = f"plz_{secrets.token_urlsafe(32)}"
    with closing(database()) as connection:
        connection.execute(
            "INSERT INTO devices(id, name, key_hash, created) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name = excluded.name, key_hash = excluded.key_hash, blocked_until = 0, failed_attempts = 0",
            (payload.device_id, payload.name, hash_credential(api_key), now()),
        )
        connection.commit()
    audit(payload.device_id, client_ip(request), "device_registered", payload.name, request_id(request))
    return {"ok": True, "device_id": payload.device_id, "name": payload.name, "api_key": api_key, "request_id": request_id(request)}


@app.post("/api/auth/session")
async def create_session(payload: SessionRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    device_id = authenticate(request, payload.device_id or x_device_id, x_api_key, x_session_token)
    session_token = f"sess_{secrets.token_urlsafe(32)}"
    expires_at = now() + SESSION_TTL_SECONDS
    with closing(database()) as connection:
        connection.execute("INSERT INTO sessions(id, device_id, token_hash, created, expires_at) VALUES (?, ?, ?, ?, ?)", (str(uuid.uuid4()), device_id, hash_credential(session_token), now(), expires_at))
        connection.commit()
    audit(device_id, client_ip(request), "session_created", "", request_id(request))
    return {"ok": True, "device_id": device_id, "session_token": session_token, "expires_at": expires_at, "request_id": request_id(request)}


@app.get("/api/auth/status")
async def auth_status(request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    device_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    return {"authenticated": True, "device_id": device_id, "lockdown": lockdown_active, "request_id": request_id(request)}


@app.get("/v1/devices")
@app.get("/api/devices")
async def list_devices(request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        rows = connection.execute("SELECT id, name, created, last_seen, blocked_until FROM devices ORDER BY created DESC").fetchall()
        pcs = {p["device_id"]: p for p in connection.execute("SELECT * FROM pcs").fetchall()}
        payload = []
        for row in rows:
            pc = pcs.get(row["id"])
            payload.append({
                "device_id": row["id"],
                "name": row["name"],
                "created": row["created"],
                "last_seen": row["last_seen"],
                "authenticated": True,
                "kind": "pc" if pc else "device",
                "status": "blocked" if row["blocked_until"] and row["blocked_until"] > now() else ("online" if pc and pc["status"] == "online" else "registered"),
                "agent_version": pc["agent_version"] if pc else None,
                "metrics": {"cpu_percent": pc["cpu_percent"], "ram_percent": pc["ram_percent"], "storage_percent": pc["storage_percent"], "network_status": pc["network_status"]} if pc else None,
                "wake_on_lan": "configured" if pc and pc["wol_enabled"] else "not_configured",
            })
    return {"devices": payload, "request_id": request_id(request)}


@app.get("/v1/security/events")
@app.get("/api/security/events")
async def list_security_events(request: Request, limit: int = Query(default=50, ge=1, le=200), x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        rows = connection.execute("SELECT id, ts, source, ip, event, detail, request_id FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        events = [dict(row) for row in rows]
    return {"events": events, "request_id": request_id(request)}


@app.post("/api/pairing/codes")
async def create_pairing_code(payload: PairingCodeRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    owner = authenticate(request, x_device_id, x_api_key, x_session_token)
    code = f"PAIR-{secrets.randbelow(900000) + 100000}"
    expires_at = now() + 600
    with closing(database()) as connection:
        connection.execute("INSERT INTO pairing_codes(code_hash, owner_device_id, pc_name, created, expires_at, used) VALUES(?, ?, ?, ?, ?, 0)", (hash_credential(code), owner, payload.pc_name, now(), expires_at))
        connection.commit()
    audit(owner, client_ip(request), "pairing_code_issued", payload.pc_name, request_id(request))
    return {"ok": True, "pairing_code": code, "expires_at": expires_at, "request_id": request_id(request)}


@app.post("/api/pairing/claim")
async def claim_pairing_code(payload: PairingClaimRequest, request: Request) -> dict[str, Any]:
    enforce_rate_limit(request, "pairing_claim", 10)
    with closing(database()) as connection:
        row = connection.execute("SELECT * FROM pairing_codes WHERE code_hash = ? AND used = 0", (hash_credential(payload.code),)).fetchone()
        if not row or row["expires_at"] < now():
            audit(payload.device_id, client_ip(request), "pairing_claim_rejected", "", request_id(request))
            raise_api("invalid_pairing_code", "The pairing code is invalid or expired.", 403)
        api_key = f"plz_pc_{secrets.token_urlsafe(32)}"
        connection.execute("UPDATE pairing_codes SET used = 1 WHERE code_hash = ?", (row["code_hash"],))
        connection.execute("INSERT INTO devices(id, name, key_hash, created) VALUES(?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name = excluded.name, key_hash = excluded.key_hash, blocked_until = 0, failed_attempts = 0", (payload.device_id, payload.name, hash_credential(api_key), now()))
        connection.commit()
    audit(payload.device_id, client_ip(request), "pairing_claimed", f"owner={row['owner_device_id']}", request_id(request))
    return {"ok": True, "device_id": payload.device_id, "api_key": api_key, "request_id": request_id(request)}


@app.post("/api/pcs")
async def configure_pc(payload: PcConfigRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    owner = authenticate(request, x_device_id, x_api_key, x_session_token)
    try:
        mac = validate_mac(payload.mac_address) if payload.mac_address else ""
        broadcast = validate_broadcast(payload.broadcast_address)
    except ValueError as exc:
        raise_api("invalid_pc_configuration", str(exc), 422)
    timestamp = now()
    with closing(database()) as connection:
        connection.execute("INSERT INTO pcs(id, device_id, name, mac_address, broadcast_address, wol_enabled, updated) VALUES(?, ?, ?, ?, ?, ?, ?) ON CONFLICT(device_id) DO UPDATE SET name = excluded.name, mac_address = excluded.mac_address, broadcast_address = excluded.broadcast_address, wol_enabled = excluded.wol_enabled, updated = excluded.updated", (payload.pc_id, payload.device_id, payload.name, mac, broadcast, int(bool(mac)), timestamp))
        connection.commit()
    audit(owner, client_ip(request), "pc_configured", f"{payload.name} ({payload.device_id})", request_id(request))
    return {"ok": True, "pc_id": payload.pc_id, "device_id": payload.device_id, "wake_on_lan": "configured" if mac else "not_configured", "request_id": request_id(request)}


@app.get("/api/pcs")
async def list_pcs(request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        rows = connection.execute("SELECT * FROM pcs ORDER BY name ASC").fetchall()
        payload = [dict(r) for r in rows]
    return {"pcs": payload, "request_id": request_id(request)}


@app.post("/api/pcs/{pc_id}/wake")
async def wake_pc(pc_id: str, payload: WakeRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    owner = authenticate(request, x_device_id, x_api_key, x_session_token)
    if not payload.confirmation:
        return {"ok": False, "requires_confirmation": True, "pc_id": pc_id, "action": "wake_pc", "request_id": request_id(request)}
    with closing(database()) as connection:
        row = connection.execute("SELECT * FROM pcs WHERE id = ? OR device_id = ?", (pc_id, pc_id)).fetchone()
    if not row:
        raise_api("unknown_pc", "The specified PC was not found.", 404)
    if not row["mac_address"]:
        return {"ok": False, "pc_id": pc_id, "wake_on_lan": "not_configured", "message": "Wake-on-LAN is not configured for this PC.", "request_id": request_id(request)}
    try:
        send_wake_on_lan(row["mac_address"], row["broadcast_address"])
    except (OSError, ValueError):
        audit(owner, client_ip(request), "wake_on_lan_failed", pc_id, request_id(request))
        raise_api("wake_on_lan_failed", "The Wake-on-LAN packet could not be sent.", 503)
    audit(owner, client_ip(request), "wake_on_lan_sent", pc_id, request_id(request))
    return {"ok": True, "pc_id": pc_id, "wake_on_lan": "packet_sent", "request_id": request_id(request)}


# ==============================================================================
# AI CHAT AND MULTI-AI ENDPOINTS
# ==============================================================================


@app.post("/api/chat")
@app.post("/v1/chat")
async def chat(payload: ChatRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    device_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    enforce_rate_limit(request, f"chat:{device_id}")
    persist_message(payload.conversation_id, device_id, "user", payload.message)

    try:
        reply = await call_ai_provider(payload.message, payload.conversation_id, request_id(request))
    except ProviderNotConfigured:
        audit(device_id, client_ip(request), "chat_failed", "AI provider not configured", request_id(request))
        raise_api("provider_not_configured", "The AI provider is not configured on the backend.", 503)
    except ProviderTimedOut:
        raise_api("provider_timeout", "The AI provider timed out. Try again later.", 504)
    except (ProviderRejected, InvalidAPIKey, AuthenticationFailed):
        raise_api("provider_error", "The AI provider rejected the request.", 502)
    except ProviderUnavailable:
        raise_api("provider_unavailable", "The AI provider is temporarily unavailable.", 503)
    except AIError as exc:
        raise_api(exc.code, str(exc), exc.status_code)

    persist_message(payload.conversation_id, device_id, "assistant", reply)
    audit(device_id, client_ip(request), "chat_completed", f"conversation={payload.conversation_id}", request_id(request))
    return {"reply": reply, "conversation_id": payload.conversation_id, "request_id": request_id(request)}


@app.get("/api/ai/providers")
async def list_ai_providers(request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        providers = get_all_providers(connection, include_secrets=False)
    return {"providers": providers, "request_id": request_id(request)}


@app.post("/api/ai/providers")
async def create_ai_provider(payload: AIProviderCreateRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    user_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        created = save_provider(connection, payload.model_dump())
        record_audit_log(
            connection=connection,
            action="AI Provider Created",
            risk_level=LEVEL_1_SAFE,
            result="SUCCESS",
            user_id=user_id,
            source_ip=client_ip(request),
            detail=f"Type: {payload.provider_type}, Name: {payload.display_name}",
        )
    return {"ok": True, "provider": created, "request_id": request_id(request)}


@app.put("/api/ai/providers/{provider_id}")
async def update_ai_provider(provider_id: str, payload: AIProviderUpdateRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    user_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        existing = get_provider_by_id(connection, provider_id, include_secrets=True)
        if not existing:
            raise_api("provider_not_found", "AI provider not found.", 404)
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        update_data["id"] = provider_id
        if "provider_type" not in update_data:
            update_data["provider_type"] = existing["provider_type"]
        if "display_name" not in update_data:
            update_data["display_name"] = existing["display_name"]
        updated = save_provider(connection, update_data)
        record_audit_log(
            connection=connection,
            action="AI Provider Updated",
            risk_level=LEVEL_1_SAFE,
            result="SUCCESS",
            user_id=user_id,
            source_ip=client_ip(request),
            detail=f"Provider ID: {provider_id}",
        )
    return {"ok": True, "provider": updated, "request_id": request_id(request)}


@app.delete("/api/ai/providers/{provider_id}")
async def remove_ai_provider(provider_id: str, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    user_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        success = delete_provider(connection, provider_id)
        if not success:
            raise_api("provider_not_found", "AI provider not found.", 404)
        record_audit_log(
            connection=connection,
            action="AI Provider Deleted",
            risk_level=LEVEL_1_SAFE,
            result="SUCCESS",
            user_id=user_id,
            source_ip=client_ip(request),
            detail=f"Provider ID: {provider_id}",
        )
    return {"ok": True, "deleted": provider_id, "request_id": request_id(request)}


@app.post("/api/ai/providers/{provider_id}/test")
async def test_ai_provider(provider_id: str, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    enforce_rate_limit(request, f"test_provider:{provider_id}", limit=15)
    with closing(database()) as connection:
        result = await test_provider_connection(connection, provider_id)
    return {"ok": result.get("ok", False), "result": result, "request_id": request_id(request)}


@app.get("/api/ai/providers/{provider_id}/models")
async def get_provider_models(provider_id: str, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        models = await discover_provider_models(connection, provider_id)
    return {"models": models, "provider_id": provider_id, "request_id": request_id(request)}


@app.get("/api/ai/models")
async def list_ai_models(request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        rows = connection.execute("SELECT * FROM ai_models ORDER BY created_at DESC").fetchall()
        models = [dict(r) for r in rows]
    return {"models": models, "request_id": request_id(request)}


@app.post("/api/ai/models")
async def create_ai_model(payload: AIModelCreateRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    model_id = f"model_{uuid.uuid4().hex[:8]}"
    with closing(database()) as connection:
        connection.execute(
            """
            INSERT INTO ai_models(id, provider_id, model_name, display_name, description, is_custom, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (model_id, payload.provider_id, payload.model_name, payload.display_name or payload.model_name, payload.description, now()),
        )
        connection.commit()
    return {"ok": True, "model_id": model_id, "request_id": request_id(request)}


@app.delete("/api/ai/models/{model_id}")
async def remove_ai_model(model_id: str, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        res = connection.execute("DELETE FROM ai_models WHERE id = ?", (model_id,))
        connection.commit()
        if res.rowcount == 0:
            raise_api("model_not_found", "Model not found.", 404)
    return {"ok": True, "deleted": model_id, "request_id": request_id(request)}


@app.get("/api/ai/settings")
async def read_ai_settings(request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        settings = get_ai_settings(connection)
    return {"settings": settings, "request_id": request_id(request)}


@app.put("/api/ai/settings")
async def save_ai_settings(payload: AISettingsUpdateRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    data = {k: str(v) for k, v in payload.model_dump().items() if v is not None}
    with closing(database()) as connection:
        settings = update_ai_settings(connection, data)
    return {"ok": True, "settings": settings, "request_id": request_id(request)}


# ==============================================================================
# CONFIRMATIONS AND ADVANCED PC TASK EXECUTION
# ==============================================================================


@app.get("/api/security/confirmations/pending")
async def get_pending_confirmations_endpoint(request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        confs = list_pending_confirmations(connection)
    return {"confirmations": confs, "request_id": request_id(request)}


@app.post("/api/security/confirmations/{confirmation_id}/confirm")
async def confirm_task_endpoint(confirmation_id: str, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    device_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    token_hash = hash_credential(x_session_token) if x_session_token else ""
    with closing(database()) as connection:
        ok, msg, conf = confirm_action(connection, confirmation_id, token_hash, device_id)
        if not ok or not conf:
            raise_api("confirmation_invalid", msg, 400)

        # Enqueue the approved command for the agent
        command_id = str(uuid.uuid4())
        connection.execute(
            """
            INSERT INTO commands(id, target_device_id, requested_by, action, args_json, status, confirmation, created, updated)
            VALUES (?, ?, ?, ?, ?, 'queued', 1, ?, ?)
            """,
            (command_id, conf["device_id"], device_id, conf["action"], json.dumps(conf["args"], ensure_ascii=False), now(), now()),
        )
        connection.commit()

        record_audit_log(
            connection=connection,
            action=f"Confirmed Action: {conf['action']}",
            risk_level=conf.get("risk_level", LEVEL_3_HIGH),
            result="QUEUED_FOR_AGENT",
            user_id=device_id,
            session_id=token_hash,
            device_id=conf["device_id"],
            source_ip=client_ip(request),
            command=conf.get("command", ""),
            confirmation_status="CONFIRMED",
            detail=f"Command ID: {command_id}",
        )

    return {"ok": True, "command_id": command_id, "action": conf["action"], "message": "Command queued for PC Agent.", "request_id": request_id(request)}


@app.post("/api/security/confirmations/{confirmation_id}/cancel")
async def cancel_task_endpoint(confirmation_id: str, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    device_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    token_hash = hash_credential(x_session_token) if x_session_token else ""
    with closing(database()) as connection:
        ok, msg = cancel_action(connection, confirmation_id, token_hash)
        if not ok:
            raise_api("cancel_failed", msg, 400)
        record_audit_log(
            connection=connection,
            action="Cancelled Confirmation",
            risk_level=LEVEL_1_SAFE,
            result="CANCELLED",
            user_id=device_id,
            session_id=token_hash,
            source_ip=client_ip(request),
            detail=f"Confirmation ID: {confirmation_id}",
        )
    return {"ok": True, "message": "Confirmation cancelled.", "request_id": request_id(request)}


@app.get("/api/audit/logs")
async def get_audit_logs(request: Request, limit: int = Query(default=100, ge=1, le=500), x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        rows = connection.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        logs = [dict(r) for r in rows]
    return {"audit_logs": logs, "request_id": request_id(request)}


# ==============================================================================
# PC COMMAND PIPELINE & WINDOWS AGENT QUEUE
# ==============================================================================


def command_impl(payload: CommandRequest, request: Request, x_device_id: str, x_api_key: str, x_session_token: str) -> dict[str, Any]:
    sender = authenticate(request, x_device_id or payload.device_id, x_api_key, x_session_token)
    enforce_rate_limit(request, f"command:{sender}")

    if payload.action not in SAFE_ACTIONS and not (payload.action in DANGEROUS_ACTIONS and payload.confirmation):
        audit(sender, client_ip(request), "command_denied", payload.action, request_id(request))
        return {"ok": False, "requires_confirmation": True, "action": payload.action, "request_id": request_id(request)}

    if not find_device(payload.device_id):
        raise_api("unknown_device", "The target device is not registered.", 404)

    command_id = str(uuid.uuid4())
    with closing(database()) as connection:
        connection.execute(
            "INSERT INTO commands(id, target_device_id, requested_by, action, args_json, status, confirmation, created, updated) VALUES(?, ?, ?, ?, ?, 'queued', ?, ?, ?)",
            (command_id, payload.device_id, sender, payload.action, json.dumps(payload.args, ensure_ascii=False), int(payload.confirmation), now(), now()),
        )
        connection.commit()

        record_audit_log(
            connection=connection,
            action=f"PC Command Queued: {payload.action}",
            risk_level=LEVEL_1_SAFE if payload.action in SAFE_ACTIONS else LEVEL_3_HIGH,
            result="QUEUED",
            user_id=sender,
            device_id=payload.device_id,
            source_ip=client_ip(request),
            command=str(payload.args.get("command") or payload.action),
            confirmation_status="YES" if payload.confirmation else "NO",
            detail=f"Command ID: {command_id}",
        )

    audit(sender, client_ip(request), "command_accepted", f"{payload.action} target={payload.device_id}", request_id(request))
    return {"ok": True, "queued": True, "command_id": command_id, "action": payload.action, "request_id": request_id(request)}


@app.post("/v1/command")
@app.post("/api/command")
async def command(payload: CommandRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    return command_impl(payload, request, x_device_id, x_api_key, x_session_token)


@app.post("/api/agent/heartbeat")
async def agent_heartbeat(payload: AgentHeartbeatRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    agent_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    try:
        mac = validate_mac(payload.mac_address) if payload.mac_address else ""
        broadcast = validate_broadcast(payload.broadcast_address)
    except ValueError as exc:
        raise_api("invalid_agent_configuration", str(exc), 422)
    timestamp = now()
    with closing(database()) as connection:
        connection.execute(
            """
            INSERT INTO pcs(id, device_id, name, mac_address, broadcast_address, agent_version, status, last_seen, cpu_percent, ram_percent, storage_percent, network_status, wol_enabled, updated)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                name = excluded.name, mac_address = excluded.mac_address, broadcast_address = excluded.broadcast_address,
                agent_version = excluded.agent_version, status = 'online', last_seen = excluded.last_seen,
                cpu_percent = excluded.cpu_percent, ram_percent = excluded.ram_percent, storage_percent = excluded.storage_percent,
                network_status = excluded.network_status, wol_enabled = excluded.wol_enabled, updated = excluded.updated
            """,
            (str(uuid.uuid4()), agent_id, payload.pc_name, mac, broadcast, payload.agent_version, "online", timestamp, payload.cpu_percent, payload.ram_percent, payload.storage_percent, payload.network_status, int(bool(mac)), timestamp),
        )
        connection.commit()
    return {"ok": True, "device_id": agent_id, "server_time": timestamp, "request_id": request_id(request)}


@app.get("/api/agent/commands")
async def agent_fetch_commands(request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    agent_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        rows = connection.execute("SELECT id as command_id, action, args_json, created FROM commands WHERE target_device_id = ? AND status = 'queued' ORDER BY created ASC", (agent_id,)).fetchall()
        commands = []
        for row in rows:
            commands.append({"command_id": row["command_id"], "action": row["action"], "args": json.loads(row["args_json"]), "created": row["created"]})
    return {"commands": commands, "request_id": request_id(request)}


@app.post("/api/agent/commands/{command_id}/result")
async def agent_command_result(command_id: str, payload: CommandResultRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    agent_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    timestamp = now()
    with closing(database()) as connection:
        command_row = connection.execute("SELECT * FROM commands WHERE id = ? AND target_device_id = ?", (command_id, agent_id)).fetchone()
        if not command_row:
            raise_api("command_not_found", "The specified command does not exist.", 404)
        status_val = "completed" if payload.ok else "failed"
        result_payload = {"ok": payload.ok, "result": payload.result, "error": payload.error, "completed_at": timestamp}
        connection.execute("UPDATE commands SET status = ?, result_json = ?, updated = ? WHERE id = ?", (status_val, json.dumps(result_payload), timestamp, command_id))
        connection.commit()

        record_audit_log(
            connection=connection,
            action=f"Agent Executed: {command_row['action']}",
            risk_level=LEVEL_1_SAFE,
            result=status_val.upper(),
            user_id=agent_id,
            device_id=agent_id,
            source_ip=client_ip(request),
            exit_code=payload.result.get("exit_code"),
            detail=json.dumps(payload.result)[:200] if payload.ok else payload.error,
        )

    audit(agent_id, client_ip(request), "command_result_saved", f"id={command_id} status={status_val}", request_id(request))
    return {"ok": True, "command_id": command_id, "status": status_val, "request_id": request_id(request)}


@app.get("/api/commands")
async def list_commands(request: Request, limit: int = Query(default=50, ge=1, le=200), x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    device_id = authenticate(request, x_device_id, x_api_key, x_session_token)
    with closing(database()) as connection:
        rows = connection.execute("SELECT id as command_id, target_device_id, requested_by, action, args_json, status, confirmation, created, updated, result_json FROM commands WHERE requested_by = ? OR target_device_id = ? ORDER BY created DESC LIMIT ?", (device_id, device_id, limit)).fetchall()
        payload = []
        for r in rows:
            item = dict(r)
            item["args"] = json.loads(item.pop("args_json", "{}"))
            payload.append(item)
    return {"commands": payload, "request_id": request_id(request)}


# ==============================================================================
# SECURITY & OWNER PRIVILEGED CONTROLS
# ==============================================================================


def require_master_key(request: Request, supplied: str) -> None:
    if not MASTER_KEY or not hmac.compare_digest(MASTER_KEY, supplied.strip()):
        audit("security", client_ip(request), "master_key_rejected", "", request_id(request))
        raise_api("forbidden", "Owner master key is required.", 403)


@app.post("/api/devices/revoke")
async def revoke_device(payload: RevokeDeviceRequest, request: Request, x_api_key: str = Header(default="")) -> dict[str, Any]:
    require_master_key(request, x_api_key)
    if not payload.confirmation:
        return {"ok": False, "requires_confirmation": True, "device_id": payload.device_id, "request_id": request_id(request)}
    with closing(database()) as connection:
        connection.execute("DELETE FROM devices WHERE id = ?", (payload.device_id,))
        connection.execute("UPDATE sessions SET revoked = 1 WHERE device_id = ?", (payload.device_id,))
        connection.commit()
    audit("owner", client_ip(request), "device_revoked", payload.device_id, request_id(request))
    return {"ok": True, "device_id": payload.device_id, "revoked": True, "request_id": request_id(request)}


@app.post("/api/security/lockdown")
async def security_lockdown(request: Request, x_api_key: str = Header(default="")) -> dict[str, Any]:
    global lockdown_active
    require_master_key(request, x_api_key)
    lockdown_active = True
    with closing(database()) as connection:
        connection.execute("UPDATE sessions SET revoked = 1")
        connection.commit()
    audit("owner", client_ip(request), "lockdown_enabled", "", request_id(request))
    return {"ok": True, "lockdown": True, "request_id": request_id(request)}


@app.post("/api/security/unlock")
async def security_unlock(request: Request, x_api_key: str = Header(default="")) -> dict[str, Any]:
    global lockdown_active
    require_master_key(request, x_api_key)
    lockdown_active = False
    audit("owner", client_ip(request), "lockdown_disabled", "", request_id(request))
    return {"ok": True, "lockdown": False, "request_id": request_id(request)}


@app.post("/v1/security/panic")
@app.post("/api/security/panic")
async def security_panic(request: Request, x_api_key: str = Header(default="")) -> dict[str, Any]:
    return await security_lockdown(request, x_api_key)


# ==============================================================================
# WEBSOCKET REALTIME CHANNEL
# ==============================================================================


def websocket_device(websocket: WebSocket) -> str | None:
    device_id = websocket.headers.get("x-device-id") or websocket.query_params.get("device_id")
    api_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
    token = websocket.headers.get("x-session-token") or websocket.query_params.get("session_token")
    resolved = device_id or ""
    if token:
        with closing(database()) as connection:
            row = connection.execute("SELECT device_id FROM sessions WHERE token_hash=? AND revoked=0 AND expires_at>?", (hash_credential(token), now())).fetchone()
        resolved = row["device_id"] if row else ""
    row = find_device(resolved) if resolved else None
    if not row or (row["blocked_until"] and float(row["blocked_until"]) > now()):
        return None
    if token or (api_key and hmac.compare_digest(row["key_hash"], hash_credential(api_key))):
        return resolved
    return None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    device = websocket_device(websocket)
    if not device:
        await websocket.close(code=4401, reason="Authentication failed")
        return
    await websocket.accept()
    await websocket.send_json({"type": "connected", "device_id": device, "time": now()})
    try:
        while True:
            payload = await websocket.receive_json()
            msg_type = payload.get("type", "ping")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "time": now()})
            elif msg_type == "status":
                await websocket.send_json({"type": "status", "lockdown": lockdown_active, "time": now()})
            else:
                await websocket.send_json({"type": "ack", "received": msg_type, "time": now()})
    except WebSocketDisconnect:
        pass


# ==============================================================================
# WHATSAPP INTEGRATION
# ==============================================================================


@app.get("/api/whatsapp/status")
async def whatsapp_status(request: Request) -> dict[str, Any]:
    configured = bool(WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_VERIFY_TOKEN)
    return {"configured": configured, "official_cloud_api": True, "voice_transcription": "cloud_or_disabled", "request_id": request_id(request)}


@app.get("/api/whatsapp/webhook")
async def whatsapp_verify_webhook(request: Request) -> Any:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token and hmac.compare_digest(WHATSAPP_VERIFY_TOKEN, token):
        audit("whatsapp", client_ip(request), "webhook_verified", "", request_id(request))
        return int(challenge) if challenge and challenge.isdigit() else challenge
    raise_api("webhook_verification_failed", "Verification token mismatch.", 403)


@app.post("/api/whatsapp/webhook")
async def whatsapp_incoming_webhook(request: Request) -> dict[str, Any]:
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes.decode())
    except Exception:
        raise_api("invalid_json", "Payload is not valid JSON.", 400)
    audit("whatsapp", client_ip(request), "webhook_received", "", request_id(request))
    entries = payload.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                msg_id = msg.get("id") or str(uuid.uuid4())
                sender = msg.get("from", "unknown")
                kind = msg.get("type", "unknown")
                body = msg.get("text", {}).get("body", "") if kind == "text" else ""
                with closing(database()) as connection:
                    connection.execute("INSERT OR IGNORE INTO whatsapp_messages(id, provider_message_id, sender, message_type, body, status, created) VALUES(?, ?, ?, ?, ?, 'received', ?)", (str(uuid.uuid4()), msg_id, sender, kind, body, now()))
                    connection.commit()
                if kind == "text" and body:
                    try:
                        reply = await call_ai_provider(body, f"whatsapp-{sender}", request_id(request))
                        if WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID:
                            await send_official_whatsapp_message(sender, reply)
                    except Exception:
                        pass
    return {"status": "ok"}


@app.post("/api/whatsapp/send")
async def whatsapp_send_endpoint(payload: WhatsAppSendRequest, request: Request, x_device_id: str = Header(default=""), x_api_key: str = Header(default=""), x_session_token: str = Header(default="")) -> dict[str, Any]:
    sender = authenticate(request, x_device_id, x_api_key, x_session_token)
    enforce_rate_limit(request, "whatsapp_send", 20)
    try:
        result = await send_official_whatsapp_message(payload.to, payload.message)
    except RuntimeError as exc:
        audit(sender, client_ip(request), "whatsapp_send_failed", str(exc), request_id(request))
        raise_api("whatsapp_failed", str(exc), 502)
    with closing(database()) as connection:
        connection.execute("INSERT INTO whatsapp_messages(id, provider_message_id, sender, message_type, body, status, created) VALUES(?, ?, ?, 'text_outbound', ?, 'sent', ?)", (str(uuid.uuid4()), result.get("messages", [{}])[0].get("id", str(uuid.uuid4())), payload.to, payload.message, now()))
        connection.commit()
    audit(sender, client_ip(request), "whatsapp_sent", f"to={payload.to}", request_id(request))
    return {"ok": True, "result": result, "request_id": request_id(request)}
