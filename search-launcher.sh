#!/usr/bin/env bash
# search-launcher.sh — 智能搜索入口
#
# tmux 环境 → tmux copy-mode 原生搜索（/ 向前搜索）
# kitty 原生 → kitty search kitten（底部 2 行分栏，高亮 + 跳转）
#
# 绑定: map ctrl+p>s launch --type=background bash ~/.config/kitty/search-launcher.sh
set -euo pipefail

# ── 找到 kitty remote control socket ────────────────────────────
# launch --type=background 不继承 KITTY_LISTEN_ON / KITTY_WINDOW_ID，
# 必须自己扫描 socket。
SOCK=""
if [[ -n "${KITTY_LISTEN_ON:-}" ]]; then
    SOCK="${KITTY_LISTEN_ON#unix:}"
fi
if [[ -z "${SOCK:-}" || ! -S "$SOCK" ]]; then
    # 扫描 /tmp/mykitty-* 取最新的 socket
    SOCK=$(ls -t /tmp/mykitty-* 2>/dev/null | head -1)
fi
if [[ -z "${SOCK:-}" || ! -S "$SOCK" ]]; then
    echo "找不到 kitty socket" >&2
    exit 1
fi
TO="unix:$SOCK"

# ── 获取活跃窗口 ────────────────────────────────────────────────
ACTIVE_WIN=$(kitty @ --to "$TO" ls 2>/dev/null | jq -r '
    .[].tabs[] | select(.is_active) | .windows[] | select(.is_focused) | .id
' | head -1)
[[ -z "$ACTIVE_WIN" ]] && exit 1

# ── (已停用) tmux 环境判断：统一走 Kitty 原生 search kitten ────────
# CMDLINE=$(kitty @ --to "$TO" ls 2>/dev/null | jq -r --argjson wid "$ACTIVE_WIN" '
#     .[].tabs[].windows[] | select(.id == $wid) | .cmdline | join(" ")
# ')
# if echo "$CMDLINE" | grep -q "tmux"; then
#     # 向活跃窗口发送 tmux prefix + [ + / (copy-mode + forward search)
#     # Ctrl+B = \x02, [ = copy mode, / = search forward
#     kitty @ --to "$TO" send-text --match="id:$ACTIVE_WIN" $'\x02\x5b\x2f'
#     exit 0
# fi

# 以 hsplit 启动 search kitten（底部 2 行）
command -v jq >/dev/null 2>&1 || { echo "缺少依赖: jq" >&2; exit 1; }

# 保存原始 layout，切到 splits 以支持 hsplit + resize 到 1 行
ORIG_LAYOUT=$(kitty @ --to "$TO" ls 2>/dev/null | jq -r --argjson wid "$ACTIVE_WIN" '
    .[].tabs[] | select(.windows[].id == $wid) | .layout
' | head -1)

if [[ -n "$ORIG_LAYOUT" && "$ORIG_LAYOUT" != "splits" ]]; then
    kitty @ --to "$TO" goto-layout --match="id:$ACTIVE_WIN" splits 2>/dev/null || true
fi

# 以 hsplit 启动 search kitten（底部 1 行）
SEARCH_WIN=$(kitty @ --to "$TO" launch --location=hsplit --allow-remote-control \
    --match="id:$ACTIVE_WIN" \
    kitty +kitten search.py "$ACTIVE_WIN" 2>/dev/null || true)

# 启动失败 → 还原 layout 并退出
if [[ -z "$SEARCH_WIN" ]]; then
    if [[ -n "$ORIG_LAYOUT" && "$ORIG_LAYOUT" != "splits" ]]; then
        kitty @ --to "$TO" goto-layout --match="id:$ACTIVE_WIN" "$ORIG_LAYOUT" 2>/dev/null || true
    fi
    exit 1
fi

# 等待 search kitten 窗口关闭（最多 120 秒）
TIMEOUT=600  # 600 × 0.2s = 120s
while [[ $TIMEOUT -gt 0 ]]; do
    kitty @ --to "$TO" ls 2>/dev/null | jq -e --argjson wid "$SEARCH_WIN" '
        .[].tabs[].windows[] | select(.id == $wid)
    ' >/dev/null 2>&1 || break
    sleep 0.2
    TIMEOUT=$((TIMEOUT - 1))
done

# 还原原始 layout
if [[ -n "$ORIG_LAYOUT" && "$ORIG_LAYOUT" != "splits" ]]; then
    kitty @ --to "$TO" goto-layout --match="id:$ACTIVE_WIN" "$ORIG_LAYOUT" 2>/dev/null || true
fi