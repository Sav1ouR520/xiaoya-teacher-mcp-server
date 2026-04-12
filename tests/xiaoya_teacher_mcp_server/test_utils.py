import json

import pytest
import requests

from xiaoya_teacher_mcp_server.tools.questions import create
from xiaoya_teacher_mcp_server.types import AutoScoreType, FillBlankAnswer, FillBlankQuestion
from xiaoya_teacher_mcp_server.utils import client, rich_text
from xiaoya_teacher_mcp_server.utils.response import ResponseUtil


class DummyResponse:
    def __init__(self, *, status_code=200, json_data=None, json_exc=None):
        self.status_code = status_code
        self._json_data = json_data
        self._json_exc = json_exc

    def raise_for_status(self):
        if self.status_code >= 400:
            response = requests.Response()
            response.status_code = self.status_code
            raise requests.HTTPError(response=response)

    def json(self):
        if self._json_exc:
            raise self._json_exc
        return self._json_data


def test_request_json_wraps_http_error(monkeypatch):
    monkeypatch.setattr(client, "headers", lambda: {})
    monkeypatch.setattr(
        client.requests,
        "request",
        lambda *args, **kwargs: DummyResponse(status_code=503, json_data={"success": False}),
    )

    with pytest.raises(client.APIRequestError, match="HTTP 请求失败: 503"):
        client.request_json("GET", "https://example.com")


def test_request_json_wraps_non_json_response(monkeypatch):
    monkeypatch.setattr(client, "headers", lambda: {})
    monkeypatch.setattr(
        client.requests,
        "request",
        lambda *args, **kwargs: DummyResponse(json_exc=ValueError("bad json")),
    )

    with pytest.raises(client.APIRequestError, match="非 JSON"):
        client.request_json("GET", "https://example.com")


def test_request_json_wraps_timeout(monkeypatch):
    monkeypatch.setattr(client, "headers", lambda: {})

    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(client.requests, "request", raise_timeout)

    with pytest.raises(client.APIRequestError, match="HTTP 请求超时"):
        client.request_json("GET", "https://example.com")


def test_request_json_refreshes_and_retries_on_http_401(monkeypatch):
    calls = {"count": 0}

    monkeypatch.setattr(client, "headers", lambda: {})
    monkeypatch.setattr(client, "refresh_active_token", lambda: "Bearer refreshed")

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return DummyResponse(status_code=401, json_data={"success": False})
        return DummyResponse(status_code=200, json_data={"success": True, "data": {"ok": True}})

    monkeypatch.setattr(client.requests, "request", fake_request)

    result = client.request_json("GET", "https://example.com")

    assert result == {"success": True, "data": {"ok": True}}
    assert calls["count"] == 2


def test_request_response_refreshes_and_retries_on_http_401(monkeypatch):
    calls = {"count": 0}

    monkeypatch.setattr(client, "headers", lambda: {})
    monkeypatch.setattr(client, "refresh_active_token", lambda: "Bearer refreshed")

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return DummyResponse(status_code=401, json_data={"success": False})
        return DummyResponse(status_code=200, json_data={"success": True})

    monkeypatch.setattr(client.requests, "request", fake_request)

    result = client.request_response("GET", "https://example.com")

    assert result.status_code == 200
    assert calls["count"] == 2


def test_request_json_refreshes_and_retries_on_business_auth_error(monkeypatch):
    calls = {"count": 0}

    monkeypatch.setattr(client, "headers", lambda: {})
    monkeypatch.setattr(client, "refresh_active_token", lambda: "Bearer refreshed")

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return DummyResponse(status_code=200, json_data={"success": False, "message": "token expired"})
        return DummyResponse(status_code=200, json_data={"success": True, "data": {"ok": True}})

    monkeypatch.setattr(client.requests, "request", fake_request)

    result = client.request_json("GET", "https://example.com")

    assert result == {"success": True, "data": {"ok": True}}
    assert calls["count"] == 2


def test_expect_success_raises_on_business_error():
    with pytest.raises(client.APIRequestError, match="失败原因"):
        client.expect_success({"success": False, "msg": "失败原因"})


def test_rich_text_plain_raw_round_trip():
    raw_text = rich_text.plain_text_to_rich_text_raw("hello")
    raw_dict = json.loads(raw_text)

    assert rich_text.render_rich_text_output(raw_text, "plain") == "hello"
    assert rich_text.render_rich_text_output(raw_text, "raw") == raw_dict


def test_normalize_rich_text_input_prefers_raw():
    raw = {"blocks": [{"text": "raw title"}], "entityMap": {}}

    assert json.loads(
        rich_text.normalize_rich_text_input(text="plain title", raw=raw)
    ) == raw


def test_response_success_preserves_naive_iso_time_without_blind_offset():
    result = ResponseUtil.success({"created_at": "2026-03-09T08:00:00"})

    assert result["success"]
    assert result["data"]["created_at"] == "2026-03-09 08:00:00"


def test_response_error_returns_compact_message():
    result = ResponseUtil.error("操作失败", ValueError("bad input"))

    assert not result["success"]
    assert result["message"] == "操作失败: ValueError: bad input"
    assert "Traceback" not in result["message"]


def test_response_error_can_include_data():
    result = ResponseUtil.error(
        "批量操作部分失败",
        data={"failed_items": [{"question_id": "q1", "message": "not found"}]},
    )

    assert not result["success"]
    assert result["data"]["failed_items"] == [{"question_id": "q1", "message": "not found"}]


def test_fill_blank_validation_runs_before_remote_creation(monkeypatch):
    called = False

    def fake_create_question_data(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("should not be called")

    monkeypatch.setattr(create, "create_question_data", fake_create_question_data)

    result = create.create_fill_blank_question(
        "paper-1",
        FillBlankQuestion(
            title="题目里没有空白标记",
            description="desc",
            options=[FillBlankAnswer(text="答案")],
            automatic_type=AutoScoreType.EXACT_ORDERED,
            score=5,
        ),
    )

    assert not result["success"]
    assert called is False
    assert "必须包含空白标记" in result["message"]
