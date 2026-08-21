#!/usr/bin/env bash
# notify-reload.sh — Cross-platform desktop notification for Kitty config reload
set -euo pipefail

if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e 'display notification "Configuration reloaded successfully" with title "Kitty" subtitle "kitty.conf"' 2>/dev/null || true
else
    notify-send "Kitty" "Configuration reloaded successfully" 2>/dev/null || true
fi
