import json
import os
import shutil
import sys
import time
from pathlib import Path

# Kitty global watcher: persist all OS windows/tabs via the official
# save_as_session action. Must use boss.call_remote_control (in-process).
# Subprocess `kitty @ ls` from inside this process deadlocks/times out,
# which is why the old shared last_session.kitty could be incomplete.

CONFIG_DIR = Path.home() / ".config/kitty"
SESSION_DIR = CONFIG_DIR / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
SESSION_FILE = SESSION_DIR / f"kitty-{os.getpid()}.kitty"
MERGED_FILE = CONFIG_DIR / "last_session.kitty"
LOG_FILE = Path("/tmp/kitty-session-watcher.log")
SAVE_ACTION = (
    f"save_as_session --save-only --use-foreground-process {SESSION_FILE}"
)

_last_save = 0.0
_quit_saved = False


def _log(msg: str) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except OSError:
        pass


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _prune_dead_snapshots() -> None:
    current_pid = os.getpid()
    for p in SESSION_DIR.glob("kitty-*.kitty"):
        if not p.is_file():
            continue
        try:
            pid = int(p.stem.split("-", 1)[1])
            if pid == current_pid:
                continue
            if not _is_pid_alive(pid):
                p.unlink(missing_ok=True)
                _log(f"pruned dead session snapshot: {p.name}")
        except (IndexError, ValueError, OSError):
            pass


def _sync_last_session() -> None:
    _prune_dead_snapshots()
    live_files = sorted(
        [
            p
            for p in SESSION_DIR.glob("kitty-*.kitty")
            if p.is_file() and p.stat().st_size > 0
        ],
        key=lambda p: (p.stat().st_mtime_ns, p.name),
    )
    if not live_files:
        return

    if len(live_files) == 1 and live_files[0] == SESSION_FILE:
        try:
            content = SESSION_FILE.read_text(encoding="utf-8")
        except OSError:
            return
    else:
        chunks = []
        for lf in live_files:
            try:
                text = lf.read_text(encoding="utf-8").strip()
                if text:
                    lines = [line for line in text.splitlines() if line.strip() != "new_os_window"]
                    if lines:
                        chunks.append("\n".join(lines))
            except OSError:
                continue
        content = "\n\n".join(chunks) + "\n" if chunks else ""

    if not content:
        return

    tmp_file = MERGED_FILE.with_name(f".{MERGED_FILE.name}.tmp")
    try:
        tmp_file.write_text(content, encoding="utf-8")
        os.chmod(tmp_file, 0o600)
        os.replace(tmp_file, MERGED_FILE)
    except OSError as exc:
        _log(f"sync to last_session.kitty failed: {exc}")
        try:
            tmp_file.unlink(missing_ok=True)
        except OSError:
            pass


def _save_via_boss(boss) -> None:
    boss.call_remote_control(None, ("action", SAVE_ACTION))


def _rewrite_codex_restore_commands() -> None:
    """Make direct Codex panes resume their last project session on restore.

    Kitty's official serializer records the shell-integrated command as
    ``codex``.  That is correct for a live snapshot, but replaying it starts a
    fresh Codex process.  Only rewrite the exact command in Kitty's serialized
    metadata; tmux panes and commands with explicit arguments are left alone.
    """
    try:
        original = SESSION_FILE.read_text(encoding="utf-8")
    except OSError:
        return

    rewritten = []
    changed = False
    marker = "kitty-unserialize-data="
    for line in original.splitlines(keepends=True):
        start = line.find(marker)
        if start < 0:
            rewritten.append(line)
            continue

        json_start = start + len(marker)
        json_end = line.find("}'", json_start)
        if json_end < 0:
            rewritten.append(line)
            continue

        try:
            payload = json.loads(line[json_start : json_end + 1])
        except (TypeError, ValueError):
            rewritten.append(line)
            continue

        if payload.get("cmd_at_shell_startup") == "codex":
            payload["cmd_at_shell_startup"] = "codex resume --last"
            line = (
                line[:json_start]
                + json.dumps(payload, separators=(",", ":"))
                + line[json_end + 1 :]
            )
            changed = True
        rewritten.append(line)

    if not changed:
        return

    temporary = SESSION_FILE.with_name(f".{SESSION_FILE.name}.tmp")
    try:
        temporary.write_text("".join(rewritten), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, SESSION_FILE)
    except OSError as exc:
        _log(f"codex restore rewrite failed: {exc}")
        try:
            temporary.unlink()
        except OSError:
            pass


def _save(boss, force: bool = False) -> None:
    global _last_save
    now = time.time()
    if not force and now - _last_save < 2.0:
        return
    try:
        _save_via_boss(boss)
        _rewrite_codex_restore_commands()
        _sync_last_session()
        _last_save = now
        _log(f"saved {SESSION_FILE} and synced last_session.kitty size={SESSION_FILE.stat().st_size}")
    except Exception as exc:
        _log(f"save failed: {exc}")


def on_load(boss, data) -> None:
    _log("watcher loaded")
    _prune_dead_snapshots()


def on_tab_bar_dirty(boss, window, data) -> None:
    _save(boss)


def on_quit(boss, window, data) -> None:
    # First on_quit fires before windows are destroyed. Save once there.
    global _quit_saved
    if _quit_saved:
        return
    _quit_saved = True
    _save(boss, force=True)
    _log("on_quit save")


def _resolve_socket():
    env = os.environ.get("KITTY_LISTEN_ON")
    if env:
        path = env[5:] if env.startswith("unix:") else env
        if os.path.exists(path):
            return env
    sockets = sorted(
        Path("/tmp").glob("mykitty-*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if sockets:
        return f"unix:{sockets[0]}"
    return None



if __name__ == "__main__":
    import subprocess

    socket = _resolve_socket()
    if not socket:
        raise SystemExit("no kitty listen socket")
    # Kitty may be launched from a GUI with a reduced PATH. Prefer the
    # current environment, then use the standard macOS app-bundle location.
    kitty_bin = shutil.which("kitty")
    if not kitty_bin and sys.platform == "darwin":
        app_kitty = "/Applications/kitty.app/Contents/MacOS/kitty"
        if os.path.exists(app_kitty):
            kitty_bin = app_kitty
    if not kitty_bin:
        kitty_bin = "kitty"
    res = subprocess.run(
        [kitty_bin, "@", "--to", socket, "action", SAVE_ACTION],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise SystemExit(res.stderr.strip() or f"save failed rc={res.returncode}")
    _rewrite_codex_restore_commands()
    _sync_last_session()
    print(f"Session saved to {SESSION_FILE} and synced to {MERGED_FILE}")
    print(SESSION_FILE.read_text(encoding="utf-8"), end="")
