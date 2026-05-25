# State Module

State management for runtime workflows and tasks.

## Backends

- **memory** - In-memory state (default, non-persistent)
- **redis** - Redis-based persistence
- **postgres** - PostgreSQL persistence
- **sqlite** - SQLite persistence

## Usage

```python
from runtime_core.state import StateManager

manager = StateManager(backend="memory")
manager.set("workflow:1:status", "running")
status = manager.get("workflow:1:status")
```
