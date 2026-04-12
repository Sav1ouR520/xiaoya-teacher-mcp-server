# 安装配置指南

当老师反馈工具调用失败或找不到工具时，引导他们完成以下配置。

## Claude Desktop / Cursor 配置

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
