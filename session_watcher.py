import json
import os
import time
from pathlib import Path

# Kitty global watcher: persist all OS windows/tabs via the official
# save_as_session action. Must use boss.call_remote_control (in-process).
# Subprocess `kitty @ ls` from inside this process deadlocks/times out,
# which is why the old shared last_session.kitty could be incomplete.

SESSION_DIR = Path.home() / ".config/kitty/sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
SESSION_FILE = SESSION_DIR / f"kitty-{os.getpid()}.kitty"
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
        _last_save = now
        _log(f"saved {SESSION_FILE} size={SESSION_FILE.stat().st_size}")
    except Exception as exc:
        _log(f"save failed: {exc}")


def on_load(boss, data) -> None:
    _log("watcher loaded")


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
    kitty_bin = "/Applications/kitty.app/Contents/MacOS/kitty"
    if not os.path.exists(kitty_bin):
        kitty_bin = "kitty"
    res = subprocess.run(
        [kitty_bin, "@", "--to", socket, "action", SAVE_ACTION],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise SystemExit(res.stderr.strip() or f"save failed rc={res.returncode}")
    _rewrite_codex_restore_commands()
    print(f"Session saved to {SESSION_FILE}")
    print(SESSION_FILE.read_text(encoding="utf-8"), end="")
