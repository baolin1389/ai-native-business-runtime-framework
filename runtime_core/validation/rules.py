"""Validation rules for runtime data validation."""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import re


class Rule(ABC):
    """Abstract base class for validation rules."""

    def __init__(self, error_message: Optional[str] = None):
        self.error_message = error_message

    @abstractmethod
    def validate(self, value: Any, field_name: str, context: Dict[str, Any]) -> bool:
        """Validate the value and return True if valid."""
        pass

    def __call__(self, value: Any, field_name: str, context: Dict[str, Any]) -> bool:
        """Allow the rule to be called as a function."""
        return self.validate(value, field_name, context)


@dataclass
class ValidationRule:
    """A validation rule with metadata."""
    name: str
    validator: Callable[[Any, str, Dict], bool]
    error_message: str
    severity: str = "error"
    tags: List[str] = field(default_factory=list)


class RequiredRule(Rule):
    """Rule that ensures a value is not None or empty."""

    def validate(self, value: Any, field_name: str, context: Dict[str, Any]) -> bool:
        if value is None:
            return False
        if isinstance(value, (str, list, dict, tuple, set)):
            return len(value) > 0
        return True


class MinLengthRule(Rule):
    """Rule that enforces minimum length."""

    def __init__(self, min_length: int, error_message: Optional[str] = None):
        super().__init__(error_message)
        self.min_length = min_length

    def validate(self, value: Any, field_name: str, context: Dict[str, Any]) -> bool:
        if value is None:
            return True
        return len(value) >= self.min_length


class MaxLengthRule(Rule):
    """Rule that enforces maximum length."""

    def __init__(self, max_length: int, error_message: Optional[str] = None):
        super().__init__(error_message)
        self.max_length = max_length

    def validate(self, value: Any, field_name: str, context: Dict[str, Any]) -> bool:
        if value is None:
            return True
        return len(value) <= self.max_length


class PatternRule(Rule):
    """Rule that validates against a regex pattern."""

    def __init__(self, pattern: str, error_message: Optional[str] = None):
        super().__init__(error_message)
        self.pattern = re.compile(pattern)

    def validate(self, value: Any, field_name: str, context: Dict[str, Any]) -> bool:
        if value is None:
            return True
        return bool(self.pattern.match(str(value)))


class RangeRule(Rule):
    """Rule that validates numeric range."""

    def __init__(
        self,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        super().__init__(error_message)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any, field_name: str, context: Dict[str, Any]) -> bool:
        if value is None:
            return True
        if not isinstance(value, (int, float)):
            return False
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        return True


class ChoiceRule(Rule):
    """Rule that validates against allowed choices."""

    def __init__(self, choices: List[Any], error_message: Optional[str] = None):
        super().__init__(error_message)
        self.choices = choices

    def validate(self, value: Any, field_name: str, context: Dict[str, Any]) -> bool:
        return value in self.choices


class EmailRule(Rule):
    """Rule that validates email format."""

    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    def validate(self, value: Any, field_name: str, context: Dict[str, Any]) -> bool:
        if value is None:
            return True
        return bool(self.EMAIL_PATTERN.match(str(value)))


class RuleSet:
    """A collection of validation rules."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._rules: Dict[str, List[Rule]] = {}

    def add_rule(self, field_name: str, rule: Rule) -> "RuleSet":
        """Add a rule for a specific field."""
        if field_name not in self._rules:
            self._rules[field_name] = []
        self._rules[field_name].append(rule)
        return self

    def get_rules(self, field_name: str) -> List[Rule]:
        """Get all rules for a field."""
        return self._rules.get(field_name, [])

    def validate(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> "ValidationResult":
        """Validate data against all rules in the set."""
        from .validator import ValidationResult

        result = ValidationResult(is_valid=True)
        context = context or {}

        for field_name, rules in self._rules.items():
            value = data.get(field_name)
            for rule in rules:
                try:
                    if not rule.validate(value, field_name, context):
                        error_msg = rule.error_message or f"Validation failed for {field_name}"
                        result.add_error(field_name, error_msg, code=rule.__class__.__name__)
                except Exception as e:
                    result.add_error(field_name, str(e), code="RULE_EXCEPTION")

        result.is_valid = len(result.errors) == 0
        return result

    def merge(self, other: "RuleSet") -> "RuleSet":
        """Merge another RuleSet into this one."""
        merged = RuleSet(f"{self.name}_merged")
        merged._rules = dict(self._rules)
        for field_name, rules in other._rules.items():
            if field_name in merged._rules:
                merged._rules[field_name].extend(rules)
            else:
                merged._rules[field_name] = rules
        return merged
