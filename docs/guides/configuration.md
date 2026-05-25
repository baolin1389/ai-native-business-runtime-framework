# Configuration Guide

## Overview

The AI Business Runtime Framework uses a hierarchical configuration system that allows settings at global, project, and command-line levels.

## Configuration Files

### Global Configuration

Located at: `~/.ai-runtime/config.yaml`

```yaml
runtime:
  home: ~/.ai-runtime
  data_dir: ~/.ai-runtime/data
  log_level: INFO

execution:
  default_timeout: 300
  max_workers: 10
  retry_policy:
    max_attempts: 3
    initial_delay: 1
    backoff: exponential
```

### Project Configuration

Located at: `./.ai-runtime/config.yaml` (project root)

Project settings override global settings.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_RUNTIME_HOME` | Framework home directory | `~/.ai-runtime` |
| `AI_RUNTIME_CONFIG` | Config file path | `~/.ai-runtime/config.yaml` |
| `AI_RUNTIME_LOG_LEVEL` | Logging level | `INFO` |
| `AI_RUNTIME_DATA_DIR` | Data directory | `~/.ai-runtime/data` |

## Provider Configuration

### OpenAI

```yaml
providers:
  openai:
    enabled: true
    api_key_env: OPENAI_API_KEY
    endpoint: https://api.openai.com/v1
    default_model: gpt-4o
    organization: null  # Optional org ID
    
    # Rate limiting
    rate_limit:
      requests_per_minute: 60
      tokens_per_minute: 90000
      
    # Retry configuration
    retry:
      max_attempts: 3
      timeout: 60
```

### Anthropic

```yaml
providers:
  anthropic:
    enabled: true
    api_key_env: ANTHROPIC_API_KEY
    endpoint: https://api.anthropic.com/v1
    default_model: claude-3-5-sonnet-20241022
    
    rate_limit:
      requests_per_minute: 50
      tokens_per_minute: 100000
      
    retry:
      max_attempts: 3
      timeout: 60
```

### Google

```yaml
providers:
  google:
    enabled: true
    api_key_env: GOOGLE_API_KEY
    endpoint: https://generativelanguage.googleapis.com/v1
    default_model: gemini-1.5-flash
    
    rate_limit:
      requests_per_minute: 60
      tokens_per_minute: 1000000
      
    retry:
      max_attempts: 3
      timeout: 60
```

## Runtime Configuration

```yaml
runtime:
  # Executor settings
  executor:
    type: default
    max_workers: 10
    queue_size: 1000
    task_timeout: 300
    
  # Scheduler settings
  scheduler:
    check_interval_ms: 100
    max_schedule_ahead: 3600
    
  # State management
  state:
    persistence_enabled: true
    snapshot_interval_seconds: 60
    cleanup_on_completion: true
    
  # Resource limits
  resources:
    cpu_limit: null  # null = unlimited
    memory_limit: null  # null = unlimited
    disk_cache_size: 1GB
```

## MCP Adapter Configuration

```yaml
mcp_adapter:
  # Transport settings
  transport:
    type: http  # http, websocket, streaming
    pool_size: 10
    keep_alive: true
    connection_timeout: 30
    
  # Default provider
  default_provider: openai
  
  # Request settings
  request:
    timeout_seconds: 60
    max_retries: 3
    retry_backoff: exponential
    
  # Response handling
  response:
    stream_chunk_size: 1024
    max_response_size: 10MB
```

## CLI Configuration

```yaml
cli:
  # Output settings
  output:
    format: pretty  # pretty, json, yaml, table
    color: true
    pager: auto
    
  # Interactive mode
  interactive:
    enabled: true
    prompt: "(ai-runtime) "
    
  # History
  history:
    enabled: true
    size: 1000
    file: ~/.ai-runtime/history
```

## Configuration Commands

### View Current Configuration

```bash
ai-runtime config show
```

### View Effective Configuration

```bash
ai-runtime config show --effective
```

### Set Configuration Value

```bash
ai-runtime config set runtime.executor.max_workers 20
```

### Reset to Defaults

```bash
ai-runtime config reset
```

## Configuration Precedence

Settings are applied in order of priority (highest first):

1. **Command-line flags** - `--runtime.max_workers 20`
2. **Environment variables** - `AI_RUNTIME_MAX_WORKERS=20`
3. **Project config** - `./.ai-runtime/config.yaml`
4. **Global config** - `~/.ai-runtime/config.yaml`
5. **Default values** - Built-in defaults

## Advanced: Multiple Config Files

Load additional configuration files:

```bash
ai-runtime --config /path/to/custom-config.yaml workflow run my-workflow.yaml
```

## Configuration Validation

The framework validates configuration on startup. Invalid settings will produce warnings or errors:

```yaml
# Example: Invalid setting warning
WARN: Unknown config key 'runtime.invalid_setting' - ignoring
ERROR: 'runtime.executor.max_workers' must be positive integer
```

## Secrets Management

API keys should never be stored in configuration files. Use environment variables:

```bash
# Set API key
export OPENAI_API_KEY="sk-..."

# Or use a secrets manager
ai-runtime secrets set openai_api_key "sk-..."
```

To use secrets in workflows:

```yaml
providers:
  openai:
    api_key_env: OPENAI_API_KEY
```

## Complete Example Configuration

```yaml
# ~/.ai-runtime/config.yaml

runtime:
  home: ~/.ai-runtime
  data_dir: ~/.ai-runtime/data
  log_level: INFO

providers:
  openai:
    enabled: true
    api_key_env: OPENAI_API_KEY
    default_model: gpt-4o
    rate_limit:
      requests_per_minute: 60
      tokens_per_minute: 90000

  anthropic:
    enabled: true
    api_key_env: ANTHROPIC_API_KEY
    default_model: claude-3-5-sonnet-20241022

mcp_adapter:
  default_provider: openai
  transport:
    type: http
    pool_size: 10

execution:
  default_timeout: 300
  max_workers: 10
  retry_policy:
    max_attempts: 3
    initial_delay: 1
    backoff: exponential

cli:
  output:
    format: pretty
    color: true
```
