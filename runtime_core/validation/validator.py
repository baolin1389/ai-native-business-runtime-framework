"""Validation engine for runtime data and workflow validation."""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ValidationLevel(Enum):
    """Severity levels for validation messages."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationMessage:
    """A single validation message."""
    level: ValidationLevel
    field: str
    message: str
    code: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[ValidationMessage] = field(default_factory=list)
    warnings: List[ValidationMessage] = field(default_factory=list)
    info: List[ValidationMessage] = field(default_factory=list)

    def __post_init__(self):
        self.is_valid = all(m.level != ValidationLevel.ERROR for m in self.errors)

    def add_error(self, field: str, message: str, code: str = "ERROR", context: Optional[Dict] = None):
        """Add an error message."""
        self.errors.append(ValidationMessage(
            level=ValidationLevel.ERROR,
            field=field,
            message=message,
            code=code,
            context=context or {}
        ))

    def add_warning(self, field: str, message: str, code: str = "WARNING", context: Optional[Dict] = None):
        """Add a warning message."""
        self.warnings.append(ValidationMessage(
            level=ValidationLevel.WARNING,
            field=field,
            message=message,
            code=code,
            context=context or {}
        ))

    def add_info(self, field: str, message: str, code: str = "INFO", context: Optional[Dict] = None):
        """Add an info message."""
        self.info.append(ValidationMessage(
            level=ValidationLevel.INFO,
            field=field,
            message=message,
            code=code,
            context=context or {}
        ))

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another ValidationResult into this one."""
        combined = ValidationResult(is_valid=self.is_valid and other.is_valid)
        combined.errors = self.errors + other.errors
        combined.warnings = self.warnings + other.warnings
        combined.info = self.info + other.info
        return combined


class Validator:
    """Main validation engine."""

    def __init__(self, strict: bool = True):
        self.strict = strict
        self._custom_rules: Dict[str, Callable] = {}

    def register_rule(self, name: str, rule: Callable) -> None:
        """Register a custom validation rule."""
        self._custom_rules[name] = rule

    def validate(
        self,
        data: Dict[str, Any],
        schema: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate data against a schema."""
        result = ValidationResult(is_valid=True)

        if hasattr(schema, "validate"):
            return schema.validate(data, context or {})

        return result

    def validate_field(
        self,
        value: Any,
        field_name: str,
        rules: List[Callable],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate a single field with a list of rules."""
        result = ValidationResult(is_valid=True)
        context = context or {}

        for rule in rules:
            try:
                rule_result = rule(value, field_name, context)
                if isinstance(rule_result, ValidationResult):
                    if not rule_result.is_valid:
                        result.errors.extend(rule_result.errors)
                    result.warnings.extend(rule_result.warnings)
                elif not rule_result:
                    result.add_error(field_name, f"Validation failed for rule {rule.__name__}")
            except Exception as e:
                result.add_error(field_name, str(e), code="VALIDATION_EXCEPTION")

        result.is_valid = len(result.errors) == 0
        return result

    def validate_batch(
        self,
        items: List[Dict[str, Any]],
        schema: Any
    ) -> List[ValidationResult]:
        """Validate a batch of items."""
        return [self.validate(item, schema) for item in items]
