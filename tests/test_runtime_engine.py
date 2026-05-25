"""Tests for RuntimeEngine."""

import pytest
import asyncio
from datetime import datetime
from runtime_core.engine.core import (
    RuntimeEngine,
    TaskDefinition,
    ExecutionContext,
)


class MockExecutor:
    """Mock executor for testing."""

    def __init__(self, result=None, should_fail=False):
        self.result = result
        self.should_fail = should_fail
        self.execute_count = 0

    async def execute(self, task, context, prior_results):
        self.execute_count += 1
        if self.should_fail:
            raise RuntimeError(f"Executor failed for task {task.task_id}")
        return self.result or {f"result_{task.task_id}": "success"}


@pytest.fixture
def engine():
    """Create a RuntimeEngine instance."""
    return RuntimeEngine(config={"test_mode": True})


@pytest.fixture
def sample_task():
    """Create a sample task definition."""
    return TaskDefinition(
        task_id="test_task_1",
        name="Test Task",
        handler="mock_handler",
        config={"key": "value"},
    )


class TestRuntimeEngine:
    """Tests for RuntimeEngine class."""

    def test_engine_initialization(self, engine):
        """Test engine initializes with empty task registry."""
        assert engine.config == {"test_mode": True}
        assert len(engine._tasks) == 0
        assert len(engine._executors) == 0

    def test_engine_initialization_with_default_config(self):
        """Test engine initializes with empty dict if no config provided."""
        engine = RuntimeEngine()
        assert engine.config == {}
        assert len(engine._tasks) == 0

    def test_register_task(self, engine, sample_task):
        """Test registering a task definition."""
        engine.register_task(sample_task)
        assert "test_task_1" in engine._tasks
        assert engine._tasks["test_task_1"].name == "Test Task"

    def test_register_multiple_tasks(self, engine):
        """Test registering multiple tasks."""
        tasks = [
            TaskDefinition(task_id=f"task_{i}", name=f"Task {i}", handler="mock")
            for i in range(3)
        ]
        for task in tasks:
            engine.register_task(task)

        assert len(engine._tasks) == 3
        assert "task_0" in engine._tasks
        assert "task_1" in engine._tasks
        assert "task_2" in engine._tasks

    def test_register_executor(self, engine):
        """Test registering an executor."""
        executor = MockExecutor()
        engine.register_executor("mock_handler", executor)
        assert "mock_handler" in engine._executors
        assert engine._executors["mock_handler"] is executor

    def test_execute_workflow_returns_results_dict(self, engine, sample_task):
        """Test that execute_workflow returns a results dictionary."""
        executor = MockExecutor()
        engine.register_executor("mock_handler", executor)

        result = asyncio.run(
            engine.execute_workflow("workflow_1", [sample_task], {"input": "data"})
        )

        assert isinstance(result, dict)
        assert "test_task_1" in result

    def test_execute_workflow_with_multiple_tasks(self, engine):
        """Test executing a workflow with multiple tasks."""
        tasks = [
            TaskDefinition(task_id=f"task_{i}", name=f"Task {i}", handler="mock")
            for i in range(3)
        ]
        executor = MockExecutor()
        engine.register_executor("mock", executor)

        result = asyncio.run(
            engine.execute_workflow("workflow_multi", tasks, {"input": "data"})
        )

        assert len(result) == 3
        for i in range(3):
            assert f"task_{i}" in result

    def test_execute_workflow_missing_executor_raises(self, engine, sample_task):
        """Test that missing executor raises ValueError."""
        with pytest.raises(ValueError, match="No executor registered"):
            asyncio.run(
                engine.execute_workflow("workflow_1", [sample_task], {"input": "data"})
            )

    def test_task_definition_with_dependencies(self):
        """Test TaskDefinition with dependency tracking."""
        task = TaskDefinition(
            task_id="dependent_task",
            name="Dependent Task",
            handler="handler",
            dependencies=["task_1", "task_2"],
        )
        assert len(task.dependencies) == 2
        assert "task_1" in task.dependencies
        assert "task_2" in task.dependencies

    def test_task_definition_with_retry_policy(self):
        """Test TaskDefinition with retry policy."""
        retry_config = {"max_retries": 3, "backoff": "exponential"}
        task = TaskDefinition(
            task_id="retry_task",
            name="Retry Task",
            handler="handler",
            retry_policy=retry_config,
        )
        assert task.retry_policy == retry_config
        assert task.retry_policy["max_retries"] == 3

    def test_execution_context_creation(self):
        """Test ExecutionContext dataclass."""
        context = ExecutionContext(
            execution_id="exec_123",
            workflow_id="wf_456",
            input_data={"key": "value"},
        )
        assert context.execution_id == "exec_123"
        assert context.workflow_id == "wf_456"
        assert context.input_data == {"key": "value"}
        assert isinstance(context.started_at, datetime)

    def test_execution_context_with_metadata(self):
        """Test ExecutionContext with metadata."""
        metadata = {"user": "test_user", "source": "api"}
        context = ExecutionContext(
            execution_id="exec_789",
            workflow_id="wf_abc",
            metadata=metadata,
        )
        assert context.metadata == metadata
        assert context.metadata["user"] == "test_user"
