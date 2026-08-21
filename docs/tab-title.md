# 标签页标题模板（tab_title_template）

控制 tab bar 上每个标签显示什么文字。多个标签都叫 `zsh` / `tmux` 时，靠标题区分。

## 本仓库配置

`kitty.conf.tmpl` 里：

```text
tab_title_template " {title} "
```

相比原来的 `"  {title}  "`（两个全角空格）：改成单空格两侧留白，更紧凑。

## 可用模板变量

Kitty 在 `tab_title_template` 里提供这些变量（详见 Kitty 文档「tab_title_template」）：

| 变量 | 含义 |
|---|---|
| `{title}` | 窗口标题（程序通过转义序列设置的标题，没有就 fallback 到 `shell` 或进程名） |
| `{index}` | 标签序号（从 1 开始） |
| `{layout_name}` | 当前布局名 |
| `{num_windows}` | 标签内窗口数 |
| `{num_window_utils}` | 类似上面 |
| `{fmt.fg.red}` / `{fmt.fg.default}` | 前景色控制 |
| `{fmt.bold}` / `{fmt.no_bold}` | 粗细控制 |
| `{bell_status}` | 是否有响铃 |

## 自定义 Python Tab Bar（tab_bar.py）与 SSH 标签高亮

本仓库已启用 `tab_bar_style custom`，通过 `~/.config/kitty/tab_bar.py` 实现**100% 满宽均分（Full-Width Equal Distribution）**、**常驻序号直达**与**智能 SSH 高亮**：

1. **100% 顶栏铺满均分**：
   - 1 个标签：占据 100% 宽度通栏展示。
   - 2 个标签：各自均分 50% 宽度。
   - N 个标签：根据终端列宽完全等宽平铺，**右侧零黑边、零留白空隙**。
   - 标签文字自动居中对齐，并智能精简超长命令（如 `tmux:main`、`debian:zellij-cb`）。
2. **常驻标签序号与 Tmux 直达体系**：
   - 每个标签名称前**默认常驻显示数字编号**（如 `1: zsh`、`2: [SSH:192.168.1.50] debian`、`3: nvim`）。
   - 完全对应 Tmux 习惯：直接按 **`Ctrl+p 1`**、**`Ctrl+p 2`**、**`Ctrl+p 3`**…… 即可瞬间直达对应标签！
3. **SSH 远程标签高亮与 `[SSH:IP/Host]` 标识**：
   - 自动提取目标连接的 **IP 地址或主机名**，格式化为 `2: [SSH:192.168.1.50] debian` 或 `2: [SSH:debian] zellij-cb`，直观标明正在连接哪台机器。
   - **激活 SSH 标签**：醒目的亮橙红底色（`#ff5500`）、白字加粗显示。
   - **未激活 SSH 标签**：温和深琥珀底色（`#64200a`）、浅桃色字，即使在多个未激活标签中也能一眼识别远程会话。
   - 退出 SSH 后自动恢复普通标签样式。
### 识别原理

`tab_bar.py` 依次检测：
- Kitty 原生 `window.child_is_remote`
- `window.ssh_kitten_cmdline()`
- 子进程前台进程树（`foreground_processes` 中的命令名）
- 用户变量 `IS_SSH=1`
- 标签标题前缀/标记回退（如 `ssh ...`、`[ssh]` 等）
## 排障

- **所有标签都叫 `zsh`**：zsh 没设标题。可以在 `.zshrc` 里加 `precmd() { print -Pn "\e]0;%~\a" }` 让 zsh 把当前目录设成窗口标题，`{title}` 就会显示路径。
- **标题太长挤掉别的标签**：`{title}` 内容长时 tab bar 会截断。可在模板里固定宽度或只显示前 N 字（需要 Python tab bar）。
- **改了模板没生效**：`chezmoi apply --force` 后重载 Kitty（`kitty @ load-config` 或重启）。

## 局限

- 无法在纯模板里取 cwd basename，需要 Python tab bar 或 shell integration 用户变量。
- 标题频繁变化（如每条命令刷新 cwd）会增加 tab bar 重绘。

---

本文件由 chezmoi 管理，源在 `~/chezmoi/dot_config/kitty/docs/tab-title.md`。