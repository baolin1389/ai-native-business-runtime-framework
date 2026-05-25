"""Tests for ActionRegistry."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime_core"))

from runtime_core.engine.actions import ActionRegistry


class TestActionRegistry:
    """Test ActionRegistry action registration and execution."""

    def setup_method(self):
        self.registry = ActionRegistry()

    # ── Registration ──────────────────────────────────────────────

    def test_register_and_retrieve(self):
        """Register a named action, then retrieve it."""
        def my_action(context):
            return "done"
        self.registry.register("my_act", my_action)
        assert self.registry.get_action("my_act") is my_action

    def test_list_actions(self):
        """list_actions returns all registered names."""
        def a(context): return None
        def b(context): return None
        self.registry.register("act_a", a)
        self.registry.register("act_b", b)
        actions = self.registry.list_actions()
        assert "act_a" in actions
        assert "act_b" in actions

    def test_unregister(self):
        """unregister removes the action."""
        def a(context): return None
        self.registry.register("temp", a)
        self.registry.unregister("temp")
        assert "temp" not in self.registry.list_actions()

    def test_unregister_unknown_raises(self):
        """Unregister unknown action raises KeyError."""
        with pytest.raises(KeyError):
            self.registry.unregister("does_not_exist")

    # ── Execution ────────────────────────────────────────────────

    def test_execute_runs_action(self):
        """execute calls the registered action with context dict."""
        def add_one(context):
            return context["value"] + 1

        self.registry.register("add_one", add_one)
        result = self.registry.execute("add_one", {"value": 5})
        assert result == 6

    def test_execute_unknown_raises(self):
        """Execute unknown action raises KeyError."""
        with pytest.raises(KeyError):
            self.registry.execute("does_not_exist", {})

    def test_execute_passes_context(self):
        """Action receives merged context (deps + provided)."""
        received = {}
        def capture(context):
            received.update(context)
            return "ok"
        self.registry.register("cap", capture)
        self.registry.execute("cap", {"key": "value"})
        assert received["key"] == "value"

    def test_execute_returns_action_result(self):
        """Action return value is returned from execute."""
        def ret(context):
            return {"status": "success", "data": [1, 2]}
        self.registry.register("ret", ret)
        result = self.registry.execute("ret", {})
        assert result["status"] == "success"

    def test_execute_action_exception_propagates(self):
        """Action exception propagates up from execute."""
        def failing(context):
            raise ValueError("action failed")
        self.registry.register("fail", failing)
        with pytest.raises(ValueError, match="action failed"):
            self.registry.execute("fail", {})

    # ── Deps ────────────────────────────────────────────────────

    def test_set_deps_merged_into_context(self):
        """set_deps values are merged into context on execute."""
        def get_val(context):
            return context.get("secret")
        self.registry.register("get_val", get_val)
        self.registry.set_deps({"secret": "xyz"})
        result = self.registry.execute("get_val", {})
        assert result == "xyz"

    def test_execute_context_overrides_deps(self):
        """Provided context values override deps."""
        def get_val(context):
            return context.get("key")
        self.registry.register("get", get_val)
        self.registry.set_deps({"key": "from_deps"})
        result = self.registry.execute("get", {"key": "from_ctx"})
        assert result == "from_ctx"
