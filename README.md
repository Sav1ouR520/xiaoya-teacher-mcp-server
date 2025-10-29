# 小雅教育管理MCP服务器

![版本](https://img.shields.io/badge/版本-1.0.9-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![MCP](https://img.shields.io/badge/MCP-1.14.0+-purple)
![许可证](https://img.shields.io/badge/许可证-MIT-yellow)

专为教师设计的小雅智能教学平台的教育管理MCP服务器, 通过MCP协议与AI助手集成, 提供完整的教育资源管理、题目创建、班级管理、签到统计和任务测验等功能. 让AI助手成为您教学工作的得力助手!

## ✨ 核心特性

### 🎯 AI助手集成
- **MCP协议支持** - 完美集成到支持MCP的AI助手(如Claude Desktop、Cursor等)
- **多种传输方式** - 支持stdio、SSE、Streamable HTTP传输协议
- **统一响应格式** - 标准化的API响应, 便于AI助手解析和展示

### 📚 智能题库系统
- **7种题型支持** - 单选题、多选题、填空题、判断题、简答题、附件题、编程题
- **富文本编辑** - 支持题目描述的富文本格式(粗体、斜体、下划线、代码块等)
- **智能评分** - 填空题支持多种自动评分策略(精确匹配、部分匹配、有序/无序)
- **批量操作** - 支持批量创建题目、导入导出题目、题目排序调整

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
- **任务发布** - 查询课程组任务列表、任务详情
- **成绩管理** - 学生答题情况统计、成绩分析
- **答题分析** - 学生答题详情预览、题目解析

## 🚀 快速开始

### 一键安装(推荐)
```bash
# 使用uvx直接运行, 无需本地安装
uvx xiaoya-teacher-mcp-server
```

### 本地开发安装
```bash
# 克隆项目
git clone https://github.com/Sav1ouR520/xiaoya-teacher-mcp-server.git
cd xiaoya-teacher-mcp-server

# 安装依赖(推荐使用uv)
uv add -e .

# 运行服务器
python -m xiaoya_teacher_mcp_server
```

## ⚙️ 配置说明

### 认证配置

服务器支持两种认证方式, 任选其一：

#### 方式一：账号密码自动登录(推荐)
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

#### 方式二：Token直接认证
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

## 📖 使用指南

1. **选择认证方式** - 根据您的需求选择账号密码或Token认证
2. **配置环境变量** - 在MCP客户端配置文件中设置相应的环境变量
3. **集成到AI助手** - 在Claude Desktop、Cursor等支持MCP的AI助手中使用
4. **开始教学管理** - 直接与AI对话, 完成题库管理、资源整理、班级管理等任务

## 🏗️ 项目架构

```
xiaoya_teacher_mcp_server/
├── config.py              # 配置文件和认证模块
├── main.py                # 服务器入口和传输协议处理
├── tools/                 # 核心工具模块
│   ├── questions/         # 题目管理工具
│   │   ├── create.py      # 题目创建(7种题型)
│   │   ├── update.py      # 题目更新和编辑
│   │   ├── query.py       # 题目查询和检索
│   │   └── delete.py      # 题目删除
│   ├── resources/         # 资源管理工具
│   │   ├── create.py      # 资源创建
│   │   ├── update.py      # 资源更新
│   │   ├── query.py       # 资源查询、文件下载和转换
│   │   └── delete.py      # 资源删除
│   ├── group/             # 班级和签到管理
│   │   ├── query.py       # 班级和签到查询
│   │   └── update.py      # 签到状态更新(预留功能)
│   └── task/              # 任务和测验管理
│       └── query.py       # 任务和成绩查询
├── types/                 # 类型定义
│   └── types.py           # Pydantic模型和枚举
└── utils/                 # 工具函数
    └── response.py        # 统一响应处理
```

### 核心模块说明

#### 🎯 题目管理模块
- **create.py** - 完整支持7种题型的创建, 包括复杂的编程题设置
- **update.py** - 题目内容更新、答案修改、选项管理
- **query.py** - 题目查询、试卷分析、学生答题详情
- **delete.py** - 题目和答案项的删除操作

#### 📁 资源管理模块
- **create.py** - 多类型资源创建(文件夹、笔记、思维导图等)
- **update.py** - 资源重命名、移动、排序、权限设置
- **query.py** - 资源树形查询、层级结构展示、文件下载、markdown格式转换
- **delete.py** - 资源文件的删除操作

#### 👥 班级管理模块
- **query.py** - 班级列表、签到记录、学生详情查询
- **update.py** - 签到状态更新(预留功能)

#### 📋 任务管理模块
- **query.py** - 任务列表、学生成绩、答题详情查询

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
