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
