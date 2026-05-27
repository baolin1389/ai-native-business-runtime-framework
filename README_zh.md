# AI 业务运行时框架

[**English**](./README.md) | [中文](./README_zh.md)

---

## 一句话说清楚

用 YAML 定义业务实体，一次生成：CRUD 引擎 + MCP 服务器 + AI 可读的操作手册。

---

## 这个框架解决什么问题？

**AI 不知道你的业务规则。** 没有显式声明哪些字段必填、哪些不能重复、什么条件下触发验证，AI 就会写出非法数据或遗漏约束。

> **约束是唯一真实来源。** 在 YAML 中定义一次 → engine 验证逻辑 + AI 提示 + MCP 工具描述三者同源。

---

## 核心功能

1. **一次定义** — 在 YAML 中定义实体和业务规则
2. **一次生成** — 同时生成 CRUD 引擎 + MCP 服务器 + SQLModel + AI.md
3. **AI 理解业务** — `AI.md` 告诉 AI 能做什么、有什么规则

---

## 快速开始

### AI 方式（推荐）

告诉 AI：「帮我根据 [ai-native-business-runtime-framework](https://github.com/baolin1389/ai-native-business-runtime-framework) 生成 XX 系统」，然后 AI 会引导你完成。

**标准流程：**

```
用户：「帮我生成 XX 系统」
AI：
  1. 引导用户提供：实体名、字段、业务规则
  2. 生成 entities.yaml
  3. 执行：python -m cli.main generate ...
  4. 交付：mcp_server.py + AI.md
```

详细流程请阅读 [AGENTS.md](./AGENTS.md)。

### 开发者方式（手动）

**第一步 — 安装：**

```bash
pip install -e .
```

**第二步 — 定义实体：**

```yaml
# entities.yaml
name: sales
description: Sales lead and customer management

entities:
  - name: Lead
    business_meaning: "潜在客户，表现出初步兴趣"
    fields:
      - name: id; type: string; primary_key: true
      - name: email; type: string; required: true; unique: true
        description: "联系邮箱 — 全系统唯一"
      - name: name; type: string; required: true
      - name: source
        type: string
        enum_values: [website, referral, event, cold_outreach]
    constraints:
      - type: required_if
        fields: [company]
        explanation: "来源为 cold_outreach 时，公司字段必填"
        params:
          when_field: source
          when_value: cold_outreach
```

**第三步 — 生成代码：**

```bash
python -m cli.main generate \
  --name sales --domain crm --entities entities.yaml --output ./output
```

**第四步 — 运行：**

```bash
cd output/sales
python mcp_server.py    # 启动 MCP 服务器
AI.md                   # ← AI 的业务参考文档
```

---

## 声明业务规则

```yaml
entities:
  - name: Order
    business_meaning: "客户采购订单"
    fields:
      - name: status
        type: string
        enum_values: [pending, paid, shipped, delivered, cancelled]
      - name: total_amount
        type: float
        required: true
    constraints:
      # 状态必须按固定路径流转
      - type: valid_transition
        fields: [status]
        explanation: "订单状态流程：pending → paid → shipped → delivered（或 cancelled）"
        params:
          from: [pending]
          to: [paid, cancelled]

      # 金额必须为正
      - type: custom
        fields: [total_amount]
        explanation: "订单金额必须大于零"
        params:
          expression: "value > 0"
```

所有支持的约束类型见 [约束类型](#约束类型)。

---

## 生成的文件

| 文件 | 用途 |
|------|------|
| `app/runtime/engine.py` | CRUD 处理器，含业务约束验证 |
| `app/infrastructure/models.py` | SQLModel 数据模型 |
| `mcp_server.py` | MCP JSON-RPC 服务器 |
| `config/runtime.yaml` | 运行时配置 |
| `app/domain/{entity}.yaml` | 实体 schema |
| `AI.md` | **AI 可读的操作参考** — 用自然语言描述业务规则 |

---

## 架构图

```
┌──────────────────────────────────────────────────────────────┐
│                     AI Agent (Hermes / OpenClaw / any)         │
│              reads AI.md → understands the business           │
└───────────────────────┬──────────────────────────────────────┘
                        │ MCP JSON-RPC  +  AI.md context
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                        mcp_server.py                         │
│         TOOL_DEFINITIONS (semantic descriptions)             │
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

## 约束类型

| 类型 | 何时使用 | 必需参数 |
|------|---------|---------|
| `required` | 字段必填，不能为空 | `fields` |
| `unique` | 字段值全局唯一 | `fields` |
| `unique_together` | 多个字段组合唯一 | `fields`（列表） |
| `required_if` | 当某字段为某值时必填 | `fields`, `params.when_field`, `params.when_value` |
| `min_length` | 字符串最短长度 | `fields`, `params.min` |
| `max_length` | 字符串最长长度 | `fields`, `params.max` |
| `valid_transition` | 状态字段转换路径 | `fields`, `params.from`, `params.to` |
| `custom` | 自定义 Python 表达式 | `fields`, `params.expression` |

所有约束同时生成：
- **验证代码** — 写入 `engine.py`，阻止非法操作
- **自然语言说明** — 写入 `AI.md`，告诉 AI 为什么

---

## 字段类型

| 类型 | 说明 | 对应 SQL 类型 |
|------|------|-------------|
| `string` | 短字符串（单行） | VARCHAR |
| `text` | 长字符串（多行） | TEXT |
| `integer` | 整数 | INTEGER |
| `float` | 浮点数 | FLOAT |
| `boolean` | 布尔值 | BOOLEAN |
| `datetime` | 日期时间 | DATETIME |
| `enum` | 枚举值，需配合 `enum_values` | VARCHAR |

---

## MCP 工具命名规范

工具名用实体名做前缀：`lead_create`、`lead_list`、`customer_update`。

描述遵循 MCP 最佳实践：
- **语义化描述** — "Creates a new Lead. Email must be unique system-wide." 而不是 "Creates a lead record."
- **完整的 inputSchema** — 每个参数都有 `description` 解释业务含义
- **统一的返回格式** — 永远是 `{success: true, result: ...}` 或 `{success: false, error: "..."}`

---

## 命令行工具

```bash
# 交互式向导
python -m cli.main init

# 从 YAML 生成
python -m cli.main generate \
  --name <项目> \
  --domain <领域> \
  --entities <file.yaml>

# 验证 YAML
python -m cli.main validate --entities <file.yaml>
```

---

## 测试

```bash
pytest tests/ -v   # 32/32 通过
```

---

## 项目结构

```
ai-business-runtime-framework/
├── AGENTS.md                    ← AI Agent 工作手册（优先阅读）
├── README.md                    ← English
├── README_zh.md                 ← 中文
├── runtime_core/
│   ├── engine.py                # RuntimeEngine, CRUD actions
│   ├── config.py               # YAML config loader
│   ├── state_machine.py
│   ├── event_bus.py
│   └── models.py               # SQLModel session
├── runtime_generator/
│   ├── generator.py            # RuntimeGenerator + data classes
│   ├── templates.py            # Code generators
│   └── cli/main.py
├── tests/                      # 32 tests
├── docs/architecture/
├── pyproject.toml
└── requirements.txt
```

---

## License

MIT
