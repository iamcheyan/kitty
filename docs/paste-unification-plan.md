# Linux/macOS 智能粘贴脚本统一方案

> **状态（2026-08-19）**：已采纳 **方案 A**（反向移植，保留各自注入管道），实施中。本文档的「修改清单」即实施契约；运行时验证（见「测试计划」）待 Linux 机器实测后勾选。下文「现状对比」是实施前的差距快照，保留作为背景。

## 目标

macOS 版 `kitty-smart-paste` 经过多轮修复已稳定；Linux 版 `sumika-kitty-smart-paste` 原为旧实现。本文档原为「如何把 macOS 的改进反向移植到 Linux」的提案，现已成为**方案 A 的实施契约**（见顶部状态）。两平台对外行为统一——只有 `ctrl+shift+v` 走智能粘贴——但保留各自注入管道（macOS 直连 `kitty @ send-text`，Linux 走 `sumika-paste-at-cursor`）。

## 现状对比

> 以下为**实施前**的差距快照（2026-08-19）。实施后 Linux 列应向 macOS 列对齐，差异仅剩注入管道与平台工具（见「修改清单」）。

| 特性 | macOS (`executable_kitty-smart-paste`) | Linux (`sumika-kitty-smart-paste`) |
|---|---|---|
| **Socket 解析** | `socket_alive()` 用 `kitty @ ls` 验活；过期 `KITTY_LISTEN_ON` 回退到最新 socket | `hyprctl activewindow` + glob `/tmp/mykitty-*`；不验证 socket 是否可连 |
| **窗口 ID** | 优先用 `KITTY_WINDOW_ID` 环境变量；回退到 `kitty @ ls` jq 解析 | 不解析窗口 ID；委托 `sumika-paste-at-cursor` 处理 |
| **单飞锁** | `mkdir` 原子锁 + stale PID 检测 | 无；依赖 `sumika-clipboard-image-path` 的 exit code 3 做去重 |
| **图片去重** | 已移除（改为 last-image 缓存 + 空白剪贴板复用） | `sumika-clipboard-image-path` exit code 3 = 同图已贴过 |
| **重复路径抑制** | 已移除 | `suppress_repeat_path` 2s 窗口 |
| **文本粘贴** | `kitty @ action paste_from_clipboard`（原生粘贴，只贴一次） | 委托 `sumika-paste-at-cursor` |
| **图片粘贴后** | 清剪贴板为空格，不写回路径 | 写回路径到 `wl-copy`（会导致再按一次贴出路径文本） |
| **同图再贴** | `last-image.png` 缓存，空白剪贴板时复用 | 不支持 |
| **SSH 检测** | 跨平台进程树 BFS + tmux 客户端遍历 | 委托 `sumika-clipboard-image-path` |
| **剪贴板读写** | `pngpaste`/`pbpaste`/`pbcopy`（macOS）vs `wl-paste`/`wl-copy`/`xclip`（Linux） | `wl-paste`/`wl-copy`（Wayland only） |
| **通知** | 无 | `notify-send` |
| **诊断** | `--probe` 模式 | `--print-socket` |
| **Kitty 二进制** | `KITTY_BIN` 变量，优先 `/Applications/kitty.app/...` | 直接 `kitty` |
| **注入方式** | `kitty @ send-text --match id:$win_id` | `sumika-paste-at-cursor` 内部实现 |

## 差距分析

### macOS 有、Linux 缺的

1. **Socket 验活** — Linux 用 `hyprctl` + glob，不检查 socket 是否可连。Kitty 退出后 socket 文件还在，会连上死套接字。
2. **单飞锁** — Linux 没有防止 `ctrl+shift+v` + `ctrl+v` 同时触发的机制。
3. ~~**文本原生粘贴**~~ — Linux 委托 `sumika-paste-at-cursor`，不走 `paste_from_clipboard`。**经评估决定保留中央管道**（见修改清单 4）：原生粘贴会丢失去重/目标解析，反而可能双贴。此项不再列为差距。
4. **图片后清剪贴板** — Linux 写回路径到 `wl-copy`，再按一次会贴出路径文本。
5. **同图复用** — Linux 不支持删掉路径后再贴同一张图。
6. **`--probe` 诊断** — Linux 没有。
7. **`KITTY_BIN` 变量** — Linux 直接用 `kitty`，PATH 问题时可能找不到。

### Linux 有、macOS 缺的

1. **`sumika-paste-at-cursor` 集成** — Linux 版注入走 sumika 统一管道，和语音输入、剪贴板菜单共享去重和目标解析。
2. **`notify-send` 通知** — Linux 贴完图片后弹通知。
3. **`sumika-clipboard-image-path`** — Linux 版 SSH 传输和去重委托给这个中央工具。

## 统一方案

### 方案 A：macOS 脚本反向移植到 Linux（推荐）

把 `executable_kitty-smart-paste` 的改进直接移植到 Linux 版的 `sumika-kitty-smart-paste`，保留 sumika 集成层。
**文件 1**（运行时，OMD 仓库）：
- 实现：`~/development/OMD/quickshell/modules/clipboard/bin/sumika-kitty-smart-paste`
- 入口包装：`~/development/OMD/bin/sumika-kitty-smart-paste`（Hyprland PATH 用，`exec` 进模块脚本）

> 状态标记：✅ 已写入 / ⏳ 待 Linux 实测验证。运行时文件由 OMD 仓库维护，本 chezmoi 仓库不改。

1. ⏳ **Socket 解析**：加入 `socket_alive()` 函数，用 `kitty @ ls` 验活。保留 `hyprctl` 作为辅助，但最终都要 `socket_alive` 确认。
2. ⏳ **单飞锁**：加入 `acquire_run_lock()` / `release_run_lock()`（`mkdir` 原子锁 + stale PID 检测）。Linux 有 `flock`，但 `mkdir` 跨平台一致。
3. ⏳ **`KITTY_WINDOW_ID`**：与 `sumika-paste-at-cursor` 兼容时优先用环境变量；不兼容则仍走中央管道。
4. ✅ **文本粘贴（决策）**：**保留 `sumika-paste-at-cursor`，不切换到原生 `paste_from_clipboard`**。`sumika-paste-at-cursor` 自带去重与目标解析，改用原生粘贴会丢失这些且可能双贴。若实测发现中央管道导致 TUI 双贴，再单独评估。
5. ⏳ **图片后清剪贴板**：改为清成空格，不写回路径（修掉「再按一次贴出路径文本」）。
6. ⏳ **last-image 缓存**：加入 `LAST_IMG` 和 `clipboard_is_blank()` 复用逻辑。
7. ⏳ **`KITTY_BIN` 变量**：加入变量，Linux 上默认 `kitty`。
8. ⏳ **`--probe` 诊断**：加入完整 probe 模式；`--print-socket` 保留。

**保留不动的**：
- `sumika-clipboard-image-path` 调用（SSH 传输 + 去重由它处理）
- `notify-send` 通知
- `wl-paste` / `wl-copy` 剪贴板操作

**文件 2**（文档，chezmoi 仓库）：
- `~/chezmoi/dot_config/kitty/docs/smart-paste-setup.md` — ✅ 已更新：统一键位说明、Linux 注入管道与可靠性改进小节。
- `~/chezmoi/dot_config/kitty/docs/paste-unification-plan.md`（本文件）— ✅ 已转为实施状态。

**参考实现（不动）**：
- `~/chezmoi/dot_config/kitty/executable_kitty-smart-paste`（macOS，部署到 `~/.config/kitty/kitty-smart-paste`）— 反向移植的来源，保持自包含便携版。

#### 风险

- **文本双贴（已规避）**：原计划把文本分支改成原生 `paste_from_clipboard`，会丢失 `sumika-paste-at-cursor` 的去重与目标解析。决策改为**保留中央管道**（见修改清单 4）。残留风险：若 `sumika-paste-at-cursor` 自身在 TUI 下双贴，需单独排查中央管道，不在本次范围。
- **两层去重叠加**：`sumika-clipboard-image-path` 的 exit code 3 同图去重 + 新的 `mkdir` 单飞锁并存。单飞锁挡并发实例，exit 3 挡同图重贴，两者作用域不同，理论上不冲突；实测需确认连按时不互相吞掉合法的「同图再贴」。
- **`wl-copy` 清空行为**：Wayland 下 `wl-copy` 写空格可能保留 MIME 类型或触发图片感知 TUI 误判；macOS `pbcopy` 清成纯文本空格。需确认 OMP 等不再 attach。
- **Wayland-only**：脚本用 `wl-paste`/`wl-copy`，**不支持 X11**；X11 用户需自行换 `xclip`（本仓库不提供 X11 分支）。
- **`hyprctl` / `notify-send` 依赖**：socket 回退与通知依赖 Hyprland 及 `notify-send`；非 Hyprland 桌面（Sway/GNOME）下 `hyprctl activewindow` 失效，退回 glob `/tmp/mykitty-*`，`notify-send` 缺失则静默（脚本已 `|| true`）。
- **死 socket 残留**：Kitty 退出后 `/tmp/mykitty-*` 文件仍在；`socket_alive()` 用 `kitty @ ls` 过滤，但 glob 无序，多个 socket 时需选最新可应答者。

#### 测试计划（⏳ 全部待 Linux 实测）

以下各项需在 Linux（Wayland + Hyprland）实测后勾选。`--probe` 可辅助验证 socket/剪贴板状态：

1. ⏳ **Wayland + Hyprland**：截图 → `ctrl+shift+v` → 路径出现。再按 → 路径再出现。
2. ⏳ **SSH**：SSH 会话内截图 → `ctrl+shift+v` → 远端路径出现。
3. ⏳ **文本**：复制文本 → `ctrl+shift+v` → 文本出现一次（不是两次）。
4. ⏳ **同图复用**：贴图 → 删路径 → 再按 → 路径再出现。
5. ⏳ **死 socket**：杀掉 Kitty → 重开 → `ctrl+shift+v` → 应连上新 socket。
6. ⏳ **语音输入**：语音输入后 `ctrl+shift+v` → 应正常粘贴文本。
7. ⏳ **单飞锁**：连按三次 `ctrl+shift+v`（立即/立即/+2s），路径恰好出现一次，日志无重复注入。
8. ⏳ **不写回路径**：贴图后检查 `wl-paste` 不再是刚贴的路径文本。

### 方案 B：统一成一份脚本

把两个脚本合并成一个，用 `$PLATFORM` 分支处理平台差异。

#### 优点
- 一份代码，修一次两边都受益
- 文档统一

#### 缺点
- Linux 的 `sumika-paste-at-cursor` / `sumika-clipboard-image-path` / `hyprctl` / `notify-send` 集成需要保留为 Linux 分支
- 脚本会更长，条件分支更多
- Linux 的注入管道和 macOS 的 `kitty @ send-text` 差异大，合并后可读性下降
- chezmoi 模板已经按平台选不同脚本入口，合并反而增加复杂度

#### 结论

**不推荐方案 B**。两个平台的注入管道差异太大（sumika 中央化 vs kitty 直连），强行合并会增加维护成本。方案 A（反向移植改进，保留各自注入管道）更安全。

## 实施步骤

1. ~~先在 Linux 机器上备份现有 `sumika-kitty-smart-paste`~~（OMD 仓库已纳管，git 即备份）
2. ⏳ 按「修改清单」逐项移植到 `~/development/OMD/quickshell/modules/clipboard/bin/sumika-kitty-smart-paste`，每项改完测试
3. 优先移植：socket 验活 → 单飞锁 → 图片后清剪贴板 → last-image 缓存 → `KITTY_WINDOW_ID` → `--probe`（文本粘贴保留 `sumika-paste-at-cursor`，不改）
4. ⏳ 全部完成后在 Linux 跑一遍「测试计划」并勾选
5. ✅ 更新 `~/chezmoi/dot_config/kitty/docs/smart-paste-setup.md`（本批次已完成）
6. ⏳ 同步 OMD 的 `docs/features/smart-paste.md`（OMD 仓库侧，本仓库不管）

---

本文件由 chezmoi 管理，源在 `~/chezmoi/dot_config/kitty/docs/paste-unification-plan.md`。