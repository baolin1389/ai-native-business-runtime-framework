# AI Business Runtime Framework

**English** | [中文](#中文版)

---

## What Is This?

A code generation framework that lets you define your business domain once, then generates everything an AI agent needs to work with your data correctly:

- **Structured data models** with field-level constraints
- **Typed CRUD actions** that return consistent `{success, result/error}` responses
- **MCP tool definitions** with rich semantic descriptions for AI agents
- **AI.md** — a machine-readable action reference that explains business rules in plain English

The core problem this solves: **AI agents don't know your business rules**. Without explicit declarations of what's allowed, what must be unique, and what conditions trigger validation, AI agents make invalid writes or miss business constraints.

---

## Core Design Principle

> **Constraints are the single source of truth.**

Define a constraint once in YAML, and it automatically becomes:
- Data validation code in the generated CRUD handlers
- Part of the AI.md action reference
- A semantic note in the MCP tool description

```
Entity YAML  →  Validation logic  +  AI context  +  MCP description
               (engine.py)          (AI.md)        (tool inputSchema)
```

---

## Declaring Business Rules

```yaml
entities:
  - name: Lead
    business_meaning: "A prospective customer who has shown interest"
    fields:
      - name: email
        type: string
        required: true
        unique: true
        description: "Contact email — must be unique system-wide"
      - name: status
        type: string
        enum_values: [new, contacted, qualified, lost]
      - name: source
        type: string
        enum_values: [website, referral, event, cold_outreach]

    constraints:
      # When source is cold_outreach, a company name is required
      - type: required_if
        fields: [company]
        explanation: "Company is needed to track cold outreach targets"
        params:
          when_field: source
          when_value: cold_outreach

      # Status transitions follow a specific path
      - type: valid_transition
        fields: [status]
        explanation: "Lead status must follow the pipeline: new → contacted → qualified → (won or lost)"
        params:
          from: [new]
          to: [contacted, lost]
```

The `business_meaning` field is especially important — it tells the AI what this entity represents in real-world terms.

---

## Generated Outputs

For each entity, the framework generates:

| File | Purpose |
|------|---------|
| `app/runtime/engine.py` | CRUD action handlers with constraint validation |
| `app/infrastructure/models.py` | SQLModel table definitions |
| `mcp_server.py` | MCP JSON-RPC server with namespaced tool definitions |
| `config/runtime.yaml` | Infrastructure config |
| `app/domain/{entity}.yaml` | Entity schema |
| `AI.md` | **AI-readable action reference** with all business rules |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent / Hermes / OpenClaw          │
│            (understands business from AI.md)            │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP JSON-RPC  +  AI.md context
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   mcp_server.py                         │
│         TOOL_DEFINITIONS (with semantic descriptions)   │
└─────────────────────┬───────────────────────────────────┘
                      │ execute(action, params)
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  RuntimeEngine                          │
│         engine.py — validates, then reads/writes       │
│         All actions return {success, result/error}       │
└─────────────────────┬───────────────────────────────────┘
                      │ SQLModel Session
                      ▼
┌─────────────────────────────────────────────────────────┐
│              app/infrastructure/models.py              │
│         (SQLite / PostgreSQL / any SQLModel backend)   │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
pip install -e .
```

### Step 1: Define entities

```yaml
# entities.yaml
name: crm
description: Customer relationship management domain

entities:
  - name: Lead
    business_meaning: "A prospective customer who has shown initial interest"
    fields:
      - name: id
        type: string
        primary_key: true
      - name: email
        type: string
        required: true
        unique: true
        description: "Primary contact email — unique across all leads"
      - name: name
        type: string
        required: true
      - name: status
        type: string
        enum_values: [new, contacted, qualified, lost]
      - name: source
        type: string
        enum_values: [website, referral, event, cold_outreach]
    constraints:
      - type: required_if
        fields: [company]
        explanation: "Company name is required for cold outreach leads"
        params:
          when_field: source
          when_value: cold_outreach

  - name: Customer
    business_meaning: "A paying customer with an active contract"
    fields:
      - name: id
        type: string
        primary_key: true
      - name: email
        type: string
        required: true
      - name: tier
        type: string
        enum_values: [standard, premium, enterprise]
```

### Step 2: Generate

```bash
python -m cli.main generate \
  --name crm \
  --domain sales \
  --entities entities.yaml \
  --output ./output
```

Output:

```
output/crm/
├── AI.md                       ← AI agent's primary reference
├── app/
│   ├── domain/
│   │   └── lead.yaml
│   ├── infrastructure/
│   │   └── models.py          ← SQLModel tables
│   └── runtime/
│       └── engine.py          ← CRUD + validation
├── config/
│   └── runtime.yaml
└── mcp_server.py              ← MCP server
```

### Step 3: Run

```bash
cd output/crm
python mcp_server.py
```

---

## How AI Agents Use This

AI agents receive two things:

1. **MCP tool definitions** — via the MCP protocol, including `description` and `inputSchema`
2. **AI.md** — passed as system context (or prompt prefix) to the agent

The `AI.md` file is the key difference. It contains:

```markdown
## Lead Management

A Lead represents: A prospective customer who has shown initial interest

### create_lead

Create a new Lead record.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | **Yes** | Primary contact email — unique across all leads |
...

**Business Rules (enforced):**
- **Required when [source] is [cold_outreach]**: Company is required for cold outreach leads
```

The AI reads `AI.md`, understands the business rules, and can make informed decisions about data operations.

---

## Constraint Types

| Type | Purpose |
|------|---------|
| `required` | Field must be non-empty |
| `unique` | Field value must be unique across all records |
| `unique_together` | Combination of fields must be unique |
| `required_if` | Field is required when another field has a specific value |
| `min_length` / `max_length` | String length bounds |
| `valid_transition` | State field can only transition through allowed values |
| `custom` | Arbitrary Python expression evaluated at write time |

All constraints generate both:
- **Validation code** in `engine.py` that blocks invalid writes
- **Natural language explanation** in `AI.md` that tells AI agents why the constraint exists

---

## MCP Tool Description Best Practices

The framework generates MCP tool definitions following these principles:

- **Semantic descriptions** — not just "creates a lead" but "Creates a new Lead record. Email must be unique system-wide."
- **Namespace prefixes** — tools grouped by entity: `lead_create`, `lead_list`, `customer_update`
- **Rich inputSchema** — descriptions on each parameter explain business meaning
- **Action consistency** — all tools return `{success: true, result: ...}` or `{success: false, error: "..."}`

---

## CLI

```bash
# Interactive wizard
python -m cli.main init

# Generate from YAML
python -m cli.main generate \
  --name <project> \
  --domain <domain> \
  --entities <file.yaml>

# Validate YAML
python -m cli.main validate --entities <file.yaml>
```

---

## Testing

```bash
pytest tests/ -v   # 32/32 passing
```

---

## Project Structure

```
ai-business-runtime-framework/
├── runtime_core/
│   ├── engine.py           # RuntimeEngine, action handlers
│   ├── config.py          # YAML config loader
│   ├── state_machine.py
│   ├── event_bus.py
│   └── models.py          # SQLModel session
├── runtime_generator/
│   ├── generator.py       # RuntimeGenerator, data classes
│   ├── templates.py        # Code generators
│   └── cli/main.py
├── tests/
│   ├── test_runtime_engine.py      # 12 tests
│   ├── test_runtime_generator.py   # 7 tests
│   └── test_templates.py           # 13 tests
├── docs/architecture/
├── pyproject.toml
└── requirements.txt
```

---

## License

MIT

---

# 中文版

## 这个框架做什么？

用 YAML 定义业务实体，一次性生成：

- **数据模型**（带字段级约束）
- **CRUD 操作处理程序**（统一返回 `{success, result/error}`）
- **MCP 工具定义**（带 AI 可理解的语义描述）
- **AI.md**（AI 可读的操作参考文档，包含所有业务规则）

核心解决的问题：**AI 不知道你的业务规则是什么。**

## 设计原则

> **约束是唯一真实来源。**

在 YAML 中定义一次约束，自动转化为：
- `engine.py` 中的数据验证逻辑
- `AI.md` 中的自然语言说明
- MCP 工具 `description` 中的语义注释

## 约束类型

| 类型 | 说明 |
|------|------|
| `required` | 字段不能为空 |
| `unique` | 字段值全局唯一 |
| `unique_together` | 字段组合唯一 |
| `required_if` | 当某字段为某值时必填 |
| `min_length` / `max_length` | 字符串长度限制 |
| `valid_transition` | 状态字段只能按允许路径转换 |
| `custom` | 自定义 Python 表达式 |

## 快速开始

### Step 1：定义实体（entities.yaml）

```yaml
entities:
  - name: Lead
    business_meaning: "表现出初步兴趣的潜在客户"
    fields:
      - name: email
        type: string
        required: true
        unique: true
      - name: status
        type: string
        enum_values: [new, contacted, qualified, lost]
    constraints:
      - type: required_if
        fields: [company]
        explanation: "冷启动线索必须填写公司名称"
        params:
          when_field: source
          when_value: cold_outreach
```

### Step 2：生成

```bash
python -m cli.main generate \
  --name crm --domain sales --entities entities.yaml
```

### Step 3：运行

```bash
cd output/crm
python mcp_server.py
```

## AI 如何使用

AI Agent 收到两样东西：
1. **MCP 工具定义**（通过 MCP 协议，含 `description` 和 `inputSchema`）
2. **AI.md**（作为系统上下文或 prompt 前缀）

`AI.md` 包含每个操作的完整说明，包括业务规则的自然语言解释。AI 读懂业务规则后，可以做出正确的决策。

## 测试

```bash
pytest tests/ -v   # 32/32 通过
```
