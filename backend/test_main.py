import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def backend_client(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYZAI_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("AUTH_SECRET", "test-auth-secret")
    monkeypatch.setenv("PLAYZAI_ENROLLMENT_SECRET", "")
    monkeypatch.setenv("PLAYZAI_MASTER_KEY", "test-master-key")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_BASE_URL", "")
    monkeypatch.setenv("AI_MODEL", "")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "30")

    sys.modules.pop("main", None)
    module = importlib.import_module("main")
    module.limiter.clear()
    client = TestClient(module.app)
    yield module, client
    client.close()
    sys.modules.pop("main", None)


def enroll(client):
    response = client.post(
        "/api/devices/register",
        json={"device_id": "phone-test", "name": "Test Android"},
    )
    assert response.status_code == 200, response.text
    return response.json()["api_key"]


def auth_headers(api_key):
    return {"X-Device-ID": "phone-test", "X-API-Key": api_key}


def test_health_does_not_expose_provider_secret(backend_client):
    _, client = backend_client
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["provider_configured"] is False
    assert "AI_API_KEY" not in response.text
    assert response.headers["X-Request-ID"] == body["request_id"]


def test_authenticated_session_and_status(backend_client):
    _, client = backend_client
    api_key = enroll(client)
    session = client.post("/api/auth/session", headers=auth_headers(api_key), json={})
    assert session.status_code == 200
    session_token = session.json()["session_token"]
    assert session_token
    status_response = client.get("/api/auth/status", headers={"X-Session-Token": session_token})
    assert status_response.status_code == 200
    assert status_response.json()["authenticated"] is True


def test_invalid_authentication_is_rejected(backend_client):
    _, client = backend_client
    enroll(client)
    response = client.post(
        "/api/chat",
        headers={"X-Device-ID": "phone-test", "X-API-Key": "wrong-key"},
        json={"message": "Hello", "conversation_id": "auth-test"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_authentication"
    assert "Traceback" not in response.text


def test_english_chat_contract(backend_client, monkeypatch):
    module, client = backend_client
    api_key = enroll(client)

    async def fake_provider(message, conversation_id, request_id):
        assert message == "Hello PlayzAI"
        return "Hello! I am PlayzAI."

    monkeypatch.setattr(module, "call_ai_provider", fake_provider)
    response = client.post(
        "/api/chat",
        headers=auth_headers(api_key),
        json={"message": "Hello PlayzAI", "conversation_id": "english-1"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "reply": "Hello! I am PlayzAI.",
        "conversation_id": "english-1",
        "request_id": response.headers["X-Request-ID"],
    }


def test_hindi_unicode_chat_contract(backend_client, monkeypatch):
    module, client = backend_client
    api_key = enroll(client)

    async def fake_provider(message, conversation_id, request_id):
        assert "नमस्ते" in message
        return "नमस्ते! मैं PlayzAI हूँ।"

    monkeypatch.setattr(module, "call_ai_provider", fake_provider)
    response = client.post(
        "/api/chat",
        headers=auth_headers(api_key),
        json={"message": "नमस्ते PlayzAI", "conversation_id": "hindi-1"},
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "नमस्ते! मैं PlayzAI हूँ।"


def test_provider_not_configured_is_not_faked(backend_client):
    _, client = backend_client
    api_key = enroll(client)
    response = client.post(
        "/api/chat",
        headers=auth_headers(api_key),
        json={"message": "Hello", "conversation_id": "no-provider"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_not_configured"


def test_provider_unavailable_and_timeout_are_safe(backend_client, monkeypatch):
    module, client = backend_client
    api_key = enroll(client)

    async def unavailable(message, conversation_id, request_id):
        raise module.ProviderUnavailable()

    monkeypatch.setattr(module, "call_ai_provider", unavailable)
    response = client.post("/api/chat", headers=auth_headers(api_key), json={"message": "Hello"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_unavailable"
    assert "Traceback" not in response.text

    async def timed_out(message, conversation_id, request_id):
        raise module.ProviderTimedOut()

    monkeypatch.setattr(module, "call_ai_provider", timed_out)
    response = client.post("/api/chat", headers=auth_headers(api_key), json={"message": "Hello again"})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "provider_timeout"


def test_rate_limiting(backend_client, monkeypatch):
    module, client = backend_client
    api_key = enroll(client)
    module.RATE_LIMIT_PER_MINUTE = 1

    async def fake_provider(message, conversation_id, request_id):
        return "ok"

    monkeypatch.setattr(module, "call_ai_provider", fake_provider)
    headers = auth_headers(api_key)
    assert client.post("/api/chat", headers=headers, json={"message": "one"}).status_code == 200
    limited = client.post("/api/chat", headers=headers, json={"message": "two"})
    assert limited.status_code == 429
    assert limited.headers.get("Retry-After")
    assert limited.json()["error"]["code"] == "rate_limited"


def test_malformed_request(backend_client):
    _, client = backend_client
    response = client.post("/api/chat", json={"conversation_id": "missing-message"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "malformed_request"
    assert "Traceback" not in response.text


def test_device_and_security_read_routes_are_authenticated(backend_client):
    _, client = backend_client
    api_key = enroll(client)
    headers = auth_headers(api_key)

    devices = client.get("/api/devices", headers=headers)
    assert devices.status_code == 200
    assert devices.json()["devices"][0]["device_id"] == "phone-test"
    assert devices.json()["devices"][0]["authenticated"] is True

    events = client.get("/api/security/events", headers=headers)
    assert events.status_code == 200
    assert any(event["event"] == "device_registered" for event in events.json()["events"])


def test_device_revoke_requires_owner_confirmation(backend_client):
    _, client = backend_client
    enroll(client)
    response = client.post(
        "/api/devices/revoke",
        headers={"X-API-Key": "test-master-key"},
        json={"device_id": "pc-test", "confirmation": False},
    )
    assert response.status_code == 200
    assert response.json()["requires_confirmation"] is True


def test_existing_safe_command_route_does_not_allow_shell(backend_client):
    _, client = backend_client
    api_key = enroll(client)
    response = client.post(
        "/api/command",
        headers=auth_headers(api_key),
        json={"device_id": "phone-test", "action": "run_command", "args": {"command": "whoami"}},
    )
    assert response.status_code == 200
    assert response.json()["requires_confirmation"] is True
    assert response.json()["ok"] is False


def test_extended_health_whatsapp_and_agent_queue(backend_client):
    _, client = backend_client
    phone_key = enroll(client)
    assert client.post('/health').json()['database_status'] == 'ok'
    assert client.get('/api/whatsapp/status').json()['configured'] is False
    pc = client.post('/api/devices/register', json={'device_id':'pc-agent','name':'Windows PC'}).json()
    pc_headers = {'X-Device-ID':'pc-agent','X-API-Key':pc['api_key']}
    heartbeat = client.post('/api/agent/heartbeat', headers=pc_headers, json={'agent_version':'1.0.0','pc_name':'Test PC','network_status':'online'})
    assert heartbeat.status_code == 200
    command = client.post('/api/command', headers=auth_headers(phone_key), json={'device_id':'pc-agent','action':'notify','args':{'message':'hello'}})
    assert command.status_code == 200
    command_id = command.json()['command_id']
    pending = client.get('/api/agent/commands', headers=pc_headers)
    assert pending.json()['commands'][0]['command_id'] == command_id
    result = client.post(f'/api/agent/commands/{command_id}/result', headers=pc_headers, json={'ok':True,'result':{'delivered':True}})
    assert result.status_code == 200
    history = client.get('/api/commands', headers=auth_headers(phone_key))
    assert history.json()['commands'][0]['status'] == 'completed'


def test_pairing_and_realtime_channel(backend_client):
    _, client = backend_client
    phone_key = enroll(client)
    code_response = client.post('/api/pairing/codes', headers=auth_headers(phone_key), json={'pc_name':'Pair PC'})
    assert code_response.status_code == 200
    claim = client.post('/api/pairing/claim', json={'code':code_response.json()['pairing_code'],'device_id':'paired-pc','name':'Paired PC'})
    assert claim.status_code == 200
    with client.websocket_connect('/ws', headers=auth_headers(phone_key)) as socket:
        assert socket.receive_json()['type'] == 'connected'
        socket.send_json({'type':'ping'})
        assert socket.receive_json()['type'] == 'pong'


def test_wol_is_explicitly_unconfigured(backend_client):
    _, client = backend_client
    phone_key = enroll(client)
    pc = client.post('/api/devices/register', json={'device_id':'pc-wol','name':'Wake PC'}).json()
    configure = client.post('/api/pcs', headers=auth_headers(phone_key), json={'pc_id':'pc-wol-record','device_id':'pc-wol','name':'Wake PC'})
    assert configure.json()['wake_on_lan'] == 'not_configured'
    response = client.post('/api/pcs/pc-wol-record/wake', headers=auth_headers(phone_key), json={'confirmation':True})
    assert response.json()['wake_on_lan'] == 'not_configured'
