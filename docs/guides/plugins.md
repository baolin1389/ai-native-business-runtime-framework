# Plugin Development Guide

## Overview

The AI Business Runtime Framework supports plugins for extending functionality. Plugins can add new task types, integrations, monitoring capabilities, and more.

## Plugin Structure

```
my-plugin/
├── plugin.yaml           # Plugin manifest
├── src/
│   ├── __init__.py
│   ├── tasks/            # Custom task types
│   ├── executors/        # Custom executors
│   ├── integrations/     # External service integrations
│   └── handlers/         # Event handlers
├── config/
│   └── default_config.yaml
└── tests/
```

## Plugin Manifest

Every plugin requires a `plugin.yaml` manifest:

```yaml
plugin:
  name: my-plugin
  version: "1.0.0"
  description: Custom plugin for domain-specific tasks
  
  # Plugin metadata
  author: Your Name
  license: MIT
  homepage: https://github.com/your-org/my-plugin
  
  # Compatibility
  min_framework_version: "1.0.0"
  
  # Plugin components
  components:
    tasks:
      - custom_task
    executors:
      - custom_executor
    integrations:
      - my_integration
```

## Custom Task Types

### Creating a Custom Task

```python
# src/tasks/custom_task.py
from runtime.tasks import BaseTask

class CustomTask(BaseTask):
    """Custom task that processes data according to domain logic."""
    
    # Task type identifier (used in workflow YAML)
    task_type = "custom_task"
    
    def __init__(self, config):
        super().__init__(config)
        self.option = config.get("option", "default")
    
    async def execute(self, context):
        """
        Execute the task.
        
        Args:
            context: Execution context with inputs and state
            
        Returns:
            dict: Task result
        """
        input_data = context.get_input()
        
        # Custom processing logic
        result = self.process(input_data)
        
        return {
            "status": "success",
            "output": result,
            "metadata": {
                "option": self.option,
                "processed_at": context.timestamp
            }
        }
    
    def process(self, data):
        """Implement custom processing."""
        # Your logic here
        return processed_data
```

### Registering the Task

```python
# src/tasks/__init__.py
from .custom_task import CustomTask

TASK_REGISTRY = {
    "custom_task": CustomTask,
}

def get_task(task_type):
    """Get task class by type."""
    return TASK_REGISTRY.get(task_type)
```

## Custom Executors

### Executor Interface

```python
from runtime.executors import BaseExecutor

class MyExecutor(BaseExecutor):
    """Custom executor for specialized execution environments."""
    
    executor_type = "my_executor"
    
    def __init__(self, config):
        super().__init__(config)
        self.environment = config.get("environment", "default")
    
    async def initialize(self):
        """Initialize the executor environment."""
        # Set up resources, connections, etc.
        pass
    
    async def execute_task(self, task, context):
        """Execute a single task."""
        # Task execution logic
        result = await task.execute(context)
        return result
    
    async def shutdown(self):
        """Clean up executor resources."""
        pass
```

## External Integrations

### Creating an Integration

```python
# src/integrations/salesforce.py
from runtime.integrations import BaseIntegration

class SalesforceIntegration(BaseIntegration):
    """Salesforce CRM integration."""
    
    integration_type = "salesforce"
    
    def __init__(self, config):
        super().__init__(config)
        self.instance_url = config["instance_url"]
        self.api_version = config.get("api_version", "v58.0")
    
    async def connect(self):
        """Establish connection to Salesforce."""
        # OAuth flow or token-based auth
        self.client = await self.authenticate()
        return self
    
    async def query(self, soql):
        """Execute SOQL query."""
        response = await self.client.query(soql)
        return response["records"]
    
    async def create_record(self, object_type, data):
        """Create a new record."""
        return await self.client.create(object_type, data)
    
    async def update_record(self, object_type, record_id, data):
        """Update an existing record."""
        return await self.client.update(object_type, record_id, data)
```

### Integration Configuration

```yaml
# config/default_config.yaml
integrations:
  salesforce:
    enabled: true
    instance_url: https://mycompany.salesforce.com
    api_version: v58.0
    auth:
      type: oauth
      client_id_env: SALESFORCE_CLIENT_ID
      client_secret_env: SALESFORCE_CLIENT_SECRET
```

## Event Handlers

### Lifecycle Hooks

```python
from runtime.handlers import EventHandler

class MyEventHandler(EventHandler):
    """Handle workflow lifecycle events."""
    
    async def on_workflow_start(self, workflow_id, context):
        """Called when workflow starts."""
        logger.info(f"Workflow {workflow_id} started")
    
    async def on_task_start(self, workflow_id, task_id, context):
        """Called when task starts."""
        logger.debug(f"Task {task_id} in workflow {workflow_id} started")
    
    async def on_task_complete(self, workflow_id, task_id, result):
        """Called when task completes."""
        logger.info(f"Task {task_id} completed with result: {result}")
    
    async def on_task_failure(self, workflow_id, task_id, error):
        """Called when task fails."""
        logger.error(f"Task {task_id} failed: {error}")
    
    async def on_workflow_complete(self, workflow_id, result):
        """Called when workflow completes."""
        logger.info(f"Workflow {workflow_id} completed")
    
    async def on_workflow_failure(self, workflow_id, error):
        """Called when workflow fails."""
        logger.error(f"Workflow {workflow_id} failed: {error}")
```

## Using Plugins

### Installation

```bash
# Install from local directory
ai-runtime plugin install ./my-plugin

# Install from git
ai-runtime plugin install git+https://github.com/your-org/my-plugin

# Install from package
pip install my-plugin
ai-runtime plugin enable my-plugin
```

### Plugin Management

```bash
# List installed plugins
ai-runtime plugin list

# Enable a plugin
ai-runtime plugin enable my-plugin

# Disable a plugin
ai-runtime plugin disable my-plugin

# Uninstall a plugin
ai-runtime plugin uninstall my-plugin
```

### Plugin Configuration

Plugins can be configured in the main config:

```yaml
plugins:
  my_plugin:
    enabled: true
    option1: value1
    option2: value2
```

## Best Practices

### Error Handling

```python
class SafeCustomTask(BaseTask):
    async def execute(self, context):
        try:
            result = await self._execute_with_retry(context)
            return {"status": "success", "data": result}
        except ValidationError as e:
            return {"status": "validation_error", "error": str(e)}
        except ExternalServiceError as e:
            # Don't fail workflow, return error result
            return {"status": "service_error", "error": str(e), "retryable": True}
        except Exception as e:
            # Re-raise for workflow-level handling
            raise TaskExecutionError(f"Task failed: {e}") from e
```

### Logging

```python
import logging

logger = logging.getLogger("my-plugin")

class MyTask(BaseTask):
    async def execute(self, context):
        logger.info(f"Starting task with input: {context.input}")
        try:
            result = await self.process(context.input)
            logger.info(f"Task completed successfully")
            return result
        except Exception as e:
            logger.error(f"Task failed: {e}")
            raise
```

### Testing

```python
# tests/test_custom_task.py
import pytest
from runtime.tasks import TaskContext
from my_plugin.tasks import CustomTask

@pytest.fixture
def task():
    return CustomTask({"option": "test_value"})

@pytest.fixture
def context():
    return TaskContext(input={"data": "test"})

@pytest.mark.asyncio
async def test_custom_task_execution(task, context):
    result = await task.execute(context)
    
    assert result["status"] == "success"
    assert "output" in result
    assert result["metadata"]["option"] == "test_value"
```

### Documentation

Document your plugin in `README.md`:

```markdown
# My Plugin

Custom plugin for domain-specific AI workflows.

## Installation

```bash
ai-runtime plugin install my-plugin
```

## Configuration

```yaml
plugins:
  my_plugin:
    enabled: true
    option1: value1
```

## Usage

Use the custom task in workflows:

```yaml
tasks:
  - id: my_task
    type: custom_task
    config:
      option: value
```

## Requirements

- AI Runtime Framework >= 1.0.0
- Python >= 3.10
```
