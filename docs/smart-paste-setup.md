# Smart Paste (kitty-smart-paste) — 按键定义与排障

剪贴板有图片时贴文件路径，有文本时贴文本。SSH 会话下图片传到远端再贴远端路径。

## 按键怎么定义

Kitty **不会**把系统的 Cmd/Ctrl+V 自动变成智能粘贴。只有 `kitty.conf` 里 `map` 到脚本的键会走 `kitty-smart-paste`；没 map 的键走 Kitty 内置 `paste_from_clipboard`，剪贴板里是什么就原样打什么。

**`cmd+v` 故意不绑脚本。** 语音输入法（Sasayaki）模拟 `cmd+v` 来自动粘贴，系统复制粘贴也走 `cmd+v`。一旦绑到脚本，这些全坏。图片在剪贴板时 `cmd+v` 本来就贴不出东西（终端不能渲染位图），用 `ctrl+shift+v` 贴路径。

### 本仓库实际绑定

| 平台 | 智能粘贴（图片→路径 / 文本） | 系统普通粘贴 | `ctrl+v` | 脚本 |
|---|---|---|---|---|
| **macOS** | `ctrl+shift+v` | `cmd+v`（原生，不动） | 不绑，留给 vim 等 | `~/.config/kitty/kitty-smart-paste` |
| **Linux** | `ctrl+shift+v`（文本走 `sumika-paste-at-cursor`） | Wayland/X11 系统粘贴（不经过脚本） | 不绑，留给 vim 等 | `sumika-kitty-smart-paste` |
| **Windows** | 本仓库不管 | Kitty 默认 | 不绑 | 需自己 map + 装剪贴板工具 |

统一原则：**系统粘贴不干涉，脚本只走 `ctrl+shift+v`**。`ctrl+v` 在终端里传统上是留给程序的（vim visual-block、emacs scroll-down），绑成粘贴会吃掉它。

macOS 脚本里文本分支调 `kitty @ action paste_from_clipboard`（原生粘贴，只贴一次），图片分支用 `send-text` 注入路径再清掉位图。Linux 脚本文本与图片都委托 `sumika-paste-at-cursor` 注入，图片路径解析（含 SSH 传远端）走 `sumika-clipboard-image-path`，贴完 `notify-send` 提示。两边注入管道不同，但键位与「图片→路径、文本→文本」的对外行为一致。


Kitty 出厂默认（未改 conf 时）：

- macOS：`cmd+c` / `cmd+v` = 系统习惯的复制粘贴
- Linux / Windows：`ctrl+shift+c` / `ctrl+shift+v` = Kitty 默认复制粘贴（`ctrl+v` 往往留给程序自己，例如 vim）

chezmoi 模板按 `{{ if eq .chezmoi.os "darwin" }}` 选 macOS 或 Linux 分支，换机 `chezmoi apply` 即可，不必手改。


## 机制

macOS（`kitty-smart-paste`，直连 kitty remote-control）：

```
ctrl+shift+v
  → kitty map: launch --type=background ~/.config/kitty/kitty-smart-paste
    → 读剪贴板 (pngpaste / pbpaste)
      ├─ 图片 → 存 /tmp + last-image.png → send-text 路径 → 剪贴板清成空格
      ├─ 剪贴板空/空格且有 last-image → 再贴同一张图的路径
      └─ 文本 → kitty 原生 paste_from_clipboard（只贴一次，不 send-text）
```

Linux（`sumika-kitty-smart-paste`，走 Sumika 中央管道）：

```
ctrl+shift+v
  → kitty map: launch --type=background sumika-kitty-smart-paste
    → 读剪贴板 (wl-paste)
      ├─ 图片 → sumika-clipboard-image-path 解析路径（含 SSH 传远端）→ sumika-paste-at-cursor 注入 → 剪贴板清成空格 → notify-send
      ├─ 剪贴板空/空白且有 last-image → 再贴同一张图的路径
      └─ 文本 → sumika-paste-at-cursor 注入
```

- SSH：焦点窗格跑着 ssh 时，图片先传到远端 `/tmp`，贴远端路径。
- 一次按键只注入一次（单飞锁）。再按一次再贴一次。
- 本地图片文件保留；只有已经传到远端的本地临时副本才会删。

## 安装（macOS）

```sh
# 1. 依赖（pbpaste/pbcopy 系统自带）
brew install pngpaste jq

# 2. kitty.conf 由 chezmoi 模板生成，确认有：
#    allow_remote_control yes
#    listen_on unix:/tmp/mykitty
#    map ctrl+shift+v launch --type=background ${HOME}/.config/kitty/kitty-smart-paste
#
#    cmd+v / ctrl+v 故意不绑脚本（见上文「按键怎么定义」）：cmd+v 留给系统粘贴与语音输入，ctrl+v 留给 vim 等程序。
#
# 3. 改 map 后至少 `kitty @ load-config`，listen_on 变更才需要重启
```


## 使用

| 场景 | 行为 |
|---|---|
| 剪贴板是截图/图片 | 光标处出现 `/tmp/ksp-clip-xxx.png` |
| 剪贴板是文本 | 正常 bracketed paste |
| shell 提示符下 | 路径出现后需自己按回车提交（与普通粘贴一致） |
| OMP 等 raw 模式 TUI | 字节即时到达，无需回车 |
| tmux 内 | 正常（send-text 穿透 tmux 客户端进 pane） |
| SSH 会话内 | 图片传远端 /tmp，贴远端路径 |

截图进剪贴板：`Cmd+Shift+4`（选区）/ `Cmd+Shift+3`（全屏）/ `Cmd+Shift+Ctrl+4`（选区进剪贴板不落文件）。

## 排障记录（2026-08-18 macOS 部署时发现的坑）

### 1. GUI 启动的 kitty 里 pngpaste 找不到（PATH 问题）

**现象**：按键后无任何反应，日志（/tmp/kitty-smart-paste.log）无 image detected，直接走 text 分支。
**原因**：从 Spotlight/Dock 启动的 kitty 继承精简 GUI PATH（`/usr/bin:/bin/...`），不含 `/opt/homebrew/bin`，脚本内 `pngpaste` 报 127。
**修复**：脚本在 macOS 分支自动补 PATH：
```sh
case "$PLATFORM" in
    macos) PATH="/opt/homebrew/bin:/usr/local/bin:$PATH" ;;
esac
```
（Apple Silicon `/opt/homebrew` + Intel `/usr/local` 都覆盖。）

### 2. EXIT trap 误删已保存的图片

**现象**：日志有 `image->path /tmp/ksp-clip-xxx.png` 但文件不存在。
**原因**：图片分支 `trap 'rm -f "$payload" "$tmp_img"' EXIT` 在退出时把刚存的图删了，贴出去的路径是悬空的。
**修复**：仅当 SSH 已把图片传到远端（本地副本不再被引用）时才删本地临时图；本地路径场景保留文件。

### 3. 失效的 KITTY_LISTEN_ON 环境变量

**现象**：脚本日志 `no kitty window id`，图片存了但路径没注入。
**原因**：`KITTY_LISTEN_ON` 从启动它的 kitty 继承，但 socket 文件可能已消失（实例退出、socket 被删），脚本盲信该变量。
**修复**：`resolve_socket` 先验证 env 指向的 socket 文件存在（`[ -S ... ]`），不存在则回退扫描 `/tmp/mykitty-*`。
**教训**：kitty 的 socket 文件一旦从文件系统删除，即使进程还握着 fd 也无法再连接——不要手动清理 `/tmp/mykitty-*`。

### 4. 排障中的一次大乌龙：send-text "时灵时不灵" ≠ 投递失败

用 `cat > 文件` 做接收端测试时，send-text 发的无换行文本**不落文件**——PTY 规范模式（canonical mode）行缓冲要等 `\n` 才交给读取者，但屏幕 ECHO 是即时的。判断投递是否成功要用屏幕内容（`kitty @ get-text` 或 `tmux capture-pane`），不要用无换行的文件接收端。send-text 本身从未坏过。

### 5. "tmux 里贴不了"的真正原因

不是 tmux 的问题：是按的 **Ctrl+Shift+V**（kitty 原生粘贴），剪贴板是图片时它贴不出东西且不经过脚本（日志零记录）。脚本机制本身在 tmux/OMP 里完全正常（等价触发验证：路径真实出现在 tmux pane 的 OMP 输入框）。修复即把 ctrl+shift+v 也绑到脚本。

### 6. 连按两下贴出两条重复路径（去重防护失效）

**现象**：ctrl+shift+v 按一两次，OMP 输入框出现两条相同路径。
**原因**：`now_ms` 用的 `date +%s%3N` 是 GNU 扩展；这台 macOS 的 date 会输出 `178706429813373000` 这类 18 位数（不含 `N`，旧 fallback 逻辑拦不住），直接被当毫秒数使用 → 所有去重窗口的 elapsed 计算都是千万级"毫秒"，**图片哈希去重（1.2s）和路径回贴抑制（2s）全部失效**，按几次贴几次。
**修复**（2026-08-18）：
- `now_ms` 改为 perl `Time::HiRes` 优先（macOS/Linux 核心模块，真毫秒），GNU date %3N 次之，秒×1000 兜底；
- 路径回贴抑制窗口 2s → 5s（`KSP_PATH_GUARD_MS` 可调），覆盖"没看到结果急着再按一次"；
- 纯空白剪贴板（恰好落在注入前 150ms 的空格反附加窗口）不再注入空格。
**验证**：隔离 kitty 实例连按三次（立即/立即/+2s），屏幕路径恰好出现一次，日志两次 `suppressed repeat path`。

附：ctrl+shift+v 原本是 kitty 内置的 `paste_from_clipboard`（纯文本粘贴）；2026-08-18 起被 re-bind 到本脚本（见上方「按键」）。最终只绑 `ctrl+shift+v`——`ctrl+v` 仍留给程序（vim 等），避免松开 Shift 略早时 `ctrl+v` + `ctrl+shift+v` 双触发。

### 7. 按一下贴两次 / 按一下没反应（2026-08-19）

**贴两次，三条独立通道叠在一起：**

1. `ctrl+v` 和 `ctrl+shift+v` 都绑同一脚本。松开 Shift 略早时，Kitty 会再收到一次 `ctrl+v`，脚本跑两遍。
2. 图片贴完后旧逻辑把**路径写回剪贴板**。下一次按键走 text 分支，把同一路径再注入一次。去重窗口只有 5s，且 macOS 没有 `flock`，两实例能同时通过。
3. OMP 看见剪贴板里的位图会自己 attach；脚本再 `send-text` 路径，TUI 里出现「附件 + 路径」或两条路径。

**按一下没反应：**

- 日志 `no kitty window id`：`resolve_socket` 只检查 `[ -S socket ]`。Kitty 退出后 unix socket **文件还在**，连上去 `kitty @ ls` 失败，路径没注入。
- glob `/tmp/mykitty-*` 无序，先命中死套接字就停。
- 本 shell 里 `KITTY_LISTEN_ON` 经常是上一只 Kitty 留下的过期值。

**修复：**

- socket 必须 `kitty @ ls` 成功才用；过期 `KITTY_LISTEN_ON` 回退到最新还能应答的 `/tmp/mykitty-*`。
- `send-text` 优先用启动脚本时继承的 `KITTY_WINDOW_ID`，不再赌 `is_focused`。
- `mkdir` 单飞锁：同一时刻只跑一个实例（macOS 无 flock）。一次按键只注入一次。
- 图片贴完把剪贴板清成空格（防 OMP 再 attach 位图），**不把路径写回剪贴板**。
- 原图另存 `…/kitty-smart-paste/last-image.png`。剪贴板空/空白时再按，复用这张图，所以删掉路径后再贴、连贴几次都可以。
- 剪贴板里是新图 → 贴新图；是普通文本 → 贴文本。哈希去重和 5s 路径抑制已去掉，避免「只能贴一次」。
- 文本粘贴不改剪贴板。


## 诊断

```sh
# 在 kitty 终端里跑
~/.config/kitty/kitty-smart-paste --probe
```

输出示例：
```
platform=Darwin
socket=<unset>          # env 未设时显示；内部会自动扫描 /tmp/mykitty-*
clipboard=image (PNG image data, 1920 x 1080, ...)
kitty_shell_pid=12345
ssh_pid=<none>
```

| 现象 | 含义 |
|---|---|
| `clipboard=text (0 bytes)` | 剪贴板是空的 |
| `kitty_shell_pid=<none>` | socket 连不上：kitty 没开 remote control，或 socket 文件被删（重启 kitty） |
| `ssh_pid=<none>` | 当前窗格无 SSH 会话（正常） |
| 按键完全无日志 | 键绑定没生效：确认 kitty.conf 两行 map；`allow_remote_control yes` 仅启动时读取，改配置要重启 kitty |

日志：`/tmp/kitty-smart-paste.log`（每次粘贴一行，排障先看这个）。

等价触发（不按键、直接模拟 map 动作，用于区分"键绑定问题"和"脚本问题"）：

```sh
kitty @ --to unix:/tmp/mykitty-$(pgrep -f 'MacOS/kitty$' | head -1) \
    launch --type=background ~/.config/kitty/kitty-smart-paste
```

## 依赖一览

| 平台 | 剪贴板读 | 剪贴板写 | SSH 检测 | 额外装 |
|------|---------|---------|---------|--------|
| macOS | pngpaste / pbpaste | pbcopy | pgrep -P | pngpaste, jq (brew) |
| Linux Wayland | wl-paste | wl-copy | /proc | jq |
| Linux X11 | xclip | xclip | /proc | jq |

kitty remote-control 和 `kitty @ send-text` 是 kitty 自带的。macOS 上脚本已内置 homebrew PATH 补全。

## Linux

Linux 上 chezmoi 模板自动选择 `sumika-kitty-smart-paste`（sumika-shell 集成版），本仓库的便携版 `executable_kitty-smart-paste` 不参与。两个脚本对外行为一致（只有 `ctrl+shift+v` 走智能粘贴），但注入管道不同：Linux 文本与图片都委托 `sumika-paste-at-cursor`，图片路径解析与 SSH 传输走 `sumika-clipboard-image-path`，贴完用 `notify-send` 提示。

想在本机测试便携版：

```sh
KITTY_LISTEN_ON=unix:/tmp/mykitty ~/.config/kitty/kitty-smart-paste --probe
```

### Linux 可靠性改进

为对齐 macOS 已稳定的可靠性，Linux 版 `sumika-kitty-smart-paste` 增加以下改动（运行时验证待 Linux 实测，见 [paste-unification-plan.md](paste-unification-plan.md)）：

- **Socket 验活 + 过期 env 回退**：`KITTY_LISTEN_ON` 不再盲信。先用 `kitty @ ls` 验证 env 指向的 socket 可连；失败则回退到 `hyprctl activewindow` + glob `/tmp/mykitty-*`，并对每个候选 socket 都做 `kitty @ ls` 确认，避免连上 Kitty 退出后残留的死套接字。
- **原子单飞锁**：`mkdir` 原子锁 + stale PID 检测，同一时刻只跑一个实例。覆盖键重复与 `ctrl+shift+v` 快速连按，一次按键只注入一次。
- **图片贴完不写回路径**：图片注入后把剪贴板清成空格（防 OMP 等图片感知 TUI 再 attach 位图），**不再把生成的路径写回 `wl-copy`**。旧逻辑写回路径会导致下一次按键走文本分支把同一路径再贴一次。
- **last-image 缓存**：原图另存到 `…/sumika-clipboard/last-image.png`。剪贴板为空/空白时再按 `ctrl+shift+v`，复用这张图，所以删掉路径后再贴、连贴几次同一张图都可以。剪贴板里是新图 → 贴新图；是普通文本 → 贴文本。
- **`KITTY_WINDOW_ID` 优先**：与 `sumika-paste-at-cursor` 兼容时优先用启动脚本时继承的 `KITTY_WINDOW_ID`，不再赌焦点窗口。
- **诊断**：`--probe` 输出 platform / socket / clipboard / ssh 等状态；`--print-socket` 仅打印解析到的 socket，供脚本外部调用。
- **保留不动**：`sumika-clipboard-image-path`（SSH 传输 + 去重）、`sumika-paste-at-cursor`（中央注入管道）、`notify-send`、`wl-paste`/`wl-copy`。

> 注：`sumika-paste-at-cursor` 自带去重与目标解析。若改用 Kitty 原生 `paste_from_clipboard` 会丢失这些，且可能与中央管道产生双贴；故 Linux 文本粘贴仍走 `sumika-paste-at-cursor`，不切换到原生粘贴。

---
本文件由 chezmoi 管理，源在 `~/chezmoi/dot_config/kitty/docs/smart-paste-setup.md`。
