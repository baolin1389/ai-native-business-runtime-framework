# API Reference

## CLI Commands

### Global Commands

#### `ai-runtime init`

Initialize a new project or reset configuration.

```bash
ai-runtime init [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--reset` | Reset to default configuration |
| `--force` | Skip confirmation prompts |

---

#### `ai-runtime version`

Display version information.

```bash
ai-runtime version
```

**Output:**
```
AI Business Runtime Framework v1.0.0
Python 3.10.12
```

---

#### `ai-runtime status`

Show system status and health.

```bash
ai-runtime status [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--detailed` | Show detailed status |

---

### Workflow Commands

#### `ai-runtime workflow create`

Create a new workflow from template.

```bash
ai-runtime workflow create <name> [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--template` | Template to use (basic, api, data-processing) |
| `--output` | Output file path |

**Example:**
```bash
ai-runtime workflow create my-workflow --template basic
```

---

#### `ai-runtime workflow list`

List all workflows.

```bash
ai-runtime workflow list [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--status` | Filter by status (pending, running, completed, failed) |
| `--format` | Output format (table, json, yaml) |

---

#### `ai-runtime workflow run`

Execute a workflow.

```bash
ai-runtime workflow run <workflow-file> [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--context` | JSON context data |
| `--timeout` | Execution timeout in seconds |
| `--verbose` | Enable verbose output |
| `--async` | Run asynchronously |

**Example:**
```bash
ai-runtime workflow run my-workflow.yaml --context '{"customer_id": "123"}'
```

---

#### `ai-runtime workflow stop`

Stop a running workflow.

```bash
ai-runtime workflow stop <workflow-id>
```

---

#### `ai-runtime workflow delete`

Delete a workflow.

```bash
ai-runtime workflow delete <workflow-id> [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--force` | Skip confirmation |
| `--logs` | Also delete associated logs |

---

#### `ai-runtime workflow logs`

Display workflow execution logs.

```bash
ai-runtime workflow logs <workflow-id> [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--task` | Filter by task ID |
| `--level` | Filter by log level |
| `--follow` | Stream logs in real-time |
| `--tail` | Number of lines to show from end |

---

#### `ai-runtime workflow validate`

Validate a workflow definition.

```bash
ai-runtime workflow validate <workflow-file> [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--verbose` | Show detailed validation output |
| `--schema` | Validate against specific schema |

---

#### `ai-runtime workflow inspect`

Inspect workflow details.

```bash
ai-runtime workflow inspect <workflow-id>
```

---

### System Commands

#### `ai-runtime system health`

Check system health.

```bash
ai-runtime system health
```

**Output:**
```
System Health Check
==================
Runtime: OK
MCP Adapter: OK
Providers: OK (3/3 configured)

Last Check: 2026-05-25T10:30:00Z
```

---

#### `ai-runtime system metrics`

Display system metrics.

```bash
ai-runtime system metrics [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--period` | Time period (1h, 24h, 7d) |
| `--format` | Output format |

---

#### `ai-runtime system reset`

Reset system state.

```bash
ai-runtime system reset [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--force` | Skip confirmation |
| `--clear-data` | Also clear all data |

---

### Config Commands

#### `ai-runtime config show`

Display configuration.

```bash
ai-runtime config show [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--effective` | Show effective configuration |
| `--format` | Output format (json, yaml) |

---

#### `ai-runtime config set`

Set configuration value.

```bash
ai-runtime config set <key> <value>
```

**Example:**
```bash
ai-runtime config set runtime.executor.max_workers 20
```

---

#### `ai-runtime config reset`

Reset configuration to defaults.

```bash
ai-runtime config reset [OPTIONS]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--global` | Reset global config only |
| `--project` | Reset project config only |

---

## Python API

### Runtime Client

```python
from runtime_client import RuntimeClient

# Initialize client
client = RuntimeClient()

# Run workflow
result = client.run_workflow(
    workflow_file="my-workflow.yaml",
    context={"key": "value"},
    timeout=300
)

print(result)
```

### Workflow Manager

```python
from workflow_manager import WorkflowManager

manager = WorkflowManager()

# Create workflow
workflow = manager.create_workflow(
    name="my-workflow",
    tasks=[...],
    config={}
)

# List workflows
workflows = manager.list_workflows(status="completed")

# Get workflow
workflow = manager.get_workflow("workflow-id")

# Delete workflow
manager.delete_workflow("workflow-id")
```

### Configuration Manager

```python
from config_manager import ConfigManager

config = ConfigManager()

# Get value
value = config.get("runtime.executor.max_workers")

# Set value
config.set("runtime.executor.max_workers", 20)

# Save
config.save()

# Reset to defaults
config.reset()
```

## Task Configuration Reference

### Prompt Task Config

```python
{
    "prompt": str,           # Required: The prompt text
    "model": str,            # Optional: Model name (default from config)
    "temperature": float,     # Optional: 0.0-1.0 (default: 0.7)
    "max_tokens": int,       # Optional: Max response tokens (default: 1000)
    "system_prompt": str,    # Optional: System instructions
    "timeout": int,          # Optional: Task timeout in seconds
}
```

### Transform Task Config

```python
{
    "operation": str,        # Required: filter|map|reduce|merge|format
    "expression": str,       # Optional: Filter/map expression
    "input": str,            # Optional: Input data reference
    "inputs": dict,          # Optional: Multiple inputs for merge
    "template": str,         # Optional: Format template
    "output": str,           # Optional: Output key name
}
```

### Condition Task Config

```python
{
    "expression": str,       # Required: Condition expression
    "then_tasks": list,      # Required: Tasks if true
    "else_tasks": list,      # Optional: Tasks if false
}
```

### Loop Task Config

```python
{
    "items": str,            # Required: Items to iterate
    "task_template": dict,   # Required: Task definition for each item
    "max_parallel": int,     # Optional: Max parallel iterations (default: 1)
    "continue_on_error": bool,  # Optional: Continue if item fails
}
```

### Function Task Config

```python
{
    "module": str,           # Required: Module name
    "function": str,         # Required: Function name
    "args": list,           # Optional: Positional arguments
    "kwargs": dict,          # Optional: Keyword arguments
    "timeout": int,         # Optional: Function timeout
}
```

## Exit Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | Success | Command completed successfully |
| 1 | GeneralError | General error occurred |
| 2 | InvalidArguments | Invalid command-line arguments |
| 3 | WorkflowExecutionError | Workflow execution failed |
| 4 | ConfigurationError | Configuration error |
| 5 | ConnectionError | Connection to service failed |
| 6 | AuthenticationError | Authentication failed |
| 7 | RateLimitError | Rate limit exceeded |
| 8 | TimeoutError | Operation timed out |
