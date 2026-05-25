"""Constraint engine for validating data against defined constraints."""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ValidationLevel(Enum):
    """Severity levels for validation messages."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ConstraintViolation:
    """Represents a constraint violation."""
    field: str
    code: str
    message: str
    level: ValidationLevel = ValidationLevel.ERROR
    context: Dict[str, Any] = field(default_factory=dict)


class ConstraintEngine:
    """Engine for validating data against constraints."""

    def __init__(self, strict: bool = True):
        self._strict = strict
        self._constraints: Dict[str, Callable] = {}
        self._required_fields: List[str] = []

    def register(self, name: str, constraint: Callable) -> None:
        """Register a named constraint."""
        self._constraints[name] = constraint

    def get_constraint(self, name: str) -> Callable:
        """Retrieve a registered constraint."""
        if name not in self._constraints:
            raise KeyError(f"Constraint '{name}' not found")
        return self._constraints[name]

    def list_constraints(self) -> List[str]:
        """List all registered constraint names."""
        return list(self._constraints.keys())

    def unregister(self, name: str) -> None:
        """Unregister a constraint."""
        if name not in self._constraints:
            raise KeyError(f"Constraint '{name}' not found")
        del self._constraints[name]

    def validate_field(
        self,
        field_name: str,
        value: Any,
        constraint_name: str,
        level: ValidationLevel = ValidationLevel.ERROR,
    ) -> List[ConstraintViolation]:
        """Validate a single field against a constraint."""
        violations = []

        if constraint_name not in self._constraints:
            return violations

        constraint = self._constraints[constraint_name]
        try:
            result = constraint(value, {})
            if not result:
                violations.append(ConstraintViolation(
                    field=field_name,
                    code=constraint_name,
                    message=f"Constraint '{constraint_name}' violated for field '{field_name}'",
                    level=level,
                ))
        except Exception as e:
            violations.append(ConstraintViolation(
                field=field_name,
                code=constraint_name,
                message=str(e),
                level=level,
            ))

        return violations

    def validate_dict(
        self,
        data: Dict[str, Any],
        field_constraints: Dict[str, List[str]],
        required_fields: Optional[List[str]] = None,
    ) -> List[ConstraintViolation]:
        """Validate a dictionary against field constraints."""
        violations = []
        required_fields = required_fields or []

        # Check required fields
        for field_name in required_fields:
            if field_name not in data:
                violations.append(ConstraintViolation(
                    field=field_name,
                    code="required",
                    message=f"Required field '{field_name}' is missing",
                    level=ValidationLevel.ERROR,
                ))

        # Check field constraints
        for field_name, constraint_names in field_constraints.items():
            value = data.get(field_name)
            for constraint_name in constraint_names:
                field_violations = self.validate_field(
                    field_name, value, constraint_name
                )
                violations.extend(field_violations)

        return violations

    def batch_validate(
        self,
        items: List[Dict[str, Any]],
        field_constraints: Dict[str, List[str]],
    ) -> List[List[ConstraintViolation]]:
        """Validate a batch of items."""
        return [
            self.validate_dict(item, field_constraints)
            for item in items
        ]
