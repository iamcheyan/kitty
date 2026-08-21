# Kitty 会话自动保存与恢复

退出 Kitty 后再打开，应还原当时的 **OS 窗口、标签页、布局、工作目录、tmux attach**。本机用 Kitty 0.48 官方 `save_as_session` + 全局 watcher，不手写 session 文本。

源文件：`~/chezmoi/dot_config/kitty/session_watcher.py`  
部署：`~/.config/kitty/session_watcher.py`  
会话快照：`~/.config/kitty/last_session.kitty`（运行时生成，**不进 git**）  
日志：`/tmp/kitty-session-watcher.log`

## 原理

Kitty 的 session 是一份启动脚本，不是「把终端屏幕截下来」。进程退出后 PTY 里的滚动缓冲、未提交输入都会丢；能留下来的只有「下次用什么命令、在哪个目录、几个 tab、什么 layout 再拉起来」。

官方 session 关键字（完整列表见 [Sessions](https://sw.kovidgoyal.net/kitty/sessions/)）：

| 关键字 | 作用 |
|---|---|
| `new_tab` | 新建标签；第一个 tab 也由官方序列化器写出 |
| `layout` / `enabled_layouts` / `set_layout_state` | 窗格布局及内部比例 |
| `cd` | 后续 `launch` 的工作目录 |
| `launch ...` | 在该 tab 里启动进程（tmux / shell / 上次前台命令） |
| `focus` / `focus_tab` | 焦点落在哪个窗格 / 哪个 tab |

`startup_session last_session.kitty` 只在 **Kitty 进程冷启动** 时读一次。macOS 点红点关掉最后一个窗口但 Dock 里进程还活着时，再点图标是「新建窗口」，不会再跑 `startup_session`。要整份回来，必须 **Cmd+Q 退出进程** 再开。

0.48 起自带 `save_as_session`：在进程内部把当前所有 OS 窗口 / tab / pane 写成合法 session 文件，标题带空格、splits 比例、ssh kitten、shell integration 记下的前台命令都由官方处理。

## 实现

### 配置（`kitty.conf.tmpl`）

```text
allow_remote_control yes
listen_on unix:/tmp/mykitty

watcher session_watcher.py
startup_session last_session.kitty
```

- `watcher`：Kitty 启动时把 `session_watcher.py` 当 **全局 watcher** import 进主进程（和 `launch --watcher` 的单窗 watcher 不同；`on_tab_bar_dirty` / `on_quit` 只在全局 watcher 里触发）。
- `listen_on unix:/tmp/mykitty`：实际 socket 是 `/tmp/mykitty-<pid>`。
- `last_session.kitty` 相对 kitty 配置目录，即 `~/.config/kitty/last_session.kitty`。

`watcher` / `startup_session` / `listen_on` 都是启动期配置，改完必须 **完全退出再开**。

### 保存路径

```
tab 增删改 / 标题变     → on_tab_bar_dirty  → 防抖 2s → save_as_session
Cmd+Q / 进程退出        → on_quit（只写一次）→ 强制     → save_as_session
下次冷启动              → startup_session 读 last_session.kitty
```

进程内调用必须走 `boss.call_remote_control`，等价于：

```text
save_as_session --save-only --use-foreground-process ~/.config/kitty/last_session.kitty
```

- `--save-only`：只写文件，不弹编辑器。
- `--use-foreground-process`：窗口里是默认 shell、但前台正在跑别的命令时，把那条命令一并写进 session（依赖 [shell integration](https://sw.kovidgoyal.net/kitty/shell-integration/)）。tmux 直接 `launch` 的窗口则写成 `tmux new-session -A -s <name>`。

手动补救（Kitty 已在跑时）：

```sh
python3 ~/.config/kitty/session_watcher.py
```

独立进程走 `kitty @ --to <socket> action save_as_session ...`。`KITTY_LISTEN_ON` 指向的 socket 若不存在，回退扫 `/tmp/mykitty-*` 里最新的那个。

### 为何必须用官方 action，不能自己拼 session

第一版自己 `kitty @ ls` + `ps`/`lsof` 拼文本，踩过三次坑：

1. **进程内 `kitty @ ls` 会死锁 / 超时**  
   watcher 跑在同一个 Kitty 里。主线程（或等主线程处理 RC 的后台线程）再 `subprocess` 连自己的 listen socket，请求排不上，1s 超时被 `except` 吃掉。结果 `last_session.kitty` 一直是空文件。空 `startup_session` = 只开一个默认 tab。

2. **`on_close` 拆除竞态**  
   Cmd+Q 时窗口是逐个拆的。每关一个就存一次，文件被写成 N-1、N-2… 最后只剩 1 个 tab。  
   现改成 `on_quit`：官方保证在确认退出、**窗口还在**时先调一次。脚本用 `_quit_saved` 保证只写这一次。

3. **手写 `new_tab` 标题带空格**  
   tab 标题经常是 `tmux new-session -A -s test`。写成 `new_tab tmux new-session -A -s test` 会被拆坏。官方序列化器写的是单独一行 `new_tab`，标题放在 `launch --title=...`。

4. **同步 `ps`/`lsof` 卡 UI**  
   旧版把扫描放在 `on_focus_change` 主线程，点 tab 卡 100–500ms。现在保存是进程内 action，且 `on_tab_bar_dirty` 有 2s 防抖；点 tab 不再跑外部进程。

### 官方写出的文件长什么样

当前这台机器上两 tab（`tmux -s main` + 在 zsh 里跑过 `tmux -s test`）的快照形态：

```text
new_tab
layout fat
enabled_layouts ...
set_layout_state {...}
cd /Users/tetsuya
launch 'kitty-unserialize-data={"id": 1}' '--title=tmux new-session -A -s main' \
    /opt/homebrew/bin/tmux new-session -A -s main
focus

new_tab
...
launch 'kitty-unserialize-data={"id": 2, "cmd_at_shell_startup": ["tmux", "new-session", "-A", "-s", "test"]}'
focus

focus_tab 1
```

`kitty-unserialize-data=...` 和 `set_layout_state` 是官方内部字段，不要手改。

## 影响

| 会恢复 | 不会恢复 |
|---|---|
| 所有 OS 窗口、tab、pane 数量 | 屏幕内容、滚动历史、未提交输入 |
| 每个 pane 的 cwd | 未走 shell integration 的「shell 里临时敲的命令」（除非 `--use-foreground-process` 抓到） |
| 直接 `launch` 的 tmux：`tmux new-session -A -s <name>` | tmux **窗格内部**布局（那是 tmux 自己的 session，由 tmux 恢复） |
| shell 里跑过的 tmux / 编辑器等（需 shell integration） | 已退出的一次性命令 |
| 焦点 tab（`focus_tab`） | 剪贴板、IME 状态 |

副作用：

- `--use-foreground-process` 会把当时前台命令再跑一遍。正在 `rm`/`mv` 时退出，下次启动可能重跑。不要在危险命令执行中途 Cmd+Q 当「保存」。
- `last_session.kitty` 是本机运行时文件。`chezmoi apply` 默认不管它（源目录不跟踪）。不要把它加成 `empty_` 占位——`apply --force` 会把正在用的快照覆盖成空文件。
- 日志在 `/tmp`，重启机器会清掉。
- 全局 watcher 随 Kitty 进程加载；脚本语法错误会打到 Kitty stderr，session 功能静默失效。改完脚本必须重启 Kitty。

## 优点

- 序列化交给官方，多 tab / 带空格标题 / splits / ssh kitten 不用自己维护解析器。
- `on_quit` 在拆除前落盘，不再出现「只回来最后一个 tab」。
- 进程内 `call_remote_control`，不阻塞 UI，也不依赖 `/tmp/mykitty-*` 在 watcher 里可达。
- 实现短（约 100 行），和 OMD `sumika-session` 的「合成 launch 行」解耦；macOS 上不必移植 `/proc`。
- 冷启动一条 `startup_session`，没有额外 restore 守护进程。

## 缺点

- **只覆盖冷启动**。点红点关窗口、进程还在，再开是空窗口，不会读 session。
- 依赖 Kitty ≥ 0.48 的 `save_as_session` / `on_quit` / `on_tab_bar_dirty`。旧版没有这些钩子。
- `--use-foreground-process` 有重跑前台命令的风险；关掉则 shell 里后起的 tmux/vim 不会写进 session。
- 崩溃 / `kill -9` 来不及走 `on_quit`。最多靠上一次 `on_tab_bar_dirty`（可能旧 2s，且若从未改过 tab 则可能根本没写过）。
- 不保存滚动缓冲；这是终端 session 模型的上限，不是漏实现。
- Linux 上若改用 sumika-shell 的会话栈，不要和这份 watcher 各写一份 `last_session.kitty`。

## 诊断

```sh
# watcher 是否加载、是否写出
cat /tmp/kitty-session-watcher.log

# 当前快照里有几个 tab
grep -c '^new_tab' ~/.config/kitty/last_session.kitty
cat ~/.config/kitty/last_session.kitty

# 手动刷一次（要在有活着的 Kitty 时）
python3 ~/.config/kitty/session_watcher.py
```

| 现象 | 原因 |
|---|---|
| 日志没有 `watcher loaded` | 没重启 Kitty，或脚本 import 失败（看启动 Kitty 的终端 stderr） |
| 文件是 0 字节 / 没有 `new_tab` | 旧 watcher 的空文件残留；手动跑一次脚本，或开着多 tab 等 `on_tab_bar_dirty` |
| 重启只有 1 个 tab，文件里其实有多个 `new_tab` | 改过 `startup_session` 没冷启动；或读的不是这份文件 |
| 点红点再开是空的 | 进程没退出，`startup_session` 不会跑 → Cmd+Q |
| 第二个 tab 是空 shell，没进 tmux | 那个 tab 当时只是 zsh、且没开 shell integration，或保存时前台已经不在 tmux |

---
本文件由 chezmoi 管理，源在 `~/chezmoi/dot_config/kitty/docs/session-restore.md`。
