# Kitty 终端配置总览与后续方向

本仓库用 chezmoi 管理 Kitty 配置。源目录 `~/chezmoi/dot_config/kitty/`，部署到 `~/.config/kitty/`。

## 已实现的特性

### 1. 会话自动保存与恢复

**文件**：`session_watcher.py`、`kitty.conf.tmpl` 里的 `watcher` + `startup_session`

退出 Kitty 再打开，恢复所有 OS 窗口、标签页、布局、工作目录、tmux attach。用 Kitty 0.48 官方 `save_as_session` action，在 `on_tab_bar_dirty`（标签变动）和 `on_quit`（退出前）各存一次。详见 [session-restore.md](session-restore.md)。

### 2. 智能粘贴（图片→路径）

**文件**：`executable_kitty-smart-paste`

`ctrl+shift+v` 时如果剪贴板有图片，存成 `/tmp/ksp-clip-*.png` 并把路径注入终端；有文本则调原生 `paste_from_clipboard`。SSH 会话下图片自动传到远端再贴远端路径。详见 [smart-paste-setup.md](smart-paste-setup.md)。

**键位原则**：系统粘贴（macOS `cmd+v`）不干涉，`ctrl+v` 留给 vim 等程序，只有 `ctrl+shift+v` 走脚本。

### 3. Tmux 风格键绑定与前缀键设计

`ctrl+p` 前缀 + 单键，和 tmux 操作一致。为什么选用 `ctrl+p`（而非 `ctrl+k` 或 `ctrl+b`）、终端全字母 `Ctrl+[A-Z]` 冲突排查详见 [keybindings-design.md](keybindings-design.md)。

| 操作 | 键 |
|---|---|
| 左右分屏 | `ctrl+p` `%` |
| 上下分屏 | `ctrl+p` `"` |
| 切换窗格 | `ctrl+p` `o` / 方向键 |
| 放大窗格 | `ctrl+p` `z` |
| 新建标签 | `ctrl+p` `c` |
| 切换标签 | `ctrl+p` `n` / `p` / `0-9` |
| 关闭标签 | `ctrl+p` `&` |
| 重命名标签 | `ctrl+p` `,` |

### 4. 搜索 Kitten
**文件**：`search.py`（来自 [trygveaa/kitty-kitten-search](https://github.com/trygveaa/kitty-kitten-search)，GPLv3）

在终端 scrollback 里正则搜索。已绑定 `ctrl+p` `s`。详见 [search-kitten.md](search-kitten.md)。

### 5. 滚动标记

**文件**：`scroll_mark.py`

在 scrollback 里跳到上一个/下一个标记位置。已绑定 `ctrl+p` `j` / `k`（no_ui remote-control kitten，用 `launch --type=background kitten scroll_mark.py next/prev` 调用）。

### 6. Hints Kitten（屏幕选词）

**文件**：`kitty.conf.tmpl` 里的 `map ctrl+p>u/f/y`

屏幕上标注 URL / 路径 / 行号，按字母键选中执行。`ctrl+p` `u` = URL，`f` = 文件（nvim 打开），`y` = 复制行。详见 [hints-kitten.md](hints-kitten.md)。

### 7. 字体回退链（暂不启用）

曾尝试用 `symbol_map` 将 CJK/Emoji 映射到 `Hiragino Sans GB` / `Apple Color Emoji`，但在当前 Kitty/zsh 环境中出现字符显示和光标形状异常，已回滚。当前保持 `Adwaita Mono` 主字体稳定；详见 [font-fallback.md](font-fallback.md)。

### 8. `kitten ssh` 别名

**文件**：`~/chezmoi/dot_config/aliases.conf` 里的 `alias kssh='kitten ssh'`

带 shell integration / terminfo / 文件传输的 SSH，不全局替换 `ssh`。详见 [kitten-ssh.md](kitten-ssh.md)。

### 9. 标签页标题与 SSH 高亮

`tab_bar_style custom` 配合 `tab_bar.py`，采用现代**矩形色块（Rectangular Blocks）**风格（去除了三角切角符号），并自动识别 SSH 进程高亮显示标签背景（激活 `#ff5500` 亮橙红，未激活 `#64200a` 深琥珀）。详见 [tab-title.md](tab-title.md)。

### 10. 其他配置

- **字体**：Adwaita Mono 12pt，行高 100%
- **配色**：Dracula 16 色 + `current-theme.conf`（3024 Night）
- **Tab Bar**：`tab_bar_style custom`（`tab_bar.py` 实现现代矩形色块 + SSH 智能高亮）
- **窗口**：`confirm_os_window_close 0`（直接关闭不确认）、`window_padding_width 5`
- **全屏/最大化/最小化**：`F11` / `ctrl+shift+m` / `ctrl+shift+i`
- **窗口缩放**：`ctrl+shift+方向键`
- **复制**：`copy_on_select yes`（选中即复制），`ctrl+c` = 复制，`ctrl+shift+c` = 发 SIGINT

## Kitty 的能力

Kitty 不只是终端模拟器，它有这些大部分终端没有的内置能力：

| 能力 | 说明 | 本仓库用到 |
|---|---|---|
| **Remote control** | 通过 Unix socket 控制 Kitty（`kitty @`），读写窗口、标签、剪贴板 | 智能粘贴、会话保存 |
| **Python watcher** | 在 Kitty 进程内加载 Python 模块，监听 `on_focus_change` / `on_close` / `on_quit` / `on_tab_bar_dirty` 等事件 | 会话保存恢复 |
| **Session 文件** | 纯文本脚本，定义 tabs / windows / layout / commands，冷启动自动加载 | 会话恢复 |
| **`save_as_session`** | 0.48+ 内置 action，把当前所有窗口/标签序列化成 session 文件 | 会话保存 |
| **Kittens** | Kitty 内置小程序：`hints`（屏幕选词）、`ssh`（带配置同步的 SSH）、`icat`（显示图片）、`clipboard`、`themes` 等 | hints、ssh(kssh) |
| **Splits layout** | 原生分屏，不用 tmux 也能多窗格 | tmux 风格键绑定 |
| **Shell integration** | 跟 shell 配合，记下每条命令的 cwd / 退出码 / 运行时间 | `save_as_session --use-foreground-process` 依赖它 |
| **Bracketed paste** | 标记粘贴内容的边界，程序能区分「粘贴」和「手打」 | 智能粘贴 |
| **Hints kitten** | 屏幕上标注 URL / 路径 / 行号，按字母键选中并执行 | `ctrl+p>u/f/y` 已启用 |
| **Remote file transfer** | `kitten ssh` 连接后可双向传文件（drag-drop / `kitten remote_file`） | `kssh` 别名 |
| **Unicode input** | `ctrl+shift+u` 输入任意 Unicode 字符 | 默认启用 |

---

## 后续可以做的

> 短期的 5 项（Hints Kitten、搜索/滚动标记绑定、字体回退链、`kitten ssh` 别名、标签标题模板）已全部实现，见上方「已实现的特性」第 4–9 节。下面是仍未做的中期/长期项。

---

### 中期

#### 1. 远程会话自动恢复

**是什么**：Kitty 会话恢复只恢复本机的 tab/pane/cwd/SSH 启动命令。远端的 tmux session、编辑器状态需要远端自己恢复。比较可靠的做法是让 Kitty session 里保存 `ssh host → tmux new-session -A -s main`，重启后自动重连并 attach。

**收益**：Kitty 重启后自动重新登录服务器并回到远端 tmux；本地和远端开发环境一起恢复。

**代价**：网络不可用时拖慢启动；SSH 密钥/跳板机/密码代理必须正常；远端 tmux session 可能已被其他地方占用。最推荐远端 tmux，而不是让 Kitty 自己保存远程终端细节。

#### 2. 剪贴板历史 kitten

**是什么**：保存最近复制过的文本、图片、路径、命令输出，通过 Kitty 内的交互界面选择历史内容粘贴。

**收益**：找回被覆盖的文本；语音输入覆盖剪贴板后仍可恢复之前内容；多次复制粘贴工作流更方便。

**注意**：Kitty 自带 `clipboard` kitten 不等于完整剪贴板历史管理器。完整历史通常需要系统级工具（macOS Maccy/Raycast，Linux `cliphist`）或自己写 kitten。

**代价**：剪贴板内容可能含敏感信息；需要设置保存数量和过期时间；图片历史占磁盘。建议默认只保存最近 50-100 条文本，敏感命令不保存，历史文件放用户私有目录，不同步进 Git。

---

### 长期

#### 3. 统一 Linux/macOS 智能粘贴脚本

**是什么**：现在 macOS 用 `kitty-smart-paste`，Linux 用 `sumika-kitty-smart-paste`，两边功能思路相同但实现不同。统一后两边都有 socket 验活、单飞锁、last-image 复用、文本原生粘贴等改进。

**收益**：不同机器行为一致；修一次 bug 两边同时受益；文档统一；换机更简单。

**代价**：Linux Wayland/X11 和 macOS 剪贴板接口不同（`wl-paste`/`xclip`/`pngpaste`）；统一脚本会增加条件分支和测试成本。适合等 macOS 版本稳定后再做。

#### 4. GPU 渲染调优

**是什么**：Kitty 用 GPU 绘制终端。当前 `repaint_delay 10`（约 100fps 上限）、`input_delay 0`（最低输入延迟）。

**收益**：降低终端输入延迟；大量日志输出更平滑；TUI 动画更流畅。

**代价**：更高 CPU/GPU 使用率；更耗电；高刷新率对普通 shell 没明显收益。当前配置已偏向低延迟，除非出现大量日志滚动卡顿或 GPU 占用异常，不建议继续调。

#### 5. 运行时主题切换

**是什么**：不用编辑配置和重启 Kitty，直接切换颜色主题。

```sh
kitten themes                          # 交互选主题
kitty @ set-colors --all current-theme.conf  # remote control
```

**收益**：深色/浅色快速切换；适配白天和夜间工作；会议演示时快速切换配色；可配合 macOS 外观自动切换。

**代价**：主题切换可能影响当前终端视觉状态；有些程序自己的颜色不会跟着变；运行时修改通常不会自动写回配置文件。

---

## 建议实施顺序

短期 5 项（Hints / 搜索 / 滚动标记 / 字体回退 / `kitten ssh` / 标签标题）已全部完成。

### 第三优先级（仍未做）

1. 剪贴板历史
2. 远程 tmux 自动恢复
3. 运行时主题切换

### 暂时不急

4. 统一 Linux/macOS 智能粘贴（等 macOS 版本稳定后再做）
5. GPU 调优（当前已偏向低延迟，除非出现明显卡顿）

---

本文件由 chezmoi 管理，源在 `~/chezmoi/dot_config/kitty/docs/kitty-overview.md`。