# Domain DSL Guide

## Overview

The Domain DSL (Domain-Specific Language) provides a declarative way to define domain models, entities, workflows, and business logic within the AI Business Runtime Framework. It allows you to model your business domain using a structured YAML format that the runtime engine can execute.

## Core Concepts

### Domain Model Structure

A domain is composed of:

- **Entities** - Core business objects with attributes and relationships
- **Workflows** - Multi-step business processes
- **Tasks** - Individual units of work within workflows
- **Rules** - Business rules and validation logic
- **Events** - Domain events for reactive behavior

### Basic Domain Definition

```yaml
domain:
  name: string (required)
  version: string (required)
  description: string (optional)
  config:
    strict_mode: boolean (default: true)
    log_level: string (info|debug|warning|error)

entities:
  - name: string (required)
    attributes: object (required)
    relationships: object (optional)
    validation_rules: list[object] (optional)

workflows:
  - name: string (required)
    version: string (required)
    tasks: list[object] (required)

rules:
  - name: string (required)
    condition: string (required)
    action: string (required)

events:
  - name: string (required)
    source: string (required)
    payload: object (optional)
```

## Entity Definition

Entities represent core business objects in your domain.

### Basic Entity

```yaml
entities:
  - name: Customer
    attributes:
      id: string
      name: string
      email: string
      created_at: datetime
      status: enum[active, inactive, suspended]
    relationships:
      orders: Order[]
      account: Account
```

### Entity with Validation Rules

```yaml
entities:
  - name: Customer
    attributes:
      id: string
      name: string
      email: string
      credit_limit: decimal
    validation_rules:
      - field: name
        rule: required
        message: "Customer name is required"
      - field: email
        rule: pattern
        pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
        message: "Invalid email format"
      - field: credit_limit
        rule: range
        min: 0
        max: 100000
```

### Entity Relationships

```yaml
entities:
  - name: Order
    attributes:
      id: string
      order_date: datetime
      total: decimal
      status: enum[pending, confirmed, shipped, delivered, cancelled]
    relationships:
      customer: Customer
      items: OrderItem[]
      shipping_address: Address
```

### Relationship Types

| Type | Description | Syntax |
|------|-------------|--------|
| `belongs_to` | Single reference to another entity | `customer: Customer` |
| `has_many` | Collection of related entities | `orders: Order[]` |
| `has_one` | Single related entity | `account: Account` |
| `through` | Many-to-many via intermediate | `products: Product[] (through OrderItem)` |

## Workflow DSL

Workflows define multi-step business processes.

### Basic Workflow

```yaml
workflows:
  - name: order-processing
    version: "1.0"
    description: Process customer orders
    
    input:
      schema:
        customer_id: string (required)
        items: array[object] (required)
        shipping_address_id: string (required)
    
    tasks:
      - id: validate-order
        type: validation
        config:
          rules:
            - "items must not be empty"
            - "customer_id is required"
      
      - id: fetch-customer
        type: function
        config:
          module: crm
          function: get_customer
          args: ["{{input.customer_id}}"]
        depends_on: [validate-order]
      
      - id: check-inventory
        type: function
        config:
          module: inventory
          function: check_stock
          args: ["{{fetch-customer.result.items}}"]
        depends_on: [fetch-customer]
      
      - id: calculate-totals
        type: transform
        config:
          operation: reduce
          input: "{{check-inventory.result}}"
          expression: "sum(item.price * item.quantity)"
        depends_on: [check-inventory]
      
      - id: create-order
        type: function
        config:
          module: crm
          function: create_order
          args:
            customer_id: "{{input.customer_id}}"
            items: "{{input.items}}"
            total: "{{calculate-totals.result}}"
        depends_on: [calculate-totals]
      
      - id: send-confirmation
        type: prompt
        config:
          prompt: |
            Send an order confirmation email to {{fetch-customer.result.email}}
            with order ID {{create-order.result.order_id}}.
          model: gpt-4o-mini
        depends_on: [create-order]
    
    output:
      schema:
        order_id: string
        status: string
        total: decimal
```

### Workflow Control Flow

#### Conditional Branching

```yaml
tasks:
  - id: check-credit
    type: condition
    config:
      expression: "{{customer.credit_limit}} >= {{order.total}}"
      then_tasks: [process-order]
      else_tasks: [request-approval, send-rejection]
```

#### Parallel Execution

```yaml
tasks:
  - id: fetch-data
    type: parallel
    config:
      tasks:
        - id: get-customer
          type: function
          config:
            module: crm
            function: get_customer
        - id: get-products
          type: function
          config:
            module: inventory
            function: get_products
        - id: get-pricing
          type: function
          config:
            module: pricing
            function: get_current_pricing
```

#### Loop/Iteration

```yaml
tasks:
  - id: process-items
    type: loop
    config:
      items: "{{input.items}}"
      max_parallel: 5
      task_template:
        id: process-item
        type: function
        config:
          module: order_processor
          function: process_single_item
          args:
            item: "{{item}}"
            order_id: "{{context.order_id}}"
```

## Task Types Reference

### Prompt Task

Executes an AI model prompt.

```yaml
tasks:
  - id: analyze-request
    type: prompt
    config:
      prompt: |
        {{input.text}}
        
        Extract: names, dates, amounts, and key actions.
      model: gpt-4o
      temperature: 0.3
      max_tokens: 500
      system_prompt: "You are a data extraction assistant."
      output_format: json
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | required | The prompt template |
| `model` | string | config default | AI model to use |
| `temperature` | float | 0.7 | Response randomness (0-1) |
| `max_tokens` | int | 1000 | Maximum response length |
| `system_prompt` | string | null | System-level instructions |
| `output_format` | string | text | Output format (text, json) |

### Function Task

Executes a Python function.

```yaml
tasks:
  - id: calculate-shipping
    type: function
    config:
      module: shipping
      function: calculate_rate
      args:
        - "{{input.weight}}"
        - "{{input.destination}}"
      kwargs:
        service_level: express
        insurance: true
```

### Transform Task

Transforms data using operations.

```yaml
tasks:
  - id: normalize-data
    type: transform
    config:
      operation: map
      input: "{{previous.result}}"
      expression: "upper(item.name)"
```

**Operations:**

| Operation | Description | Syntax |
|-----------|-------------|--------|
| `filter` | Filter items based on condition | `expression: "item.status == 'active'"` |
| `map` | Transform each item | `expression: "item.price * 1.1"` |
| `reduce` | Aggregate values | `expression: "sum(item.total)"` |
| `merge` | Combine multiple inputs | `inputs: {a: "{{task1}}", b: "{{task2}}"}` |
| `format` | Format as string | `template: "Order #{{id}}: {{total}}" ` |

### Condition Task

Implements conditional logic.

```yaml
tasks:
  - id: route-order
    type: condition
    config:
      expression: "{{order.total}} > 1000"
      then_tasks: [premium-processing]
      else_tasks: [standard-processing]
      then_expression: |
        result = {
          "priority": "high",
          "discount": 0.1
        }
```

### Validation Task

Validates data against rules.

```yaml
tasks:
  - id: validate-input
    type: validation
    config:
      rules:
        - field: email
          rule: required
        - field: email
          rule: pattern
          pattern: "^[^@]+@[^@]+\\.[^@]+$"
        - field: amount
          rule: range
          min: 0
          max: 1000000
      on_failure: halt
      error_context: true
```

### Event Task

Emits a domain event.

```yaml
tasks:
  - id: notify-order-created
    type: event
    config:
      event: order.created
      payload:
        order_id: "{{create-order.result.id}}"
        customer_id: "{{input.customer_id}}"
        timestamp: "{{now}}"
```

### HTTP Task

Makes external HTTP requests.

```yaml
tasks:
  - id: call-payment-gateway
    type: http
    config:
      url: "https://api.payment.example.com/charge"
      method: POST
      headers:
        Authorization: "Bearer {{env.PAYMENT_API_KEY}}"
        Content-Type: "application/json"
      body:
        amount: "{{order.total}}"
        currency: USD
        customer_id: "{{customer.id}}"
      timeout: 30
      retry_policy:
        max_attempts: 3
        backoff: exponential
```

## Business Rules

Rules define declarative business logic.

### Rule Definition

```yaml
rules:
  - name: discount-eligibility
    description: Customers with 10+ orders get 10% discount
    condition: "customer.order_count >= 10"
    action: apply_discount
    params:
      discount_rate: 0.10
      discount_type: percentage
  
  - name: high-value-threshold
    condition: "order.total >= 5000"
    action: flag_high_value
    priority: high
  
  - name: fraud-risk-check
    condition: |
      order.total > customer.average_order_value * 3
      and order.shipping_address != customer.billing_address
    action: require_review
    priority: critical
```

### Rule Actions

| Action | Description |
|--------|-------------|
| `apply_discount` | Apply discount to order total |
| `flag_high_value` | Mark order for special handling |
| `require_review` | Flag for manual review |
| `send_notification` | Send alert to team/customer |
| `block_transaction` | Prevent transaction from proceeding |
| `apply_tax` | Calculate and apply taxes |

## Domain Events

Events enable reactive and event-driven architectures.

### Event Definition

```yaml
events:
  - name: order.created
    description: Fired when a new order is created
    source: order-processing-workflow
    payload:
      order_id: string
      customer_id: string
      total: decimal
      items: array[object]
    handlers:
      - workflow: send-confirmation-email
        async: true
      - workflow: update-inventory
        async: false
      - function: log_order_created
        module: analytics
        function: track_event
  
  - name: customer.created
    payload:
      customer_id: string
      email: string
      source: string
    handlers:
      - workflow: welcome-sequence
  
  - name: payment.failed
    payload:
      order_id: string
      error_code: string
      amount: decimal
    handlers:
      - workflow: handle-payment-failure
```

### Event Subscription

```yaml
domain:
  name: order-management
  
subscriptions:
  - event: inventory.low
    handlers:
      - function: reorder_products
        module: inventory
      - notification:
          channel: email
          recipients: [purchasing@example.com]
  
  - event: customer.churn_risk
    handlers:
      - workflow: retention-campaign
        priority: high
```

## Data Types

### Scalar Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text data | `"Hello World"` |
| `integer` | Whole numbers | `42` |
| `decimal` | Decimal numbers | `19.99` |
| `boolean` | True/false | `true` |
| `datetime` | Date and time | `2024-01-15T10:30:00Z` |
| `date` | Date only | `2024-01-15` |
| `time` | Time only | `10:30:00` |
| `enum[values]` | Enumeration | `enum[pending, approved, rejected]` |
| `uuid` | Unique identifier | `550e8400-e29b-41d4-a716-446655440000` |

### Complex Types

```yaml
# Array
items: array[object]

# Object/Map
metadata: object
  key1: string
  key2: integer

# Optional
nickname: string | null

# Union
status: string | enum[active, inactive]

# Custom Type Reference
customer: Customer
products: Product[]
```

## Template Variables

Reference dynamic values using the `{{}}` syntax.

| Variable | Description |
|----------|-------------|
| `{{input.*}}` | Workflow input parameters |
| `{{context.*}}` | Execution context data |
| `{{env.*}}` | Environment variables |
| `{{workflow.name}}` | Current workflow name |
| `{{workflow.version}}` | Current workflow version |
| `{{task_id.result}}` | Output from a specific task |
| `{{task_id.result.field}}` | Specific field from task result |
| `{{entity.*}}` | Domain entity data |
| `{{event.*}}` | Event payload data |
| `{{now}}` | Current timestamp |
| `{{uuid}}` | Generate a new UUID |

### Variable Filters

```yaml
tasks:
  - id: format-date
    type: transform
    config:
      operation: format
      template: "Order date: {{input.date | date: '%Y-%m-%d'}}"
  
  - id: uppercase-name
    type: transform
    config:
      operation: map
      input: "{{input.names}}"
      expression: "{{item | upper}}"
  
  - id: truncate-text
    type: transform
    config:
      template: "{{input.description | truncate: 100}}"
```

**Available Filters:**

| Filter | Description |
|--------|-------------|
| `upper` | Convert to uppercase |
| `lower` | Convert to lowercase |
| `trim` | Remove leading/trailing whitespace |
| `truncate: n` | Truncate to n characters |
| `date: format` | Format datetime |
| `round: decimals` | Round number |
| `json` | Serialize to JSON |
| `default: value` | Use default if null |

## Error Handling

### Error Policies

```yaml
tasks:
  - id: risky-operation
    type: function
    config:
      module: external_api
      function: call_service
    error_policy:
      on_failure: retry | skip | halt | fallback
      max_retries: 3
      retry_delay: 2
      backoff: exponential | linear
      fallback_task: fallback-handler
```

### Error Handling in Workflows

```yaml
workflows:
  - name: resilient-order-process
    version: "1.0"
    
    error_handlers:
      - on_error: payment_failed
        tasks: [notify-customer, log-error, queue-retry]
      
      - on_error: inventory_unavailable
        tasks: [notify-customer, suggest-alternatives]
    
    tasks:
      - id: process-payment
        type: function
        config:
          module: payment
          function: charge
        error_handlers:
          - condition: "error.code == 'INSUFFICIENT_FUNDS'"
            action: request-alternate-payment
          - condition: "error.code == 'CARD_DECLINED'"
            action: notify-customer
```

## Complete Example

```yaml
domain:
  name: trade-crm
  version: "2.0"
  description: Trade CRM domain with customer and order management
  
  config:
    strict_mode: true
    log_level: info

# ─────────────────────────────────────────────────────────────
# Entities
# ─────────────────────────────────────────────────────────────
entities:
  - name: Customer
    attributes:
      id: uuid
      name: string
      email: string
      phone: string
      tier: enum[standard, premium, enterprise]
      credit_limit: decimal
      created_at: datetime
      status: enum[active, inactive]
    relationships:
      orders: Order[]
      addresses: Address[]
    validation_rules:
      - field: name
        rule: required
      - field: email
        rule: pattern
        pattern: "^[^@]+@[^@]+\\.[^@]+$"

  - name: Order
    attributes:
      id: uuid
      order_number: string
      customer_id: uuid
      status: enum[pending, confirmed, processing, shipped, delivered, cancelled]
      subtotal: decimal
      tax: decimal
      total: decimal
      created_at: datetime
      shipped_at: datetime
    relationships:
      customer: Customer
      items: OrderItem[]
      shipping_address: Address
    validation_rules:
      - field: total
        rule: range
        min: 0

  - name: OrderItem
    attributes:
      id: uuid
      order_id: uuid
      product_id: uuid
      quantity: integer
      unit_price: decimal
      total: decimal

  - name: Product
    attributes:
      id: uuid
      sku: string
      name: string
      description: string
      price: decimal
      stock_quantity: integer
      status: enum[active, discontinued]

  - name: Address
    attributes:
      id: uuid
      customer_id: uuid
      type: enum[billing, shipping]
      street: string
      city: string
      state: string
      postal_code: string
      country: string

# ─────────────────────────────────────────────────────────────
# Business Rules
# ─────────────────────────────────────────────────────────────
rules:
  - name: premium-customer-discount
    description: Premium customers get 10% off orders over $100
    condition: "customer.tier == 'premium' and order.subtotal >= 100"
    action: apply_discount
    params:
      discount_rate: 0.10
      discount_type: percentage

  - name: enterprise-credit-override
    description: Enterprise customers have unlimited credit
    condition: "customer.tier == 'enterprise'"
    action: override_credit_check
    priority: high

  - name: high-value-order-flag
    condition: "order.total >= 10000"
    action: flag_high_value
    priority: high

  - name: low-stock-alert
    condition: "product.stock_quantity < 10"
    action: send_low_stock_alert
    priority: medium

# ─────────────────────────────────────────────────────────────
# Domain Events
# ─────────────────────────────────────────────────────────────
events:
  - name: order.created
    description: Fired when a new order is placed
    payload:
      order_id: uuid
      customer_id: uuid
      total: decimal
    handlers:
      - workflow: send-order-confirmation
        async: true
      - function: update_customer_order_count
        module: crm
      - function: reserve_inventory
        module: inventory

  - name: order.shipped
    payload:
      order_id: uuid
      tracking_number: string
    handlers:
      - workflow: send-shipping-notification
      - function: track_shipping
        module: logistics

  - name: customer.created
    handlers:
      - workflow: welcome-email-sequence
      - function: initialize_customer_metrics
        module: analytics

# ─────────────────────────────────────────────────────────────
# Workflows
# ─────────────────────────────────────────────────────────────
workflows:
  - name: process-order
    version: "1.0"
    description: Main order processing workflow
    
    input:
      schema:
        customer_id: uuid (required)
        items: array[object] (required)
        shipping_address_id: uuid (required)
        payment_method_id: string (optional)
    
    tasks:
      - id: validate-customer
        type: validation
        config:
          rules:
            - "customer_id is required"
            - "items must not be empty"
          on_failure: halt

      - id: fetch-customer
        type: function
        config:
          module: crm
          function: get_customer
          args: ["{{input.customer_id}}"]
        depends_on: [validate-customer]

      - id: fetch-products
        type: function
        config:
          module: inventory
          function: get_products_by_id
          args: ["{{input.items | map: 'product_id'}}"]
        depends_on: [validate-customer]

      - id: calculate-line-items
        type: transform
        config:
          operation: map
          input: "{{input.items}}"
          expression: |
            product = {{fetch-products.result | filter: "id == item.product_id" | first}}
            {
              "product_id": item.product_id,
              "quantity": item.quantity,
              "unit_price": product.price,
              "total": product.price * item.quantity
            }
        depends_on: [fetch-products]

      - id: calculate-subtotal
        type: transform
        config:
          operation: reduce
          input: "{{calculate-line-items.result}}"
          expression: "sum(item.total)"
        depends_on: [calculate-line-items]

      - id: apply-discounts
        type: function
        config:
          module: pricing
          function: apply_business_rules
          args:
            customer: "{{fetch-customer.result}}"
            subtotal: "{{calculate-subtotal.result}}"
        depends_on: [calculate-subtotal, fetch-customer]

      - id: calculate-tax
        type: function
        config:
          module: pricing
          function: calculate_tax
          args:
            subtotal: "{{apply-discounts.result.subtotal}}"
            discount: "{{apply-discounts.result.discount}}"
            customer_id: "{{input.customer_id}}"
        depends_on: [apply-discounts]

      - id: create-order-record
        type: function
        config:
          module: crm
          function: create_order
          args:
            customer_id: "{{input.customer_id}}"
            items: "{{calculate-line-items.result}}"
            subtotal: "{{apply-discounts.result.subtotal}}"
            discount: "{{apply-discounts.result.discount}}"
            tax: "{{calculate-tax.result}}"
            total: "{{calculate-tax.result.total}}"
        depends_on: [calculate-tax]

      - id: reserve-inventory
        type: function
        config:
          module: inventory
          function: reserve_stock
          args:
            order_id: "{{create-order-record.result.id}}"
            items: "{{calculate-line-items.result}}"
        depends_on: [create-order-record]

      - id: process-payment
        type: function
        config:
          module: payment
          function: charge
          args:
            customer_id: "{{input.customer_id}}"
            amount: "{{calculate-tax.result.total}}"
            payment_method_id: "{{input.payment_method_id}}"
        depends_on: [create-order-record]

      - id: confirm-order
        type: function
        config:
          module: crm
          function: update_order_status
          args:
            order_id: "{{create-order-record.result.id}}"
            status: confirmed
        depends_on: [process-payment]

      - id: send-confirmation
        type: event
        config:
          event: order.created
          payload:
            order_id: "{{create-order-record.result.id}}"
            customer_id: "{{input.customer_id}}"
            total: "{{calculate-tax.result.total}}"
        depends_on: [confirm-order]

    output:
      schema:
        order_id: uuid
        order_number: string
        status: string
        subtotal: decimal
        discount: decimal
        tax: decimal
        total: decimal

  - name: cancel-order
    version: "1.0"
    
    input:
      schema:
        order_id: uuid (required)
        reason: string (optional)
    
    tasks:
      - id: fetch-order
        type: function
        config:
          module: crm
          function: get_order
        
      - id: validate-cancellation
        type: condition
        config:
          expression: "{{fetch-order.result.status}} in ['pending', 'confirmed']"
          then_tasks: [cancel-order-flow]
          else_tasks: [reject-cancellation]

      - id: cancel-order-flow
        type: parallel
        config:
          tasks:
            - id: update-order-status
              type: function
              config:
                module: crm
                function: update_order_status
            - id: release-inventory
              type: function
              config:
                module: inventory
                function: release_stock
            - id: refund-payment
              type: function
              config:
                module: payment
                function: refund

      - id: send-cancellation-notice
        type: event
        config:
          event: order.cancelled
        depends_on: [cancel-order-flow]
```

## Best Practices

### Domain Modeling

1. **Start with entities** - Identify core business objects first
2. **Use clear naming** - Entity and workflow names should be self-documenting
3. **Keep workflows focused** - Each workflow should handle one business process
4. **Validate early** - Add validation tasks at the start of workflows
5. **Handle errors explicitly** - Define error handlers for critical operations

### DSL Writing Tips

1. **Use comments** - Document complex expressions and business rules
2. **Group related tasks** - Use visual separation for complex workflows
3. **Avoid deep nesting** - Refactor deeply nested conditions into separate tasks
4. **Use meaningful IDs** - Task IDs should describe what the task does
5. **Version your workflows** - Always specify versions for backward compatibility

### Performance Considerations

1. **Parallelize independent tasks** - Use `parallel` type for tasks that can run concurrently
2. **Limit loop parallelism** - Set `max_parallel` appropriately for loop tasks
3. **Use appropriate models** - Use smaller models (gpt-4o-mini) for simple extractions
4. **Cache expensive operations** - Store results of expensive function calls for reuse

## Validation

Validate your domain DSL before execution:

```bash
ai-runtime domain validate my-domain.yaml
```

This checks:
- YAML syntax correctness
- Required fields presence
- Entity relationship validity
- Workflow task type validity
- No circular dependencies
- Expression syntax
- Data type consistency

## Related Documentation

- [Workflow Creation](workflow-creation.md) - Detailed workflow authoring
- [API Reference](api-reference.md) - Programmatic API
- [Configuration](configuration.md) - Runtime configuration
- [Plugins](plugins.md) - Extending the framework
