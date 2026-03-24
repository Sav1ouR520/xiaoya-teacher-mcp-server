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
