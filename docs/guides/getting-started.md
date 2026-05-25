# Getting Started with AI Business Runtime Framework

## Prerequisites

Before using the AI Business Runtime Framework, ensure you have:

- **Python 3.10 or later** installed
- **pip** package manager
- Access to at least one supported AI provider (OpenAI, Anthropic, or Google)

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/your-org/ai-business-runtime-framework.git

# Navigate to project directory
cd ai-business-runtime-framework

# Install dependencies
pip install -e .
```

### Verify Installation

```bash
ai-runtime version
```

Expected output:
```
AI Business Runtime Framework v1.0.0
```

## Quick Start

### 1. Initialize Configuration

```bash
ai-runtime init
```

This creates a `.ai-runtime` directory in your home folder with default configuration.

### 2. Configure API Keys

Set your AI provider API key as an environment variable:

```bash
# For OpenAI
export OPENAI_API_KEY="sk-..."

# For Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# For Google
export GOOGLE_API_KEY="your-api-key"
```

### 3. Create Your First Workflow

Create a file named `hello-world.yaml`:

```yaml
workflow:
  name: hello-world
  version: "1.0"
  description: My first AI-powered workflow

tasks:
  - id: greet
    type: prompt
    config:
      prompt: "Hello! What is the current date?"
      model: gpt-4o
      max_tokens: 100
```

### 4. Run the Workflow

```bash
ai-runtime workflow run hello-world.yaml
```

Expected output:
```
Workflow: hello-world
Status: COMPLETED
Duration: 2.3s

Result:
---
Hello! The current date is May 25, 2026.
```

## Project Structure

A typical AI Business Runtime project:

```
my-project/
├── workflows/
│   ├── workflow1.yaml
│   └── workflow2.yaml
├── tasks/
│   └── custom_tasks.py
├── .ai-runtime/
│   └── config.yaml
└── output/
    └── results/
```

## Basic Concepts

### Workflows

A workflow is a collection of tasks organized to accomplish a specific goal. Workflows are defined in YAML or JSON format.

### Tasks

Tasks are the fundamental execution units. Common task types:

| Type | Description |
|------|-------------|
| `prompt` | Send a prompt to an AI model |
| `transform` | Transform data between tasks |
| `condition` | Conditional branching |
| `loop` | Iterative execution |
| `function` | Custom Python function |

### Executors

Executors are runtime environments that execute tasks. Default executor handles standard tasks.

## Next Steps

- [Create more complex workflows](./workflow-creation.md)
- [Configure providers and settings](./configuration.md)
- [Explore advanced usage patterns](./advanced-usage.md)
- [Build custom plugins](./plugins.md)

## Common Commands

| Command | Description |
|---------|-------------|
| `ai-runtime workflow list` | List all workflows |
| `ai-runtime workflow run <file>` | Execute a workflow |
| `ai-runtime workflow logs <id>` | View execution logs |
| `ai-runtime system health` | Check system health |
| `ai-runtime config show` | Display current configuration |

## Troubleshooting

If you encounter issues:

1. Verify Python version: `python --version`
2. Check installation: `ai-runtime version`
3. Validate configuration: `ai-runtime config show`
4. Run with verbose logging: `ai-runtime workflow run <file> --verbose`

For detailed troubleshooting, see the [Troubleshooting Guide](./troubleshooting.md).
