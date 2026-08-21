import os
import re
import socket
import unicodedata
from typing import Optional

from kitty.tab_bar import (
    Color,
    DrawData,
    ExtraData,
    Screen,
    TabBarData,
    as_rgb,
    color_as_int,
    get_boss,
)

# ==============================================================================
# Tab Bar Display & SSH Highlighting Settings
# ==============================================================================
# Maximum character length for each tab title
MAX_TAB_TITLE_LEN = 30

# Active SSH Tab: Eye-catching vivid warning orange/red with bold white text
SSH_ACTIVE_BG = as_rgb(color_as_int(Color(255, 85, 0)))      # #ff5500 (Vibrant Orange-Red)
SSH_ACTIVE_FG = as_rgb(color_as_int(Color(255, 255, 255)))   # #ffffff (White)

# Inactive SSH Tab: Distinct warm dark amber-brown with peach text
SSH_INACTIVE_BG = as_rgb(color_as_int(Color(100, 32, 10)))    # #64200a (Dark Amber-Brown)
SSH_INACTIVE_FG = as_rgb(color_as_int(Color(255, 170, 130)))  # #ffaa82 (Light Peach)


def _get_local_hosts() -> set[str]:
    """Retrieve all local hostnames/IPs to prevent false-positive SSH detection."""
    hosts = {"localhost", "127.0.0.1", "::1"}
    try:
        hn = socket.gethostname().lower()
        hosts.add(hn)
        if "." in hn:
            hosts.add(hn.split(".")[0])
    except Exception:
        pass
    try:
        nodename = os.uname().nodename.lower()
        hosts.add(nodename)
        if "." in nodename:
            hosts.add(nodename.split(".")[0])
    except Exception:
        pass
    return hosts


LOCAL_HOSTS = _get_local_hosts()


def display_width(s: str) -> int:
    """Calculate terminal column width accounting for CJK and ANSI escape codes."""
    w = 0
    in_esc = False
    for ch in s:
        if ch == "\033":
            in_esc = True
            continue
        if in_esc:
            if ch == "m":
                in_esc = False
            continue
        status = unicodedata.east_asian_width(ch)
        w += 2 if status in ("W", "F") else 1
    return w


def _extract_ssh_target(cmdline: list[str]) -> str:
    """Extract destination host/IP from an SSH command line."""
    if not cmdline:
        return ""
    args = cmdline[:]
    if args and os.path.basename(args[0]).lower() == "kitten":
        args = args[1:]
        if args and args[0] in ("ssh", "run-shell"):
            args = args[1:]
    elif args and os.path.basename(args[0]).lower() in ("ssh", "sftp", "scp", "mosh-client", "mosh"):
        args = args[1:]

    flags_with_arg = {"-p", "-i", "-l", "-o", "-F", "-c", "-b", "-e", "-m", "-O", "-S", "-W", "-w", "-J"}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in flags_with_arg:
            i += 2
            continue
        if arg.startswith("-") and len(arg) > 1 and arg[1] in "piIoFcbeMOSWwJ":
            i += 1
            continue
        if arg.startswith("-"):
            i += 1
            continue
        target = arg
        if "@" in target:
            target = target.split("@", 1)[1]
        return target
    return ""


def _format_ssh_title(raw_title: str, target_ip_or_host: str = "") -> str:
    """Format SSH tab title as [SSH:Host/IP] with optional machine name or path."""
    t = raw_title.strip()

    title_host = ""
    title_path = ""
    m = re.match(r"^(?:\[SSH(?::[^\]]+)?\]\s*)?(?:[\w.-]+@)?([\w.-]+)(?::\s*~?(/?[^ ]*))?", t)
    if m and ("@" in t or ":" in t):
        title_host = m.group(1) or ""
        title_path = (m.group(2) or "").strip()
        if title_path in ("~", "/", ""):
            title_path = ""

    label_host = target_ip_or_host if target_ip_or_host else (title_host if title_host else "remote")

    detail = ""
    if title_path:
        base = os.path.basename(title_path.rstrip("/"))
        if base and base != "~":
            detail = base
    elif title_host and title_host.lower() != label_host.lower() and title_host.lower() not in LOCAL_HOSTS:
        detail = title_host
    elif t and not any(t.startswith(prefix) for prefix in ("[SSH", f"{label_host}", f"{title_host}")):
        if "@" in t and ":" in t:
            pass
        else:
            clean_t = os.path.basename(t.rstrip("/"))
            if clean_t.lower() not in (label_host.lower(), title_host.lower(), "zsh", "bash"):
                detail = clean_t

    if detail:
        return f"[SSH:{label_host}] {detail}"
    else:
        return f"[SSH:{label_host}]"


def _clean_title(title: str, is_ssh: bool = False, ssh_target: str = "", max_len: int = MAX_TAB_TITLE_LEN) -> str:
    """
    Format verbose window titles into clean, concise tab labels:
      - SSH: '[SSH:192.168.1.50] debian' or '[SSH:debian] zellij-cb'
      - Local user@hostname: ~/path -> 'path' or 'zsh'
      - Tmux: 'tmux:main'
      - Editor: 'nvim file.py'
      - Path: 'foo'
    """
    t = title.strip()
    if not t:
        return "zsh"

    # 1. SSH session formatting
    if is_ssh:
        ssh_t = _format_ssh_title(t, ssh_target)
        if len(ssh_t) > max_len:
            ssh_t = ssh_t[:max_len - 1] + "…"
        return ssh_t

    # 2. Local prompt title: user@hostname: ~/path -> extract path or zsh
    m_local = re.match(r"^(?:[\w.-]+@)?([\w.-]+)(?::\s*~?(/?[^ ]*))?", t)
    if m_local and ("@" in t or ":" in t):
        path = (m_local.group(2) or "").strip()
        if path and path not in ("~", "/"):
            base = os.path.basename(path.rstrip("/"))
            if base:
                t = base
        else:
            t = "zsh"

    # 3. Tmux commands: tmux new-session -A -s main -> tmux:main
    m_tmux = re.search(r"tmux(?:\s+(?:new(?:-session)?|attach(?:-session)?))?.*?(?:-s|-t)\s+([^\s]+)", t)
    if m_tmux:
        t = f"tmux:{m_tmux.group(1)}"
    elif t.startswith("tmux "):
        t = "tmux"

    # 4. Editor commands: nvim /a/b/c/file.py -> nvim file.py
    m_edit = re.match(r"^(nvim|vim|vi|nano|code|hx)\s+(?:.+/)?([^/]+)$", t)
    if m_edit:
        t = f"{m_edit.group(1)} {m_edit.group(2)}"

    # 5. Long absolute or home paths: /Users/tetsuya/dev/foo -> foo
    if t.startswith(("/", "~/")):
        t = os.path.basename(t.rstrip("/"))

    # 6. Truncate if still exceeds max_len
    if len(t) > max_len:
        t = t[:max_len - 1] + "…"

    return t


def _get_total_tabs() -> int:
    """Get total number of tabs in current active OS window."""
    try:
        boss = get_boss()
        if boss:
            tm = getattr(boss, "active_tab_manager", None)
            if tm:
                return len(tm)
    except Exception:
        pass
    return 1


def _is_ssh_cmd(cmdline: list[str]) -> bool:
    """Check if command-line represents an SSH / remote session."""
    if not cmdline:
        return False
    exe = os.path.basename(cmdline[0]).lower()
    if exe in ("ssh", "sftp", "scp", "mosh-client", "mosh"):
        return True
    if exe == "kitten" and len(cmdline) > 1 and cmdline[1] in ("ssh", "remote_file"):
        return True
    return False


def _get_ssh_info(tab: TabBarData) -> tuple[bool, str]:
    """Detect SSH session and extract target Host/IP (filtering out local hostnames)."""
    try:
        boss = get_boss()
        if boss:
            t = boss.tab_for_id(tab.tab_id)
            if t:
                windows = [t.active_window] if t.active_window else []
                for w in t:
                    if w and w not in windows:
                        windows.append(w)

                for w in windows:
                    if not w:
                        continue
                    # 1. Kitten ssh / kssh check
                    try:
                        cmdline = w.ssh_kitten_cmdline()
                        if cmdline:
                            target = _extract_ssh_target(cmdline)
                            if target and target.lower() not in LOCAL_HOSTS:
                                return True, target
                    except Exception:
                        pass

                    # 2. Check child foreground processes
                    try:
                        child = getattr(w, "child", None)
                        if child and hasattr(child, "foreground_processes"):
                            for p in child.foreground_processes:
                                cmdline = p.get("cmdline") or []
                                if _is_ssh_cmd(cmdline):
                                    target = _extract_ssh_target(cmdline)
                                    if not target or target.lower() not in LOCAL_HOSTS:
                                        return True, target
                    except Exception:
                        pass

                    # 3. Built-in remote child check
                    if getattr(w, "child_is_remote", False):
                        return True, ""

                    # 4. User variable check
                    try:
                        user_vars = getattr(w, "user_vars", {}) or {}
                        if user_vars.get("IS_SSH") in ("1", "true", "yes"):
                            target = user_vars.get("SSH_HOST", "") or user_vars.get("SSH_IP", "")
                            if not target or target.lower() not in LOCAL_HOSTS:
                                return True, target
                    except Exception:
                        pass
    except Exception:
        pass

    # 5. Title-based fallback (Strict check: must explicitly be ssh/kssh/mosh/sftp or [SSH:...)
    title_lower = (tab.title or "").lower().strip()
    if title_lower.startswith(("ssh ", "ssh:", "kssh ", "sftp ", "scp ", "mosh ")):
        parts = tab.title.split()
        target = parts[1] if len(parts) > 1 else ""
        if "@" in target:
            target = target.split("@", 1)[1]
        if target and target.lower() not in LOCAL_HOSTS:
            return True, target
    if "[ssh" in title_lower or "(ssh)" in title_lower:
        m = re.search(r"\[ssh(?::([^\]]+))?\]", title_lower)
        target = m.group(1).strip() if (m and m.group(1)) else ""
        if not target or target.lower() not in LOCAL_HOSTS:
            return True, target

    return False, ""


def draw_tab(
    draw_data: DrawData,
    screen: Screen,
    tab: TabBarData,
    before: int,
    max_tab_length: int,
    index: int,
    is_last: bool,
    extra_data: ExtraData,
) -> int:
    """
    Custom 100% full-width equal-distribution tab bar renderer:
    - 1 Tab: 100% full width.
    - 2 Tabs: 50% / 50%.
    - N Tabs: evenly distributed across screen.columns, always filling the entire top bar.
    - Tab number always visible at front (e.g. '1: zsh', '2: [SSH:192.168.1.50] debian').
    - Direct Tmux-style switching: Ctrl+p 1, Ctrl+p 2, Ctrl+p 3...
    - SSH tabs: highlighted in vivid orange-red with [SSH:IP/Host] machine label.
    """
    is_ssh, ssh_target = _get_ssh_info(tab)

    # 1. Apply tab background and foreground colors
    try:
        if is_ssh:
            if tab.is_active:
                screen.cursor.bg = SSH_ACTIVE_BG
                screen.cursor.fg = SSH_ACTIVE_FG
                screen.cursor.bold = True
                screen.cursor.italic = False
            else:
                screen.cursor.bg = SSH_INACTIVE_BG
                screen.cursor.fg = SSH_INACTIVE_FG
                screen.cursor.bold = False
                screen.cursor.italic = False
    except Exception:
        pass

    tab_bg = screen.cursor.bg
    tab_fg = screen.cursor.fg

    # 2. Calculate 100% full-width equal distribution
    total_cols = screen.columns
    num_tabs = max(1, _get_total_tabs())

    if is_last:
        tab_width = max(1, total_cols - before)
    else:
        tab_width = max(1, total_cols // num_tabs)

    # 3. Format title with tab number at front (e.g. '1: zsh', '2: [SSH:debian]')
    clean_t = _clean_title(tab.title, is_ssh=is_ssh, ssh_target=ssh_target)
    full_title = f"{index}: {clean_t}"
    tw = display_width(full_title)

    # 4. Render centered content to fill exact tab_width
    screen.cursor.bg = tab_bg
    screen.cursor.fg = tab_fg

    if tab_width >= tw:
        pad_left = (tab_width - tw) // 2
        pad_right = tab_width - tw - pad_left
        if pad_left > 0:
            screen.draw(" " * pad_left)
        screen.draw(full_title)
        screen.cursor.bg = tab_bg
        screen.cursor.fg = tab_fg
        if pad_right > 0:
            screen.draw(" " * pad_right)
    else:
        # If tab width is smaller than text, truncate with ellipsis
        trunc_t = full_title[:max(1, tab_width - 1)] + "…" if tab_width > 2 else full_title[:tab_width]
        screen.draw(trunc_t)
        rem = max(0, tab_width - display_width(trunc_t))
        if rem > 0:
            screen.draw(" " * rem)

    end = before + tab_width
    return end
