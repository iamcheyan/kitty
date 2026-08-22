#!/usr/bin/env python3
"""Build one Kitty session from snapshots written by separate Kitty processes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config/kitty"
SESSION_DIR = CONFIG_DIR / "sessions"
MERGED_FILE = CONFIG_DIR / "last_session.kitty"
MANIFEST_FILE = SESSION_DIR / ".restore-manifest"


def candidates() -> list[Path]:
    return sorted(
        (path for path in SESSION_DIR.glob("kitty-*.kitty") if path.is_file()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )


def prepare() -> int:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    sources = candidates()
    if not sources:
        # Compatibility with the pre-multi-process implementation.
        if MERGED_FILE.is_file() and MERGED_FILE.stat().st_size:
            return 0
        return 1

    chunks: list[str] = []
    valid_sources: list[Path] = []
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
        chunks.append("\n".join(lines).rstrip() + "\n")
        valid_sources.append(source)

    if not chunks:
        return 1

    temporary = MERGED_FILE.with_name(f".{MERGED_FILE.name}.tmp")
    temporary.write_text("\n".join(chunks), encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, MERGED_FILE)

    manifest_tmp = MANIFEST_FILE.with_name(f".{MANIFEST_FILE.name}.tmp")
    manifest_tmp.write_text(
        "\n".join(str(path) for path in valid_sources) + "\n", encoding="utf-8"
    )
    os.chmod(manifest_tmp, 0o600)
    os.replace(manifest_tmp, MANIFEST_FILE)
    return 0


def cleanup() -> int:
    try:
        sources = MANIFEST_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0

    for raw_path in sources:
        path = Path(raw_path)
        try:
            # Only delete files inside our session directory.
            if path.parent == SESSION_DIR and path.name.startswith("kitty-"):
                path.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        MANIFEST_FILE.unlink()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"--prepare", "--cleanup"}:
        raise SystemExit("usage: session_merge.py --prepare|--cleanup")
    raise SystemExit(prepare() if sys.argv[1] == "--prepare" else cleanup())
