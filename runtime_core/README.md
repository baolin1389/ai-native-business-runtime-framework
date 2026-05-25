# Runtime Core

This directory contains the core runtime components for the AI Business Runtime Framework.

## Components

- **engine/** - Execution engine (scheduler, executor, core)
- **validation/** - Schema and rule validation
- **domain/** - Domain-specific models and workflows
- **state/** - State management
- **shared/** - Shared utilities and helpers
- **runtime/** - Runtime instance management

## Usage

```python
from runtime_core.engine import RuntimeEngine

engine = RuntimeEngine()
engine.start()
```
