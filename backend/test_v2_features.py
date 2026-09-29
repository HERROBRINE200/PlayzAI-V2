import importlib
import json
import sqlite3
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import ai_manager
import ai_providers
import confirmation_manager
import risk_engine


@pytest.fixture
def v2_client(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_v2.db")
    monkeypatch.setenv("PLAYZAI_DB", db_path)
    monkeypatch.setenv("AUTH_SECRET", "test-auth-secret-v2")
    monkeypatch.setenv("PLAYZAI_ENROLLMENT_SECRET", "")
    monkeypatch.setenv("PLAYZAI_MASTER_KEY", "test-master-key-v2")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_BASE_URL", "")
    monkeypatch.setenv("AI_MODEL", "")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "60")

    sys.modules.pop("main", None)
    module = importlib.import_module("main")
    module.limiter.clear()
    client = TestClient(module.app)
    yield module, client, db_path
    client.close()
    sys.modules.pop("main", None)


def enroll(client, device_id="phone-v2", name="Android Device"):
    resp = client.post("/api/devices/register", json={"device_id": device_id, "name": name})
    assert resp.status_code == 200
    return resp.json()["api_key"]


def auth_headers(api_key, device_id="phone-v2"):
    return {"X-Device-ID": device_id, "X-API-Key": api_key}


def test_ai_provider_crud_and_key_masking(v2_client):
    module, client, _ = v2_client
    api_key = enroll(client)
    headers = auth_headers(api_key)

    # 1. Add Gemini Provider
    gemini_payload = {
        "provider_type": "gemini",
        "display_name": "Google Gemini Pro",
        "api_key": "AIzaSyTestSecretApiKeyForGemini12345",
        "base_url": "https://generativelanguage.googleapis.com",
        "default_model": "gemini-1.5-flash",
        "enabled": True,
        "priority": 1,
        "description": "Primary Gemini Provider",
    }
    create_resp = client.post("/api/ai/providers", headers=headers, json=gemini_payload)
    assert create_resp.status_code == 200
    prov = create_resp.json()["provider"]
    prov_id = prov["id"]
    assert prov["display_name"] == "Google Gemini Pro"
    assert prov["provider_type"] == "gemini"
    assert "AIzaSyTestSecretApiKeyForGemini12345" not in json.dumps(create_resp.json())
    assert "api_key_masked" in prov
    assert prov["has_key"] is True

    # 2. Add OpenAI Provider
    openai_payload = {
        "provider_type": "openai",
        "display_name": "OpenAI GPT-4o",
        "api_key": "sk-proj-SecretOpenAiKey998877665544",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "enabled": True,
        "priority": 2,
    }
    client.post("/api/ai/providers", headers=headers, json=openai_payload)

    # 3. List Providers
    list_resp = client.get("/api/ai/providers", headers=headers)
    assert list_resp.status_code == 200
    providers = list_resp.json()["providers"]
    assert len(providers) == 2
    assert providers[0]["priority"] == 1
    # Check that secrets are NEVER leaked in list
    assert "sk-proj-SecretOpenAiKey998877665544" not in list_resp.text
    assert "AIzaSyTestSecretApiKeyForGemini12345" not in list_resp.text

    # 4. Update Provider (retaining masked key)
    update_resp = client.put(
        f"/api/ai/providers/{prov_id}",
        headers=headers,
        json={"display_name": "Google Gemini 1.5 Updated", "priority": 3},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["provider"]["display_name"] == "Google Gemini 1.5 Updated"
    assert update_resp.json()["provider"]["has_key"] is True

    # 5. Delete Provider
    del_resp = client.delete(f"/api/ai/providers/{prov_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] == prov_id

    # Verify only 1 left
    list_resp2 = client.get("/api/ai/providers", headers=headers)
    assert len(list_resp2.json()["providers"]) == 1


def test_ai_settings_and_models_endpoints(v2_client):
    module, client, _ = v2_client
    api_key = enroll(client)
    headers = auth_headers(api_key)

    # Read default settings
    settings_resp = client.get("/api/ai/settings", headers=headers)
    assert settings_resp.status_code == 200
    settings = settings_resp.json()["settings"]
    assert settings["fallback_enabled"] == "true"
    assert settings["default_provider"] == "gemini"

    # Update settings
    update_resp = client.put(
        "/api/ai/settings",
        headers=headers,
        json={"default_provider": "openai", "default_model": "gpt-4o", "default_language": "hinglish"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()["settings"]
    assert updated["default_provider"] == "openai"
    assert updated["default_model"] == "gpt-4o"
    assert updated["default_language"] == "hinglish"

    # Custom Model CRUD
    model_resp = client.post(
        "/api/ai/models",
        headers=headers,
        json={"provider_id": "openai", "model_name": "custom-finetuned-model", "display_name": "Fine-Tuned Model"},
    )
    assert model_resp.status_code == 200
    model_id = model_resp.json()["model_id"]

    models_list = client.get("/api/ai/models", headers=headers)
    assert any(m["model_name"] == "custom-finetuned-model" for m in models_list.json()["models"])

    del_model = client.delete(f"/api/ai/models/{model_id}", headers=headers)
    assert del_model.status_code == 200


def test_provider_connection_test_live_dispatch(v2_client, monkeypatch):
    module, client, _ = v2_client
    api_key = enroll(client)
    headers = auth_headers(api_key)

    # Add test provider
    prov_resp = client.post(
        "/api/ai/providers",
        headers=headers,
        json={
            "provider_type": "openai",
            "display_name": "Test OpenAI",
            "api_key": "sk-mock-key-for-test",
            "default_model": "gpt-4o-mini",
        },
    )
    prov_id = prov_resp.json()["provider"]["id"]

    # Mock adapter test_connection
    async def mock_test(self, api_key, base_url, model, timeout_seconds=12.0):
        return {
            "ok": True,
            "latency_ms": 42.5,
            "models": ["gpt-4o", "gpt-4o-mini"],
            "detail": "Connected successfully to OpenAI.",
        }

    monkeypatch.setattr(ai_providers.OpenAIProvider, "test_connection", mock_test)

    test_resp = client.post(f"/api/ai/providers/{prov_id}/test", headers=headers)
    assert test_resp.status_code == 200
    body = test_resp.json()
    assert body["ok"] is True
    assert body["result"]["latency_ms"] == 42.5
    assert "gpt-4o" in body["result"]["models"]


def test_risk_classification_engine():
    # Level 1 Safe
    lvl1_cases = [
        ("get_status", {}),
        ("cpu", {}),
        ("ram", {}),
        ("storage", {}),
        ("network", {}),
        ("list_processes", {}),
        ("list_directory", {"path": "C:\\"}),
        ("open_app", {"name": "notepad"}),
        ("open_app", {"name": "chrome"}),
        ("open_app", {"name": "calc"}),
    ]
    for action, args in lvl1_cases:
        lvl, explanation = risk_engine.classify_task(action, args)
        assert lvl == risk_engine.LEVEL_1_SAFE, f"Expected SAFE for {action}, got {lvl}"

    # Level 2 Moderate
    lvl2_cases = [
        ("obs_start", {}),
        ("obs_record_start", {}),
        ("minecraft_start", {}),
        ("write_file", {"path": "C:\\Users\\User\\Documents\\test.txt"}),
        ("rename_file", {"path": "C:\\Users\\User\\notes.txt"}),
    ]
    for action, args in lvl2_cases:
        lvl, explanation = risk_engine.classify_task(action, args)
        assert lvl == risk_engine.LEVEL_2_MODERATE, f"Expected MODERATE for {action}, got {lvl}"

    # Level 3 High Risk / Heavy
    lvl3_cases = [
        ("shutdown", {}),
        ("restart", {}),
        ("delete_file", {"path": "C:\\temp\\data.txt"}),
        ("delete_folder", {"path": "D:\\backups"}),
        ("run_powershell", {"command": "Remove-Item -Recurse -Force C:\\test"}),
        ("run_powershell", {"command": "Set-ExecutionPolicy Unrestricted"}),
        ("run_command", {"command": "rmdir /s /q C:\\data"}),
        ("run_command", {"command": "format D: /fs:NTFS"}),
        ("run_command", {"command": "reg delete HKLM\\Software\\Test"}),
        ("run_powershell", {"command": "Stop-Computer -Force"}),
    ]
    for action, args in lvl3_cases:
        lvl, explanation = risk_engine.classify_task(action, args)
        assert lvl == risk_engine.LEVEL_3_HIGH, f"Expected HIGH RISK for {action}, got {lvl}"


def test_zero_trust_confirmation_security_lifecycle(v2_client):
    module, client, _ = v2_client
    api_key = enroll(client)
    headers = auth_headers(api_key)

    # 1. Create session
    sess_resp = client.post("/api/auth/session", headers=headers, json={})
    assert sess_resp.status_code == 200
    session_token = sess_resp.json()["session_token"]
    session_headers = {"X-Session-Token": session_token, "X-Device-ID": "phone-v2"}

    # 2. Register PC Agent
    pc_reg = client.post("/api/devices/register", json={"device_id": "pc-target", "name": "Windows Gaming PC"}).json()
    pc_headers = {"X-Device-ID": "pc-target", "X-API-Key": pc_reg["api_key"]}
    client.post("/api/agent/heartbeat", headers=pc_headers, json={"pc_name": "Windows Gaming PC", "network_status": "online"})

    # 3. Request high risk command without confirmation token
    high_risk_req = client.post(
        "/api/command",
        headers=session_headers,
        json={"device_id": "pc-target", "action": "delete_folder", "args": {"path": "D:\\temporary"}, "confirmation": False},
    )
    assert high_risk_req.status_code == 200
    assert high_risk_req.json()["requires_confirmation"] is True
    assert high_risk_req.json()["ok"] is False

    # 4. Generate confirmation through confirmation manager
    conn = module.database()
    conf = confirmation_manager.create_confirmation(
        connection=conn,
        session_token_hash=module.hash_credential(session_token),
        device_id="pc-target",
        action="delete_folder",
        command="Remove-Item -Recurse D:\\temporary",
        args={"path": "D:\\temporary"},
        risk_level=risk_engine.LEVEL_3_HIGH,
        risk_explanation="Destructive directory deletion.",
    )
    conf_id = conf["confirmation_id"]
    conn.close()

    # 5. Check pending confirmations list
    pending = client.get("/api/security/confirmations/pending", headers=session_headers)
    assert pending.status_code == 200
    assert any(c["id"] == conf_id for c in pending.json()["confirmations"])

    # 6. Confirm the action with active session
    confirm_resp = client.post(f"/api/security/confirmations/{conf_id}/confirm", headers=session_headers)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["ok"] is True
    queued_cmd_id = confirm_resp.json()["command_id"]

    # 7. Check that confirmation is consumed and CANNOT be reused (single use policy)
    replay_resp = client.post(f"/api/security/confirmations/{conf_id}/confirm", headers=session_headers)
    assert replay_resp.status_code == 400
    assert "already been used" in replay_resp.json()["error"]["message"]

    # 8. Check that PC agent receives the queued command
    agent_cmds = client.get("/api/agent/commands", headers=pc_headers)
    assert any(c["command_id"] == queued_cmd_id for c in agent_cmds.json()["commands"])

    # 9. Agent executes and reports result
    res_resp = client.post(
        f"/api/agent/commands/{queued_cmd_id}/result",
        headers=pc_headers,
        json={"ok": True, "result": {"exit_code": 0, "stdout": "Folder deleted successfully.", "stderr": ""}},
    )
    assert res_resp.status_code == 200

    # 10. Audit log verification
    audit_resp = client.get("/api/audit/logs", headers=session_headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["audit_logs"]
    assert any("delete_folder" in log["action"] and log["confirmation_status"] == "CONFIRMED" for log in logs)


def test_ai_multi_provider_fallback(v2_client, monkeypatch):
    module, client, _ = v2_client
    api_key = enroll(client)
    headers = auth_headers(api_key)

    # Configure Priority 1: Gemini (will fail with 429 Rate Limit)
    client.post(
        "/api/ai/providers",
        headers=headers,
        json={"provider_type": "gemini", "display_name": "Gemini 1", "api_key": "gemini-key", "priority": 1, "enabled": True},
    )

    # Configure Priority 2: OpenAI (will succeed)
    client.post(
        "/api/ai/providers",
        headers=headers,
        json={"provider_type": "openai", "display_name": "OpenAI 2", "api_key": "openai-key", "priority": 2, "enabled": True},
    )

    # Mock Gemini to raise RateLimited
    async def gemini_rate_limit(*args, **kwargs):
        raise ai_providers.RateLimited("Google Gemini rate limit exceeded.")

    # Mock OpenAI to return valid response
    async def openai_success(*args, **kwargs):
        return {"reply": "Response from OpenAI fallback.", "model": "gpt-4o-mini", "provider": "openai", "raw": {}}

    monkeypatch.setattr(ai_providers.GeminiProvider, "generate_response", gemini_rate_limit)
    monkeypatch.setattr(ai_providers.OpenAIProvider, "generate_response", openai_success)

    # Call chat
    chat_resp = client.post("/api/chat", headers=headers, json={"message": "Hello Multi-AI", "conversation_id": "fallback-conv"})
    assert chat_resp.status_code == 200
    assert chat_resp.json()["reply"] == "Response from OpenAI fallback."

    # Verify audit logs captured fallback
    audit_resp = client.get("/api/audit/logs", headers=headers)
    logs = audit_resp.json()["audit_logs"]
    assert any(log["result"] == "FALLBACK_TRIGGERED" for log in logs)


def test_audit_logs_scrub_credentials(v2_client):
    module, client, _ = v2_client
    api_key = enroll(client)
    headers = auth_headers(api_key)

    conn = module.database()
    ai_manager.record_audit_log(
        connection=conn,
        action="Test Action",
        risk_level=risk_engine.LEVEL_3_HIGH,
        result="TEST",
        command="connect --api_key sk-1234567890abcdef1234567890 --token=supersecrettoken",
        detail="user password=SecretPassword123! and Gemini key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q",
    )
    conn.close()

    logs_resp = client.get("/api/audit/logs", headers=headers)
    assert logs_resp.status_code == 200
    logs_text = logs_resp.text
    # Assert NO secret leaked into the output
    assert "sk-1234567890abcdef1234567890" not in logs_text
    assert "supersecrettoken" not in logs_text
    assert "SecretPassword123!" not in logs_text
    assert "AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q" not in logs_text
    assert "[REDACTED" in logs_text
