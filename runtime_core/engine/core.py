"""Core runtime engine implementation."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TaskDefinition:
    """Defines a task within the runtime."""
    task_id: str
    name: str
    handler: str
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    retry_policy: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionContext:
    """Context passed during task execution."""
    execution_id: str
    workflow_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)


class RuntimeEngine:
    """Main engine for executing business workflows and tasks."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._tasks: Dict[str, TaskDefinition] = {}
        self._executors: Dict[str, Any] = {}

    def register_task(self, task: TaskDefinition) -> None:
        """Register a task definition with the engine."""
        self._tasks[task.task_id] = task

    def register_executor(self, name: str, executor: Any) -> None:
        """Register an executor for handling specific task types."""
        self._executors[name] = executor

    async def execute_workflow(
        self,
        workflow_id: str,
        tasks: List[TaskDefinition],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a workflow consisting of multiple tasks."""
        context = ExecutionContext(
            execution_id=f"exec_{workflow_id}_{datetime.utcnow().timestamp()}",
            workflow_id=workflow_id,
            input_data=input_data
        )

        results = {}
        for task in tasks:
            result = await self._execute_task(task, context, results)
            results[task.task_id] = result

        return results

    async def _execute_task(
        self,
        task: TaskDefinition,
        context: ExecutionContext,
        prior_results: Dict[str, Any]
    ) -> Any:
        """Execute a single task with its dependencies resolved."""
        executor = self._executors.get(task.handler)
        if not executor:
            raise ValueError(f"No executor registered for handler: {task.handler}")

        return await executor.execute(task, context, prior_results)
