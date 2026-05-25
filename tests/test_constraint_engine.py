"""Tests for ConstraintEngine."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime_core"))

from runtime_core.validation.constraints import (
    ConstraintEngine,
    ConstraintViolation,
    ValidationLevel,
)


class TestConstraintEngine:
    """Test ConstraintEngine constraint registration and validation."""

    def setup_method(self):
        self.engine = ConstraintEngine(strict=False)

    # ── Registration ────────────────────────────────────────────────

    def test_register_and_retrieve(self):
        """Register a named constraint, then retrieve it."""
        fn = lambda v, ctx: True
        self.engine.register("always_pass", fn)
        assert self.engine.get_constraint("always_pass") is fn

    def test_register_overwrites_duplicate(self):
        """Duplicate registration silently overwrites (no exception raised)."""
        fn1 = lambda ctx: 1
        fn2 = lambda ctx: 2
        self.engine.register("dup", fn1)
        self.engine.register("dup", fn2)  # no raise
        assert self.engine.get_constraint("dup") is fn2

    def test_unregister(self):
        """Unregister removes the constraint."""
        fn = lambda v, ctx: True
        self.engine.register("temp", fn)
        self.engine.unregister("temp")
        assert "temp" not in self.engine.list_constraints()

    def test_unregister_unknown_raises(self):
        """Unregister unknown name raises KeyError."""
        with pytest.raises(KeyError):
            self.engine.unregister("does_not_exist")

    def test_list_constraints(self):
        """list_constraints returns registered names."""
        self.engine.register("a", lambda v, ctx: True)
        self.engine.register("b", lambda v, ctx: True)
        constraints = self.engine.list_constraints()
        assert "a" in constraints
        assert "b" in constraints

    # ── Validation ─────────────────────────────────────────────────

    def test_validate_dict_passes(self):
        """validate_dict returns empty violations on valid data."""
        self.engine.register("non_empty", lambda v, ctx: bool(v))
        violations = self.engine.validate_dict(
            {"name": "Hans"}, {"name": ["non_empty"]}, required_fields=["name"]
        )
        assert violations == []

    def test_validate_dict_required_missing(self):
        """Missing required field produces a violation."""
        violations = self.engine.validate_dict({}, {}, required_fields=["email"])
        assert len(violations) == 1
        assert violations[0].code == "required"
        assert violations[0].field == "email"

    def test_validate_dict_constraint_fails(self):
        """Constraint returning False produces a violation."""
        self.engine.register("is_email", lambda v, ctx: "@" in v)
        violations = self.engine.validate_dict(
            {"email": "not-an-email"},
            {"email": ["is_email"]},
            required_fields=["email"]
        )
        assert len(violations) == 1
        assert violations[0].code == "is_email"

    def test_validate_dict_constraint_raises(self):
        """Constraint raising exception produces a violation."""
        self.engine.register(
            "always_fail",
            lambda v, ctx: (_ for _ in ()).throw(ValueError("boom"))
        )
        violations = self.engine.validate_dict(
            {"field": "x"},
            {"field": ["always_fail"]}
        )
        assert len(violations) == 1
        assert violations[0].level == ValidationLevel.ERROR

    def test_validate_dict_multiple_constraints(self):
        """Multiple constraints on same field all checked."""
        self.engine.register("non_empty", lambda v, ctx: bool(v))
        self.engine.register("longEnough", lambda v, ctx: len(v) >= 3)
        violations = self.engine.validate_dict(
            {"name": "Ab"},
            {"name": ["non_empty", "longEnough"]},
        )
        assert len(violations) == 1  # longEnough fails

    def test_validate_dict_multiple_fields(self):
        """Constraints on multiple fields checked independently."""
        self.engine.register("required", lambda v, ctx: bool(v))
        violations = self.engine.validate_dict(
            {"email": "a@b.de", "name": ""},
            {"name": ["required"], "email": ["required"]},
        )
        assert len(violations) == 1
        assert violations[0].field == "name"

    # ── Batch ──────────────────────────────────────────────────────

    def test_batch_validate(self):
        """batch_validate returns one violation list per item."""
        self.engine.register("pos", lambda v, ctx: v > 0)
        items = [{"score": 10}, {"score": -1}, {"score": 5}]
        results = self.engine.batch_validate(items, {"score": ["pos"]})
        assert len(results) == 3
        assert results[0] == []
        assert len(results[1]) == 1
        assert results[2] == []

    # ── ValidationLevel ────────────────────────────────────────────

    def test_validation_level_error_default(self):
        """validate_field uses ERROR level by default."""
        self.engine.register("always_false", lambda v, ctx: False)
        violations = self.engine.validate_field("x", "val", "always_false")
        assert violations[0].level == ValidationLevel.ERROR

    def test_validation_level_warning(self):
        """validate_field accepts explicit level."""
        self.engine.register("warn_len", lambda v, ctx: len(v) > 3)
        violations = self.engine.validate_field(
            "name", "Ab", "warn_len", level=ValidationLevel.WARNING
        )
        assert violations[0].level == ValidationLevel.WARNING

    def test_validation_level_info(self):
        """INFO level violation is recorded correctly."""
        self.engine.register("info_check", lambda v, ctx: isinstance(v, str))
        violations = self.engine.validate_field(
            "data", 42, "info_check", level=ValidationLevel.INFO
        )
        assert violations[0].level == ValidationLevel.INFO
