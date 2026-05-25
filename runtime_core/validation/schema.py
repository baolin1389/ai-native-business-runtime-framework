"""Schema definitions for validation."""

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FieldSchema:
    """Schema definition for a single field."""
    name: str
    field_type: Union[type, str]
    required: bool = True
    default: Any = None
    nullable: bool = False
    min_value: Optional[Number] = None
    max_value: Optional[Number] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    choices: Optional[List[Any]] = None
    custom_validator: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self, value: Any, context: Dict[str, Any]) -> "ValidationResult":
        """Validate a value against this field schema."""
        from .validator import ValidationResult, ValidationLevel

        result = ValidationResult(is_valid=True)

        # Handle None and missing values
        if value is None:
            if self.required and not self.nullable:
                result.add_error(self.name, "Field is required", "REQUIRED_FIELD")
            return result

        # Type checking
        if self.field_type != "any" and not isinstance(value, self._get_python_type()):
            result.add_error(
                self.name,
                f"Expected type {self.field_type}, got {type(value).__name__}",
                "TYPE_MISMATCH"
            )
            return result

        # Length validations
        if self.min_length is not None and hasattr(value, "__len__"):
            if len(value) < self.min_length:
                result.add_error(
                    self.name,
                    f"Value length must be at least {self.min_length}",
                    "MIN_LENGTH"
                )

        if self.max_length is not None and hasattr(value, "__len__"):
            if len(value) > self.max_length:
                result.add_error(
                    self.name,
                    f"Value length must be at most {self.max_length}",
                    "MAX_LENGTH"
                )

        # Range validations
        if self.min_value is not None and isinstance(value, (int, float)):
            if value < self.min_value:
                result.add_error(
                    self.name,
                    f"Value must be at least {self.min_value}",
                    "MIN_VALUE"
                )

        if self.max_value is not None and isinstance(value, (int, float)):
            if value > self.max_value:
                result.add_error(
                    self.name,
                    f"Value must be at most {self.max_value}",
                    "MAX_VALUE"
                )

        # Choice validation
        if self.choices is not None and value not in self.choices:
            result.add_error(
                self.name,
                f"Value must be one of {self.choices}",
                "INVALID_CHOICE"
            )

        # Pattern validation
        if self.pattern is not None and isinstance(value, str):
            import re
            if not re.match(self.pattern, value):
                result.add_error(
                    self.name,
                    f"Value does not match pattern {self.pattern}",
                    "PATTERN_MISMATCH"
                )

        # Custom validation
        if self.custom_validator:
            try:
                custom_result = self.custom_validator(value, context)
                if isinstance(custom_result, ValidationResult):
                    result = result.merge(custom_result)
                elif not custom_result:
                    result.add_error(self.name, "Custom validation failed", "CUSTOM_VALIDATION")
            except Exception as e:
                result.add_error(self.name, str(e), "CUSTOM_VALIDATION_ERROR")

        result.is_valid = len(result.errors) == 0
        return result

    def _get_python_type(self) -> type:
        """Map schema types to Python types."""
        type_map = {
            "string": str,
            "int": int,
            "integer": int,
            "float": float,
            "bool": bool,
            "boolean": bool,
            "list": list,
            "dict": dict,
            "datetime": datetime,
        }
        if isinstance(self.field_type, str):
            return type_map.get(self.field_type, self.field_type)
        return self.field_type


@dataclass
class Schema:
    """Schema definition for a structured object."""
    name: str
    fields: List[FieldSchema] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_field(self, field: FieldSchema) -> None:
        """Add a field to the schema."""
        self.fields.append(field)

    def get_field(self, name: str) -> Optional[FieldSchema]:
        """Get a field by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def validate(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> "ValidationResult":
        """Validate data against this schema."""
        from .validator import ValidationResult

        result = ValidationResult(is_valid=True)
        context = context or {}

        # Check for required fields
        for field_schema in self.fields:
            if field_schema.required and field_schema.name not in data:
                result.add_error(field_schema.name, "Required field is missing", "MISSING_FIELD")

        # Validate present fields
        for field_name, value in data.items():
            field_schema = self.get_field(field_name)
            if field_schema:
                field_result = field_schema.validate(value, context)
                result = result.merge(field_result)

        result.is_valid = len(result.errors) == 0
        return result
