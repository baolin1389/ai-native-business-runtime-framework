"""State manager for workflow state management."""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


@dataclass
class StateHistoryEntry:
    """Record of a state change."""
    from_state: Optional[str]
    to_state: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class StateManager:
    """Manages workflow state and transitions."""

    def __init__(self, initial_state: Optional[str] = None):
        self._current_state: Optional[str] = initial_state
        self._state_history: List[StateHistoryEntry] = []
        self._listeners: List[Callable] = []
        self._metadata: Dict[str, Any] = {}
        self._allowed_transitions: Dict[str, List[str]] = {}

        if initial_state:
            self._state_history.append(StateHistoryEntry(
                from_state=None,
                to_state=initial_state,
            ))

    def set_allowed_transitions(self, transitions: Dict[str, List[str]]) -> None:
        """Set allowed state transitions."""
        self._allowed_transitions = transitions

    def can_transition(self, target_state: str) -> bool:
        """Check if transition to target state is allowed."""
        if not self._allowed_transitions:
            return True
        if self._current_state is None:
            return True
        allowed = self._allowed_transitions.get(self._current_state, [])
        return target_state in allowed

    def set_state(self, new_state: str) -> None:
        """Set a new state."""
        if not self.can_transition(new_state):
            raise StateTransitionError(
                f"Invalid transition from '{self._current_state}' to '{new_state}'"
            )

        entry = StateHistoryEntry(
            from_state=self._current_state,
            to_state=new_state,
        )
        self._state_history.append(entry)
        old_state = self._current_state
        self._current_state = new_state

        for listener in self._listeners:
            listener(old_state, new_state)

    def get_state(self) -> Optional[str]:
        """Get current state."""
        return self._current_state

    def get_state_history(self) -> List[StateHistoryEntry]:
        """Get state change history."""
        return self._state_history.copy()

    def add_listener(self, listener: Callable) -> None:
        """Add a state change listener."""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable) -> None:
        """Remove a state change listener."""
        self._listeners.remove(listener)

    def state_context(self, target_state: str) -> "StateContext":
        """Context manager for temporary state changes."""
        return StateContext(self, target_state)

    def snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of current state."""
        return {
            "current_state": self._current_state,
            "metadata": self._metadata.copy(),
            "history": [
                {"from": h.from_state, "to": h.to_state, "timestamp": h.timestamp.isoformat()}
                for h in self._state_history
            ],
        }

    def restore(self, snapshot: Dict[str, Any]) -> None:
        """Restore state from a snapshot."""
        self._current_state = snapshot.get("current_state")
        self._metadata = snapshot.get("metadata", {}).copy()
        history_data = snapshot.get("history", [])
        self._state_history = [
            StateHistoryEntry(
                from_state=h.get("from"),
                to_state=h.get("to"),
                timestamp=datetime.fromisoformat(h.get("timestamp", datetime.utcnow().isoformat())),
            )
            for h in history_data
        ]

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self._metadata.get(key, default)

    def clear_metadata(self) -> None:
        """Clear all metadata."""
        self._metadata.clear()

    def reset(self) -> None:
        """Reset to initial state."""
        self._current_state = None
        self._state_history.clear()
        self._metadata.clear()
        self._listeners.clear()

    def is_in_state(self, state: str) -> bool:
        """Check if current state matches given state."""
        return self._current_state == state

    async def wait_for_state(
        self,
        target_state: str,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for state to become the target state."""
        if self._current_state == target_state:
            return

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def listener(old_state, new_state):
            if new_state == target_state:
                if not future.done():
                    future.set_result(True)

        self.add_listener(listener)
        try:
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.remove_listener(listener)
            raise


class StateContext:
    """Context manager for temporary state changes."""

    def __init__(self, manager: StateManager, target_state: str):
        self.manager = manager
        self.target_state = target_state
        self._previous_state: Optional[str] = None

    def __enter__(self):
        self._previous_state = self.manager._current_state
        self.manager.set_state(self.target_state)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._previous_state is not None:
            # Restore previous state directly, bypassing transition rules
            # (we're undoing a temporary state change, not making a business transition)
            self.manager._current_state = self._previous_state
        return False
