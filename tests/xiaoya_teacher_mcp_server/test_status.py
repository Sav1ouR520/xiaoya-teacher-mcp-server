from xiaoya_teacher_mcp_server import config as cfg
from xiaoya_teacher_mcp_server.main import _mask_sensitive_headers
from xiaoya_teacher_mcp_server.tools import status


def test_mask_sensitive_headers_redacts_credentials():
    headers = {
        "authorization": "Bearer secret-token",
        "x-xiaoya-password": "super-secret",
        "x-xiaoya-account": "teacher",
    }

    result = _mask_sensitive_headers(headers)

    assert result["authorization"] == "<redacted>"
    assert result["x-xiaoya-password"] == "<redacted>"
    assert result["x-xiaoya-account"] == "teacher"


def test_auth_status_hides_token(monkeypatch):
    state = cfg.auth_state
    monkeypatch.setattr(state, "is_initialized", True)
    monkeypatch.setattr(state, "cached_token", "Bearer secret-token")
    token = state.request_transport.set("stdio")
    try:
        result = status.auth_status()
    finally:
        state.request_transport.reset(token)

    assert result["success"]
    assert result["data"]["token_present"] is True
    assert "token" not in result["data"]


def test_auth_status_remote_refresh_forces_active_token_refresh(monkeypatch):
    state = cfg.auth_state
    called = {"refresh": 0}

    def fake_refresh_active_token():
        called["refresh"] += 1
        return "Bearer refreshed"

    monkeypatch.setattr(cfg, "refresh_active_token", fake_refresh_active_token)
    transport_token = state.request_transport.set("sse")
    token_token = state.request_token.set("Bearer old")
    account_token = state.request_account.set("teacher")
    password_token = state.request_password.set("secret")
    try:
        result = status.auth_status(refresh=True)
    finally:
        state.request_transport.reset(transport_token)
        state.request_token.reset(token_token)
        state.request_account.reset(account_token)
        state.request_password.reset(password_token)

    assert result["success"]
    assert called["refresh"] == 1
    assert result["data"]["replaced"] is True
