"""Unit tests for update manager safety behavior."""

from pathlib import Path

import pytest

from autoshop_crm.services.updater import UpdateError, UpdateManager


def _build_manager(tmp_path: Path) -> UpdateManager:
    return UpdateManager(
        repo_path=tmp_path,
        instance_path=tmp_path / "instance",
        remote="origin",
        branch="main",
        allow_dirty=False,
    )


def test_apply_update_blocks_when_branch_diverged(tmp_path):
    """Apply should stop when local and remote histories diverge."""
    manager = _build_manager(tmp_path)
    manager.status = lambda fetch: {
        "error": None,
        "dirty": False,
        "ahead_by": 1,
        "behind_by": 1,
        "has_update": True,
        "branch": "main",
        "current_commit": "1111111111111111",
    }

    with pytest.raises(UpdateError, match="diverged"):
        manager.apply_update()


def test_apply_update_blocks_when_local_is_ahead(tmp_path):
    """Apply should stop when local branch has unpublished commits."""
    manager = _build_manager(tmp_path)
    manager.status = lambda fetch: {
        "error": None,
        "dirty": False,
        "ahead_by": 2,
        "behind_by": 0,
        "has_update": False,
        "branch": "main",
        "current_commit": "1111111111111111",
    }

    with pytest.raises(UpdateError, match="ahead of remote"):
        manager.apply_update()


def test_status_derives_repo_state_flags(tmp_path):
    """Repo state helper should emit clear blocking reasons."""
    manager = _build_manager(tmp_path)

    state, reason = manager._derive_repo_state(dirty=True, ahead_by=0, behind_by=3)
    assert state == "dirty"
    assert reason == "Working tree has local changes."

    state, reason = manager._derive_repo_state(dirty=False, ahead_by=1, behind_by=1)
    assert state == "diverged"
    assert reason == "Branch has diverged from remote."

    state, reason = manager._derive_repo_state(dirty=False, ahead_by=0, behind_by=2)
    assert state == "behind"
    assert reason is None
