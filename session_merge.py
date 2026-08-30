#!/usr/bin/env python3
"""Build one Kitty session from snapshots written by separate Kitty processes."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config/kitty"
SESSION_DIR = CONFIG_DIR / "sessions"
MERGED_FILE = CONFIG_DIR / "last_session.kitty"
MANIFEST_FILE = SESSION_DIR / ".restore-manifest"
RESTORE_PID_FILE = SESSION_DIR / ".restore-pid"


def _normalize_metadata(line: str) -> str:
    """Remove Kitty's process-local window id before comparing tab snapshots."""
    marker = "kitty-unserialize-data="
    start = line.find(marker)
    if start < 0:
        return line.strip()

    json_start = start + len(marker)
    json_end = line.find("}'", json_start)
    if json_end < 0:
        return line.strip()

    try:
        payload = json.loads(line[json_start : json_end + 1])
    except (TypeError, ValueError):
        return line.strip()

    payload.pop("id", None)
    return (
        line[:json_start]
        + json.dumps(payload, separators=(",", ":"))
        + line[json_end + 1 :]
    ).strip()


def _tab_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip() == "new_tab":
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _filter_tabs(text: str, seen: set[str] | None = None) -> tuple[str, int]:
    """Drop empty tabs and duplicate tab snapshots while preserving valid tabs."""
    seen = set() if seen is None else seen
    kept: list[str] = []
    removed = 0

    for block in _tab_blocks(text):
        launch_lines = [line for line in block if line.lstrip().startswith("launch ")]
        if not launch_lines:
            removed += 1
            continue

        normalized = "\n".join(
            _normalize_metadata(line)
            for line in block
            if line.strip()
            and line.strip() not in {"focus", "focus_tab"}
            and not line.lstrip().startswith("set_layout_state ")
        )
        if normalized in seen:
            removed += 1
            continue
        seen.add(normalized)
        kept.extend(
            line for line in block if not line.strip().startswith("focus_tab")
        )
        kept.append("")

    if not kept:
        return "", removed
    return "\n".join(kept).rstrip() + "\n", removed


def _replace_merged(text: str) -> None:
    temporary = MERGED_FILE.with_name(f".{MERGED_FILE.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, MERGED_FILE)


def candidates() -> list[Path]:
    return sorted(
        (path for path in SESSION_DIR.glob("kitty-*.kitty") if path.is_file()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )


def _manifest_sources() -> list[Path]:
    try:
        return [
            Path(line)
            for line in MANIFEST_FILE.read_text(encoding="utf-8").splitlines()
            if line
        ]
    except OSError:
        return []


def _registered_snapshot() -> Path | None:
    """Return the snapshot produced by the process that replayed the manifest.

    A non-empty snapshot from that exact PID proves the restored process got far
    enough to serialize its state.  The manifest inputs are therefore an older
    generation and must not be merged with their restored copy after an
    interrupted asynchronous cleanup.
    """
    try:
        pid = int(RESTORE_PID_FILE.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return None
    snapshot = SESSION_DIR / f"kitty-{pid}.kitty"
    try:
        snapshot_text = snapshot.read_text(encoding="utf-8")
        merged_text = MERGED_FILE.read_text(encoding="utf-8")
    except OSError:
        return None

    # A watcher can save while startup is still replaying tabs. Do not treat a
    # partial early snapshot as proof that it safely supersedes the manifest.
    restored_tabs = sum(line.strip() == "new_tab" for line in snapshot_text.splitlines())
    expected_tabs = sum(line.strip() == "new_tab" for line in merged_text.splitlines())
    if snapshot_text.strip() and restored_tabs >= expected_tabs:
        return snapshot
    return None


def _remove_manifest_generation() -> bool:
    complete = True
    for path in _manifest_sources():
        try:
            # Never trust paths read from a state file outside this directory.
            if path.parent == SESSION_DIR and path.name.startswith("kitty-"):
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
    if MANIFEST_FILE.is_file() and _registered_snapshot() is not None:
        if _remove_manifest_generation():
            _clear_restore_state()


def prepare() -> int:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    reconcile_previous_restore()
    sources = candidates()
    if not sources:
        # Compatibility with the pre-multi-process implementation.
        if MERGED_FILE.is_file() and MERGED_FILE.stat().st_size:
            try:
                existing = MERGED_FILE.read_text(encoding="utf-8")
            except OSError:
                return 1
            filtered, _ = _filter_tabs(existing)
            if filtered:
                if filtered != existing:
                    _replace_merged(filtered)
                return 0
            MERGED_FILE.unlink(missing_ok=True)
            return 1
        return 1

    chunks: list[str] = []
    valid_sources: list[Path] = []
    seen_tabs: set[str] = set()
    for source in sources:
        try:
            text = source.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.strip():
            continue
        # Flatten OS windows into one restored Kitty process. Tabs and panes
        # remain intact; the separator itself is the only discarded command.
        lines = [line for line in text.splitlines() if line.strip() != "new_os_window"]
        filtered, _ = _filter_tabs("\n".join(lines), seen_tabs)
        if filtered:
            chunks.append(filtered)
            valid_sources.append(source)

    if not chunks:
        return 1

    _replace_merged("\n".join(chunks))

    manifest_tmp = MANIFEST_FILE.with_name(f".{MANIFEST_FILE.name}.tmp")
    manifest_tmp.write_text(
        "\n".join(str(path) for path in valid_sources) + "\n", encoding="utf-8"
    )
    os.chmod(manifest_tmp, 0o600)
    os.replace(manifest_tmp, MANIFEST_FILE)
    return 0


def cleanup() -> int:
    if _remove_manifest_generation():
        _clear_restore_state()
        return 0
    # Keep the manifest so a later prepare/cleanup can retry failed deletions.
    return 1


def register_restore(pid_text: str) -> int:
    try:
        pid = int(pid_text)
    except ValueError:
        return 1
    if pid <= 0 or not MANIFEST_FILE.is_file():
        return 1
    temporary = RESTORE_PID_FILE.with_name(f".{RESTORE_PID_FILE.name}.tmp")
    temporary.write_text(f"{pid}\n", encoding="ascii")
    os.chmod(temporary, 0o600)
    os.replace(temporary, RESTORE_PID_FILE)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--prepare":
        raise SystemExit(prepare())
    if len(sys.argv) == 2 and sys.argv[1] == "--cleanup":
        raise SystemExit(cleanup())
    if len(sys.argv) == 3 and sys.argv[1] == "--register":
        raise SystemExit(register_restore(sys.argv[2]))
    raise SystemExit("usage: session_merge.py --prepare|--cleanup|--register PID")
