#!/usr/bin/env python3
"""Unified setup/deploy/backup/uninstall manager for Autoshop CRM."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import secrets
import shlex
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = PROJECT_ROOT / ".autoshop"
STATE_FILE = STATE_DIR / "install_state.json"
DEFAULT_SERVICE_PATH = Path("/etc/systemd/system/autoshop.service")
DEFAULT_SQLITE_URL = "sqlite:///autoshop.db"


@dataclass
class InstallState:
    version: int = 1
    created_paths: list[str] = field(default_factory=list)
    env_created: bool = False
    env_backup: str | None = None
    components: dict[str, Any] = field(default_factory=dict)
    updated_at: str | None = None

    @classmethod
    def load(cls) -> "InstallState":
        if not STATE_FILE.exists():
            return cls()
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return cls(
            version=data.get("version", 1),
            created_paths=data.get("created_paths", []),
            env_created=data.get("env_created", False),
            env_backup=data.get("env_backup"),
            components=data.get("components", {}),
            updated_at=data.get("updated_at"),
        )

    def mark_path(self, path: Path) -> None:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        if rel_path not in self.created_paths:
            self.created_paths.append(rel_path)

    def save(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        STATE_FILE.write_text(
            json.dumps(
                {
                    "version": self.version,
                    "created_paths": sorted(self.created_paths),
                    "env_created": self.env_created,
                    "env_backup": self.env_backup,
                    "components": self.components,
                    "updated_at": self.updated_at,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def info(message: str) -> None:
    print(f"[autoshopctl] {message}")


def abort(message: str, code: int = 1) -> None:
    info(f"ERROR: {message}")
    raise SystemExit(code)


def run(cmd: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    info("$ " + " ".join(shlex.quote(part) for part in cmd))
    return subprocess.run(cmd, check=check, text=True, env=env)


def is_linux() -> bool:
    return platform.system().lower() == "linux"


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def read_os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path("/etc/os-release")
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def detect_package_manager() -> str | None:
    if not is_linux():
        return None

    os_release = read_os_release()
    os_id = os_release.get("ID", "").lower()
    os_like = os_release.get("ID_LIKE", "").lower()

    # Prefer distro family from /etc/os-release before command presence.
    if ("arch" in os_like or os_id in {"arch", "endeavouros", "manjaro"}) and shutil.which("pacman"):
        return "pacman"
    if (
        "debian" in os_like
        or os_id in {"debian", "ubuntu", "linuxmint", "pop", "neon"}
    ) and shutil.which("apt-get"):
        return "apt"
    if ("rhel" in os_like or "fedora" in os_like or os_id in {"fedora", "rhel", "centos", "rocky", "almalinux"}) and shutil.which("dnf"):
        return "dnf"

    # Fallback by available package manager.
    if shutil.which("pacman"):
        return "pacman"
    if shutil.which("apt-get"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    return None


def system_package_list(manager: str) -> list[str]:
    if manager == "apt":
        return [
            "python3-venv",
            "python3-pip",
            "python3-dev",
            "build-essential",
            "mariadb-server",
            "mariadb-client",
            "curl",
            "openssl",
        ]
    if manager == "pacman":
        return [
            "python",
            "python-pip",
            "base-devel",
            "mariadb",
            "curl",
            "openssl",
        ]
    if manager == "dnf":
        return [
            "python3",
            "python3-pip",
            "python3-devel",
            "@development-tools",
            "mariadb-server",
            "mariadb",
            "curl",
            "openssl",
        ]
    return []


def is_package_installed(manager: str, package: str) -> bool:
    if manager == "apt":
        return subprocess.run(
            ["dpkg", "-s", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
    if manager == "pacman":
        return subprocess.run(
            ["pacman", "-Q", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
    if manager == "dnf":
        return subprocess.run(
            ["rpm", "-q", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
    return False


def install_system_packages(state: InstallState) -> None:
    manager = detect_package_manager()
    if not manager:
        abort("No supported package manager found for --install-system-packages.")
    if os.geteuid() != 0:
        abort("Installing system packages requires root. Re-run with sudo.")

    requested = system_package_list(manager)
    missing = [pkg for pkg in requested if not is_package_installed(manager, pkg)]
    if not missing:
        info("System packages already present. Nothing to install.")
    else:
        info(f"Installing missing system packages via {manager}: {', '.join(missing)}")
        if manager == "apt":
            run(["apt-get", "update", "-y"])
            run(["apt-get", "install", "-y", *missing])
        elif manager == "pacman":
            run(["pacman", "-Sy", "--noconfirm", "--needed", *missing])
        elif manager == "dnf":
            run(["dnf", "install", "-y", *missing])

    state.components["system_packages"] = {
        "manager": manager,
        "requested": requested,
        "installed_by_setup": missing,
    }


def purge_system_packages(state: InstallState) -> None:
    metadata = state.components.get("system_packages")
    if not isinstance(metadata, dict):
        info("No tracked system packages to purge.")
        return

    manager = str(metadata.get("manager") or "")
    installed_by_setup = metadata.get("installed_by_setup", [])
    if not manager or not isinstance(installed_by_setup, list):
        info("System package tracking metadata is invalid; skipping purge.")
        return

    packages = [pkg for pkg in installed_by_setup if isinstance(pkg, str) and is_package_installed(manager, pkg)]
    if not packages:
        info("No tracked system packages remain installed.")
        return

    if not is_linux():
        info("Skipping system package purge: supported on Linux only.")
        return
    if os.geteuid() != 0:
        info("Skipping system package purge (requires root).")
        return

    info(f"Purging tracked system packages via {manager}: {', '.join(packages)}")
    if manager == "apt":
        run(["apt-get", "purge", "-y", *packages], check=False)
        run(["apt-get", "autoremove", "-y"], check=False)
    elif manager == "pacman":
        run(["pacman", "-Rns", "--noconfirm", *packages], check=False)
    elif manager == "dnf":
        run(["dnf", "remove", "-y", *packages], check=False)
    else:
        info(f"Unsupported package manager for purge: {manager}")
        return

    metadata["installed_by_setup"] = []
    state.components["system_packages"] = metadata


def ensure_project_root() -> None:
    expected = [PROJECT_ROOT / "run.py", PROJECT_ROOT / "src" / "autoshop_crm" / "__init__.py"]
    if not all(path.exists() for path in expected):
        abort(f"Run this command inside the Autoshop CRM repository: {PROJECT_ROOT}")


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def prompt_text(label: str, default: str | None = None, required: bool = False, secret: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default not in {None, ""} else ""
        prompt = f"{label}{suffix}: "
        raw = getpass.getpass(prompt) if secret else input(prompt)
        value = raw.strip()
        if value:
            return value
        if default is not None:
            return str(default)
        if not required:
            return ""
        print("Value is required.")


def prompt_bool(label: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{label} [{hint}]: ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter yes or no.")


def prompt_choice(label: str, options: list[str], default: str) -> str:
    joined = "/".join(options)
    while True:
        answer = input(f"{label} ({joined}) [{default}]: ").strip().lower()
        if not answer:
            return default
        if answer in options:
            return answer
        print(f"Please choose one of: {joined}")


def guess_db_kind(db_url: str | None) -> str:
    if not db_url:
        return "sqlite"
    scheme = urlparse(db_url).scheme.lower()
    if scheme.startswith("sqlite"):
        return "sqlite"
    if scheme.startswith("mysql"):
        return "mysql"
    if scheme.startswith("mariadb"):
        return "mariadb"
    return "custom"


def redact_db_url(db_url: str) -> str:
    parsed = urlparse(db_url)
    if not parsed.password:
        return db_url
    netloc = parsed.netloc.replace(parsed.password, "********", 1)
    return parsed._replace(netloc=netloc).geturl()


def build_interactive_db_url(existing_db_url: str | None) -> str:
    kind = prompt_choice(
        "Database backend",
        ["sqlite", "mysql", "mariadb", "custom"],
        default=guess_db_kind(existing_db_url),
    )

    if kind == "sqlite":
        default_path = "autoshop.db"
        if existing_db_url and existing_db_url.startswith("sqlite:///"):
            default_path = existing_db_url.replace("sqlite:///", "", 1) or default_path
        sqlite_path = prompt_text("SQLite database path", default=default_path, required=True)
        return f"sqlite:///{sqlite_path}"

    if kind == "custom":
        return prompt_text("Database URL", default=existing_db_url, required=True)

    parsed = urlparse(existing_db_url or "")
    db_host = prompt_text("DB host", default=parsed.hostname or "localhost", required=True)
    db_port = prompt_text("DB port", default=str(parsed.port or 3306), required=True)
    db_name = prompt_text("DB name", default=parsed.path.lstrip("/") or "autoshop", required=True)
    db_user = prompt_text("DB user", default=unquote(parsed.username or "autoshop_user"), required=True)
    db_pass = prompt_text(
        "DB password",
        default=unquote(parsed.password or ""),
        required=True,
        secret=True,
    )
    return f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


def run_setup_wizard(args: argparse.Namespace) -> None:
    env_values = parse_env_file(PROJECT_ROOT / ".env")
    existing_db_url = args.db_url or env_values.get("DATABASE_URL")

    print("Autoshop Setup Wizard")
    print("-" * 20)
    args.mode = prompt_choice("Mode", ["dev", "prod"], default=args.mode)
    args.venv = prompt_text("Virtualenv directory", default=args.venv, required=True)
    args.python = prompt_text("Python executable", default=args.python or sys.executable, required=True)
    args.db_url = build_interactive_db_url(existing_db_url)

    if is_linux():
        args.install_system_packages = prompt_bool(
            "Install OS packages and track them for uninstall purge",
            default=args.install_system_packages,
        )
        args.with_systemd = prompt_bool("Enable systemd service", default=args.with_systemd)
        if args.with_systemd:
            default_user = args.service_user or os.environ.get("SUDO_USER") or getpass.getuser()
            args.service_user = prompt_text("systemd service user", default=default_user, required=True)
    else:
        args.install_system_packages = False
        args.with_systemd = False

    args.with_tailscale = prompt_bool("Enable tailscale", default=args.with_tailscale)
    if args.with_tailscale:
        args.tailscale_auth_key = prompt_text(
            "Tailscale auth key (optional)",
            default=args.tailscale_auth_key,
            required=False,
            secret=True,
        )
        args.tailscale_tags = prompt_text(
            "Tailscale tags (optional, comma-separated)",
            default=args.tailscale_tags,
            required=False,
        )

    env_overrides: dict[str, str] = {}
    env_overrides["HOST"] = prompt_text("App host", default=env_values.get("HOST", "0.0.0.0"), required=True)
    env_overrides["PORT"] = prompt_text("App port", default=env_values.get("PORT", "5000"), required=True)
    env_overrides["LOG_FILE"] = prompt_text("Log file", default=env_values.get("LOG_FILE", "logs/app.log"), required=True)

    keep_secret = prompt_bool(
        "Keep existing SECRET_KEY",
        default=bool(env_values.get("SECRET_KEY")) and not is_placeholder_secret(env_values.get("SECRET_KEY")),
    )
    if keep_secret and env_values.get("SECRET_KEY"):
        env_overrides["SECRET_KEY"] = env_values["SECRET_KEY"]
    else:
        env_overrides["SECRET_KEY"] = secrets.token_hex(32)

    update_enabled_default = env_values.get("UPDATE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    update_enabled = prompt_bool("Enable in-app updater", default=update_enabled_default)
    env_overrides["UPDATE_ENABLED"] = "true" if update_enabled else "false"
    env_overrides["UPDATE_LOCAL_ONLY"] = "true" if prompt_bool(
        "Restrict updater actions to local requests",
        default=env_values.get("UPDATE_LOCAL_ONLY", "true").strip().lower() in {"1", "true", "yes", "on"},
    ) else "false"
    env_overrides["UPDATE_CONFIRM_PHRASE"] = prompt_text(
        "Updater confirmation phrase",
        default=env_values.get("UPDATE_CONFIRM_PHRASE", "CONFIRM"),
        required=True,
    )
    args.env_overrides = env_overrides

    print("\nSetup summary")
    print(f"- mode: {args.mode}")
    print(f"- venv: {args.venv}")
    print(f"- database: {redact_db_url(args.db_url)}")
    print(f"- install system packages: {args.install_system_packages}")
    print(f"- systemd: {args.with_systemd}")
    print(f"- tailscale: {args.with_tailscale}")
    if not prompt_bool("Proceed with setup", default=True):
        abort("Setup cancelled.")


def write_env_file(path: Path, values: dict[str, str]) -> None:
    ordered_keys = [
        "FLASK_ENV",
        "FLASK_APP",
        "PYTHONPATH",
        "SECRET_KEY",
        "DEVELOPMENT",
        "HOST",
        "PORT",
        "DATABASE_URL",
        "LOG_FILE",
        "SESSION_COOKIE_SECURE",
        "REMEMBER_COOKIE_SECURE",
        "SESSION_COOKIE_SAMESITE",
        "REMEMBER_COOKIE_SAMESITE",
        "PREFERRED_URL_SCHEME",
        "MAX_CONTENT_LENGTH",
        "UPDATE_ENABLED",
        "UPDATE_LOCAL_ONLY",
        "UPDATE_CONFIRM_PHRASE",
        "UPDATE_ALLOWED_COMMAND_PREFIXES",
        "UPDATE_POST_UPDATE_COMMANDS",
    ]
    lines = [
        "# Generated by scripts/autoshopctl.py",
        "# Edit values as needed for your environment.",
    ]

    seen: set[str] = set()
    for key in ordered_keys:
        if key in values:
            lines.append(f"{key}={values[key]}")
            seen.add(key)

    for key in sorted(values):
        if key in seen:
            continue
        lines.append(f"{key}={values[key]}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def is_placeholder_secret(secret: str | None) -> bool:
    if not secret:
        return True
    normalized = secret.strip().lower()
    return normalized in {"change-me-in-production", "changeme", "replace-me"}


def venv_bin_dir(venv_path: Path) -> Path:
    if is_windows():
        return venv_path / "Scripts"
    return venv_path / "bin"


def choose_python_for_venv(python_cmd: str | None) -> str:
    if python_cmd:
        return python_cmd
    return sys.executable


def activate_hint(venv_path: Path) -> str:
    if is_windows():
        return f"{venv_path}\\Scripts\\activate"
    return f"source {venv_path}/bin/activate"


def ensure_venv(args: argparse.Namespace, state: InstallState) -> Path:
    venv_path = (PROJECT_ROOT / args.venv).resolve()
    vpython = venv_bin_dir(venv_path) / ("python.exe" if is_windows() else "python")

    if not vpython.exists():
        info(f"Creating virtualenv at {venv_path}")
        run([choose_python_for_venv(args.python), "-m", "venv", str(venv_path)])
        if venv_path.is_relative_to(PROJECT_ROOT):
            state.mark_path(venv_path)

    pip_cmd = venv_bin_dir(venv_path) / ("pip.exe" if is_windows() else "pip")
    run([str(pip_cmd), "install", "--upgrade", "pip"])

    requirements = PROJECT_ROOT / "requirements.txt"
    if requirements.exists():
        run([str(pip_cmd), "install", "-r", str(requirements)])
    else:
        abort("requirements.txt is missing")

    state.components["venv"] = str(venv_path.relative_to(PROJECT_ROOT))
    return venv_path


def merge_env(
    mode: str,
    db_url: str | None,
    env_path: Path,
    state: InstallState,
    overrides: dict[str, str] | None = None,
) -> None:
    env_values = parse_env_file(env_path)

    if env_path.exists() and not state.env_backup:
        backup_dir = STATE_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_name = f"env.pre-setup.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.bak"
        backup_path = backup_dir / backup_name
        shutil.copy2(env_path, backup_path)
        state.env_backup = str(backup_path.relative_to(PROJECT_ROOT))

    if not env_path.exists():
        state.env_created = True
        state.mark_path(env_path)

    env_values["FLASK_ENV"] = "production" if mode == "prod" else "development"
    env_values["FLASK_APP"] = env_values.get("FLASK_APP", "run.py")
    env_values["PYTHONPATH"] = "src"
    env_values["DEVELOPMENT"] = "false" if mode == "prod" else "true"
    env_values["HOST"] = env_values.get("HOST", "0.0.0.0")
    env_values["PORT"] = env_values.get("PORT", "5000")
    env_values["LOG_FILE"] = env_values.get("LOG_FILE", "logs/app.log")
    env_values["DATABASE_URL"] = db_url or env_values.get("DATABASE_URL") or DEFAULT_SQLITE_URL

    if is_placeholder_secret(env_values.get("SECRET_KEY")):
        env_values["SECRET_KEY"] = secrets.token_hex(32)

    if mode == "prod":
        env_values.setdefault("SESSION_COOKIE_SECURE", "true")
        env_values.setdefault("REMEMBER_COOKIE_SECURE", "true")
        env_values.setdefault("PREFERRED_URL_SCHEME", "https")

    env_values.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    env_values.setdefault("REMEMBER_COOKIE_SAMESITE", "Lax")
    env_values.setdefault("MAX_CONTENT_LENGTH", "8388608")
    env_values.setdefault("UPDATE_ENABLED", "false")
    env_values.setdefault("UPDATE_LOCAL_ONLY", "true")
    env_values.setdefault("UPDATE_CONFIRM_PHRASE", "CONFIRM")
    env_values.setdefault("UPDATE_ALLOWED_COMMAND_PREFIXES", "./scripts/autoshopctl.py")

    if overrides:
        env_values.update({key: value for key, value in overrides.items() if value is not None})

    write_env_file(env_path, env_values)


def run_migrations(venv_path: Path, state: InstallState) -> None:
    flask_cmd = venv_bin_dir(venv_path) / ("flask.exe" if is_windows() else "flask")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    run([str(flask_cmd), "--app", "run.py", "db", "upgrade"], env=env)
    state.components["migrations"] = "applied"


def setup_systemd(venv_path: Path, service_user: str | None, state: InstallState) -> None:
    if not is_linux():
        abort("systemd setup is only supported on Linux")
    if shutil.which("systemctl") is None:
        abort("systemctl is not available on this host")
    if os.geteuid() != 0:
        abort("systemd setup requires root. Re-run with sudo.")

    resolved_user = service_user or os.environ.get("SUDO_USER") or "root"
    unit = f"""[Unit]
Description=AutoShop CRM
After=network.target

[Service]
Type=simple
User={resolved_user}
Group={resolved_user}
WorkingDirectory={PROJECT_ROOT}
EnvironmentFile={PROJECT_ROOT / '.env'}
Environment=PYTHONPATH={PROJECT_ROOT / 'src'}
ExecStart={venv_bin_dir(venv_path) / 'gunicorn'} --workers 3 --bind 127.0.0.1:8000 autoshop_crm:create_app()
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    DEFAULT_SERVICE_PATH.write_text(unit, encoding="utf-8")
    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", "--now", "autoshop.service"])
    state.components["systemd"] = {"unit": str(DEFAULT_SERVICE_PATH), "user": resolved_user}


def setup_tailscale(args: argparse.Namespace, state: InstallState) -> None:
    if shutil.which("tailscale") is None:
        abort("tailscale CLI not found. Install Tailscale first, then re-run with --with-tailscale.")

    cmd = ["tailscale", "up"]
    if args.tailscale_auth_key:
        cmd += ["--authkey", args.tailscale_auth_key]
    if args.tailscale_tags:
        cmd += ["--advertise-tags", args.tailscale_tags]

    run(cmd)
    state.components["tailscale"] = {
        "enabled": True,
        "tags": args.tailscale_tags or "",
    }


def command_setup(args: argparse.Namespace) -> int:
    ensure_project_root()
    state = InstallState.load()

    interactive = args.interactive if args.interactive is not None else sys.stdin.isatty()
    if interactive:
        if not sys.stdin.isatty():
            abort("Interactive setup requires a TTY. Use --no-interactive for automation.")
        run_setup_wizard(args)

    if STATE_FILE.exists() and not args.force:
        info("Setup state already exists. Re-running idempotent steps.")

    for relative in ["instance", "instance/uploads", "logs"]:
        path = PROJECT_ROOT / relative
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            state.mark_path(path)

    if args.install_system_packages:
        install_system_packages(state)

    venv_path = ensure_venv(args, state)
    merge_env(args.mode, args.db_url, PROJECT_ROOT / ".env", state, getattr(args, "env_overrides", None))
    run_migrations(venv_path, state)

    if args.with_systemd:
        setup_systemd(venv_path, args.service_user, state)

    if args.with_tailscale:
        setup_tailscale(args, state)

    state.components["mode"] = args.mode
    state.save()

    info("Setup complete.")
    info(
        f"Run: {activate_hint(venv_path)} && flask --app run.py run --host=0.0.0.0 --port=5000"
    )
    return 0


def command_status(_: argparse.Namespace) -> int:
    ensure_project_root()
    state = InstallState.load()
    env_exists = (PROJECT_ROOT / ".env").exists()
    venv_exists = (PROJECT_ROOT / "venv").exists() or (PROJECT_ROOT / ".venv").exists()
    migrations_ready = "migrations" in state.components
    systemd_enabled = bool(state.components.get("systemd"))
    tailscale_enabled = bool(state.components.get("tailscale"))

    print("Autoshop setup status")
    print(f"- state file: {'present' if STATE_FILE.exists() else 'missing'}")
    print(f"- virtualenv: {'present' if venv_exists else 'missing'}")
    print(f"- .env: {'present' if env_exists else 'missing'}")
    print(f"- migrations: {'applied' if migrations_ready else 'unknown'}")
    print(f"- systemd: {'configured' if systemd_enabled else 'not configured'}")
    print(f"- tailscale: {'configured' if tailscale_enabled else 'not configured'}")

    if not STATE_FILE.exists() or not venv_exists or not env_exists:
        print("- recommendation: run `python scripts/autoshopctl.py setup`")
    else:
        print("- recommendation: setup appears complete")
    return 0


def find_venv_bin() -> Path | None:
    for folder in [PROJECT_ROOT / "venv", PROJECT_ROOT / ".venv"]:
        candidate = venv_bin_dir(folder)
        python_bin = candidate / ("python.exe" if is_windows() else "python")
        if python_bin.exists():
            return candidate
    return None


def command_deploy(args: argparse.Namespace) -> int:
    ensure_project_root()
    if shutil.which("git") is None:
        abort("git is required for deploy")

    branch = args.branch
    if not branch:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
        ).strip()

    if not args.skip_pull:
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True).strip()
        if dirty:
            abort("Refusing deploy with a dirty working tree. Commit or stash changes first.")

        run(["git", "fetch", "--prune", args.remote, branch])
        run(["git", "merge", "--ff-only", f"{args.remote}/{branch}"])

    venv = find_venv_bin()
    if not venv:
        abort("No virtualenv found. Run setup first.")

    pip_cmd = venv / ("pip.exe" if is_windows() else "pip")
    flask_cmd = venv / ("flask.exe" if is_windows() else "flask")
    run([str(pip_cmd), "install", "-r", str(PROJECT_ROOT / "requirements.txt")])

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    run([str(flask_cmd), "--app", "autoshop_crm:create_app", "db", "upgrade"], env=env)

    if args.restart_service and is_linux() and shutil.which("systemctl"):
        if os.geteuid() == 0:
            run(["systemctl", "restart", "autoshop.service"])
        else:
            info("Skipping service restart (requires root). Run: sudo systemctl restart autoshop.service")

    info(f"Deploy complete for branch '{branch}'.")
    return 0


def command_backup(args: argparse.Namespace) -> int:
    ensure_project_root()
    if shutil.which("mysqldump") is None:
        abort("mysqldump is required for backup")

    db_name = args.db_name or os.getenv("DB_NAME")
    db_user = args.db_user or os.getenv("DB_USER", "root")
    db_password = args.db_password or os.getenv("DB_PASSWORD")

    if not db_name:
        abort("Provide --db-name or DB_NAME env var")
    if not db_password:
        abort("Provide --db-password or DB_PASSWORD env var")

    outdir = PROJECT_ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    output_file = outdir / f"{db_name}-{timestamp}.sql"

    cmd = [
        "mysqldump",
        "-h",
        args.db_host,
        "-P",
        str(args.db_port),
        "-u",
        db_user,
        f"-p{db_password}",
        db_name,
    ]

    info("$ " + " ".join(shlex.quote(p) if not p.startswith("-p") else "-p********" for p in cmd))
    with output_file.open("w", encoding="utf-8") as handle:
        subprocess.run(cmd, check=True, text=True, stdout=handle)

    info(f"Backup written: {output_file}")
    return 0


def remove_paths(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists():
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        info(f"Removed: {path.relative_to(PROJECT_ROOT)}")


def maybe_drop_database(db_url: str) -> None:
    parsed = urlparse(db_url)
    scheme = parsed.scheme.lower()

    if scheme.startswith("sqlite"):
        sqlite_target = db_url.replace("sqlite:///", "", 1)
        sqlite_target = sqlite_target.replace("sqlite://", "", 1)
        if not sqlite_target or sqlite_target == ":memory:":
            return
        target_path = Path(sqlite_target)
        if not target_path.is_absolute():
            target_path = PROJECT_ROOT / target_path
        if target_path.exists():
            target_path.unlink()
            info(f"Dropped sqlite database file: {target_path}")
        return

    if not (scheme.startswith("mysql") or scheme.startswith("mariadb")):
        info(f"Skipping database drop for unsupported scheme: {scheme}")
        return

    client = shutil.which("mariadb") or shutil.which("mysql")
    if not client:
        info("Skipping database drop: mysql/mariadb client not found.")
        return

    db_name = parsed.path.lstrip("/")
    if not db_name:
        info("Skipping database drop: database name missing in DATABASE_URL.")
        return

    user = unquote(parsed.username or "root")
    password = unquote(parsed.password or "")
    host = parsed.hostname or "localhost"
    port = str(parsed.port or 3306)
    safe_db = db_name.replace("`", "``")

    cmd = [
        client,
        "-h",
        host,
        "-P",
        port,
        "-u",
        user,
    ]
    if password:
        cmd.append(f"-p{password}")
    cmd.extend(["-e", f"DROP DATABASE IF EXISTS `{safe_db}`;"])

    log_cmd = [part if not part.startswith("-p") else "-p********" for part in cmd]
    info("$ " + " ".join(shlex.quote(part) for part in log_cmd))
    subprocess.run(cmd, check=True, text=True)
    info(f"Dropped database: {db_name}")


def command_uninstall(args: argparse.Namespace) -> int:
    ensure_project_root()
    state = InstallState.load()

    to_remove = [
        PROJECT_ROOT / "venv",
        PROJECT_ROOT / ".venv",
        PROJECT_ROOT / ".pytest_cache",
        PROJECT_ROOT / ".mypy_cache",
        PROJECT_ROOT / ".ruff_cache",
        PROJECT_ROOT / "build",
        PROJECT_ROOT / "dist",
        PROJECT_ROOT / ".coverage",
        PROJECT_ROOT / ".flaskenv",
        
    ]

    if not args.keep_data:
        to_remove.extend([
            PROJECT_ROOT / "instance",
            PROJECT_ROOT / "logs",
            PROJECT_ROOT / "autoshop.db",
        ])

    for rel in state.created_paths:
        to_remove.append(PROJECT_ROOT / rel)

    if args.remove_env and not state.env_backup:
        to_remove.append(PROJECT_ROOT / ".env")

    summary = [str(path.relative_to(PROJECT_ROOT)) for path in to_remove if path.exists()]
    if summary:
        print("Paths scheduled for removal:")
        for item in sorted(set(summary)):
            print(f"- {item}")
    else:
        print("No local artifacts found to remove.")

    if not args.yes:
        answer = input("Continue uninstall? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            info("Aborted.")
            return 0

    should_remove_systemd = args.remove_systemd or bool(state.components.get("systemd"))
    if should_remove_systemd and is_linux() and shutil.which("systemctl"):
        if os.geteuid() == 0:
            run(["systemctl", "disable", "--now", "autoshop.service"], check=False)
            if DEFAULT_SERVICE_PATH.exists():
                DEFAULT_SERVICE_PATH.unlink()
                info("Removed systemd unit: autoshop.service")
            run(["systemctl", "daemon-reload"], check=False)
        else:
            info("Skipping systemd removal (requires root).")

    should_remove_tailscale = args.remove_tailscale or bool(state.components.get("tailscale"))
    if should_remove_tailscale and shutil.which("tailscale"):
        run(["tailscale", "down"], check=False)

    env_values = parse_env_file(PROJECT_ROOT / ".env")
    db_url = args.db_url or env_values.get("DATABASE_URL")
    if args.drop_db and not args.keep_data and db_url:
        try:
            maybe_drop_database(db_url)
        except subprocess.CalledProcessError as exc:
            info(f"Database drop failed ({exc}). Continue cleanup manually if needed.")

    if args.purge_system_packages:
        purge_system_packages(state)

    remove_paths(sorted(set(to_remove), key=lambda p: str(p)))

    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)
    for pyc in PROJECT_ROOT.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)
    for pyo in PROJECT_ROOT.rglob("*.pyo"):
        pyo.unlink(missing_ok=True)

    if state.env_backup and args.restore_env:
        backup_path = PROJECT_ROOT / state.env_backup
        if backup_path.exists():
            shutil.copy2(backup_path, PROJECT_ROOT / ".env")
            info("Restored original .env from backup.")
    elif (PROJECT_ROOT / ".env").exists() and not args.keep_env:
        (PROJECT_ROOT / ".env").unlink()
        info("Removed: .env")

    if STATE_DIR.exists():
        backup_dir = STATE_DIR / "backups"
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
            info("Removed install backup artifacts.")

    if STATE_FILE.exists():
        STATE_FILE.unlink()
    if STATE_DIR.exists() and not any(STATE_DIR.iterdir()):
        STATE_DIR.rmdir()

    info("Uninstall complete.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autoshopctl",
        description="Unified Autoshop CRM environment manager.",
    )
    sub = parser.add_subparsers(dest="command")

    setup = sub.add_parser("setup", help="Install dependencies and configure environment")
    setup.add_argument("--mode", choices=["dev", "prod"], default="dev")
    setup.add_argument("--db-url", default=None, help=f"SQLAlchemy database URL (default: {DEFAULT_SQLITE_URL})")
    setup.add_argument("--venv", default="venv", help="Virtualenv directory relative to repo root")
    setup.add_argument("--python", default=None, help="Python executable used to create virtualenv")
    setup.add_argument(
        "--interactive",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Prompt for setup choices interactively (default: enabled in TTY shells)",
    )
    setup.add_argument("--with-systemd", action="store_true", help="Configure and start autoshop.service (Linux only)")
    setup.add_argument("--service-user", default=None, help="Linux user for systemd service (default: sudo user)")
    setup.add_argument("--with-tailscale", action="store_true", help="Run tailscale up as part of setup")
    setup.add_argument("--tailscale-auth-key", default=None, help="Optional tailscale auth key")
    setup.add_argument("--tailscale-tags", default=None, help="Optional tailscale advertised tags")
    setup.add_argument(
        "--install-system-packages",
        action="store_true",
        help="Install OS dependencies and track newly-installed packages for uninstall purge (Linux/root only)",
    )
    setup.add_argument("--force", action="store_true", help="Force setup even if state file exists")
    setup.set_defaults(func=command_setup)

    status = sub.add_parser("status", help="Show setup state")
    status.set_defaults(func=command_status)

    deploy = sub.add_parser("deploy", help="Fast-forward deploy and apply migrations")
    deploy.add_argument("--remote", default=os.getenv("REMOTE", "origin"))
    deploy.add_argument("--branch", default=os.getenv("BRANCH", ""))
    deploy.add_argument("--skip-pull", action="store_true")
    deploy.add_argument("--restart-service", action="store_true")
    deploy.set_defaults(func=command_deploy)

    backup = sub.add_parser("backup", help="Create MySQL/MariaDB backup")
    backup.add_argument("--db-name", default=None)
    backup.add_argument("--db-user", default=None)
    backup.add_argument("--db-password", default=None)
    backup.add_argument("--db-host", default=os.getenv("DB_HOST", "localhost"))
    backup.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    backup.add_argument("--outdir", default="backups")
    backup.set_defaults(func=command_backup)

    uninstall = sub.add_parser("uninstall", help="Remove local setup artifacts")
    uninstall.add_argument("--yes", action="store_true", help="Skip confirmation")
    uninstall.add_argument("--keep-data", action="store_true", help="Keep instance/, logs/, and sqlite db")
    uninstall.add_argument("--keep-env", action="store_true", help="Keep .env instead of removing/restoring it")
    uninstall.add_argument("--remove-env", action="store_true", help="Compatibility flag (legacy behavior)")
    uninstall.add_argument("--restore-env", action="store_true", help="Restore pre-setup .env backup when available")
    uninstall.add_argument(
        "--drop-db",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Drop database from DATABASE_URL during uninstall (default: enabled)",
    )
    uninstall.add_argument("--db-url", default=None, help="Override DATABASE_URL used for drop-db")
    uninstall.add_argument(
        "--purge-system-packages",
        action="store_true",
        help="Remove system packages that were installed by setup --install-system-packages",
    )
    uninstall.add_argument("--remove-systemd", action="store_true", help="Disable/remove autoshop.service")
    uninstall.add_argument("--remove-tailscale", action="store_true", help="Run tailscale down")
    uninstall.set_defaults(func=command_uninstall)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        return command_status(args)

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
