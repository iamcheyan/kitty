# Kitty 快捷键体系设计与前缀键选型论证

本文档详细记录了本仓库 Kitty 终端快捷键体系的设计哲学、前缀键（Prefix）的选型分析，以及终端环境下全字母 `Ctrl + [A-Z]` 的冲突排查表。

---

## 1. 核心设计哲学：双层模态解耦

在高级终端工作流中，通常存在两层环境：
1. **外层终端模拟器**：Kitty（负责 OS 窗口、原生 Tab、原生 Split 分屏、Kitten 扩展小程序）。
2. **内层终端复用器**：Zellij / Tmux（负责远程 SSH 会话持久化、会话共享）。

为了避免内外层快捷键互相抢占、拦截或产生连击穿透负担，本仓库采取**分层解耦设计**：

| 层级 | 工具 | 前缀键 (Prefix) | 核心职责 |
|---|---|---|---|
| **外层** | **Kitty** | **`Ctrl + P`** | 终端窗口/标签管理、Hints 屏幕取词、原生正则搜索、智能粘贴 |
| **内层** | **Zellij / Tmux** | **`Ctrl + B`** | 会话持久化、多 Pane 编排、远程 Session 恢复 |

---

## 2. 前缀键为什么选 `Ctrl + P`？

### (1) `P` 的心智模型

* **`P` = Prefix（前缀引导键）**：作为进入下层指令的唯一引导入口。
* **`P` = Palette / Panel（命令面板）**：与现代代码编辑器（VS Code / Sublime Text / JetBrains `Cmd/Ctrl+P`）建立相同的“呼出动作”心智模型。
* **`P` = Pane（窗格管理）**：Kitty 原生负责 Pane 级的分屏、缩放与跳转。

### (2) 人体工学优势（左右手平衡）

* **双手交替击键**：左手小指按下 `Ctrl`，右手小指/无名指轻点 `P`。
* **后续动作极度顺畅**：松开 `Ctrl+P` 后，后续常用子命令（`c` 新建标签、`o` 换窗格、`%` 垂直分屏、`z` 最大化、`u` 提取链接、`s` 搜索）大多分布在主键盘区或左手区，左右手交替敲击流畅且不易疲劳。

---

## 3. 为什么不用 `Ctrl + K`（Kitty）或其他字母？

### 终端全字母 `Ctrl + [A-Z]` 冲突与排查表

在终端环境（Shell、Readline、Emacs 模式、Vim、FZF）中，大部分 `Ctrl` 组合键都有极其关键且不可替代的系统级职责：

| 按键 | Shell / 终端原生功能 | 替代方案 / 能否占用 | 结论 |
|---|---|---|---|
| `Ctrl + A` | 跳到行首 (Beginning of Line) | 极难替代，命令行高频使用 | ❌ 严禁占用 |
| `Ctrl + B` | 光标后退 / **Tmux & Zellij 默认前缀** | 内层已用作复用器前缀，不可内外冲突 | ❌ 冲突 |
| `Ctrl + C` | 终止前台程序 (SIGINT 信号) | 核心系统信号 | ❌ 严禁占用 |
| `Ctrl + D` | 退出 Shell (EOF) / 删除光标处字符 | 核心系统信号与输入流终止 | ❌ 严禁占用 |
| `Ctrl + E` | 跳到行尾 (End of Line) | 极难替代，命令行高频使用 | ❌ 严禁占用 |
| `Ctrl + F` | 光标前进一个字符 | 可用 `→` 键替代，但在 Vim/Emacs 中广泛使用 | ⚠️ 不建议 |
| `Ctrl + G` | 取消 / 中止当前操作 | Emacs / Readline 取消搜索或未完成输入 | ⚠️ 不建议 |
| `Ctrl + H` | 退格删除 (Backspace) | 终端底层 ASCII 8，拦截会导致退格异常 | ❌ 严禁占用 |
| `Ctrl + I` | 制表符 (Tab 自动补全) | 终端底层 ASCII 9，与 Tab 等价，拦截会导致补全失效 | ❌ 严禁占用 |
| `Ctrl + J` | 换行 (LineFeed / Enter) | 终端底层 ASCII 10，与回车等价 | ❌ 严禁占用 |
| **`Ctrl + K`** | **从光标处删除到行尾 (Kill Line)** | **文本编辑与改错黄金键；Neovim LSP 悬浮文档** | **❌ 严禁占用 (不能用作 K)** |
| `Ctrl + L` | 清屏 (Clear Screen) | 命令行高频刷新与清屏键 | ❌ 严禁占用 |
| `Ctrl + M` | 回车 (Carriage Return) | 终端底层 ASCII 13 | ❌ 严禁占用 |
| `Ctrl + N` | 下一条历史记录 / 下一行 | 可用 `↓` 替代，但 Vim 补全常用 | ⚠️ 略别扭 |
| `Ctrl + O` | 执行并加载下一条历史命令 | 特殊运维重放多条命令使用 | ⚠️ 偏僻 |
| **`Ctrl + P`** | **上一条历史记录** | **100% 可被 `↑` 方向键与 `Ctrl+R`/FZF 模糊搜索完美替代** | **✅ 综合影响最小的最佳之选** |
| `Ctrl + Q` | 终端流控恢复 (XON) | 容易与流控冲突导致终端假死 | ❌ 不建议 |
| `Ctrl + R` | 历史记录反向搜索 (FZF 唤出键) | 终端最核心的搜索交互键 | ❌ 严禁占用 |
| `Ctrl + S` | 终端流控暂停 (XOFF) 挂起 | 容易误触导致终端无响应 | ❌ 不建议 |
| `Ctrl + T` | 交换前后字符 / **FZF 查找文件** | FZF 全局核心快捷键 | ❌ 冲突 |
| `Ctrl + U` | 从光标处删除到行首 (Kill to line start)| 快速清空当前输入行 | ❌ 严禁占用 |
| `Ctrl + V` | 输入转义字面量 (Literal Next) | 终端输入特殊控制字符必需 | ❌ 严禁占用 |
| `Ctrl + W` | 向前删除一个词 (Backward kill word) | 命令行极高频改错删除键 | ❌ 严禁占用 |
| `Ctrl + X` | 复合前缀引导 / 编辑器扩展 | 部分命令行工具扩展前缀 | ⚠️ 不建议 |
| `Ctrl + Y` | 粘贴刚才删除的文本 (Yank) | 配合 Ctrl+U/K/W 恢复误删内容 | ❌ 严禁占用 |
| `Ctrl + Z` | 挂起前台进程到后台 (SIGTSTP) | 终端与后台作业管理必备 | ❌ 严禁占用 |

---

### 为什么 `Ctrl + P` 是破坏性最小的唯一解？

1. **功能重叠度极低**：
   * `Ctrl + P` 在 Shell 中的原生功能仅仅是“翻出上一条命令”。
   * 在现代终端使用习惯中，**99% 的历史命令查找都通过 `↑` 方向键或 `Ctrl + R`（FZF / Atuin）完成**，几乎没有任何场景非要依赖 `Ctrl + P`。
2. **完全保护文本编辑流**：
   * 保留了 `Ctrl + A/E`（行首尾移动）、`Ctrl + U/W/K/Y`（行词剪切与粘贴恢复）、`Ctrl + C/Z/D`（进程控制）等所有肌肉记忆。
3. **不与内层工具冲突**：
   * 不影响 FZF 的 `Ctrl + R` / `Ctrl + T`，也不影响 Tmux/Zellij 的 `Ctrl + B`。

---

## 4. macOS 下 Option 键作为 Alt/Meta 键配置

在 macOS 下，默认按 `Option + P` 会被系统文本引擎解释为特殊符号 `π`，无法触发终端程序（如 omp 模型切换、readline 快捷键等）所需要的 `Alt+P`（`\x1bp`）转义信号。

本仓库在 `kitty.conf.tmpl` 中开启了：
```conf
{{ if eq .chezmoi.os "darwin" }}
macos_option_as_alt yes
{{ end }}
```
* **效果**：将 macOS 的 `Option` 键转换为标准终端 `Alt / Meta` 转义序列，无需按 `Ctrl+P` 前缀，直接单按 `Option + P` 即可呼出 omp 快速模型切换菜单。

---

## 5. 当前 Kitty 完整快捷键速查表（基于 `Ctrl + P`）

所有 Kitty 自身管理指令均以 **`Ctrl + P`** 作为前缀引导：

### 窗格与分屏管理 (Splits)
| 快捷键 | 功能 | 说明 |
|---|---|---|
| `Ctrl+p %` | 左右垂直分屏 | 自动切到 splits 布局并创建右侧窗口 |
| `Ctrl+p "` | 上下水平分屏 | 自动切到 splits 布局并创建下方窗口 |
| `Ctrl+p o` | 切换到下一个窗格 | Next window |
| `Ctrl+p ← / ↓ / ↑ / →` | 按方向切换窗格聚焦 | 移动到相邻方向的 window |
| `Ctrl+p z` | 最大化 / 还原窗格 | Toggle stack layout |
| `Ctrl+p x` | 关闭当前窗格 | 带安全确认对话框 |
| `Ctrl+p !` | 将当前窗格拆出为独立标签页 | Detach window to new tab |
| `Ctrl+p { / }` | 与上 / 下一个窗格交换位置 | Move window |

### 标签页管理 (Tabs)
| 快捷键 | 功能 | 说明 |
|---|---|---|
| `Ctrl+p c` | 新建标签页 | New tab |
| `Ctrl+p n / p` | 切换到下 / 上一个标签页 | Next / Previous tab |
| `Ctrl+p 0 ~ 9` | **直达对应编号标签页** | 顶栏默认常驻编号（`1: zsh`、`2: ssh`），按对应数字直达 |
| `Ctrl+p r` | **重载 Kitty 配置 (Reload Config)** | 重新读取 kitty.conf 就地热重载，并弹出系统通知横幅 |
| `Ctrl+p &` | 关闭当前标签页 | Close tab |
| `Ctrl+p ,` | 重命名当前标签页 | Set tab title |
### Kitten 增强小程序
| 快捷键 | 功能 | 说明 |
|---|---|---|
| `Ctrl+p s` | 正则搜索 Scrollback 历史 | Search kitten |
| `Ctrl+p ?` | **打开全英文按键帮助速查文档** | 弹出 `cheatsheet.txt` 完整键位表，按 `q` 退出 |
| `Ctrl+p u` | 屏幕标注并打开 URL | Hints kitten (url) |
| `Ctrl+p f` | 屏幕标注并在 Neovim 打开文件路径 | Hints kitten (path $\rightarrow$ nvim) |
| `Ctrl+p y` | 屏幕选行并复制到剪贴板 | Hints kitten (line) |
---

*本文件由 chezmoi 统一管理，源文件路径：`~/chezmoi/dot_config/kitty/docs/keybindings-design.md`。*
