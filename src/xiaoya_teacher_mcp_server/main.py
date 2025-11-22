import os
import sys
import threading

import uvicorn
from starlette.routing import Mount
from starlette.applications import Starlette

import logging
from xiaoya_teacher_mcp_server import tools  # noqa: F401
from xiaoya_teacher_mcp_server.config import MCP, request_context

VALID = {"stdio", "sse", "streamable-http"}


def _start_transports(transports, mount_path):
    other = transports - {"stdio"}
    if not other:
        return

    logger = logging.getLogger("xiaoya_teacher_mcp_server.transports")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s %(message)s")
        )
        logger.addHandler(handler)
        logger.propagate = False

    def wrap(app, transport):
        async def _wrapped(scope, receive, send):
            if scope.get("type") != "http":
                await app(scope, receive, send)
                return
            headers = {
                k.decode("latin-1").lower(): v.decode("latin-1")
                for k, v in (scope.get("headers") or [])
            }
            client = scope.get("client") or ("-", "-")
            method = scope.get("method", "GET")
            path = scope.get("path", "-")
            protocol = scope.get("http_version", "1.1")
            auth_ok = headers.get("authorization") or (
                headers.get("x-xiaoya-account") and headers.get("x-xiaoya-password")
            )
            if transport != "stdio" and not auth_ok:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json; charset=utf-8")
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b'{"error":"missing credentials"}',
                    }
                )
                logger.warning(
                    "Unauthorized %s request to %s over %s from %s:%s | Headers: %s"
                    % (method, path, protocol, client[0], client[1], headers)
                )
                return
            logger.info(
                "Accepted %s request to %s over %s from %s:%s | Headers: %s"
                % (method, path, protocol, client[0], client[1], headers)
            )
            with request_context(
                transport=transport,
                authorization=headers.get("authorization"),
                account=headers.get("x-xiaoya-account"),
                password=headers.get("x-xiaoya-password"),
            ):
                await app(scope, receive, send)

        return _wrapped

    routes = []
    if "streamable-http" in other:
        routes.append(
            Mount("/", app=wrap(MCP.streamable_http_app(), "streamable-http"))
        )
    if "sse" in other:
        routes.append(Mount(mount_path, app=wrap(MCP.sse_app(), "sse")))
    if routes:
        uvicorn.run(
            Starlette(debug=MCP.settings.debug, routes=routes),
            host=MCP.settings.host,
            port=MCP.settings.port,
            log_level=MCP.settings.log_level.lower(),
        )


def main():
    try:
        raw = {
            p.strip()
            for p in os.getenv("MCP_TRANSPORT", "").lower().split(",")
            if p.strip()
        }
        transports = raw & VALID
        invalid = raw - VALID
        if invalid:
            print(f"忽略无效传输: {sorted(invalid)}")
        host = os.getenv("MCP_HOST")
        port = os.getenv("MCP_PORT")
        if host:
            MCP.settings.host = host
        if port:
            try:
                MCP.settings.port = int(port)
            except ValueError:
                print(f"无效端口 {port}, 使用默认 {MCP.settings.port}")
        mount_path = os.getenv("MCP_MOUNT_PATH", "/mcp")
        if transports - {"stdio"}:
            threading.Thread(
                target=_start_transports, args=(transports, mount_path), daemon=True
            ).start()
        print("启动 MCP 服务器: stdio (延迟认证初始化)")
        MCP.run(transport="stdio")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
