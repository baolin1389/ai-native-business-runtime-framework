# MCP Adapter

Model Context Protocol (MCP) adapter for integrating AI providers.

## Components

- **client.py** - MCP client implementation
- **protocol.py** - Protocol definitions
- **transport.py** - Transport layer
- **config.py** - Configuration management
- **rate_limiter.py** - Rate limiting
- **exceptions.py** - Custom exceptions
- **providers/** - AI provider integrations

## Supported Providers

- OpenAI
- Anthropic
- Google AI
- Custom providers

## Usage

```python
from mcp_adapter import MCPClient

client = MCPClient(provider="openai", api_key="...")
response = await client.complete(prompt="Hello, world!")
```
