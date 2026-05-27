# AI Business Runtime Framework

A code generation framework for AI-powered business applications. Define your domain entities once, generate a complete runtime: engine, MCP adapter, SQLModel tables, config, and example workflows.

## Features

- **Entity-driven code generation** — Define entities in YAML, get a complete runtime
- **Runtime Engine** — CRUD action handlers with SQLite via SQLModel
- **MCP Server adapter** — Auto-generated JSON-RPC MCP server mapping tools to engine actions
- **SQLModel tables** — Type-safe database models generated from entity definitions
- **YAML configuration** — Runtime config, domain schemas, and example workflows
- **CLI** — Interactive wizard or declarative YAML to scaffold a new runtime

## Architecture

```
entities.yaml          →  RuntimeGenerator  →  app/runtime/engine.py
                                        →  mcp_server.py
                                        →  app/infrastructure/models.py
                                        →  config/runtime.yaml
                                        →  config/domains/{entity}.yaml
```

## Installation

```bash
pip install -e .
```

Requires Python 3.10+.

## Quick Start

### 1. Create entities YAML

```yaml
entities:
  - name: Lead
    table_name: lead
    description: Sales lead
    fields:
      - name: id
        type: string
        primary_key: true
      - name: name
        type: string
        required: true
      - name: email
        type: string
        required: true
```

### 2. Generate runtime

```bash
python -m cli.main generate \
  --name sales \
  --domain crm \
  --entities entities.yaml
```

Output:

```
sales/
├── app/
│   ├── infrastructure/
│   │   └── models.py       # SQLModel table definitions
│   └── runtime/
│       └── engine.py       # CRUD action handlers
├── config/
│   ├── runtime.yaml        # Infrastructure config
│   └── domains/
│       └── lead.yaml       # Entity schema
├── mcp_server.py           # MCP JSON-RPC adapter
└── workflows/
    └── example.yaml
```

### 3. Run MCP server

```bash
python mcp_server.py
```

## CLI Commands

```bash
# Interactive wizard
python -m cli.main init

# Generate from YAML
python -m cli.main generate --name <name> --domain <domain> --entities <file.yaml>

# Validate entities
python -m cli.main validate --entities <file.yaml>
```

## Testing

```bash
pytest tests/ -v
```

All 32 tests pass, covering:
- `runtime_core.engine` — 12 tests
- `runtime_generator.generator` — 7 tests (GeneratorConfig, RuntimeGenerator, CLI)
- `runtime_generator.templates` — 13 tests (AST validation, YAML generation, end-to-end)

## Project Structure

```
ai-business-runtime-framework/
├── runtime_core/
│   ├── __init__.py
│   ├── engine.py          # RuntimeEngine, TaskExecutor, ExecutionContext
│   ├── config.py          # Config loader (YAML)
│   ├── state_machine.py   # State machine definitions
│   ├── event_bus.py       # EventBus
│   └── models.py          # SQLModel session management
├── runtime_generator/
│   ├── __init__.py
│   ├── generator.py       # RuntimeGenerator, GeneratorConfig, entity data classes
│   ├── templates.py       # Code generators (engine_py, mcp_server_py, models_py, etc.)
│   └── cli/
│       └── main.py        # CLI entry point
├── tests/
│   ├── test_runtime_engine.py
│   ├── test_runtime_generator.py
│   └── test_templates.py
├── docs/
│   └── architecture/
│       ├── overview.md
│       ├── entity-definition.md
│       ├── state-machine.md
│       ├── mcp-adapter.md
│       └── workflow.md
├── pyproject.toml
└── requirements.txt
```

## Key Classes

### `RuntimeGenerator`

```python
from runtime_generator.generator import RuntimeGenerator, GeneratorConfig, EntityDef, FieldDef

cfg = GeneratorConfig(name="sales", output_dir="./output")
g = RuntimeGenerator(cfg)
g.add_entity(EntityDef(name="Lead", table_name="lead", fields=[...]))
g.save()  # generates all files
```

### `RuntimeEngine`

```python
from runtime_core.engine import RuntimeEngine

engine = RuntimeEngine()
engine.execute("create_lead", {"name": "Alice", "email": "alice@example.com"})
engine.execute("list_leads", {"limit": 10})
```
