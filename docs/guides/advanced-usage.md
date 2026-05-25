# Advanced Usage Guide

## Async Workflow Execution

Run workflows asynchronously for better performance with multiple workflows:

```bash
ai-runtime workflow run workflow1.yaml --async &
ai-runtime workflow run workflow2.yaml --async &
wait
```

### Python API Async Usage

```python
import asyncio
from runtime_client import RuntimeClient

async def run_workflows():
    client = RuntimeClient()
    
    # Run multiple workflows concurrently
    tasks = [
        client.run_workflow_async("workflow1.yaml"),
        client.run_workflow_async("workflow2.yaml"),
        client.run_workflow_async("workflow3.yaml"),
    ]
    
    results = await asyncio.gather(*tasks)
    
    for result in results:
        print(f"Result: {result}")

asyncio.run(run_workflows())
```

## Parallel Task Execution

Configure tasks to run in parallel when they don't depend on each other:

```yaml
tasks:
  - id: fetch_data_1
    type: function
    config:
      module: data
      function: fetch_type_a
      
  - id: fetch_data_2
    type: function
    config:
      module: data
      function: fetch_type_b
      
  - id: process_both
    type: transform
    config:
      operation: merge
      inputs:
        type_a: "{{fetch_data_1}}"
        type_b: "{{fetch_data_2}}"
    depends_on: [fetch_data_1, fetch_data_2]
```

The framework automatically parallelizes independent tasks within a stage.

## Custom Executors

Create custom task executors for specialized processing:

```python
# my_executors.py
from runtime import BaseExecutor

class CustomDataExecutor(BaseExecutor):
    async def execute(self, task_config, context):
        # Custom execution logic
        data = task_config.get("input_data")
        processed = self.process_data(data)
        return {"result": processed, "metadata": {...}}
    
    def process_data(self, data):
        # Implement custom logic
        return processed_data
```

Register the executor:

```yaml
executors:
  custom:
    type: module
    module: my_executors
    class: CustomDataExecutor
```

Use in workflow:

```yaml
tasks:
  - id: custom_task
    type: custom
    config:
      input_data: "{{previous_task.result}}"
```

## Workflow Chaining

Execute multiple workflows in sequence with data passing:

```python
from runtime_client import RuntimeClient

client = RuntimeClient()

# First workflow
result1 = client.run_workflow(
    "data-fetch.yaml",
    context={"source": "database"}
)

# Second workflow uses output from first
result2 = client.run_workflow(
    "process.yaml",
    context={
        "raw_data": result1["data"],
        "config": result1["config"]
    }
)

# Third workflow
result3 = client.run_workflow(
    "report.yaml",
    context={"processed": result2["processed"]}
)
```

## Dynamic Workflow Generation

Generate workflows programmatically:

```python
from workflow_manager import WorkflowManager

manager = WorkflowManager()

# Build workflow dynamically
workflow_def = {
    "workflow": {
        "name": "dynamic-workflow",
        "version": "1.0"
    },
    "tasks": []
}

# Add tasks dynamically
for i, item in enumerate(items):
    workflow_def["tasks"].append({
        "id": f"task_{i}",
        "type": "function",
        "config": {
            "module": "processors",
            "function": f"process_{item['type']}",
            "args": [item["data"]]
        }
    })

# Create and run
workflow = manager.create_workflow(**workflow_def)
result = manager.run_workflow(workflow.id)
```

## Caching Results

Enable caching to avoid redundant computations:

```yaml
workflow:
  name: cached-workflow
  version: "1.0"
  
config:
  cache_enabled: true
  cache_ttl: 3600  # 1 hour
  cache_key: "{{context.input_hash}}"  # Custom cache key

tasks:
  - id: expensive_task
    type: function
    config:
      module: expensive
      function: compute
      cache: true  # Per-task override
```

## Error Handling Patterns

### Retry with Backoff

```yaml
tasks:
  - id: unreliable_api
    type: prompt
    config:
      prompt: "Query the API"
      retry_policy:
        max_attempts: 5
        backoff: exponential
        initial_delay: 1
        max_delay: 60
```

### Fallback Path

```yaml
tasks:
  - id: primary_task
    type: prompt
    config:
      prompt: "Try primary model"
    on_failure: fallback_task
      
  - id: fallback_task
    type: prompt
    config:
      prompt: "Use simpler query"
      model: gpt-4o-mini
```

### Graceful Degradation

```yaml
tasks:
  - id: analytics
    type: transform
    config:
      operation: map
      items: "{{data.items}}"
      continue_on_error: true  # Partial results
      error_default: null
```

## Conditional Execution

### Input-Based Conditions

```yaml
tasks:
  - id: check_input
    type: condition
    config:
      expression: "{{context.processing_mode}} == 'fast'"
      
  - id: fast_path
    type: transform
    config:
      operation: simple_transform
    depends_on: [check_input]
    
  - id: detailed_path
    type: transform
    config:
      operation: detailed_transform
    depends_on: [check_input]
```

### Output-Based Conditions

```yaml
tasks:
  - id: analyze
    type: prompt
    config:
      prompt: "Analyze data"
      
  - id: check_quality
    type: condition
    config:
      expression: "{{analyze.confidence}} > 0.8"
      
  - id: finalize
    type: transform
    config:
      operation: finalize
    depends_on: [check_quality]
```

## Resource Management

### Memory-Intensive Workflows

```yaml
config:
  resources:
    memory_limit: 8GB
    enable_streaming: true  # Process in chunks

tasks:
  - id: process_large_file
    type: function
    config:
      module: processor
      function: process_streaming
      chunk_size: 1048576  # 1MB chunks
```

### CPU-Parallel Workflows

```yaml
config:
  execution:
    max_workers: 20  # Increase parallelism

tasks:
  - id: parallel_tasks
    type: loop
    config:
      items: "{{large_dataset}}"
      max_parallel: 20
```

## Monitoring and Observability

### Custom Metrics

```python
from runtime import Metrics

metrics = Metrics()

@metrics.timer("task_duration")
@metrics.counter("task_executions")
async def my_task(task_config, context):
    # Task logic
    metrics.gauge("memory_usage", get_memory_usage())
    return result
```

### Structured Logging

```python
import logging

logger = logging.getLogger("my-workflow")

logger.info("Starting task", extra={
    "task_id": "task_1",
    "workflow_id": "wf_123"
})

logger.warning("Retrying", extra={
    "attempt": 2,
    "max_attempts": 5
})

logger.error("Task failed", extra={
    "error": str(e),
    "task_id": "task_1"
})
```

### Health Checks

```yaml
health_checks:
  enabled: true
  interval: 30
  checks:
    - name: provider_availability
      type: http
      endpoint: https://api.openai.com/v1/models
      timeout: 5
    - name: disk_space
      type: disk
      threshold: 1GB
```

## Performance Tuning

### Batching Requests

```yaml
tasks:
  - id: batch_process
    type: function
    config:
      module: batcher
      function: process_batch
      batch_size: 100
      batch_timeout: 5  # seconds
```

### Connection Pooling

```yaml
mcp_adapter:
  transport:
    type: http
    pool_size: 20
    keep_alive: true
    max_keepalive_connections: 10
```

### Profile and Optimize

```bash
# Enable profiling
ai-runtime workflow run my-workflow.yaml --profile

# View performance report
ai-runtime workflow inspect <id> --profile
```
