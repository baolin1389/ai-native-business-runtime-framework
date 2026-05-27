# AI Business Runtime Framework

**English** | [中文](#中文版)

---

## What Is This?

一个 Python 代码生成框架，为 AI 外贸业务系统提供从**领域建模 → 完整代码生成 → 自动化运行**的全链路能力。

你只需要定义 YAML 实体（Entity），框架自动生成：

- **Runtime Engine** — CRUD 操作处理程序（SQLite + SQLModel）
- **MCP Server** — JSON-RPC MCP 协议适配器，供 AI Agent 调用
- **SQLModel 表** — 类型安全的数据库模型
- **运行时配置** — `runtime.yaml`
- **领域 schema** — `domains/{entity}.yaml`
- **示例工作流** — `workflows/example.yaml`

---

## Why Does This Exist?（解决了什么问题）

### 痛点

AI 外贸业务系统通常面临以下循环：

```
每次新业务场景 → 手工写 CRUD API → 写数据库模型 → 配 MCP 工具 → 调试协议兼容 → 重复劳动
```

每增加一个实体（Lead、Customer、Order...），就要重复写一套：`engine.py handler` + `models.py` + `mcp_server.py tool` + `runtime.yaml config`。

### 解决方案

**一次建模，自动生成一切。**

```
entities.yaml  →  RuntimeGenerator  →  app/runtime/engine.py
                                    →  mcp_server.py
                                    →  app/infrastructure/models.py
                                    →  config/runtime.yaml
                                    →  config/domains/{entity}.yaml
```

每新增一个实体，改一处 YAML，重新生成，工具立即在 AI Agent 中可用。

### 核心价值

| 维度 | 说明 |
|------|------|
| **效率** | 从手工 30 分钟/实体 → 框架 5 秒/实体 |
| **一致性** | 所有实体遵循同一套命名、结构和协议 |
| **可维护性** | 改 YAML 即可，无需追踪散落在多处的手写代码 |
| **AI 原生** | MCP 协议适配器让 AI Agent 直接调用业务操作 |

---

## Use Cases（适用场景）

### 1. B2B 外贸客户管理

定义 `Lead`、`Customer`、`Contact` 实体，生成完整的客户信息管理 runtime，MCP 工具自动暴露给 AI Agent，支持自然语言查询和操作客户数据。

### 2. AI Agent 外贸业务流程

结合 [Hermes Agent](#hermes-agent-集成) 和 [OpenClaw](#openclaw-集成)，实现：
- 自然语言录入新线索（Lead）
- AI 自动识别客户类型、分配销售
- 定时任务自动跟进未成交客户

### 3. 多业务线快速启动

新业务线（如宠物食品、化妆品原料）只需：
1. 写一个新的 `entities.yaml`
2. 运行生成命令
3. 上线运营

---

## Architecture（架构）

```
┌─────────────────────────────────────────────────────────┐
│                   Hermes Agent / OpenClaw               │
│              (自然语言 → AI 推理 → 工具调用)              │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP JSON-RPC
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   mcp_server.py                         │
│         (TOOL_DEFINITIONS + TOOL_MAP)                  │
│         将 MCP 工具映射到 engine action                 │
└─────────────────────┬───────────────────────────────────┘
                      │ execute("action", params)
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  RuntimeEngine                          │
│         (engine.py — CRUD action handlers)             │
│         create_lead / list_leads / update_customer...  │
└─────────────────────┬───────────────────────────────────┘
                      │ SQLModel Session
                      ▼
┌─────────────────────────────────────────────────────────┐
│              app/infrastructure/models.py              │
│         (SQLModel — 自动生成的表结构)                   │
└─────────────────────┬───────────────────────────────────┘
                      │ SQLite
                      ▼
              data/{name}.db
```

---

## Quick Start

### 安装

```bash
git clone https://github.com/baolin1389/ai-native-business-runtime-framework.git
cd ai-native-business-runtime-framework
pip install -e .
```

依赖：Python 3.10+，sqlmodel，pyyaml，tomli

### Step 1：定义实体

```yaml
# entities.yaml
name: sales
description: 外贸客户管理系统
author: Eric

entities:
  - name: Lead
    table_name: lead
    description: 销售线索
    fields:
      - name: id
        type: string
        primary_key: true
      - name: name
        type: string
        required: true
      - name: email
        type: string
        required: true
      - name: company
        type: string
      - name: source
        type: string
        enum_values: [website, trade_show, referral, cold_call]

  - name: Customer
    table_name: customer
    description: 已成交客户
    fields:
      - name: id
        type: string
        primary_key: true
      - name: name
        type: string
        required: true
      - name: email
        type: string
        required: true
      - name: level
        type: string
        enum_values: [A, B, C]
```

### Step 2：生成代码

```bash
python -m cli.main generate \
  --name sales \
  --domain crm \
  --entities entities.yaml \
  --output ./output
```

生成的目录结构：

```
output/sales/
├── app/
│   ├── infrastructure/
│   │   └── models.py       # LeadModel, CustomerModel
│   └── runtime/
│       └── engine.py       # _create_lead, _list_leads, _update_customer...
├── config/
│   ├── runtime.yaml        # 数据库路径、实体列表
│   └── domains/
│       ├── lead.yaml
│       └── customer.yaml
├── mcp_server.py           # MCP JSON-RPC Server
└── workflows/
    └── example.yaml
```

### Step 3：运行 MCP Server

```bash
cd output/sales
python mcp_server.py
```

Server 通过 stdin/stdout 接收 JSON-RPC 请求，响应格式符合 MCP 协议规范。

---

## Hermes Agent 集成

### 配置 MCP Server

在 Hermes Agent 的 `config.yaml` 中添加 `foreign-trade-mcp`（已有）：

```yaml
mcp_servers:
  foreign-trade-mcp:
    command: /Users/ICECOOL/.hermes/hermes-agent/venv/bin/python3
    args:
      - /Users/ICECOOL/.hermes/workspace/ai-business-runtime-framework
      - --mcp-server
    env: {}
```

### 在 Hermes 中使用生成的 Runtime

通过 `ai-business-runtime` skill 或直接调用：

```python
# 场景：Hermes 定时任务中发现新线索，录入系统
from runtime_generator.generator import RuntimeGenerator, GeneratorConfig, EntityDef, FieldDef
from runtime_core.engine import RuntimeEngine

# 加载已生成的 engine
engine = RuntimeEngine()  # 自动读取 config/runtime.yaml

# 录入线索
result = engine.execute("create_lead", {
    "name": "John Smith",
    "email": "john@acme.com",
    "company": "Acme Corp",
    "source": "trade_show"
})
print(result)
# → {"success": True, "result": {...}}

# 查询线索
leads = engine.execute("list_leads", {"limit": 10})
```

### 通过 MCP 工具暴露给 AI

生成的 `mcp_server.py` 注册了以下工具：

| 工具名 | 对应 action | 说明 |
|--------|-------------|------|
| `mcp_lead_list_leads` | `list_leads` | 分页查询线索 |
| `mcp_lead_create_lead` | `create_lead` | 创建新线索 |
| `mcp_lead_get_lead` | `get_lead` | 按 ID 查询 |
| `mcp_lead_update_lead` | `update_lead` | 更新线索信息 |
| `mcp_lead_delete_lead` | `delete_lead` | 删除线索 |
| `mcp_customer_list_customers` | `list_customers` | 查询客户 |
| `mcp_customer_create_customer` | `create_customer` | 创建客户 |
| ... | ... | ... |

AI Agent 通过 MCP 协议调用这些工具，实现自然语言驱动的业务操作。

---

## OpenClaw 集成

### 方式一：通过 MCP 协议调用

OpenClaw 的 Agent 通过 MCP 协议调用 `mcp_server.py` 暴露的工具：

```bash
# 启动 mcp_server（后台运行）
cd output/sales
python mcp_server.py &

# OpenClaw Agent 通过 MCP 协议调用工具
# 工具自动映射到 engine action
```

### 方式二：在 OpenClaw Workflow 中使用

在 OpenClaw 的 AI workflow 定义中引用生成的 runtime：

```python
# openclaw_workflow.py
from runtime_core.engine import RuntimeEngine

def process_lead_workflow(lead_data: dict):
    engine = RuntimeEngine()
    
    # AI 判断客户等级
    level = classify_customer(lead_data)
    
    # 创建线索
    result = engine.execute("create_lead", {**lead_data, "level": level})
    
    # 根据等级分配跟进策略
    if level == "A":
        schedule_follow_up(lead_data, priority="high")
    else:
        schedule_follow_up(lead_data, priority="normal")
    
    return result
```

---

## CLI 命令

```bash
# 交互式初始化（向导模式）
python -m cli.main init

# 从 YAML 生成
python -m cli.main generate \
  --name <项目名> \
  --domain <领域> \
  --entities <entities.yaml>

# 验证 YAML
python -m cli.main validate --entities <file.yaml>
```

---

## 测试

```bash
pytest tests/ -v
```

**当前状态：32/32 通过**

| 测试文件 | 覆盖范围 |
|---------|---------|
| `test_runtime_engine.py` | RuntimeEngine, TaskExecutor, ExecutionContext（12项）|
| `test_runtime_generator.py` | GeneratorConfig, RuntimeGenerator, CLI（7项）|
| `test_templates.py` | 所有模板 AST 验证、YAML 生成、端到端（13项）|

---

## 项目结构

```
ai-business-runtime-framework/
├── runtime_core/
│   ├── engine.py          # RuntimeEngine（CRUD action 执行器）
│   ├── config.py          # YAML 配置加载
│   ├── state_machine.py  # 状态机定义
│   ├── event_bus.py      # 事件总线
│   └── models.py         # SQLModel 会话管理
├── runtime_generator/
│   ├── generator.py      # RuntimeGenerator + 数据类
│   ├── templates.py      # 代码生成器（engine_py, mcp_server_py...）
│   └── cli/main.py       # CLI 入口
├── tests/
│   ├── test_runtime_engine.py
│   ├── test_runtime_generator.py
│   └── test_templates.py
├── docs/architecture/     # 架构设计文档
├── pyproject.toml
└── requirements.txt
```

---

## License

MIT

---

# 中文版

## 是什么？

一个 **AI 外贸业务 runtime 代码生成框架**。用 YAML 定义领域实体，自动生成完整的外贸业务运行时代码（Engine + MCP Server + SQLModel + 配置文件）。

## 解决了什么问题？

每次新增加一个业务实体（Lead、Customer、Order），需要：
- 写 CRUD handler
- 写 SQLModel 表
- 配 MCP 工具
- 写配置文件

**这个框架让你只改一处 YAML，重新生成，全部自动搞定。**

## 核心价值

| 效率 | 一键从 YAML 生成完整代码，新增实体只需 5 秒 |
|------|---------------------------------------|
| 一致性 | 所有实体统一命名、结构和协议 |
| 可维护 | 改 YAML 即可，无需追踪散落的手写代码 |
| AI 原生 | MCP 协议让 AI Agent 直接调用业务操作 |

## 适用场景

1. **B2B 外贸客户管理** — 线索、客户、联系人全程数字化
2. **AI Agent 外贸业务流程** — 自然语言录入/查询/操作客户数据
3. **多业务线快速启动** — 新品类只需写 YAML + 生成

## 快速开始

### Step 1：定义实体（entities.yaml）

```yaml
entities:
  - name: Lead
    table_name: lead
    fields:
      - name: id; type: string; primary_key: true
      - name: name; type: string; required: true
      - name: email; type: string; required: true
```

### Step 2：生成代码

```bash
python -m cli.main generate \
  --name sales --domain crm --entities entities.yaml
```

### Step 3：运行

```bash
cd output/sales
python mcp_server.py  # 启动 MCP Server
```

## Hermes Agent 集成

在 `config.yaml` 中配置 `foreign-trade-mcp` 后，通过 MCP 协议调用生成的工具：

```python
engine = RuntimeEngine()  # 读取 config/runtime.yaml
engine.execute("create_lead", {"name": "Eric", "email": "eric@example.com"})
```

## OpenClaw 集成

OpenClaw Agent 通过 MCP 协议调用 `mcp_server.py` 中暴露的工具，实现自然语言驱动的业务操作。

## 测试

```bash
pytest tests/ -v   # 32/32 通过
```
