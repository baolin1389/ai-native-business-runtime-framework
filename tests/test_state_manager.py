"""Tests for StateManager."""

import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime_core"))

from runtime_core.state.manager import (
    StateManager,
    StateTransitionError,
    StateHistoryEntry,
)


class TestStateManager:
    """Test StateManager state transitions and history."""

    def setup_method(self):
        self.mgr = StateManager(initial_state="new")

    # ── Basic state ───────────────────────────────────────────────

    def test_initial_state(self):
        """Manager starts with initial_state."""
        assert self.mgr.get_state() == "new"

    def test_set_state_changes_current(self):
        """set_state updates current state."""
        self.mgr.set_state("contacted")
        assert self.mgr.get_state() == "contacted"

    def test_is_in_state_true(self):
        """is_in_state returns True when matching."""
        assert self.mgr.is_in_state("new") is True

    def test_is_in_state_false(self):
        """is_in_state returns False when not matching."""
        assert self.mgr.is_in_state("qualified") is False

    # ── Allowed transitions ───────────────────────────────────────

    def test_can_transition_allowed(self):
        """can_transition returns True for allowed transition."""
        self.mgr.set_allowed_transitions({"new": ["contacted", "qualified"]})
        assert self.mgr.can_transition("contacted") is True

    def test_can_transition_not_allowed(self):
        """can_transition returns False for disallowed transition."""
        self.mgr.set_allowed_transitions({"new": ["contacted"]})
        assert self.mgr.can_transition("qualified") is False

    def test_can_transition_no_rules_allows_all(self):
        """With no rules set, can_transition allows all."""
        assert self.mgr.can_transition("anything") is True

    def test_set_state_invalid_raises(self):
        """set_state raises StateTransitionError for invalid transition."""
        self.mgr.set_allowed_transitions({"new": ["contacted"]})
        with pytest.raises(StateTransitionError):
            self.mgr.set_state("qualified")

    def test_set_state_valid_succeeds(self):
        """set_state succeeds for valid transition."""
        self.mgr.set_allowed_transitions({"new": ["contacted", "qualified"]})
        self.mgr.set_state("qualified")  # no raise

    # ── History ──────────────────────────────────────────────────

    def test_state_history_records_transitions(self):
        """History tracks each state change."""
        self.mgr.set_state("contacted")
        self.mgr.set_state("qualified")
        history = self.mgr.get_state_history()
        assert len(history) == 3  # initial + 2 transitions
        assert history[0].to_state == "new"
        assert history[1].from_state == "new"
        assert history[1].to_state == "contacted"
        assert history[2].from_state == "contacted"
        assert history[2].to_state == "qualified"

    def test_history_timestamps_set(self):
        """History entries have timestamps."""
        self.mgr.set_state("contacted")
        entry = self.mgr.get_state_history()[1]
        assert entry.timestamp is not None

    # ── Listeners ────────────────────────────────────────────────

    def test_add_listener_called_on_transition(self):
        """Listener is called with (old, new) on each transition."""
        calls = []
        self.mgr.add_listener(lambda old, new: calls.append((old, new)))
        self.mgr.set_state("contacted")
        self.mgr.set_state("qualified")
        assert calls == [("new", "contacted"), ("contacted", "qualified")]

    def test_remove_listener(self):
        """Removed listener no longer receives events."""
        def listener(old, new):
            pass
        self.mgr.add_listener(listener)
        self.mgr.remove_listener(listener)
        self.mgr.set_state("contacted")  # no raise, listener not called

    # ── Snapshot / restore ───────────────────────────────────────

    def test_snapshot_contains_current_state(self):
        """snapshot returns dict with current_state key."""
        snap = self.mgr.snapshot()
        assert snap["current_state"] == "new"
        assert "history" in snap

    def test_restore_restores_state(self):
        """restore sets manager back to snapshot state."""
        self.mgr.set_state("contacted")
        snap = self.mgr.snapshot()
        self.mgr.set_state("qualified")
        self.mgr.restore(snap)
        assert self.mgr.get_state() == "contacted"

    def test_restore_restores_history(self):
        """restore also restores history."""
        self.mgr.set_state("contacted")
        snap = self.mgr.snapshot()
        self.mgr.set_state("qualified")
        self.mgr.restore(snap)
        # history now has only 2 entries (initial + one transition)
        assert len(self.mgr.get_state_history()) == 2

    # ── Metadata ─────────────────────────────────────────────────

    def test_set_and_get_metadata(self):
        """Metadata can be set and retrieved."""
        self.mgr.set_metadata("owner", "Eric")
        assert self.mgr.get_metadata("owner") == "Eric"

    def test_get_metadata_default(self):
        """get_metadata returns default for unknown key."""
        assert self.mgr.get_metadata("missing", "default_val") == "default_val"

    def test_metadata_in_snapshot(self):
        """snapshot includes metadata."""
        self.mgr.set_metadata("score", 85)
        snap = self.mgr.snapshot()
        assert snap["metadata"]["score"] == 85

    def test_restore_restores_metadata(self):
        """restore includes metadata."""
        self.mgr.set_metadata("key", "value")
        snap = self.mgr.snapshot()
        self.mgr.set_metadata("key", "overwritten")
        self.mgr.restore(snap)
        assert self.mgr.get_metadata("key") == "value"

    def test_clear_metadata(self):
        """clear_metadata removes all keys."""
        self.mgr.set_metadata("a", 1)
        self.mgr.set_metadata("b", 2)
        self.mgr.clear_metadata()
        assert self.mgr.get_metadata("a") is None

    # ── Reset ───────────────────────────────────────────────────

    def test_reset_clears_state(self):
        """reset clears current state, history, metadata."""
        self.mgr.set_state("contacted")
        self.mgr.set_metadata("k", "v")
        self.mgr.reset()
        assert self.mgr.get_state() is None
        assert self.mgr.get_state_history() == []
        assert self.mgr.get_metadata("k") is None

    # ── StateContext ─────────────────────────────────────────────

    def test_state_context_temporary_transition(self):
        """state_context temporarily changes state, reverts on exit."""
        self.mgr.set_allowed_transitions({"new": ["contacted"], "contacted": ["qualified"]})
        with self.mgr.state_context("contacted"):
            assert self.mgr.get_state() == "contacted"
        # After context exit, reverts to original
        assert self.mgr.get_state() == "new"

    def test_state_context_reverts_on_exception(self):
        """state_context reverts even if exception raised inside."""
        self.mgr.set_allowed_transitions({"new": ["contacted"], "contacted": ["qualified"]})
        try:
            with self.mgr.state_context("contacted"):
                assert self.mgr.get_state() == "contacted"
                raise ValueError("boom")
        except ValueError:
            pass
        assert self.mgr.get_state() == "new"


class TestStateManagerAsync:
    """Async tests for StateManager."""

    def setup_method(self):
        self.mgr = StateManager(initial_state="new")

    @pytest.mark.asyncio
    async def test_wait_for_state_already_there(self):
        """wait_for_state returns immediately if already in target state."""
        await self.mgr.wait_for_state("new")  # no raise, returns instantly

    @pytest.mark.asyncio
    async def test_wait_for_state_resolves(self):
        """wait_for_state resolves when target state is set."""
        async def change_later():
            await asyncio.sleep(0.05)
            self.mgr.set_state("qualified")

        async def wait_task():
            await self.mgr.wait_for_state("qualified", timeout=2.0)

        await asyncio.gather(change_later(), wait_task())
        assert self.mgr.get_state() == "qualified"

    @pytest.mark.asyncio
    async def test_wait_for_state_timeout(self):
        """wait_for_state raises TimeoutError if state never reached."""
        with pytest.raises(asyncio.TimeoutError):
            await self.mgr.wait_for_state("qualified", timeout=0.1)
