# CLI Architecture

## Overview

The Command Line Interface (CLI) provides a terminal-based interface for interacting with the AI Business Runtime Framework. It serves as the primary user-facing component for workflow management and system operation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Entry Point                          │
│                           (main.py)                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Command Dispatcher                          │
│                    (argparse / click)                            │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ↓                       ↓                       ↓
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   Workflow   │       │    System    │       │   Config     │
│   Commands   │       │   Commands   │       │   Commands   │
└──────────────┘       └──────────────┘       └──────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Runtime    │  │   Workflow   │  │      Config          │  │
│  │   Client     │  │   Manager    │  │      Manager         │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Command Structure

### Global Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize a new project or configuration |
| `version` | Display version information |
| `status` | Show system status and health |
| `help` | Display help information |

### Workflow Commands

| Command | Description |
|---------|-------------|
| `workflow create` | Create a new workflow definition |
| `workflow list` | List all workflows |
| `workflow run` | Execute a workflow |
| `workflow stop` | Stop a running workflow |
| `workflow delete` | Delete a workflow |
| `workflow logs` | Display workflow execution logs |

### System Commands

| Command | Description |
|---------|-------------|
| `system health` | Check system health |
| `system metrics` | Display system metrics |
| `system reset` | Reset system state |

## Command Parser

The CLI uses argparse for command-line argument parsing with the following features:

- **Subcommands:** Hierarchical command structure
- **Type validation:** Automatic argument type conversion
- **Help generation:** Auto-generated help text
- **Shell completion:** Optional tab completion support

## Output Formatting

### Console Output

| Format | Description |
|--------|-------------|
| `pretty` | Human-readable with colors and spacing |
| `json` | Machine-readable JSON output |
| `yaml` | YAML formatted output |
| `table` | Tabular output for lists |

### Progress Indicators

- Spinner for indeterminate operations
- Progress bar for lengthy operations
- Status indicators for quick feedback

## Configuration Integration

The CLI integrates with the configuration system:

```
CLI Config Precedence:
1. Command-line flags (highest priority)
2. Environment variables
3. Project configuration file
4. Global configuration file
5. Default values (lowest priority)
```

## Error Handling

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Workflow execution error |
| 4 | Configuration error |
| 5 | Connection error |

### Error Output

Errors are formatted consistently:
```
ERROR: [Error Type] - Description
  Location: command/component
  Suggestion: Recommended action
```

## Interactive Mode

The CLI supports an interactive mode for complex operations:

```bash
$ ai-runtime interactive
Welcome to AI Business Runtime Framework v1.0.0
(framework) > workflow list
(framework) > workflow run my-workflow
```

## Shell Integration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `AI_RUNTIME_HOME` | Framework installation directory |
| `AI_RUNTIME_CONFIG` | Path to configuration file |
| `AI_RUNTIME_LOG_LEVEL` | Logging verbosity |

### Aliases

Common commands can be aliased for convenience:
```bash
alias ai='ai-runtime'
alias ai-w='ai-runtime workflow'
```
