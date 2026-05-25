"""Action registry for managing and executing actions."""

from typing import Any, Callable, Dict, List, Optional


class ActionRegistry:
    """Registry for managing and executing actions."""

    def __init__(self):
        self._actions: Dict[str, Callable] = {}
        self._handlers: Dict[str, Callable] = {}
        self._deps: Dict[str, Any] = {}

    def register(self, name: str, action: Callable) -> None:
        """Register an action by name."""
        self._actions[name] = action

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a handler for action types."""
        self._handlers[name] = handler

    def get_action(self, name: str) -> Callable:
        """Retrieve a registered action."""
        if name not in self._actions:
            raise KeyError(f"Action '{name}' not found")
        return self._actions[name]

    def execute(self, name: str, context: Dict[str, Any]) -> Any:
        """Execute a registered action."""
        if name not in self._actions:
            raise KeyError(f"Action '{name}' not found")

        action = self._actions[name]
        full_context = {**self._deps, **context}

        if callable(action):
            return action(full_context)
        return None

    def list_actions(self) -> List[str]:
        """List all registered action names."""
        return list(self._actions.keys())

    def unregister(self, name: str) -> None:
        """Unregister an action."""
        if name not in self._actions:
            raise KeyError(f"Action '{name}' not found")
        del self._actions[name]

    def set_deps(self, deps: Dict[str, Any]) -> None:
        """Set dependency injection dictionary."""
        self._deps = deps
