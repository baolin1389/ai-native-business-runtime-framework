# Tests — AI Business Runtime Framework
# =======================================

## Purpose

`tests/` validates the **framework itself** — not any concrete runtime.
Tests are portable: they can run against any project that uses the framework
runtime_core components.

## Structure

```
tests/
├── test_runtime_engine.py        # RuntimeEngine core
├── test_action_registry.py      # ActionRegistry
├── test_constraint_engine.py     # ConstraintEngine
└── test_state_manager.py         # StateManager
```

## Run

```bash
# From framework root
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=runtime_core
```

## What Each Test Covers

| File | Component | What it Tests |
|------|-----------|---------------|
| `test_runtime_engine.py` | `RuntimeEngine` | Task registration, workflow execution, context handling |
| `test_action_registry.py` | `ActionRegistry` | Action registration, execution, deps injection |
| `test_constraint_engine.py` | `ConstraintEngine` | Constraint registration, field validation, batch validation |
| `test_state_manager.py` | `StateManager` | State transitions, history, listeners, snapshots, async waiting |

## Design Principle

Tests use the **real implementations** from `runtime_core/`.
No mocks — if a test passes, the component actually works.
