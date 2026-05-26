# MCP Adapter Architecture

## Overview

The MCP (Model Context Protocol) Adapter is the component responsible for communication between the AI Business Runtime Framework and external AI models and services. It provides a standardized interface for model interactions while abstracting provider-specific implementation details.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Adapter Layer                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Protocol Handler                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │   Request   │  │   Response  │  │     Error       │  │  │
│  │  │   Builder   │  │   Parser    │  │    Handler      │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Transport Layer                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │     HTTP    │  │    WebSocket   │  │   Streaming   │  │  │
│  │  │   Client    │  │    Client    │  │     Support    │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Provider Adapters                         │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │  │
│  │  │  OpenAI │  │ Anthropic│ │  Google │  │  Custom │      │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Protocol Handler

The Protocol Handler implements the MCP specification for request/response communication:

### Request Builder

Constructs properly formatted MCP requests including:
- Model identification and version
- Input payload serialization
- Authentication headers
- Protocol metadata

### Response Parser

Processes MCP responses:
- Status code interpretation
- Payload deserialization
- Error extraction and classification
- Streaming response handling

### Error Handler

Manages protocol-level errors:
- Retry conditions detection
- Rate limiting handling
- Timeout management
- Authentication failures

## Transport Layer

### HTTP Transport

Standard synchronous communication:
- Persistent connection pooling
- Automatic request retry
- Certificate validation
- Proxy support

### WebSocket Transport

For real-time and streaming interactions:
- Bidirectional communication
- Heartbeat/keep-alive
- Graceful reconnection
- Message framing

### Streaming Support

Handles server-sent events and streaming responses:
- Chunked response processing
- Progress callbacks
- Partial result access
- Stream termination handling

## Provider Adapters

### OpenAI Adapter

**Endpoint:** `https://api.openai.com/v1/*`

**Capabilities:**
- Chat completions
- Embeddings
- Function calling
- Vision support

### Anthropic Adapter

**Endpoint:** `https://api.anthropic.com/v1/*`

**Capabilities:**
- Claude completions
- Tool use
- Vision support
- Streaming

### Google Adapter

**Endpoint:** `https://generativelanguage.googleapis.com/v1/*`

**Capabilities:**
- Gemini completions
- Function calling
- Batch processing

### Custom Provider Adapter

For self-hosted or custom models:
- Configurable endpoint
- Custom authentication
- Protocol translation

## Message Flow

```
┌────────────┐     MCP Protocol      ┌────────────┐
│  Runtime   │ ←──────────────────→  │   MCP      │
│   Core     │                       │   Adapter  │
└────────────┘                       └────────────┘
                                              ↓
                                    ┌────────────────────┐
                                    │   AI Provider      │
                                    │   (OpenAI, etc.)   │
                                    └────────────────────┘
```

## Configuration

```yaml
mcp_adapter:
  default_provider: openai
  timeout_seconds: 60
  max_retries: 3
  
  providers:
    openai:
      api_key_env: OPENAI_API_KEY
      endpoint: https://api.openai.com/v1
      default_model: gpt-4o
      
    anthropic:
      api_key_env: ANTHROPIC_API_KEY
      endpoint: https://api.anthropic.com/v1
      default_model: claude-3-5-sonnet-20241022
      
  transport:
    type: http
    pool_size: 10
    keep_alive: true
```

## Security

- **API Key Management:** Keys stored in environment variables, never in config files
- **Request Signing:** HMAC signatures for authenticated requests where supported
- **TLS Encryption:** All network traffic encrypted via TLS 1.2+
- **Input Sanitization:** All prompts validated before transmission

## Rate Limiting

The adapter implements provider-aware rate limiting:

```python
class RateLimiter:
    def __init__(self, requests_per_minute: int, tokens_per_minute: int):
        self.rpm_limit = requests_per_minute
        self.tpm_limit = tokens_per_minute
        
    async def acquire(self, tokens: int) -> bool:
        # Token bucket algorithm implementation
        pass
```

## Error Codes

| MCP Code | Description |
|----------|-------------|
| `-32700` | Parse error - Invalid JSON |
| `-32600` | Invalid request |
| `-32601` | Method not found |
| `-32602` | Invalid parameters |
| `-32603` | Internal error |
| `-32000` | Provider authentication failed |
| `-32001` | Provider rate limit exceeded |
| `-32002` | Provider resource exhausted |

---

## MCP Server Mode (Exposing Tools to AI)

The framework's `mcp_adapter/` is designed as an **AI client** (sends requests to LLM providers). To use the framework with AI agents that act as MCP *servers* (exposing your business actions as tools to AI clients), implement the following pattern.

### When to Use MCP Server Mode

- AI agents (e.g., Claude Desktop, Cursor, GPTs) need to call your business actions as tools
- You want to wrap domain actions (`lead.create_lead`, `customer.update_customer`, etc.) as MCP tools
- Your project runs as a stdio daemon that AI clients connect to

### Architecture

```
AI Agent (Claude Desktop, etc.)
        ↓ MCP over stdio
┌─────────────────────────────────────────┐
│           mcp_server.py                 │  ← Your MCP stdio server
│  (uses mcp.server.Server from MCP SDK) │
└──────────────────┬──────────────────────┘
                   ↓ calls
┌─────────────────────────────────────────┐
│           tools.py                       │  ← THIN WRAPPER LAYER
│  (converts MCP params → engine params) │     Single source of truth
└──────────────────┬──────────────────────┘
                   ↓ calls
┌─────────────────────────────────────────┐
│           engine.execute()               │  ← Business logic dispatcher
└──────────────────┬──────────────────────┘
                   ↓
         domain_actions.py + SQLite
```

### Key Rules

1. **tools.py is the single source of truth** — all parameter names, types, defaults, and field conversions (e.g., `score` → `qualification_score`) live here
2. **mcp_server.py delegates to tools.py** — it does NOT call `engine.execute()` directly or hardcode schemas
3. **mcp_server.py discovers tools dynamically** — use `inspect.signature()` to auto-generate JSON schemas from `tools.py` function signatures
4. **No `mcp/` directory name** — if your project has a directory named `mcp/`, it will shadow the MCP SDK's `mcp/` package. Rename it to `ft_mcp_tools/` or similar

### Parameter Mapping Pattern

MCP tool parameter names should be user-friendly (e.g., `score`), while engine/action parameter names may differ (e.g., `qualification_score`). Handle this in `tools.py`, NOT in `mcp_server.py`:

```python
# tools.py — do the conversion HERE (single source of truth)
def qualify_lead(lead_id: str, score: int, notes: str = None) -> dict:
    params = {"lead_id": lead_id, "qualification_score": score}
    if notes:
        params["qualification_notes"] = notes
    return engine.execute("lead.qualify_lead", params)

# mcp_server.py — just delegate, no mapping needed
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    func = TOOL_MAP[name]  # get the tools.py function
    result = func(**arguments)  # tools.py already converted score→qualification_score
```

### Auto-Generated Schema (Recommended)

Instead of hardcoding JSON schemas in `mcp_server.py`, derive them from function signatures:

```python
import inspect

def sig_to_schema(sig: inspect.Signature) -> dict:
    properties, required = {}, []
    for param_name, param in sig.parameters.items():
        if param_name in ('self', 'cls'):
            continue
        param_type = "string"
        if param.annotation == int:   param_type = "integer"
        elif param.annotation == bool: param_type = "boolean"
        prop = {"type": param_type}
        if param.default is not inspect.Parameter.empty:
            prop["default"] = param.default
        else:
            required.append(param_name)
        properties[param_name] = prop
    return {"type": "object", "properties": properties, "required": required}
```

### Directory Naming Warning

> ⚠️ **Do NOT name a directory `mcp/`** in your project root. Python's import system resolves `import mcp` to your local `mcp/` directory before the MCP SDK's `mcp/` package in site-packages. This causes `ImportError: cannot import name 'Server' from 'mcp'`.

**Solution:** Rename `mcp/` to `ft_mcp_tools/`, `biz_tools/`, or any other name that doesn't conflict with the `mcp` top-level package.

---

## Import/Export Pattern in MCP Tools

When your MCP tools need to handle bulk data import/export (CSV, JSON, Excel), apply these patterns to avoid common pitfalls.

### Pattern: Session-In Data Extraction

SQLAlchemy ORM objects become **detached** after the session closes. Accessing their attributes outside the session block raises `DetachedInstanceError`. Always extract data inside the `with get_db_session()` block:

```python
# ❌ WRONG — detached after session closes
def export_customers(format: str = "csv") -> dict:
    with get_db_session() as session:
        repo = CustomerRepository(session)
        rows = repo.get_all()
    # rows are now detached!
    return write_file(rows)  # fails

# ✅ RIGHT — extract data inside session
def export_customers(format: str = "csv") -> dict:
    with get_db_session() as session:
        repo = CustomerRepository(session)
        rows = repo.get_all()
        data = [{"id": r.id, "company_name": r.company_name} for r in rows]
    # data is plain dict, safe to use outside session
    return write_file(data, format)
```

### Pattern: Field Mapping Table with Multi-Language Headers

Import tools must handle source files with different column naming conventions. Use a `FIELD_MAP` dict that maps source field names (including localized headers) to database column names:

```python
# In tools.py — the ONLY place field mapping lives
FIELD_MAP = {
    # English (exported files)
    "company_name": "company_name",
    "website":      "website",
    "country":      "country",
    "contact_email": "contact_email",
    # Chinese (Excel imports from business users)
    "公司名称":  "company_name",
    "官网":      "website",
    "国家":      "country",
    "联系人邮箱": "contact_email",
}

def import_customers(file_path: str, format: str = "auto") -> dict:
    detected = _detect_format(file_path)  # csv / json / xlsx
    rows = _read_file(file_path, detected)

    created = updated = skipped = 0
    for row in rows:
        mapped = {}
        for src_field, db_field in FIELD_MAP.items():
            if src_field in row:
                mapped[db_field] = row[src_field]

        # Remove prefixed IDs before constructor call to avoid duplicate kwargs
        lead_id = mapped.pop("lead_id", None)
        # ... upsert logic using mapped dict
```

### Pattern: `pop()` Before Passing `**mapped` to Constructor

When importing, the mapped dict may still contain `lead_id`/`customer_id` keys from the source file's column names. Passing `**mapped` to a SQLAlchemy constructor after already extracting `lead_id` causes a duplicate keyword argument error:

```python
# ❌ WRONG — lead_id appears twice
lead_id = mapped.get("lead_id")
customer = Customer(lead_id=lead_id, **mapped)  # mapped still has "lead_id"!

# ✅ RIGHT — pop it first
lead_id = mapped.pop("lead_id", None)
customer = Customer(lead_id=lead_id, **mapped)  # safe, lead_id removed from mapped
```

The same applies to any field passed as an explicit parameter before `**mapped`.

### Pattern: Auto-Detect Format and Column Shift

For Excel files that may have misaligned columns (e.g., inserted/deleted columns shifting data), auto-detect the shift and correct the mapping:

```python
def detect_shift(header: list[str], data_rows: list[list]) -> int:
    """Score each candidate shift (-3 to +3) by header match rate."""
    best_score, best_shift = -1, 0
    for shift in range(-3, 4):
        score = sum(
            header[i + shift] == expected
            for row in data_rows
            for i, expected in enumerate(EXPECTED_HEADERS)
            if 0 <= i + shift < len(header)
        )
        if score > best_score:
            best_score, best_shift = score, shift
    return best_shift

def read_sheet_with_shift(ws, expected_headers: list[str], shift: int = 0) -> list[dict]:
    """Read Excel rows, applying column shift correction."""
    rows = []
    for data_row in ws.iter_rows(min_row=2, values_only=True):
        mapped = {}
        for i, header in enumerate(expected_headers):
            src_idx = i + shift
            if 0 <= src_idx < len(data_row):
                mapped[header] = data_row[src_idx]
        rows.append(mapped)
    return rows
```

### Pattern: Upsert with Unique Field Lookup

Import should be idempotent — re-running the same file updates existing records rather than creating duplicates. Use the domain's unique identifier fields for lookup:

```python
def _import_customers(file_path: str, rows: list[dict]) -> dict:
    created = updated = skipped = 0
    for row in rows:
        mapped = {k: v for k, v in row.items() if v is not None and k in CUSTOMER_FIELD_MAP.values()}
        customer_id = mapped.pop("customer_id", None)

        if customer_id:
            existing = Customer.get_by_id(customer_id)
            if existing:
                for k, v in mapped.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                Customer.create(customer_id=customer_id, **mapped)
                created += 1
        else:
            # Fallback: lookup by unique fields
            existing = Customer.get_by_company_name(mapped.get("company_name"))
            if existing:
                for k, v in mapped.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                Customer.create(**mapped)
                created += 1
    return {"created": created, "updated": updated, "skipped": skipped}
```

### Summary

| Concern | Solution |
|---------|----------|
| ORM detached after session | Extract data inside `with get_db_session()` block |
| Multi-language Excel headers | `FIELD_MAP` dict with all language variants |
| Duplicate `**mapped` kwargs | `pop()` explicit fields before constructor call |
| Excel column misalignment | `detect_shift()` scoring across candidate offsets |
| Idempotent imports | Upsert by unique fields (`customer_id`, `company_name`, `email`) |

---

## Deployment Contract for Sensitive Data

When an MCP Server manages sensitive business data, **code-level constraints are insufficient**. AI Agents have arbitrary code execution capability — any check placed inside the execution context can be inspected and bypassed by the agent itself.

The only reliable protection is **architectural isolation**: the database is physically unreachable from the agent's execution context.

### The Contract

```
AI Agent (any framework: OpenClaw / Hermes / other)
    ↓ MCP over stdio (the ONLY legal data access gate)
MCP Server (tools.py is the only data access path)
    ↓ DB connection (MCP Server process only)
Database (path and credentials unreachable from agent)
```

### Three Requirements

1. **Database path outside agent workspace**
   - Agent can explore its workspace but cannot guess or access `~/.hermes/.db/`
2. **Credentials via `env:`, not filesystem**
   - MCP Server config passes `DB_KEY`/`DB_PATH` via environment variables
   - Agent cannot read another process's environment
3. **No filesystem access to DB path**
   - File permissions, containerization, or network isolation ensures this

### MCP Server Packaging Requirement

All MCP Servers generated from this framework MUST include this contract in their `README.md`:

```markdown
## Security / Deployment Requirements

This MCP Server manages sensitive business data.
The database MUST be isolated from the AI Agent's execution environment:

1. Database file path MUST be outside the agent's workspace
2. DB credentials MUST be passed via `env:` in your MCP config
3. The agent MUST NOT have filesystem access to the DB file path

Failure to meet these requirements allows the agent to bypass MCP tools
and access data directly, defeating the purpose of access control.
```

See `docs/security/deployment-isolation.md` for the canonical reference, including implementation checklists and deployment patterns.
