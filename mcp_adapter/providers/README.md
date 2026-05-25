# MCP Providers

AI provider implementations for the MCP adapter.

## Supported Providers

- **openai.py** - OpenAI GPT models
- **anthropic.py** - Anthropic Claude models
- **google.py** - Google AI models
- **custom.py** - Custom provider interface

## Base Provider

All providers inherit from `BaseProvider` which defines the common interface.

## Usage

```python
from mcp_adapter.providers import OpenAIProvider, AnthropicProvider

openai = OpenAIProvider(api_key="...")
claude = AnthropicProvider(api_key="...")
```
