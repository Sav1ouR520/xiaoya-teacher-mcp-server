import os
import sys

import xiaoya_teacher_mcp_server.tools  # noqa: F401
from xiaoya_teacher_mcp_server.config import MCP


def main():
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    mount_path = os.getenv("MCP_MOUNT_PATH", "/mcp")

    if transport not in ["stdio", "sse", "streamable-http"]:
        print(f"不支持的传输方式: {transport},使用stdio")
        transport = "stdio"

    try:
        print(f"启动MCP服务器,传输方式: {transport}")
        if mount_path and transport != "stdio":
            MCP.run(transport=transport, mount_path=mount_path)
        else:
            MCP.run(transport=transport)
    except KeyboardInterrupt:
        print("服务器已停止")
    except Exception as e:
        print(f"服务器运行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
