"""Git-backed application update and rollback operations."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .time import utc_now_aware


class UpdateError(RuntimeError):
    """Raised when update operations cannot be completed safely."""


@dataclass(frozen=True)
class CommandResult:
    """Normalized subprocess result payload."""

    stdout: str
    stderr: str
    returncode: int


class UpdateManager:
    """Encapsulate update checks, apply, and rollback logic for a git checkout."""

    def __init__(
        self,
        *,
        repo_path: Path,
        instance_path: Path,
        remote: str = "origin",
        branch: str | None = None,
        rollback_limit: int = 6,
        allow_dirty: bool = False,
        command_timeout: int = 300,
        post_update_commands: tuple[str, ...] = (),
        post_rollback_commands: tuple[str, ...] = (),
        allowed_command_prefixes: tuple[str, ...] = (),
    ) -> None:
        self.repo_path = repo_path.resolve()
        self.instance_path = instance_path.resolve()
        self.remote = remote.strip() or "origin"
        self.configured_branch = branch.strip() if branch else None
        self.rollback_limit = max(2, rollback_limit)
        self.allow_dirty = allow_dirty
        self.command_timeout = max(30, command_timeout)
        self.post_update_commands = tuple(post_update_commands)
        self.post_rollback_commands = tuple(post_rollback_commands)
        self.allowed_command_prefixes = tuple(prefix.strip() for prefix in allowed_command_prefixes if prefix.strip())
        self.history_path = self.instance_path / "update_history.json"
        self.lock_path = self.instance_path / "update.lock"

    def status(self, *, fetch: bool = False) -> dict[str, Any]:
        """Return update status details for rendering in UI."""
        base = {
            "enabled": True,
            "repo_path": str(self.repo_path),
            "remote": self.remote,
            "branch": None,
            "is_git_repo": False,
            "current_commit": None,
            "current_short_commit": None,
            "latest_commit": None,
            "latest_short_commit": None,
            "dirty": False,
            "ahead_by": 0,
            "behind_by": 0,
            "has_update": False,
            "rollback_points": self._load_history(),
            "error": None,
        }

        try:
            if not self._git_dir().exists():
                raise UpdateError("Configured repository path is not a git checkout.")

            base["is_git_repo"] = True
            branch = self._current_branch()
            base["branch"] = branch

            if fetch:
                self._run_git("fetch", "--prune", self.remote, branch)

            current_commit = self._run_git("rev-parse", "HEAD").stdout.strip()
            latest_commit = self._run_git("rev-parse", f"{self.remote}/{branch}").stdout.strip()
            counts = self._run_git("rev-list", "--left-right", "--count", f"HEAD...{self.remote}/{branch}")
            ahead_raw, behind_raw = counts.stdout.strip().split()
            ahead_by = int(ahead_raw)
            behind_by = int(behind_raw)
            dirty = bool(self._run_git("status", "--porcelain").stdout.strip())

            base.update(
                {
                    "current_commit": current_commit,
                    "current_short_commit": current_commit[:8],
                    "latest_commit": latest_commit,
                    "latest_short_commit": latest_commit[:8],
                    "dirty": dirty,
                    "ahead_by": ahead_by,
                    "behind_by": behind_by,
                    "has_update": behind_by > 0,
                }
            )
        except (UpdateError, subprocess.SubprocessError, FileNotFoundError, ValueError) as exc:
            base["error"] = str(exc)

        return base

    def apply_update(self) -> dict[str, Any]:
        """Apply latest fast-forward update from configured remote branch."""
        with self._operation_lock():
            status = self.status(fetch=True)
            if status["error"]:
                raise UpdateError(str(status["error"]))
            if status["dirty"] and not self.allow_dirty:
                raise UpdateError("Working tree has local changes. Commit or stash them before updating.")
            if not status["has_update"]:
                return {
                    "updated": False,
                    "message": "No updates available.",
                    "current_commit": status["current_commit"],
                }

            branch = str(status["branch"])
            previous_commit = str(status["current_commit"])

            try:
                self._run_git("merge", "--ff-only", f"{self.remote}/{branch}")
                current_commit = self._run_git("rev-parse", "HEAD").stdout.strip()
                if current_commit == previous_commit:
                    return {
                        "updated": False,
                        "message": "Already up to date.",
                        "current_commit": current_commit,
                    }

                self._push_rollback_point(previous_commit)
                self._run_post_commands(self.post_update_commands)
            except Exception as exc:
                self._run_git("reset", "--hard", previous_commit)
                raise UpdateError(f"Update failed and was rolled back: {exc}") from exc

            return {
                "updated": True,
                "from_commit": previous_commit,
                "to_commit": current_commit,
            }

    def rollback(self, *, steps: int = 1) -> dict[str, Any]:
        """Rollback to a prior recorded commit."""
        with self._operation_lock():
            if steps < 1 or steps > 2:
                raise UpdateError("Rollback steps must be 1 or 2.")

            status = self.status(fetch=False)
            if status["error"]:
                raise UpdateError(str(status["error"]))
            if status["dirty"] and not self.allow_dirty:
                raise UpdateError("Working tree has local changes. Commit or stash them before rollback.")

            history = self._load_history()
            if len(history) < steps:
                raise UpdateError("Not enough rollback history for requested rollback.")

            target = history[steps - 1]["commit"]
            current_commit = str(status["current_commit"])

            self._run_git("reset", "--hard", target)
            self._run_post_commands(self.post_rollback_commands)

            remaining = history[steps:]
            if current_commit != target:
                remaining.insert(0, self._history_entry(current_commit))
            self._save_history(remaining)

            return {
                "rolled_back": True,
                "from_commit": current_commit,
                "to_commit": target,
                "steps": steps,
            }

    def _git_dir(self) -> Path:
        return self.repo_path / ".git"

    def _current_branch(self) -> str:
        if self.configured_branch:
            return self.configured_branch
        result = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        branch = result.stdout.strip()
        if branch == "HEAD":
            raise UpdateError("Detached HEAD is not supported for in-app updates.")
        return branch

    def _run_git(self, *args: str) -> CommandResult:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=self.command_timeout,
            check=False,
        )
        if result.returncode != 0:
            error_output = result.stderr.strip() or result.stdout.strip() or "Unknown git error"
            raise UpdateError(error_output)
        return CommandResult(stdout=result.stdout, stderr=result.stderr, returncode=result.returncode)

    def _run_post_commands(self, commands: tuple[str, ...]) -> None:
        for command in commands:
            command_text = command.strip()
            if not command_text:
                continue
            command_parts = shlex.split(command_text)
            if not command_parts:
                continue
            if not self._is_allowed_command(command_parts):
                raise UpdateError("Post-update command is not in the allowed command prefix list.")
            result = subprocess.run(
                command_parts,
                cwd=self.repo_path,
                timeout=self.command_timeout,
                check=False,
                text=True,
                capture_output=True,
                env=os.environ.copy(),
            )
            if result.returncode != 0:
                output = result.stderr.strip() or result.stdout.strip() or "Command failed"
                raise UpdateError(f"Post-update command failed: {output}")

    def _is_allowed_command(self, command_parts: list[str]) -> bool:
        if not self.allowed_command_prefixes:
            return False
        for prefix in self.allowed_command_prefixes:
            prefix_parts = shlex.split(prefix)
            if not prefix_parts:
                continue
            if command_parts[: len(prefix_parts)] == prefix_parts:
                return True
        return False

    def _history_entry(self, commit: str) -> dict[str, str]:
        return {
            "commit": commit,
            "short_commit": commit[:8],
            "timestamp_utc": utc_now_aware().isoformat(),
        }

    def _load_history(self) -> list[dict[str, str]]:
        if not self.history_path.exists():
            return []

        try:
            with self.history_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return []

        if not isinstance(payload, list):
            return []

        history: list[dict[str, str]] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            commit = str(entry.get("commit", "")).strip()
            if len(commit) < 8:
                continue
            history.append(
                {
                    "commit": commit,
                    "short_commit": str(entry.get("short_commit", commit[:8]))[:8],
                    "timestamp_utc": str(entry.get("timestamp_utc", "")),
                }
            )
        return history[: self.rollback_limit]

    def _save_history(self, history: list[dict[str, str]]) -> None:
        self.instance_path.mkdir(parents=True, exist_ok=True)
        trimmed = history[: self.rollback_limit]
        with self.history_path.open("w", encoding="utf-8") as handle:
            json.dump(trimmed, handle, indent=2)

    def _push_rollback_point(self, commit: str) -> None:
        history = [entry for entry in self._load_history() if entry.get("commit") != commit]
        history.insert(0, self._history_entry(commit))
        self._save_history(history)

    @contextmanager
    def _operation_lock(self) -> Iterator[None]:
        self.instance_path.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise UpdateError("Another update operation is already in progress.") from exc

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(str(os.getpid()))
            yield
        finally:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
