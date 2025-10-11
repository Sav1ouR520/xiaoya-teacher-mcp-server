# 小雅教育管理MCP服务器

专为教师设计的小雅MCP服务器, 提供在线课程管理系统中的教育资源和题目管理工具.通过MCP协议集成到AI助手中, 帮助教师高效完成教学资源管理和试题创建工作.

## 功能特性

### 📁 资源管理
- **创建教育资源**: 支持创建文件夹、笔记、思维导图、作业、教学设计等多种类型的教育资源
- **资源操作**: 删除、重命名、移动教育资源
- **资源下载**: 支持文件下载和markdown格式转换
- **资源组织**: 浏览课程资源、重新排序、批量更新下载属性和可见性设置
- **资源查询**: 查询特定课程组的所有资源, 支持树形和列表两种格式

### ❓ 题目管理
- **题目创建**:
  - 创建单选题(支持超过4个选项)
  - 创建多选题(支持超过4个选项)
  - 创建填空题(支持多种评分模式)
  - 创建判断题
  - 创建编程题(支持多语言、测试用例、富文本描述)
  - 批量创建题目(官方接口和自定义接口)
- **题目管理**:
  - 创建空白题目和答案项
  - 删除题目和答案项
  - 更新题目设置(标题、解析、分值、必答性等)
  - 更新题目选项和答案
  - 更新编程题测试用例和配置
  - 调整题目和选项顺序
  - 设置试卷随机化(题目和选项随机)
- **试卷管理**:
  - 查询试卷编辑缓冲区信息
  - 导入题目到试卷

### 👥 班级与签到管理
- **课程组管理**: 查询教师的课程组信息
- **班级管理**: 查询课程组的班级列表
- **签到管理**:
  - 查询课程组的全部签到记录
  - 查询单次签到的学生列表

### 📋 任务与测验管理
- **任务查询**:
  - 查询课程组发布的全部任务
  - 查询指定试卷的详细任务信息(包含发布ID等)
- **成绩管理**:
  - 查询学生答题情况和成绩
  - 查询学生答题预览信息

## 安装与使用

### 快速开始
```bash
# 直接使用(推荐)
uvx xiaoya-teacher-mcp-server
```

### 本地开发
```bash
# 克隆项目
git clone https://github.com/Sav1ouR520/xiaoya-teacher-mcp-server
cd xiaoya-teacher-mcp-server

# 安装依赖(推荐使用uv)
uv add -e .

# 运行服务器
python -m xiaoya_teacher_mcp_server
```

## 配置说明

### 认证配置
服务器支持两种认证方式, 任选其一配置即可:

#### 方式一: 账号密码自动登录(推荐)
```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-server": {
      "command": "uvx",
      "args": ["xiaoya-teacher-mcp-server"],
      "env": {
        "XIAOYA_ACCOUNT": "your_account_here",
        "XIAOYA_PASSWORD": "your_password_here"
      }
    }
  }
}
```

#### 方式二: 直接设置认证令牌
```json
{
  "mcpServers": {
    "xiaoya-teacher-mcp-server": {
      "command": "uvx",
      "args": ["xiaoya-teacher-mcp-server"],
      "env": {
        "XIAOYA_AUTH_TOKEN": "your_authorization_token_here"
      }
    }
  }
}
```

### 技术配置

#### 传输方式

支持多种传输方式:

**stdio(标准输入输出)**:
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

**SSE(服务器发送事件)**:
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

**Streamable HTTP**:
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

## 使用指南

1. **选择认证方式**: 根据您的需求选择合适的认证配置方式
2. **配置环境变量**: 将相应配置添加到MCP客户端配置文件中
3. **开始使用**: 在支持MCP的AI助手(如Claude Desktop)中使用各种教育管理功能

## 项目结构

```
xiaoya_teacher_mcp_server/
├── config.py            # 配置文件, 包含认证和API配置
├── main.py              # 服务器入口文件
├── group/               # 班级与签到管理模块
│   ├── __init__.py
│   ├── query.py         # 班级和签到查询功能
│   └── update.py        # 签到状态更新功能(功能实现,未测试,未启用)
├── questions/           # 题目管理模块
│   ├── __init__.py
│   ├── create.py        # 题目创建功能(单选、多选、填空、判断题、编程题)
│   ├── delete.py        # 题目删除功能
│   ├── query.py         # 题目查询功能
│   └── update.py        # 题目更新功能(包含编程题测试用例管理)
├── resources/           # 资源管理模块
│   ├── __init__.py
│   ├── create.py        # 资源创建功能
│   ├── delete.py        # 资源删除功能
│   ├── download.py      # 文件下载和转换功能
│   ├── query.py         # 资源查询功能
│   └── update.py        # 资源更新功能
├── task/                # 任务与测验管理模块
│   ├── __init__.py
│   └── query.py         # 任务和成绩查询功能
├── types/               # 类型定义模块
│   ├── __init__.py
│   └── types.py         # 数据类型和枚举定义
└── utils/               # 工具函数模块
    ├── __init__.py
    └── response.py      # 响应处理工具
```

## 核心功能API详解

### 题目管理 API
#### 创建题目
- `create_single_choice_question()` - 创建单选题
- `create_multiple_choice_question()` - 创建多选题
- `create_fill_blank_question()` - 创建填空题
- `create_true_false_question()` - 创建判断题
- `create_programming_question()` - 创建编程题(支持多语言和测试用例)
- `batch_create_questions()` - 批量创建题目(自定义接口)
- `office_create_questions()` - 批量导入题目(官方接口)

#### 题目操作
- `create_question()` - 创建空白题目
- `delete_questions()` - 批量删除题目
- `update_question()` - 更新题目基本信息
- `update_question_options()` - 更新题目选项
- `update_programming_test_cases()` - 更新编程题测试用例
- `move_answer_item()` - 调整选项顺序
- `update_paper_question_order()` - 更新试卷题目顺序
- `update_paper_randomization()` - 设置试卷随机化
- `create_blank_answer_items()` - 创建填空题答案项
- `update_fill_blank_answer()` - 更新填空题答案

### 编程题管理 API
#### 编程题功能特点
- **多语言支持**: 支持C、C++、Java、Python、JavaScript等多种编程语言
- **测试用例管理**: 支持多个测试用例，每个用例包含输入输出数据
- **富文本题目描述**: 支持格式化的题目说明，包括代码高亮、列表等
- **资源限制配置**: 可设置内存限制、时间限制、调试模式等
- **安全沙箱**: 代码执行在安全环境中进行，防止恶意代码

#### 编程题配置选项
- **语言设置**: 指定允许使用的编程语言列表
- **资源限制**: 内存限制(kb)、时间限制(ms)
- **调试模式**: 允许试运行、设置试运行次数
- **测试用例**: 允许运行测试用例、设置运行次数
- **示例代码**: 提供示例代码和参考答案

#### 核心API
- `create_programming_question()` - 创建编程题
- `update_programming_test_cases()` - 更新编程题测试用例
- `update_question()` - 更新编程题配置(通过program_config参数)

### 资源管理 API
#### 资源操作
- `create_resource()` - 创建教育资源
- `delete_resource()` - 删除资源
- `update_resource_name()` - 重命名资源
- `move_resource()` - 移动资源到其他文件夹
- `query_course_resources()` - 查询课程资源

#### 资源属性管理
- `batch_update_resource_download()` - 批量设置下载属性
- `batch_update_resource_visibility()` - 批量设置可见性
- `update_resource_sort()` - 更新资源排序

#### 文件处理
- `download_file()` - 下载文件
- `read_file_by_markdown()` - 转换文件为markdown格式

### 班级与签到 API
#### 班级管理
- `query_teacher_groups()` - 查询教师课程组
- `query_group_classes()` - 查询班级列表

#### 签到管理
- `query_attendance_records()` - 查询签到记录
- `query_single_attendance_students()` - 查询单次签到学生

### 任务与测验 API
#### 任务查询
- `query_group_tasks()` - 查询课程组发布的全部测试/考试/任务
- `query_test_result()` - 查询学生的测试/考试/任务的答题情况

#### 成绩管理
- `query_preview_student_paper()` - 查询学生答题信息

## 许可证

MIT License
