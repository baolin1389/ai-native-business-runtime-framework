# Engine Module

The execution engine handles task scheduling, execution, and orchestration.

## Components

- **core.py** - Core engine implementation
- **scheduler.py** - Task scheduling strategies (FIFO, Priority, Deadline)
- **executor.py** - Task execution (ThreadPool, ProcessPool, AsyncIO)

## Scheduling Strategies

- `FIFO` - First in, first out
- `Priority` - Priority-based scheduling
- `Deadline` - Deadline-aware scheduling

## Executors

- `ThreadPool` - Thread-based parallel execution
- `ProcessPool` - Process-based parallel execution
- `AsyncIO` - Asynchronous execution

## Usage

```python
from runtime_core.engine import RuntimeEngine, Scheduler, Executor

scheduler = Scheduler(strategy="Priority")
executor = Executor(type="AsyncIO", max_workers=10)
engine = RuntimeEngine(scheduler=scheduler, executor=executor)
```
