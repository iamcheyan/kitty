# Kitty 会话自动保存与恢复

退出 Kitty 后再打开，应还原当时的 **OS 窗口、标签页、布局、工作目录、tmux attach**。本机用 Kitty 0.48 官方 `save_as_session` + 全局 watcher，不手写 session 文本。

源文件：`~/chezmoi/dot_config/kitty/session_watcher.py`  
部署：`~/.config/kitty/session_watcher.py`  
会话快照：`~/.config/kitty/sessions/kitty-<pid>.kitty`（每进程独立保存）  
统一快照：`~/.config/kitty/last_session.kitty`（冷启动合并生成，**不进 git**）  
日志：`/tmp/kitty-session-watcher.log`

## 设计契约（先明确期望行为）

这里的“Kitty 会话”是一个独立 Kitty **进程**内的全部 OS 窗口、tab 和 pane。系统允许同时存在多个独立 Kitty 进程，每个进程拥有自己的快照。

必须满足以下三种行为：

| 启动前状态 | 用户动作 | 期望结果 |
|---|---|---|
| 没有 Kitty 进程，也没有历史快照 | 打开默认终端 | 启动一个全新的 Kitty 进程 |
| 已有至少一个 Kitty 进程 | 再次打开默认终端 | 启动一个全新的 Kitty 进程/窗口，使用 `--session none`，绝不重放历史快照 |
| 所有 Kitty 进程均已退出，存在一个或多个独立快照 | 再次打开默认终端 | 合并全部快照，在一个新的 Kitty 进程中恢复全部 tab/pane |

例如先后打开两个独立 Kitty 进程：

```text
进程 A（PID 100）: tab A1 + tab A2
进程 B（PID 200）: tab B1
```

运行期间分别保存：

```text
sessions/kitty-100.kitty
sessions/kitty-200.kitty
```

当 A、B 全部退出后，下一次冷启动应执行：

```text
kitty-launch
  ├─ 确认当前没有 kitty 进程
  ├─ session_merge.py --prepare
  ├─ 合并为 last_session.kitty（A1 + A2 + B1）
  ├─ kitty --session last_session.kitty
  └─ 新进程确认可远控后，删除已消费的独立快照
```

“最后一个窗口退出时”只要求最后一次保存各进程自己的快照；**合并发生在下一次冷启动前**，而不是退出回调里。这样异常退出或启动失败时，原始快照仍可恢复。

## 启动入口契约

会话恢复是否工作，取决于所有“默认终端”入口是否经过 `kitty-launch`。仅配置 `watcher` 和 `startup_session` 不够。

Omarchy/Wayland 的标准链路应为：

```text
$TERMINAL=xdg-terminal-exec
  → ~/.config/xdg-terminals.list 选择 kitty.desktop
  → 用户级 ~/.local/share/applications/kitty.desktop
  → Exec=kitty-launch
  → ~/.local/bin/kitty-launch
```

不能直接落到系统 desktop entry：

```text
/usr/share/applications/kitty.desktop
Exec=kitty
```

直接执行 `kitty` 会绕过进程检测和 `session_merge.py`，因此只能得到新会话。`kitty-launch` 是恢复协议的一部分，不只是一个可选启动脚本。

用户级 `kitty.desktop` 需要保留标准 ID，并把启动命令覆盖为：

```ini
[Desktop Entry]
Type=Application
Name=kitty
TryExec=kitty-launch
Exec=kitty-launch
Icon=kitty
Categories=System;TerminalEmulator;
X-TerminalArgExec=--
X-TerminalArgTitle=--title
X-TerminalArgAppId=--class
X-TerminalArgDir=--working-directory
X-TerminalArgHold=--hold
```

包装脚本会原样转发 `xdg-terminal-exec` 传入的 `--title`、`--working-directory`、`--hold` 和命令参数。

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

`startup_session last_session.kitty` 负责 Kitty 冷启动时恢复会话；`kitty-launch` 负责启动前判断是否已有 Kitty 进程。已有进程时传入 `--session none`，因此新窗口不会再次执行快照。

Linux/Wayland 的默认终端入口必须通过用户级 `kitty.desktop` 调用 chezmoi 部署的 `kitty-launch`：没有 Kitty 进程时显式使用 `kitty --session ~/.config/kitty/last_session.kitty` 恢复快照；已有 Kitty 进程时使用 `kitty --session none`，创建一个全新的实例，不重复打开旧快照。密码修改和系统更新等一次性终端同样应显式使用 `--session none`。

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
- 每个进程写入 `sessions/kitty-<pid>.kitty`；`kitty-launch` 冷启动时由 `session_merge.py` 合并到 `last_session.kitty`。

`watcher` / `startup_session` / `listen_on` 都是启动期配置，改完必须 **完全退出再开**；新窗口入口必须使用 `kitty-launch`。

### 保存路径

```
tab 增删改 / 标题变     → on_tab_bar_dirty  → 防抖 2s → 保存到 sessions/kitty-<pid>.kitty
Cmd+Q / 进程退出        → on_quit（只写一次）→ 强制     → 保存独立快照
下次冷启动              → kitty-launch 合并所有独立快照 → startup_session
```

各阶段的所有权：

| 文件 | 写入者 | 删除者 | 生命周期 |
|---|---|---|---|
| `sessions/kitty-<pid>.kitty` | 对应 PID 的 watcher | `session_merge.py --cleanup` | 从进程运行期间保留到下一次成功恢复 |
| `sessions/.restore-manifest` | `session_merge.py --prepare` | `session_merge.py --cleanup` | 记录本次合并消费了哪些独立快照 |
| `sessions/.restore-pid` | `kitty-launch` | `session_merge.py --cleanup` | 记录本次重放进程；用于识别清理中断后遗留的旧世代 |
| `last_session.kitty` | `session_merge.py --prepare` | 不主动删除；下次合并原子覆盖 | 冷启动使用的统一快照 |
| `/tmp/kitty-session-watcher.log` | watcher | 系统清理 `/tmp` | 仅用于诊断 |

安全约束：

- watcher 只写自己 PID 对应的独立快照，多个进程不能竞争写同一个文件。
- 合并器只在确认当前没有 Kitty 进程的冷启动入口运行。
- 合并时去掉 `new_os_window`，把多个进程的 tab/pane 扁平化到同一个新进程。
- 新 Kitty 的 remote-control socket 可用之后才清理源快照。
- 启动失败、脚本报错或 socket 未就绪时，不删除任何源快照。
- 若异步清理被中断，但 `.restore-pid` 对应进程已经写出非空快照，下次合并前会先删除 manifest 中的旧世代；不会把恢复前后的同一批 tab 再合并一次。
- 去重依据是恢复世代，不是 cwd、标题或命令；两个刻意打开且内容相同的 tab 都会保留。

进程内调用必须走 `boss.call_remote_control`，等价于：

```text
save_as_session --save-only --use-foreground-process ~/.config/kitty/sessions/kitty-<pid>.kitty
```

- `--save-only`：只写文件，不弹编辑器。
- `--use-foreground-process`：窗口里是默认 shell、但前台正在跑别的命令时，把那条命令一并写进 session（依赖 [shell integration](https://sw.kovidgoyal.net/kitty/shell-integration/)）。tmux 直接 `launch` 的窗口则写成 `tmux new-session -A -s <name>`。

保存完成后，watcher 还会把 shell integration 记录的精确命令 `codex` 改为 `codex resume --last`。这样直接运行在 Kitty pane 里的 Codex 会恢复当前项目最近的 Codex 会话；已经带有参数的 Codex 命令和 tmux pane 不会被改写。

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
- `sessions/` 和 `last_session.kitty` 都是本机运行时文件。合并成功并确认新 Kitty 的 remote-control socket 可用后，`kitty-launch` 才清理本次已消费的独立快照；启动失败时会保留它们。
- 日志在 `/tmp`，重启机器会清掉。
- 全局 watcher 随 Kitty 进程加载；脚本语法错误会打到 Kitty stderr，session 功能静默失效。改完脚本必须重启 Kitty。

## 优点

- 序列化交给官方，多 tab / 带空格标题 / splits / ssh kitten 不用自己维护解析器。
- `on_quit` 在拆除前落盘，不再出现「只回来最后一个 tab」。
- 进程内 `call_remote_control`，不阻塞 UI，也不依赖 `/tmp/mykitty-*` 在 watcher 里可达。
- 实现短（约 100 行），和 OMD `sumika-session` 的「合成 launch 行」解耦；macOS 上不必移植 `/proc`。
- 多个独立 Kitty 进程的快照会在冷启动时合并成一个 Kitty 进程；旧快照确认恢复成功后清理。

## 缺点

- **只覆盖冷启动**。已有 Kitty 进程时，`kitty-launch` 使用 `--session none` 打开空窗口；只有没有 Kitty 进程时才合并并恢复。
- 依赖 Kitty ≥ 0.48 的 `save_as_session` / `on_quit` / `on_tab_bar_dirty`。旧版没有这些钩子。
- `--use-foreground-process` 有重跑前台命令的风险；关掉则 shell 里后起的 tmux/vim 不会写进 session。
- 崩溃 / `kill -9` 来不及走 `on_quit`。最多靠上一次 `on_tab_bar_dirty`（可能旧 2s，且若从未改过 tab 则可能根本没写过）。
- 不保存滚动缓冲；这是终端 session 模型的上限，不是漏实现。
- Linux 上若改用 sumika-shell 的会话栈，不要和这份 watcher 各写一份 `last_session.kitty`。

## 诊断

```sh
# watcher 是否加载、是否写出
cat /tmp/kitty-session-watcher.log

# 当前统一快照里有几个 tab
grep -c '^new_tab' ~/.config/kitty/last_session.kitty
cat ~/.config/kitty/last_session.kitty

# 手动刷一次（要在有活着的 Kitty 时）
python3 ~/.config/kitty/session_watcher.py

# 默认终端当前实际会执行什么
xdg-terminal-exec --print-id --print-path --print-cmd

# 哪些快照属于活着/已退出的进程
for file in ~/.config/kitty/sessions/kitty-*.kitty; do
  pid=${file##*/kitty-}; pid=${pid%.kitty}
  kill -0 "$pid" 2>/dev/null && state=alive || state=dead
  printf '%s %s %s\n' "$pid" "$state" "$file"
done
```

| 现象 | 原因 |
|---|---|
| 日志没有 `watcher loaded` | 没重启 Kitty，或脚本 import 失败（看启动 Kitty 的终端 stderr） |
| 文件是 0 字节 / 没有 `new_tab` | 旧 watcher 的空文件残留；手动跑一次 watcher，或开着多 tab 等 `on_tab_bar_dirty` |
| 重启只有 1 个 tab，文件里其实有多个 `new_tab` | 改过 `startup_session` 没冷启动；或读的不是这份文件 |
| 当前已有 Kitty，再从启动器打开却恢复旧快照 | 启动入口没有使用 `kitty-launch` 或 `--session none` |
| 点红点再开是空的 | 进程没退出，`startup_session` 不会跑 → 完全退出 Kitty |
| Codex 窗口回来但进入新会话 | 快照保存前未部署新版 watcher；手动运行 `python3 ~/.config/kitty/session_watcher.py` |
| 第二个 tab 是空 shell，没进 tmux | 那个 tab 当时只是 zsh、且没开 shell integration，或保存时前台已经不在 tmux |

## 2026-08-24 修复与验证记录

当日审计发现恢复链路因缺少用户级 desktop entry 而失效后，已实施修复：

- 新增 `dot_local/share/applications/kitty.desktop`（chezmoi 管理），`Exec=kitty-launch`，
  内容即上文「启动入口契约」一节。`chezmoi apply` 部署到
  `~/.local/share/applications/kitty.desktop` 后自动覆盖系统 entry。

验证结果（全部通过）：

```text
xdg-terminal-exec --print-id   → kitty.desktop
xdg-terminal-exec --print-path → ~/.local/share/applications/kitty.desktop
xdg-terminal-exec --print-cmd  → kitty-launch
```

1. **热路径**：已有 Kitty 进程时经默认终端入口开新窗口 → 新独立进程带
   `--session none`，无快照重放，`last_session.kitty` 未生成。线上实测：用户正常
   打开终端得到 `kitty --session none --working-directory ...`。
2. **冷启动全链路**（HOME 沙箱 + 假 `pgrep` 复现零进程状态，真实快照不受影响）：
   8 个独立快照合并为含 10 个 `new_tab` 的 `last_session.kitty`；恢复出
   1 个 OS 窗口、10 个 tab；socket 应答后源快照与 manifest 全部清理。
3. **on_quit**：显式退出（quit action）触发 `on_quit save` 并强制落盘；
   被动关窗（直接关最后一个 OS 窗口）不触发，但依赖 `on_tab_bar_dirty`
   的周期性保存兜底（实测死前 3 秒有完整快照），符合设计模型。

已知语义（非缺陷）：`--use-foreground-process` 抓到的前台命令会原样重跑，
一次性命令（init 脚本、screensaver 等）的 pane 在恢复后跑完即关。

---
本文件由 chezmoi 管理，源在 `~/chezmoi/dot_config/kitty/docs/session-restore.md`。
