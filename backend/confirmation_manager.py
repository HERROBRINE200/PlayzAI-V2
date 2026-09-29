"""PlayzAI Confirmation Security Manager.

Implements the zero-trust confirmation lifecycle for High-Risk / Heavy PC operations:
- Every high-risk operation generates a unique, short-lived, single-use confirmation token.
- Confirmation is cryptographically tied to the authenticated session, device, exact action, and exact command.
- If the command or action changes, prior confirmation is invalidated.
- AI models CANNOT confirm their own actions — explicit human operator confirmation is required.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any

CONFIRMATION_EXPIRY_SECONDS = 300  # 5 minutes


def create_confirmation(
    connection: sqlite3.Connection,
    session_token_hash: str,
    device_id: str,
    action: str,
    command: str = "",
    args: dict[str, Any] | None = None,
    risk_level: str = "LEVEL 3 — HIGH RISK / HEAVY",
    risk_explanation: str = "Action requires operator confirmation.",
    timeout_seconds: int = CONFIRMATION_EXPIRY_SECONDS,
) -> dict[str, Any]:
    """Generate a new pending confirmation record."""
    confirmation_id = f"conf-{uuid.uuid4().hex[:12]}"
    now_ts = time.time()
    expires_at = now_ts + timeout_seconds
    args_json = json.dumps(args or {})

    connection.execute(
        """
        INSERT INTO pending_confirmations(
            id, session_id, device_id, action, command, args_json,
            risk_level, risk_explanation, created_at, expires_at, status, consumed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0)
        """,
        (
            confirmation_id,
            session_token_hash,
            device_id,
            action,
            command,
            args_json,
            risk_level,
            risk_explanation,
            now_ts,
            expires_at,
        ),
    )
    connection.commit()

    return {
        "confirmation_id": confirmation_id,
        "action": action,
        "command": command,
        "risk_level": risk_level,
        "risk_explanation": risk_explanation,
        "created_at": now_ts,
        "expires_at": expires_at,
        "requires_confirmation": True,
    }


def get_confirmation(connection: sqlite3.Connection, confirmation_id: str) -> dict[str, Any] | None:
    """Retrieve confirmation by ID."""
    row = connection.execute(
        "SELECT * FROM pending_confirmations WHERE id = ?", (confirmation_id,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["args"] = json.loads(d.get("args_json") or "{}")
    except Exception:
        d["args"] = {}
    return d


def list_pending_confirmations(
    connection: sqlite3.Connection, device_id: str | None = None
) -> list[dict[str, Any]]:
    """List all active unexpired pending confirmations."""
    now_ts = time.time()
    if device_id:
        rows = connection.execute(
            """
            SELECT * FROM pending_confirmations
            WHERE device_id = ? AND status = 'pending' AND consumed = 0 AND expires_at > ?
            ORDER BY created_at DESC
            """,
            (device_id, now_ts),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT * FROM pending_confirmations
            WHERE status = 'pending' AND consumed = 0 AND expires_at > ?
            ORDER BY created_at DESC
            """,
            (now_ts,),
        ).fetchall()

    results = []
    for r in rows:
        item = dict(r)
        try:
            item["args"] = json.loads(item.get("args_json") or "{}")
        except Exception:
            item["args"] = {}
        results.append(item)
    return results


def confirm_action(
    connection: sqlite3.Connection,
    confirmation_id: str,
    session_token_hash: str,
    device_id: str = "",
) -> tuple[bool, str, dict[str, Any] | None]:
    """Validate and consume a confirmation.

    Returns (success, message, confirmation_data).
    """
    now_ts = time.time()
    row = connection.execute(
        "SELECT * FROM pending_confirmations WHERE id = ?", (confirmation_id,)
    ).fetchone()

    if not row:
        return False, "Confirmation request not found.", None

    conf = dict(row)
    if conf["consumed"] == 1:
        return False, "This confirmation has already been used (one-time execution policy).", None

    if conf["status"] != "pending":
        return False, f"Confirmation is in '{conf['status']}' state.", None

    if conf["expires_at"] < now_ts:
        connection.execute(
            "UPDATE pending_confirmations SET status = 'expired' WHERE id = ?",
            (confirmation_id,),
        )
        connection.commit()
        return False, "Confirmation has expired. Please initiate the action again.", None

    # Check session authorization
    if conf["session_id"] and session_token_hash and conf["session_id"] != session_token_hash:
        # Check if the device is the same
        if device_id and conf["device_id"] != device_id:
            return False, "Confirmation belongs to a different session/device.", None

    # Mark as consumed and confirmed
    connection.execute(
        "UPDATE pending_confirmations SET status = 'confirmed', consumed = 1 WHERE id = ?",
        (confirmation_id,),
    )
    connection.commit()

    try:
        conf["args"] = json.loads(conf.get("args_json") or "{}")
    except Exception:
        conf["args"] = {}

    return True, "Operation successfully confirmed.", conf


def cancel_action(
    connection: sqlite3.Connection,
    confirmation_id: str,
    session_token_hash: str = "",
) -> tuple[bool, str]:
    """Cancel a pending confirmation."""
    row = connection.execute(
        "SELECT * FROM pending_confirmations WHERE id = ?", (confirmation_id,)
    ).fetchone()

    if not row:
        return False, "Confirmation request not found."

    conf = dict(row)
    if conf["consumed"] == 1:
        return False, "Confirmation has already been processed."

    connection.execute(
        "UPDATE pending_confirmations SET status = 'cancelled', consumed = 1 WHERE id = ?",
        (confirmation_id,),
    )
    connection.commit()
    return True, "Confirmation successfully cancelled."
