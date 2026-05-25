# Workflow Creation Guide

## Overview

This guide covers creating workflows using the AI Business Runtime Framework. You'll learn the workflow definition format, task types, and best practices.

## Workflow Definition Format

Workflows are defined in YAML format with the following structure:

```yaml
workflow:
  name: string (required)
  version: string (required)
  description: string (optional)
  config:
    timeout: number (optional)
    retry_policy: object (optional)

tasks:
  - id: string (required)
    type: string (required)
    config: object (required)
    depends_on: list[string] (optional)
```

## Task Types

### Prompt Task

Sends a prompt to an AI model and returns the response.

```yaml
tasks:
  - id: analyze_text
    type: prompt
    config:
      prompt: |
        Analyze the following text and extract key themes.
        Text: {{input}}
      model: gpt-4o
      temperature: 0.7
      max_tokens: 500
```

**Configuration Options:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | required | The prompt template |
| `model` | string | config default | Model to use |
| `temperature` | float | 0.7 | Response randomness (0-1) |
| `max_tokens` | int | 1000 | Maximum response length |
| `system_prompt` | string | null | System-level instructions |

### Transform Task

Transforms data from previous task outputs.

```yaml
tasks:
  - id: format_output
    type: transform
    config:
      operation: filter
      expression: "status == 'success'"
      input: "{{analyze_text.result}}"
```

**Operations:**
- `filter` - Filter items based on expression
- `map` - Transform each item
- `reduce` - Aggregate values
- `merge` - Combine multiple inputs
- `format` - Format as string

### Condition Task

Implements conditional branching.

```yaml
tasks:
  - id: check_status
    type: condition
    config:
      expression: "{{analyze_text.confidence}} > 0.8"
      then_tasks: [high_confidence_path]
      else_tasks: [low_confidence_path]
```

### Loop Task

Iterates over a collection of items.

```yaml
tasks:
  - id: process_items
    type: loop
    config:
      items: "{{fetch_data.items}}"
      task_template:
        id: process_item
        type: transform
        config:
          operation: uppercase
          input: "{{item}}"
      max_parallel: 5
```

### Function Task

Executes a custom Python function.

```yaml
tasks:
  - id: custom_processing
    type: function
    config:
      module: my_tasks
      function: process_data
      args:
        - "{{previous_task.result}}"
      kwargs:
        option: value
```

## Dependencies

Tasks can depend on other tasks using `depends_on`:

```yaml
tasks:
  - id: task_a
    type: prompt
    config:
      prompt: "Task A"
      
  - id: task_b
    type: prompt
    config:
      prompt: "Task B"
    depends_on: [task_a]
    
  - id: task_c
    type: prompt
    config:
      prompt: "Task C"
    depends_on: [task_a]
    
  - id: task_d
    type: prompt
    config:
      prompt: "Task D"
    depends_on: [task_b, task_c]
```

This creates the dependency structure:
```
task_a
   ├── task_b
   └── task_c
        └── task_d
```

## Data Passing

Reference task outputs using the `{{task_id.output_key}}` syntax:

```yaml
tasks:
  - id: fetch_user
    type: function
    config:
      module: helpers
      function: get_user
      
  - id: fetch_orders
    type: function
    config:
      module: helpers
      function: get_orders
      args: ["{{fetch_user.user_id}}"]
      
  - id: format_summary
    type: transform
    config:
      operation: merge
      inputs:
        user: "{{fetch_user}}"
        orders: "{{fetch_orders}}"
```

## Complete Example

```yaml
workflow:
  name: customer-analysis
  version: "1.0"
  description: Analyze customer data and generate report
  
config:
  timeout: 300
  retry_policy:
    max_attempts: 3
    backoff: exponential

tasks:
  # Fetch customer data
  - id: get_customer
    type: function
    config:
      module: crm
      function: fetch_customer
      args: ["{{context.customer_id}}"]

  # Fetch order history
  - id: get_orders
    type: function
    config:
      module: crm
      function: fetch_orders
      args: ["{{get_customer.customer_id}}"]
    depends_on: [get_customer]

  # Analyze purchasing patterns
  - id: analyze_patterns
    type: prompt
    config:
      prompt: |
        Analyze this customer's order history:
        {{get_orders.data}}
        
        Identify:
        1. Purchase frequency
        2. Average order value
        3. Preferred product categories
      model: gpt-4o
      temperature: 0.5
      max_tokens: 800
    depends_on: [get_orders]

  # Generate summary
  - id: generate_report
    type: transform
    config:
      operation: format
      template: |
        Customer Report for {{get_customer.name}}
        
        Summary: {{analyze_patterns.summary}}
        Total Orders: {{get_orders.count}}
      output: report
    depends_on: [analyze_patterns, get_orders]
```

## Workflow Validation

Validate a workflow before running:

```bash
ai-runtime workflow validate my-workflow.yaml
```

This checks:
- YAML syntax
- Required fields
- Task type validity
- Dependency cycles
- Configuration schema

## Best Practices

1. **Use descriptive task IDs** - Makes logs easier to understand
2. **Set timeouts** - Prevents runaway workflows
3. **Implement error handling** - Use retry policies for unreliable tasks
4. **Keep prompts concise** - Longer prompts cost more and can reduce quality
5. **Use appropriate models** - Use gpt-4o-mini for simple tasks to save cost
6. **Test incrementally** - Build complex workflows step by step

## Template Variables

Available template variables:

| Variable | Description |
|----------|-------------|
| `{{context.*}}` | Workflow context data |
| `{{env.*}}` | Environment variables |
| `{{task_id.output}}` | Task result data |
| `{{workflow.name}}` | Current workflow name |
| `{{workflow.version}}` | Current workflow version |
