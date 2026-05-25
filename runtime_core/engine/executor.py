"""Task executor implementations."""

import asyncio
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


class BaseExecutor(ABC):
    """Abstract base class for task executors."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    async def execute(
        self,
        task: Any,
        context: Any,
        prior_results: Dict[str, Any]
    ) -> Any:
        """Execute the task and return results."""
        pass


class PythonExecutor(BaseExecutor):
    """Executor for running Python callable tasks."""

    async def execute(
        self,
        task: Any,
        context: Any,
        prior_results: Dict[str, Any]
    ) -> Any:
        """Execute a Python function as a task."""
        handler = self.config.get("handler")
        if not callable(handler):
            raise ValueError("PythonExecutor requires a callable handler")

        if asyncio.iscoroutinefunction(handler):
            return await handler(task, context, prior_results)
        return handler(task, context, prior_results)


class ScriptExecutor(BaseExecutor):
    """Executor for running external script tasks."""

    async def execute(
        self,
        task: Any,
        context: Any,
        prior_results: Dict[str, Any]
    ) -> Any:
        """Execute an external script as a task."""
        script_path = task.config.get("script_path")
        if not script_path:
            raise ValueError("ScriptExecutor requires script_path in task config")

        process = await asyncio.create_subprocess_exec(
            "python",
            script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Script failed: {stderr.decode()}")

        return stdout.decode()


class TaskExecutor:
    """High-level task execution coordinator."""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_batch(
        self,
        tasks: List[Any],
        context: Any
    ) -> List[Any]:
        """Execute multiple tasks with concurrency control."""
        async def execute_with_semaphore(task):
            async with self._semaphore:
                return await task.execute(context)

        return await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
