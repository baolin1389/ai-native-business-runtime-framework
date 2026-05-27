# AI Business Runtime Framework

**English** | [中文](#中文版)

---

## TL;DR — AI First

**Want to build a business system?** Just tell an AI:

```
帮我根据 https://github.com/baolin1389/ai-native-business-runtime-framework
生成一个[系统名称]系统，我的需求是：
- 实体：[列出你的数据表]
- 字段：[每个表的字段]
- 业务规则：[有什么约束？]
```

The AI will read [AGENTS.md](./AGENTS.md), guide you through defining your entities and constraints, generate `entities.yaml`, run the code generator, and deliver a complete MCP server with `AI.md`.

**Try it:** Open any AI agent (Claude, GPT, Hermes...) and paste the above.

---

## What Is This?

A code generation framework that makes your business domain **AI-native**:

1. **Define once** — entities and business rules in YAML
2. **Generate everything** — CRUD engine + MCP server + SQLModel + AI.md
3. **AI understands the business** — `AI.md` tells the AI what it can do and what rules apply

The core problem this solves: **AI agents don't know your business rules.** Without explicit declarations of what's allowed, what must be unique, and what conditions trigger validation, AI agents make invalid writes or miss constraints.

> **Constraints are the single source of truth.** Define a constraint once → it becomes validation logic in `engine.py` + AI-readable explanation in `AI.md` + semantic note in the MCP tool description.

---

## Quick Start

### For AI Agents

Read [AGENTS.md](./AGENTS.md) for the standard workflow. TL;DR:

```
用户：「帮我生成 XX 系统」
AI：
  1. 引导用户提供：实体名、字段、业务规则
  2. 生成 entities.yaml
  3. 执行：python -m cli.main generate ...
  4. 交付：mcp_server.py + AI.md
```

### For Developers (Manual)

```bash
pip install -e .
```

**Step 1 — Define entities:**

```yaml
# entities.yaml
name: sales
description: Sales lead and customer management

entities:
  - name: Lead
    business_meaning: "A prospective customer showing initial interest"
    fields:
      - name: id; type: string; primary_key: true
      - name: email; type: string; required: true; unique: true
        description: "Contact email — unique across all leads"
      - name: name; type: string; required: true
      - name: source
        type: string
        enum_values: [website, referral, event, cold_outreach]
    constraints:
      - type: required_if
        fields: [company]
        explanation: "Company is required when source is cold_outreach"
        params:
          when_field: source
          when_value: cold_outreach
```

**Step 2 — Generate:**

```bash
python -m cli.main generate \
  --name sales --domain crm --entities entities.yaml --output ./output
```

**Step 3 — Run:**

```bash
cd output/sales
python mcp_server.py    # MCP JSON-RPC server
AI.md                   # ← AI agent's business reference
```

---

## Declaring Business Rules

```yaml
entities:
  - name: Order
    business_meaning: "A customer purchase order"
    fields:
      - name: status
        type: string
        enum_values: [pending, paid, shipped, delivered, cancelled]
      - name: total_amount
        type: float
        required: true
    constraints:
      # Status must follow the pipeline
      - type: valid_transition
        fields: [status]
        explanation: "Order status flows: pending → paid → shipped → delivered (or cancelled)"
        params:
          from: [pending]
          to: [paid, cancelled]

      # Amount must be positive
      - type: custom
        fields: [total_amount]
        explanation: "Total amount must be greater than zero"
        params:
          expression: "value > 0"
```

See [Constraint Types](#constraint-types) for all supported rules.

---

## Generated Outputs

For each entity, the framework generates:

| File | Purpose |
|------|---------|
| `app/runtime/engine.py` | CRUD handlers with constraint validation |
| `app/infrastructure/models.py` | SQLModel table definitions |
| `mcp_server.py` | MCP JSON-RPC server with namespaced tools |
| `config/runtime.yaml` | Infrastructure config |
| `app/domain/{entity}.yaml` | Entity schema |
| `AI.md` | **AI-readable action reference** — business rules in plain English |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     AI Agent (Hermes / OpenClaw / any)         │
│              reads AI.md → understands the business           │
└───────────────────────┬──────────────────────────────────────┘
                        │ MCP JSON-RPC  +  AI.md context
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                        mcp_server.py                         │
│         TOOL_DEFINITIONS (semantic descriptions)            │
└───────────────────────┬──────────────────────────────────────┘
                        │ execute(action, params)
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                       RuntimeEngine                          │
│         engine.py — validates → reads/writes                  │
│         All actions return {success, result/error}           │
└───────────────────────┬──────────────────────────────────────┘
                        │ SQLModel Session
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                    models.py (SQLModel)                      │
│               (SQLite / PostgreSQL / any)                   │
└──────────────────────────────────────────────────────────────┘
```

---

## Constraint Types

| Type | Use When | Required Params |
|------|----------|----------------|
| `required` | Field cannot be empty | `fields` |
| `unique` | Field must be globally unique | `fields` |
| `unique_together` | Field combination must be unique | `fields` (list) |
| `required_if` | Field required when another = specific value | `fields`, `params.when_field`, `params.when_value` |
| `min_length` | String minimum length | `fields`, `params.min` |
| `max_length` | String maximum length | `fields`, `params.max` |
| `valid_transition` | State field follows specific path | `fields`, `params.from`, `params.to` |
| `custom` | Arbitrary Python validation expression | `fields`, `params.expression` |

All constraints generate:
- **Validation code** in `engine.py` (blocks invalid writes)
- **Natural language explanation** in `AI.md` (tells AI why)

---

## Field Types

| Type | SQL Equivalent |
|------|---------------|
| `string` | VARCHAR |
| `text` | TEXT |
| `integer` | INTEGER |
| `float` | FLOAT |
| `boolean` | BOOLEAN |
| `datetime` | DATETIME |
| `enum` | VARCHAR (use with `enum_values`) |

---

## MCP Tool Design Principles

Tools are named with entity namespace prefix: `lead_create`, `lead_list`, `customer_update`.

Descriptions follow MCP best practices:
- **Semantic, not structural** — "Creates a new Lead. Email must be unique system-wide." not "Creates a lead record."
- **Rich inputSchema** — each parameter has a `description` explaining business meaning
- **Consistent return shape** — always `{success: true, result: ...}` or `{success: false, error: "..."}`

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
├── AGENTS.md                    ← AI agent workflow (READ THIS FIRST)
├── runtime_core/
│   ├── engine.py                # RuntimeEngine, CRUD actions
│   ├── config.py               # YAML config loader
│   ├── state_machine.py
│   ├── event_bus.py
│   └── models.py               # SQLModel session
├── runtime_generator/
│   ├── generator.py            # RuntimeGenerator + data classes
│   ├── templates.py            # Code generators (engine_py, mcp_server_py...)
│   └── cli/main.py
├── tests/                      # 32 tests
├── docs/architecture/
├── pyproject.toml
└── requirements.txt
```

---

## License

MIT

---

# 中文版

## 一句话说明

用 YAML 定义业务实体，一次生成：CRUD 引擎 + MCP 服务器 + AI 可读的操作手册。

## 设计原则

**约束是唯一真实来源。** 在 YAML 中定义一次 → engine 验证逻辑 + AI 提示 + MCP 工具描述三者同源。

## 约束类型

| 类型 | 说明 |
|------|------|
| `required` | 字段必填 |
| `unique` | 字段值全局唯一 |
| `unique_together` | 字段组合唯一 |
| `required_if` | 当某字段为某值时必填 |
| `min_length` / `max_length` | 字符串长度限制 |
| `valid_transition` | 状态只能按固定路径转换 |
| `custom` | 自定义 Python 表达式 |

## 快速开始

### AI 方式（推荐）

告诉 AI：「帮我根据 ai-native-business-runtime-framework 生成 XX 系统」，然后 AI 会引导你完成。

### 开发者方式

```bash
pip install -e .
python -m cli.main init   # 交互式向导
```

或手动：

```bash
python -m cli.main generate \
  --name <项目> --domain <领域> --entities entities.yaml
cd output/<项目>
python mcp_server.py
```

## 测试

```bash
pytest tests/ -v   # 32/32 通过
```
