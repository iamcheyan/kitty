#!/usr/bin/env python3
"""Prepare and clean per-process Kitty session restores."""

from __future__ import annotations

import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config/kitty"
SESSION_DIR = CONFIG_DIR / "sessions"
MERGED_FILE = CONFIG_DIR / "last_session.kitty"
MANIFEST_FILE = SESSION_DIR / ".restore-manifest"
RESTORE_PID_FILE = SESSION_DIR / ".restore-pids"
LEGACY_RESTORE_FILE = SESSION_DIR / ".restore-legacy.kitty"


def _atomic_write(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def _manifest_sources() -> list[Path]:
    try:
        return [
            Path(line)
            for line in MANIFEST_FILE.read_text(encoding="utf-8").splitlines()
            if line
        ]
    except OSError:
        return []


def _tab_count(path: Path) -> int:
    try:
        return sum(
            line.strip() == "new_tab"
            for line in path.read_text(encoding="utf-8").splitlines()
        )
    except OSError:
        return 0


def _registered_restore_is_complete() -> bool:
    try:
        records = [
            line.split("\t", 1)
            for line in RESTORE_PID_FILE.read_text(encoding="utf-8").splitlines()
            if line
        ]
        restored = {Path(source): int(pid) for pid, source in records}
    except (OSError, ValueError):
        return False
    sources = _manifest_sources()
    if not sources or set(sources) != set(restored):
        return False
    for source in sources:
        expected_tabs = _tab_count(source)
        restored_tabs = _tab_count(SESSION_DIR / f"kitty-{restored[source]}.kitty")
        if expected_tabs == 0 or restored_tabs < expected_tabs:
            return False
    return True


def _remove_manifest_generation() -> bool:
    complete = True
    for path in _manifest_sources():
        try:
            if path.parent != SESSION_DIR:
                continue
            if path.name.startswith("kitty-") and path.suffix == ".kitty":
                path.unlink(missing_ok=True)
            elif path == LEGACY_RESTORE_FILE:
                path.unlink(missing_ok=True)
        except OSError:
            complete = False
    return complete


def _clear_restore_state() -> None:
    for path in (MANIFEST_FILE, RESTORE_PID_FILE):
        try:
            path.unlink()
        except OSError:
            pass


def reconcile_previous_restore() -> None:
    if not MANIFEST_FILE.is_file():
        return
    if _registered_restore_is_complete():
        if _remove_manifest_generation():
            _clear_restore_state()
        return

    # If a prior restore was interrupted, its original inputs are still intact.
    # Remove only dead partial outputs so they cannot be restored alongside
    # their originals on the next cold launch.
    try:
        records = [
            line.split("\t", 1)
            for line in RESTORE_PID_FILE.read_text(encoding="utf-8").splitlines()
            if line
        ]
    except OSError:
        return
    source_paths = set(_manifest_sources())
    for pid_text, _source in records:
        try:
            pid = int(pid_text)
            os.kill(pid, 0)
        except ProcessLookupError:
            output = SESSION_DIR / f"kitty-{pid_text}.kitty"
            if output not in source_paths:
                output.unlink(missing_ok=True)
        except (ValueError, PermissionError, OSError):
            continue


def prepare() -> int:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    reconcile_previous_restore()

    sources = sorted(
        path
        for path in SESSION_DIR.glob("kitty-*.kitty")
        if path.is_file() and path.stat().st_size > 0
    )
    if not sources and MERGED_FILE.is_file() and MERGED_FILE.stat().st_size > 0:
        # Migrate the old single-file snapshot without flattening it further.
        _atomic_write(LEGACY_RESTORE_FILE, MERGED_FILE.read_text(encoding="utf-8"))
        sources = [LEGACY_RESTORE_FILE]

    if not sources:
        return 1

    _atomic_write(MANIFEST_FILE, "".join(f"{source}\n" for source in sources))
    try:
        RESTORE_PID_FILE.unlink()
    except OSError:
        pass
    return 0


def cleanup() -> int:
    if not _registered_restore_is_complete():
        return 1
    if _remove_manifest_generation():
        _clear_restore_state()
        return 0
    return 1


def register_restore(pid_text: str, source_text: str) -> int:
    try:
        pid = int(pid_text)
    except ValueError:
        return 1
    source = Path(source_text)
    if pid <= 0 or source not in _manifest_sources():
        return 1
    try:
        existing = RESTORE_PID_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        existing = []
    record = f"{pid}\t{source}"
    records = list(dict.fromkeys([*existing, record]))
    _atomic_write(RESTORE_PID_FILE, "".join(f"{value}\n" for value in records))
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--prepare":
        raise SystemExit(prepare())
    if len(sys.argv) == 2 and sys.argv[1] == "--cleanup":
        raise SystemExit(cleanup())
    if len(sys.argv) == 4 and sys.argv[1] == "--register":
        raise SystemExit(register_restore(sys.argv[2], sys.argv[3]))
    raise SystemExit("usage: session_merge.py --prepare|--cleanup|--register PID SESSION")
