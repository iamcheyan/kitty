# Kitty Terminal Configuration

> Production-grade, GPU-accelerated [Kitty](https://sw.kovidgoyal.net/kitty/) terminal setup featuring a custom 100% full-width tab bar, SSH highlighting, Tmux-style modal keybindings, automatic session restore, and smart image paste.

---

## Highlights

- **✨ 100% Full-Width Equal Distribution Tab Bar**: Custom Python-rendered tab bar with zero black margins, centered titles, and permanent tab numbers (`1: zsh`, `2: debian`).
- **🔥 Intelligent SSH State Highlighting**: Auto-detects remote SSH/Kitten-SSH sessions, highlights the active tab in vivid warning orange-red (`#ff5500`) with `[SSH:IP/Hostname]` labels.
- **⌨️ Tmux-Style `Ctrl+P` Keybinding Suite**:
  - `Ctrl+p %` / `"`: Vertical and horizontal splits
  - `Ctrl+p 1~9`: Instant direct tab jump (matches permanent top-bar numbers)
  - `Ctrl+p s`: In-terminal regex scrollback search
  - `Ctrl+p u/f/y`: Hints kitten (screen URL, file path, line picker)
  - `Ctrl+p r`: Hot-reload configuration with desktop notification
  - `Ctrl+p ?`: Interactive keybindings cheat sheet overlay
- **💾 Auto Session Save & Restore**: Powered by `session_watcher.py` to seamlessly persist and recover all OS windows, tabs, layouts, and working directories across cold restarts.
- **🖼️ Smart Paste**: `Ctrl+Shift+V` automatically saves clipboard images to disk and injects the image path into the terminal.

---

## Quick Install (Standalone)

Clone directly to your `~/.config/kitty` directory:

```bash
# Backup existing config if present
[ -d ~/.config/kitty ] && mv ~/.config/kitty ~/.config/kitty.bak

# Clone configuration
git clone https://github.com/iamcheyan/kitty.git ~/.config/kitty
```

---

## Documentation

Full architectural deep-dives, cheat sheets, and design rationales are available in [`docs/`](docs/):

- [`docs/cheatsheet.txt`](docs/cheatsheet.txt): Full keybindings reference (press `Ctrl+p ?` inside Kitty).
- [`docs/keybindings-design.md`](docs/keybindings-design.md): Why `Ctrl+P`? Complete 26-letter `Ctrl+[A-Z]` conflict analysis.
- [`docs/tab-title.md`](docs/tab-title.md): 100% full-width equal-distribution tab bar & SSH detection logic.
- [`docs/session-restore.md`](docs/session-restore.md): Official Kitty 0.48+ session persistence watcher.
- [`docs/search-kitten.md`](docs/search-kitten.md): Scrollback regex search kitten.

---

## License

MIT / Public Domain
