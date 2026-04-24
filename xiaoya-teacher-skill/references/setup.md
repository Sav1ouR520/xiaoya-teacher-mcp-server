# 安装配置指南

当老师反馈工具调用失败或找不到工具时，引导他们完成以下配置。

## 通用 MCP 配置

在 MCP 配置文件中添加（推荐账号密码方式，自动登录和缓存）：

```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-server": {
      "command": "uvx",
      "args": ["xiaoya-teacher-mcp-server"],
      "env": {
        "XIAOYA_ACCOUNT": "你的小雅账号",
        "XIAOYA_PASSWORD": "你的小雅密码"
      }
    }
  }
}
```

也可以用 Token 方式认证（需要手动管理 token 过期）：
```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-server": {
      "command": "uvx",
      "args": ["xiaoya-teacher-mcp-server"],
      "env": {
        "XIAOYA_AUTH_TOKEN": "你的Bearer Token"
      }
    }
  }
}
```

## Codex / OpenAI Agents

在支持 MCP 的 Codex 或 OpenAI agent 环境中，服务名保持为：

```text
xiaoya-teacher-mcp-server
```

本地 stdio 启动命令：

```text
uvx xiaoya-teacher-mcp-server
```

环境变量认证仍使用：

```text
XIAOYA_ACCOUNT=你的小雅账号
XIAOYA_PASSWORD=你的小雅密码
```

或：

```text
XIAOYA_AUTH_TOKEN=你的Bearer Token
```

如果 agent 能看到工具但调用返回认证失败，先调用 `server_status` 确认服务在线，再调用 `auth_status(refresh=true)` 检查登录状态。

## 远程部署（多人共用）

启用 SSE 或 Streamable HTTP 传输：
```json
{
  "env": {
    "MCP_TRANSPORT": "sse",
    "MCP_HOST": "0.0.0.0",
    "MCP_PORT": "8000",
    "MCP_MOUNT_PATH": "/mcp"
  }
}
```
远程访问时通过 HTTP Header 传递认证信息：
```
X-XIAOYA-ACCOUNT: 账号
X-XIAOYA-PASSWORD: 密码
```

也可以用：

```text
Authorization: Bearer 你的Token
```
