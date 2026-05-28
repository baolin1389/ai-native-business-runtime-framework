# AGENTS.md — AI Agent 使用手册

> 本文档面向 AI Agent。当用户要求你构建业务系统时，按此流程执行。

---

## 何时使用

用户提出以下类似需求时，**不要直接生成**，先运行 `python -m cli.main plan`：

- 「帮我根据 ai-native-business-runtime-framework 生成一个 XX 系统」
- 「我想做一个 XX 管理平台，帮我定义数据表和业务逻辑」
- 「我要构建 XX 业务系统，帮我生成 MCP」
- 「我想用这个框架做一个 XX」

**标准响应：**

```
好的！我先用交互式向导帮你收集需求，生成 entities.yaml 草稿，
你确认后再生成完整代码。

→ python -m cli.main plan
```

禁止在未经用户确认的情况下直接生成 entities.yaml 或运行 generate 命令。

---

## 核心原则

**YAML 是唯一真实来源。**

数据模型、业务约束、MCP 工具定义、AI 操作文档 — 全部从 `entities.yaml` 生成。禁止手工修改生成后的文件，所有改动都必须回到 YAML，重新生成。

---

## 工作流程

### 第一步：收集需求（`python -m cli.main plan`）

当用户说「帮我生成 XX 系统」时，**不要直接生成**，先运行 plan 命令收集需求：

```bash
python -m cli.main plan
```

这会启动交互式向导，询问：
1. 系统名称
2. 实体列表（Lead、Order、Product…）
3. 每个实体的字段（名称、类型、是否必填）
4. 业务约束（唯一、状态转换、条件必填…）
5. 需求摘要确认

确认后生成 `entities.yaml`，或直接保存到指定路径：
```bash
python -m cli.main plan -o my-system/entities.yaml
```

### 第二步：预览（`python -m cli.main generate --dry-run`）

在正式生成前，**先用 dry-run 预览**，让用户确认：
```bash
python -m cli.main generate --config my-system/entities.yaml --dry-run
```

这会显示将要生成的实体、字段、约束和文件列表，**不写入任何文件**。

### 第三步：生成（`python -m cli.main generate`）

用户确认无误后，正式生成：
```bash
python -m cli.main generate --config my-system/entities.yaml
```

### 第四步：交付物检查

生成完成后，确认以下文件存在：

| 文件 | 必须 | 说明 |
|------|------|------|
| `AI.md` | ✅ | AI 操作参考文档，必须随 MCP 一起使用 |
| `mcp_server.py` | ✅ | MCP 服务器主文件 |
| `app/runtime/engine.py` | ✅ | CRUD 处理器，含业务约束验证 |
| `app/infrastructure/models.py` | ✅ | SQLModel 数据模型 |
| `config/runtime.yaml` | ✅ | 运行时配置 |

### 第五步：向用户说明如何使用

```
生成完成！系统包含以下内容：

📁 输出目录：./output/<系统名称>/

📄 AI.md — AI 操作手册（重要！）
   将此文件内容作为 AI 的系统上下文，AI 才能理解业务规则。

🚀 启动 MCP Server：
   cd ./output/<系统名称>
   python mcp_server.py

📋 可用的 MCP 工具：
   lead_create  — 创建线索
   lead_list    — 查询线索列表
   lead_get     — 获取单个线索
   lead_update  — 更新线索
   lead_delete  — 删除线索
   customer_*   — 客户相关操作（同样模式）
   ...

💡 在 Hermes Agent / OpenClaw 中使用：
   只需将 mcp_server.py 配置为 MCP Server，
   然后将 AI.md 内容作为 prompt 前缀或系统消息，
   AI 就能理解业务规则并正确操作数据。
```

---

## 约束类型速查

定义业务规则时，用以下类型：

| type | 何时使用 | 必需参数 |
|------|---------|---------|
| `required` | 字段必填，不能为空 | `fields` |
| `unique` | 字段值全局唯一 | `fields` |
| `unique_together` | 多个字段组合唯一 | `fields`（列表） |
| `required_if` | 当某字段为某值时必填 | `fields`, `params.when_field`, `params.when_value` |
| `min_length` | 字符串最短长度 | `fields`, `params.min` |
| `max_length` | 字符串最长长度 | `fields`, `params.max` |
| `valid_transition` | 状态字段转换路径 | `fields`, `params.from`, `params.to` |
| `custom` | 自定义 Python 表达式 | `fields`, `params.expression` |

---

## 字段类型速查

| type | 说明 | 对应 SQL 类型 |
|------|------|-------------|
| `string` | 短字符串（单行） | VARCHAR |
| `text` | 长字符串（多行） | TEXT |
| `integer` | 整数 | INTEGER |
| `float` | 浮点数 | FLOAT |
| `boolean` | 布尔值 | BOOLEAN |
| `datetime` | 日期时间 | DATETIME |
| `enum` | 枚举值，需配合 `enum_values` | VARCHAR |

---

## 常见问题

**Q: 用户说「帮我生成」但没给字段信息**
→ 按第一步引导用户提供，不要猜测字段。

**Q: 用户给的字段是中文**
→ 转换为英文 camelCase/snake_case（如「姓名」→ `name`，「客户等级」→ `customer_tier`），中文填入 `description`。

**Q: 用户不确定业务约束**
→ 提供常见选项：「是否有字段必须唯一（如邮箱、编号）？」「有没有状态字段（如订单状态、客户等级）？状态变化有固定路径吗？」

**Q: 用户想要的功能超出约束类型**
→ 使用 `custom` 类型，通过 `params.expression` 写任意 Python 表达式。

**Q: 需要修改已生成的文件**
→ 不要直接改。回到 `entities.yaml`，修改后重新生成。

---

## 示例对话

**用户**：「我想做一个图书馆管理系统，帮我用这个框架生成」

**AI**：

```
好的，先帮你梳理一下需求：

1. 有哪些实体？
   （图书、读者、借阅记录...）

2. 每个实体有哪些字段？
   比如图书：书名、ISBN、作者、分类、库存数量...
   读者：姓名、会员卡号、联系方式...

3. 有什么业务规则？
   - ISBN 必须唯一？
   - 借阅状态有固定流程（借出 → 归还 → 逾期）？
   - 库存为 0 时不能再借出？
```

**用户**：「图书有 ISBN 必须唯一，读者有借阅状态，从 available → borrowed → returned，不能超期」

**AI** → 生成 `entities.yaml` → 执行生成 → 交付

---

## 重要提示

- **YAML 是唯一真实来源**。不要直接修改生成后的 `engine.py`、`models.py`、`mcp_server.py`。
- **每次改需求**，都改 YAML 重新生成。
- **交付时必须包含 AI.md**，这是 AI 理解业务规则的唯一文档。
- **数据操作必须通过 MCP** 或生成的 `RuntimeEngine`，禁止直接操作数据库文件。
