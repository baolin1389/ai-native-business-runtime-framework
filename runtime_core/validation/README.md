# Validation Module

Schema and rule validation for runtime configuration and data.

## Components

- **schema.py** - Schema definitions for structured objects
- **validator.py** - Validation result and execution logic
- **rules.py** - Built-in validation rules

## Usage

```python
from runtime_core.validation import Schema, FieldSchema

schema = Schema(name="UserConfig")
schema.add_field(FieldSchema(name="name", field_type="string", required=True))
result = schema.validate({"name": "test"})
```
