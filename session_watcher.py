import os
import time
from pathlib import Path

# Kitty global watcher: persist all OS windows/tabs via the official
# save_as_session action. Must use boss.call_remote_control (in-process).
# Subprocess `kitty @ ls` from inside this process deadlocks/times out,
# which is why last_session.kitty stayed empty and only one tab came back.

SESSION_FILE = Path.home() / ".config/kitty/last_session.kitty"
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


def _save(boss, force: bool = False) -> None:
    global _last_save
    now = time.time()
    if not force and now - _last_save < 2.0:
        return
    try:
        _save_via_boss(boss)
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
    print(f"Session saved to {SESSION_FILE}")
    print(SESSION_FILE.read_text(encoding="utf-8"), end="")
