# 小雅教育管理MCP服务器

![版本](https://img.shields.io/badge/版本-1.5.1-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![MCP](https://img.shields.io/badge/MCP-1.26.0+-purple)
![许可证](https://img.shields.io/badge/许可证-MIT-yellow)

专为教师设计的小雅智能教学平台教育管理 MCP 服务器。通过 MCP 与 AI 助手集成，提供课程资源管理、Markdown 富文本题目创建、试卷配置、班级查询、签到统计、任务测验与学生答卷批阅等能力。

默认安装包含常用文档转换依赖，适合本地 editable、`uv tool` 和标准发布包。

## ✨ 核心特性

### 🎯 AI助手集成
- **MCP协议支持** - 完美集成到支持MCP的AI助手(如Claude Desktop、Cursor等)
- **多种传输方式** - 支持stdio、SSE、Streamable HTTP传输协议
- **摘要优先查询** - 题目、资源、任务默认返回摘要, 减少 AI token 消耗
- **统一响应格式** - 标准化的API响应, 便于AI助手解析和展示

### 📚 智能题库系统
- **7种题型支持** - 单选题、多选题、填空题、判断题、简答题、附件题、编程题
- **富文本编辑** - 支持题目描述的富文本格式(粗体、斜体、下划线、代码块等)
- **智能评分** - 填空题支持多种自动评分策略(精确匹配、部分匹配、有序/无序)
- **批量操作** - 支持批量创建题目、官方导入题目、题目排序调整

### 📁 资源管理系统
- **多类型资源** - 文件夹、笔记、思维导图、文件、作业、教学设计
- **完整生命周期** - 创建、删除、重命名、移动、排序、权限管理
- **文件处理** - 文件下载、markdown格式转换
- **树形结构** - 清晰的资源层级展示

### 👥 班级与签到
- **班级管理** - 班级信息查询、学生统计
- **签到系统** - 签到记录查询、学生签到详情、多种签到状态
- **数据统计** - 出勤率分析、签到趋势

### 📋 任务与测验
- **任务查询** - 查询课程组已发布任务列表、任务详情
- **成绩管理** - 学生答题情况统计、成绩分析
- **答题分析** - 学生答题详情预览、题目解析
- **AI 批阅** - 按学生打包整张答卷和附件，本地缓存图片/PDF/文件，支持多题分数与评语一次写入并提交；已提交批阅可确认后重开修改

## 🆕 附件下载行为变更（v1.5.2）

- `get_answer_file` 已从 `file_access` 预览端点切换为 `file_down/v2` 真实下载链路，避免将网页预览当作附件内容。
- 新增 HTML 负载识别：当响应为 HTML 预览页时，接口会返回结构化错误，不会把伪文件写入附件缓存。
- 本地附件缓存新增 HTML 伪缓存跳过逻辑：如果历史缓存命中 HTML 内容，会自动忽略并重新下载真实文件。

## 🚀 快速开始

### 发布安装
```bash
# 使用 uvx 直接运行
uvx xiaoya-teacher-mcp-server
```

### 本地开发安装
```bash
git clone https://github.com/Sav1ouR520/xiaoya-teacher-mcp-server.git
cd xiaoya-teacher-mcp-server

# 安装开发依赖
uv sync --dev

# 运行服务器
uv run xiaoya-teacher-mcp-server
```

### 本机工具安装
```bash
# 将当前仓库安装为本机可执行 MCP 命令
uv tool install -e --reinstall .
```

## ⚙️ 配置说明


### 认证配置

服务器支持两种认证方式,本地(stdio)与远程(SSE/HTTP)均可使用。账号密码模式支持自动登录和 token 缓存；Bearer Token 模式只使用调用方提供的 token。

#### 方式一：账号密码自动登录(推荐,支持多账号远程缓存)
本地(stdio)和远程(SSE/HTTP)均可通过账号密码自动登录,token 会自动缓存,远程多账号也会自动保存。若请求过程中检测到认证过期,服务端会自动重新登录一次并重试当前请求.
```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-server": {
      "command": "uvx",
      "args": ["xiaoya-teacher-mcp-server"],
      "env": {
        "XIAOYA_ACCOUNT": "your_account",
        "XIAOYA_PASSWORD": "your_password"
      }
    }
  }
}
```
远程请求也支持通过 header 传递账号密码,首次访问自动登录并缓存：
```http
POST /mcp/xxx
X-XIAOYA-ACCOUNT: your_account
X-XIAOYA-PASSWORD: your_password
```

#### 方式二：Token直接认证
本地和远程均可直接传递 Bearer Token,无需账号密码。该模式不会自动重新登录,若 token 过期需由调用方更新后再重试.
```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-server": {
      "command": "uvx",
      "args": ["xiaoya-teacher-mcp-server"],
      "env": {
        "XIAOYA_AUTH_TOKEN": "your_bearer_token"
      }
    }
  }
}
```
远程请求也支持通过 header 传递 Authorization：
```http
Authorization: Bearer your_bearer_token
```

### 传输协议配置

#### 标准输入输出(默认)
```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-server": {
      "command": "uvx",
      "args": ["xiaoya-teacher-mcp-server"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

#### 服务器发送事件
```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-server": {
      "command": "uvx",
      "args": ["xiaoya-teacher-mcp-server"],
      "env": {
        "MCP_TRANSPORT": "sse",
        "MCP_MOUNT_PATH": "/mcp"
      }
    }
  }
}
```

#### Streamable HTTP
```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-server": {
      "command": "uvx",
      "args": ["xiaoya-teacher-mcp-server"],
      "env": {
        "MCP_TRANSPORT": "streamable-http",
        "MCP_MOUNT_PATH": "/mcp"
      }
    }
  }
}
```

### 高级配置：多传输同时启用

在需要同时对多种客户端开放 MCP 服务时, 可通过逗号分隔一次性启用多个传输协议.示例：

```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-server": {
      "command": "uvx",
      "args": ["xiaoya-teacher-mcp-server"],
      "env": {
        "MCP_TRANSPORT": "sse,streamable-http",
        "MCP_MOUNT_PATH": "/mcp",
        "MCP_HOST": "0.0.0.0",
        "MCP_PORT": "8000"
      }
    }
  }
}
```

此时，远程客户端只需如下配置即可访问（无需本地环境变量，支持自动登录和多账号缓存）：

```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-sse-server": {
      "url": "http://ip:port/mcp/sse",
      "headers": {
        "x-xiaoya-account": "你的账号",
        "x-xiaoya-password": "你的密码"
      }
    }
  }
}
```
也支持 streamable-http 协议，只需将 url 改为 `/mcp` 路径。

- MCP_PORT 与 MCP_HOST 为可选项, 用于指定监听地址与端口(仅对基于 HTTP 的传输生效)
- 同时启用 SSE 与 Streamable HTTP 时会复用同一 Uvicorn/Starlette 服务, 客户端可并发使用两种协议
- 所有基于 HTTP 的传输挂载到相同路径, 默认为 http://host:port/mcp/*, 可用 MCP_MOUNT_PATH 调整
- stdio 传输不使用 MCP_HOST/MCP_PORT

## 📖 使用指南

1. **选择认证方式** - 根据您的需求选择账号密码或Token认证
2. **配置环境变量** - 在MCP客户端配置文件中设置相应的环境变量
3. **集成到AI助手** - 在Claude Desktop、Cursor等支持MCP的AI助手中使用
4. **开始教学管理** - 直接与AI对话, 完成题库管理、资源整理、班级管理等任务

### 常用流程与能力边界

#### 出题/组卷

- 试卷通常对应课程资源中的 `ASSIGNMENT` 作业资源。新建试卷时先用 `query_course_resources_summary` 定位目标文件夹，再用 `create_course_resource(type=ASSIGNMENT)` 创建资源并取得 `paper_id`。
- 修改已有试卷时，优先从 `query_course_resources_summary` 或 `query_course_resources` 中查找带 `paper_id` 的作业资源，再用 `query_paper_summary` 查看题数、题型和总分。
- `query_group_tasks` 面向已发布任务，主要提供 `paper_id` 和 `publish_id` 给批阅/答题统计流程使用，不负责筛选未发布试卷。
- 当前没有单独的“自动生成试卷标题”工具。需要个性化标题时，建议让 AI 先给出候选标题，经老师确认后作为 `create_course_resource` 的资源名称。
- 题干、选项和简答参考答案支持 Markdown 输入字段（如 `title_md`、`text_md`、`answer_md`），工具会自动转换为小雅富文本；需要精确 Draft.js 控制时再使用 `*_raw`。
- Markdown 中的图片和附件使用 `asset://id` 占位，并通过相邻 assets 字段传本地文件。示例：`title_md="![节点图](asset://img_1)\n\n[实验附件](asset://file_1)"`，`title_assets=[{"id":"img_1","type":"image","name":"节点图.png","file_path":"/abs/node.png"},{"id":"file_1","type":"attachment","name":"实验附件.zip","file_path":"/abs/lab.zip"}]`。工具会按小雅网页端流程上传并写入富文本。
- 读取试卷或答卷时可设置 `parse_mode="markdown"`，富文本会返回为标准 Markdown 字段和资源列表，例如 `title_md` + `title_assets`、`value_md` + `value_assets`、`answer_md` + `answer_assets`。

#### 批阅/成绩

- 先用 `query_group_tasks` 选择已发布任务，再调用 `query_test_result` 获取提交人数、未提交人数、平均分和学生答题记录。
- AI 批阅单个学生时优先使用 `get_student_grading_bundle`，可传 `save_dir` 指定附件保存目录；不传则使用当前系统临时目录。
- `get_student_grading_bundle` 只返回 `grading_context` 和需人工批阅的简答题/附件题；自动评分题、空字段、`quote_id`、文件大小和缓存命中信息不会返回。
- AI 判断完分数后使用 `grade_student_paper(grading_context=..., grades=[...])` 一次传入多道主观题/附件题的分数和评语，默认会提交整卷批阅。
- 批阅包核心格式为 `{"grading_context": {...}, "questions": [{"question_id": "...", "answer_id": "...", "max_score": 10, "title": "...", "student_answer": "...", "attachments": [{"name": "...", "mimetype": "image/png", "file_path": "/tmp/..."}]}]}`；打分只需传 `grades=[{"question_id": "...", "answer_id": "...", "score": 10, "comment": "..."}]`。
- 低层单题修正时仍可用 `query_preview_student_paper(detail_level=full)`、`get_answer_file`、`grade_student_question` 和 `submit_student_mark` 逐步执行。
- 已提交批阅如需修改，先用 `withdraw_student_mark` 重开，或在明确确认后用 `revise_student_mark(..., allow_reopen=true, submit_after=true)` 重开、改单题并重新提交。
- 附件答案可用 `get_answer_file` 单独获取；图片/PDF 批阅推荐落盘读取或走 `get_student_grading_bundle`，避免 base64 撑爆上下文。

#### 编程题

- `create_code_question` 的 `program_setting.in_cases` 只需要提供输入，格式为 `[{"in": "输入内容"}]`。
- 平台会根据参考答案代码运行生成期望输出，不需要在 `in_cases` 里手写 `out` 字段。
- `description` 用于解析或补充说明，参考答案代码请放在 `program_setting.code_answer`。

#### 批量操作

- 批量创建、批量删除和资源批量更新只有全部成功时顶层 `success=true`；部分失败时 `success=false`，但 `data.failed_items` 会列出未创建/未删除/未更新的条目及原因，`data.success_ids` 会保留已成功的 ID。

## 🏗️ 项目架构

```text
xiaoya-teacher-mcp-server/
├── pyproject.toml         # 打包配置
├── README.md              # 项目文档
├── hatch_build.py         # Hatchling 打包钩子
├── xiaoya-teacher-skill/  # AI 助手 skill，封装小雅平台操作流程
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── references/        # 安装配置、操作链路和富文本参考
├── src/
│   └── xiaoya_teacher_mcp_server/
│       ├── config.py              # 配置文件和认证模块
│       ├── field_descriptions.py  # MCP 字段描述常量
│       ├── main.py                # 服务器入口和传输协议处理
│       ├── tools/                 # 核心工具模块
│       │   ├── questions/         # 题目管理工具
│       │   ├── resources/         # 资源管理工具
│       │   ├── group/             # 班级和签到查询
│       │   └── task/              # 任务和测验管理
│       ├── types/                 # 类型定义
│       │   ├── enums.py           # 通用枚举
│       │   ├── question_models.py # 题目相关模型
│       │   ├── resource_models.py # 资源相关模型
│       │   └── task_models.py     # 班课相关模型
│       └── utils/                 # 公共工具函数
│           ├── client.py          # 统一 HTTP 客户端与自动重登
│           ├── logging.py         # 统一日志
│           ├── response.py        # 统一响应处理
│           ├── rich_text.py       # 纯文本、Markdown、raw 富文本转换
│           └── upload.py          # 小雅网页端同款富文本资源上传
└── tests/                  # 回归测试
```

### 核心模块说明

#### 🎯 题目管理模块
- **create.py** - 完整支持7种题型的创建, 包括复杂的编程题设置
- **update.py** - 题目内容更新、答案修改、选项管理
- **query.py** - 默认返回试卷摘要, 按需返回完整明细
- **delete.py** - 题目和答案项的删除操作

#### 📁 资源管理模块
- **create.py** - 多类型资源创建(文件夹、笔记、思维导图等)
- **update.py** - 资源重命名、移动、排序、权限设置
- **query.py** - 默认返回资源摘要, 支持文件夹局部快照、文件下载、markdown格式转换
- **delete.py** - 资源文件的删除操作

#### 👥 班级管理模块
- **query.py** - 班级列表、签到记录、课程组总览查询

#### 📋 任务管理模块
- **query.py** - 默认返回任务和答题摘要, 按需返回完整答卷明细
- **grade.py** - 学生整卷批改包、批量打分提交、逐题打分、提交批改、重开已提交批阅
- **attachments.py** - 答卷附件收集、并行下载和本地缓存

## 🔧 技术栈

- **Python 3.11+** - 主要开发语言
- **FastMCP** - MCP协议实现框架
- **Pydantic** - 数据验证和类型定义
- **Requests** - HTTP客户端
- **MarkItDown** - 文档格式转换

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情.

## 👨‍💻 作者

**Sav1ouR520**
- Email: 3300233150@qq.com
- GitHub: https://github.com/Sav1ouR520
