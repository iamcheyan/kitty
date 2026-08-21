# Search Kitten — 在 scrollback 里搜索

在终端 scrollback 历史里正则搜索，可以在匹配项之间跳转。适合翻几百屏日志找错误。

**来源**：[`search.py`](https://github.com/trygveaa/kitty-kitten-search)（GPLv3 第三方 kitten），已放进 `~/chezmoi/dot_config/kitty/search.py`，部署到 `~/.config/kitty/search.py`。

## 本仓库绑定

| 键 | 作用 | 命令 |
|---|---|---|
| `ctrl+p` `s` | 终端正则搜索 | `search-launcher.sh`（直接启动 Kitty 原生 search kitten） |

`s` = search。沿用 `ctrl+p` 前缀风格，不与已有绑定冲突。

## 搜索入口（search-launcher.sh）

`~/.config/kitty/search-launcher.sh` 是搜索的统一入口：

无论前台运行的是普通 Shell 还是 Tmux/Zellij，均统一调用 Kitty 原生的 `search.py` Kitten（底部 2 行 hsplit 浮层），在当前窗口的整个终端 scrollback 历史中进行正则搜索与跳转（原 tmux copy-mode 切换分支已注释停用）。
### kitty 原生搜索流程

```
按 Ctrl+P S
  → search-launcher.sh 检测：非 tmux
  → 保存当前 tab 的 layout（如 fat）
  → goto-layout splits
  → launch --location=hsplit search kitten
  → resize-window 自动收缩到 2 行（有充足内边距，内容清晰可见）
  → 用户输入搜索 → 高亮匹配 → 跳转
  → 按 Esc 退出
  → 检测到 search 窗口关闭
  → goto-layout 还原为原始 layout
```

## 怎么用

### kitty 原生模式

1. 按 `ctrl+p` 松开，再按 `s`，底部弹出 2 行搜索输入框。
2. 输入普通文本或正则表达式，匹配项实时高亮。
3. `up` / `f3` 跳到上一个匹配，`down` / `shift+f3` 跳到下一个。
4. `enter` 退出搜索并保持当前滚动位置；`esc` 退出搜索。
5. `tab` 切换 text / regex 模式。

### tmux 模式

1. 按 `ctrl+p` 松开，再按 `s`，直接进入 tmux copy-mode 搜索提示符。
2. 输入搜索词，`n` 下一个，`N` 上一个。
3. `q` 退出 copy-mode。

## 配置位置

`kitty.conf.tmpl` 里 `# ===== Hints / Search / Scroll Marks =====` 一节：

```text
map ctrl+p>s launch --type=background bash $HOME/.config/kitty/search-launcher.sh
```

`search-launcher.sh` 由 chezmoi 管理（源：`executable_search-launcher.sh`），部署到 `~/.config/kitty/search-launcher.sh`（0755）。

`search.py` 依赖 `--allow-remote-control` 才能向 Kitty 发送 `create-marker` 等远程控制指令高亮匹配项。launcher 脚本在 `kitty @ launch` 时自动传入。
- **搜索栏高度**：默认收缩至 2 行高，兼顾视野与输入/提示信息清晰度。
## 排障

- **搜索栏不是 1 行**：`resize-window` 依赖 `splits` 布局。launcher 会自动临时切换到 `splits`，退出后还原。如果手动改了布局可能导致还原失败。
- **tmux 下按 Ctrl+P S 没反应**：确认 `kitty @ send-text` 可用（`allow_remote_control yes`），且 tmux prefix 是默认的 `Ctrl+B`。
- **搜索框不出现**：可能 Kitty 版本太旧，search.py 依赖的 `kittens.tui` API 变了。升级 Kitty 后重新 `chezmoi apply`。
- **`__file__` not defined**：Kitty 0.48+ 的 kitten runner 不设置 `__file__`，search.py 已用 `try/except` 回退到 `kitty.config` 目录。
- **正则不匹配**：search.py 用 Python `re` 语法，不是 PCRE。比如 `\d` 可用，`(?P<name>...)` 可用，但部分 PCRE 特性不支持。
- **复杂正则慢**：大 scrollback + 复杂正则可能卡顿，先用普通文本定位再细化。

## 局限

- 第三方 kitten，需随 Kitty Python API 变化维护。
- 复杂正则可能比普通文本慢。
- tmux 环境下使用 tmux 原生搜索，不使用 kitty search kitten（架构不兼容：kitty scrollback 无法访问 tmux 内部缓冲区）。
- `search-launcher.sh` 的 layout 还原依赖 `kitty @ goto-layout`，如果手动改变了 tab 布局可能导致还原到错误状态。

---
本文件由 chezmoi 管理，源在 `~/chezmoi/dot_config/kitty/docs/search-kitten.md`。