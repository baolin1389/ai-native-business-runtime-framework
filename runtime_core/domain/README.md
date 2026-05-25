# Domain Module

Domain-specific models, workflows, and business logic.

## Overview

This module contains domain models and workflow definitions specific to your business logic.

## Usage

```python
# Import domain models
from runtime_core.domain import Workflow, Task

workflow = Workflow(name="example")
workflow.add_task(Task(name="step1", action="process"))
```
