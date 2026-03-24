"""Shared HTTP helpers for XiaoYa API requests."""

from __future__ import annotations

from typing import Any, Optional

import requests

from ..config import headers, refresh_active_token
from .logging import get_logger

DEFAULT_TIMEOUT = 20
LOGGER = get_logger("xiaoya_teacher_mcp_server.http")


class APIRequestError(RuntimeError):
    """Raised when an API request fails or returns an invalid response."""


def extract_response_message(
    response: dict[str, Any], default: str = "未知错误"
) -> str:
    message = response.get("msg") or response.get("message")
    if isinstance(message, dict):
        return str(message.get("message") or message.get("msg") or default)
    return str(message or default)


def _parse_json_response(response: requests.Response) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError as exc:
        raise APIRequestError("接口返回了非 JSON 响应") from exc


def _looks_like_auth_error(response: dict[str, Any]) -> bool:
    message = extract_response_message(response, "").strip().lower()
    if not message:
        return False
    markers = (
        "unauthorized",
        "invalid token",
        "token expired",
        "token无效",
        "token过期",
        "认证失败",
        "未授权",
        "未登录",
        "登录失效",
        "登录过期",
    )
    return any(marker in message for marker in markers)


def request_json(
    method: str,
    url: str,
    *,
    params: Optional[dict[str, Any]] = None,
    payload: Optional[dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    allow_http_error: bool = False,
) -> dict[str, Any]:
    response = None
    refreshed = False

    while True:
        try:
            response = requests.request(
                method,
                url,
                headers=headers(),
                params=params,
                json=payload,
                timeout=timeout,
            )
            if response.status_code == 401 and not refreshed:
                new_token = refresh_active_token()
                if new_token:
                    refreshed = True
                    LOGGER.info("检测到 401，已自动刷新认证并重试请求")
                    continue

            if not allow_http_error:
                response.raise_for_status()
        except requests.Timeout as exc:
            raise APIRequestError("HTTP 请求超时") from exc
        except requests.HTTPError as exc:
            status_code = (
                exc.response.status_code
                if exc.response is not None
                else (response.status_code if response is not None else "unknown")
            )
            raise APIRequestError(f"HTTP 请求失败: {status_code}") from exc
        except requests.RequestException as exc:
            raise APIRequestError(f"HTTP 请求失败: {exc.__class__.__name__}") from exc

        parsed = _parse_json_response(response)
        if (
            not parsed.get("success")
            and not refreshed
            and _looks_like_auth_error(parsed)
        ):
            new_token = refresh_active_token()
            if new_token:
                refreshed = True
                LOGGER.info("检测到认证失效响应，已自动刷新认证并重试请求")
                continue
        return parsed


def get_json(
    url: str,
    *,
    params: Optional[dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    allow_http_error: bool = False,
) -> dict[str, Any]:
    return request_json(
        "GET",
        url,
        params=params,
        timeout=timeout,
        allow_http_error=allow_http_error,
    )


def post_json(
    url: str,
    *,
    payload: Optional[dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    allow_http_error: bool = False,
) -> dict[str, Any]:
    return request_json(
        "POST",
        url,
        payload=payload,
        timeout=timeout,
        allow_http_error=allow_http_error,
    )


def expect_success(response: dict[str, Any], default: str = "未知错误") -> Any:
    if response.get("success"):
        return response.get("data")
    raise APIRequestError(extract_response_message(response, default))
