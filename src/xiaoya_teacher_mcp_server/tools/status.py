import os
from typing import Any, Dict

from xiaoya_teacher_mcp_server.config import MCP
from xiaoya_teacher_mcp_server.utils.response import ResponseUtil
from xiaoya_teacher_mcp_server import config as cfg


@MCP.tool()
def server_status() -> Dict[str, Any]:
    """返回当前 MCP 服务器运行模式、URL 与端口信息。"""

    # 规范化挂载路径
    mount = os.getenv("MCP_MOUNT_PATH", "/mcp") or "/"
    mount = "/" + mount.lstrip("/")
    if len(mount) > 1 and mount.endswith("/"):
        mount = mount[:-1]

    # 路径拼接
    def _join(prefix: str, suffix: str) -> str:
        suffix = "/" + suffix.lstrip("/")
        return suffix if prefix in ("", "/") else prefix.rstrip("/") + suffix

    # 启用的传输方式
    extras = {
        p.strip()
        for p in os.getenv("MCP_TRANSPORT", "").lower().split(",")
        if p.strip()
    }
    transports = ["stdio"] + sorted(
        t for t in extras if t in {"sse", "streamable-http"}
    )

    return ResponseUtil.success(
        {
            "transports": transports,
            "baseUrl": f"http://{MCP.settings.host}:{MCP.settings.port}",
            "paths": {
                "streamable_http": MCP.settings.streamable_http_path,
                "sse_stream": _join(mount, MCP.settings.sse_path),
                "sse_messages": _join(mount, MCP.settings.message_path),
            },
        },
        "MCP 服务器状态获取成功",
    )


@MCP.tool()
def auth_status(refresh: bool = False) -> Dict[str, Any]:
    """返回当前认证信息。"""
    try:
        state = cfg.auth_state
        transport = state.request_transport.get()
        token, account, source, replaced = None, None, None, False

        if transport == "stdio":
            account = os.getenv("XIAOYA_ACCOUNT")
            if not state.is_initialized:
                cfg.initialize_auth()
            token = state.cached_token
            source = "env"
            if refresh and account and (pwd := os.getenv("XIAOYA_PASSWORD")):
                norm = cfg._normalize_token(cfg.login(account, pwd))
                if norm:
                    state.cached_token = norm
                    token = norm
                    replaced = True
                    source = "provided"
        else:
            token = state.request_token.get()
            account = state.request_account.get()
            source = "header" if token else None
            if refresh and account and (pwd := state.request_password.get()):
                new = cfg.resolve_request_token(account=account, password=pwd)
                if new:
                    state.request_token.set(new)
                    token = new
                    replaced = True
                    source = "provided"

        if not token:
            return ResponseUtil.error("认证令牌不存在或登录失败")
        return ResponseUtil.success(
            {
                "token": token,
                "transport": transport,
                "account": account,
                "replaced": replaced,
                "source": source,
            },
            "认证状态获取成功",
        )
    except Exception as e:
        return ResponseUtil.error("获取或更新认证状态失败", e)
