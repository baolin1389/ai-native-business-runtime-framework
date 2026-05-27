# AGENTS.md — AI Agent 使用手册

> 本文档面向 AI Agent。当用户要求你构建业务系统时，按此流程执行。

---

## 何时使用

用户提出以下类似需求时，按本手册执行：

- 「帮我根据 ai-native-business-runtime-framework 生成一个 XX 系统」
- 「我想做一个 XX 管理平台，帮我定义数据表和业务逻辑」
- 「我要构建 XX 业务系统，帮我生成 MCP」
- 「我想用这个框架做一个 XX」

---

## 核心原则

**YAML 是唯一真实来源。**

数据模型、业务约束、MCP 工具定义、AI 操作文档 — 全部从 `entities.yaml` 生成。禁止手工修改生成后的文件，所有改动都必须回到 YAML，重新生成。

---

## 工作流程

### 第一步：了解业务全貌

用以下问题引导用户，收集所有必要信息：

```
好的，我先帮你梳理清楚需求：

1. 【实体（数据表）】
   这个系统有哪些核心对象？比如：用户、订单、产品、会员...
   请列出所有实体名称。

2. 【字段定义】
   每个实体有哪些字段？请告诉我：
   - 字段名称（英文，用于代码）
   - 字段类型（string / text / integer / float / boolean / datetime / enum）
   - 业务含义（这个字段代表什么）
   - 是否必填
   - 是否唯一（如邮箱、编号）
   - 枚举值（如状态字段有哪几种）

3. 【业务约束】
   有什么业务规则需要遵守？比如：
   - 什么情况下某个字段必须填写？
   - 什么情况下不能重复（如邮箱、编号）？
   - 状态字段的转换路径（如 new → processing → done）？
   - 有什么自定义的业务逻辑？

4. 【其他需求】
   - 系统名称是什么？
   - 有没有工作流需要定义？
```

### 第二步：构建 entities.yaml

根据用户回答，写出完整的 `entities.yaml`。

**标准模板：**

```yaml
name: <系统名称，英文>
description: <系统描述>
author: <用户名称>

entities:
  - name: <实体名，PascalCase，如 Lead、Order、Product>
    table_name: <表名，snake_case，如 lead、order、product>
    business_meaning: <这个实体代表什么，用一句话说清楚>
    description: <可选，补充说明>
    fields:
      - name: id
        type: string
        primary_key: true
        description: "唯一标识符"

      - name: <字段名>
        type: <类型>
        required: <true/false>
        unique: <true/false>
        indexed: <true/false>
        description: "<字段的业务含义>"
        enum_values:  # 仅当 type 为 enum 时
          - <值1>
          - <值2>

    constraints:  # 如有业务约束
      - type: <required_if/unique/valid_transition/custom>
        fields: [<字段名>]
        explanation: "<用自然语言解释这条规则>"
        params:
          # 根据 type 不同，填写对应参数
```

### 第三步：调用生成器

在项目目录下执行：

```bash
python -m cli.main generate \
  --name <系统名称，英文> \
  --domain <领域标识，如 crm、erp、sales> \
  --entities entities.yaml \
  --output ./output
```

或在 Python 中直接调用：

```python
from runtime_generator.generator import RuntimeGenerator, GeneratorConfig, EntityDef, FieldDef, ConstraintDef

config = GeneratorConfig(
    name="<系统名称>",
    output_dir="./output"
)
generator = RuntimeGenerator(config)

# 添加所有实体（从 entities.yaml 解析）
generator.add_entity(EntityDef(...))
# ...

generator.save()
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
