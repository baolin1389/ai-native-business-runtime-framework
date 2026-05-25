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
