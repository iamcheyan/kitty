# kitten ssh — 带 Kitty 能力的 SSH

`kitten ssh` 是 Kitty 提供的 SSH 辅助工具。不只是调系统 `ssh`，还配合 Kitty 的终端能力处理远端 shell integration、terminfo、文件传输等。本仓库用 shell alias `kssh` 调用它，不全局替换 `ssh`。

## 本仓库配置

`~/chezmoi/dot_config/aliases.conf` 里加了：

```sh
# Kitty ssh：带 shell integration / terminfo / 文件传输的 SSH
alias kssh='kitten ssh'
```

这是 **shell alias**，不是 `kitty.conf` 的 map。`kitten ssh` 是命令行程序，不能绑成 Kitty 按键。部署靠 chezmoi 管理 `aliases.conf`（由 shell rc source）。

## 怎么用

```sh
kssh user@host
kssh -p 2222 student@localhost
```

等价于 `kitten ssh user@host`。普通 `ssh` 不受影响，照常用。

## 带来的能力

- **远端 shell integration**：自动注入 Kitty shell integration 脚本，远端能识别 cwd / 退出码 / 命令运行时间，本仓库的会话保存（`save_as_session`）对 SSH 进程识别更准。
- **terminfo**：自动把 Kitty 的 terminfo 装到远端，避免 `tmux` / `nvim` 颜色和键位异常。
- **文件传输**：连上后可双向传文件（拖拽，或 `kitten remote_file`）。

## 排障

- **`kssh: command not found`**：`kitten` 是 Kitty 自带的子命令，需要 Kitty 在 PATH 里（macOS 通常 `/Applications/kitty.app/Contents/MacOS/kitten`）。确认 `which kitten` 能找到；找不到就把 Kitty 的 bin 目录加进 PATH，或新建 `~/bin/kitten` 软链。
- **alias 没生效**：确认 `aliases.conf` 被 shell rc source 了（`type kssh` 应显示 alias）。改完 `chezmoi apply --force` 后重开终端或 `source` 一次。
- **远端注入失败**：远端 shell 不支持（如受限 shell / 老 bash），`kitten ssh` 会回退到普通 ssh 行为，不影响连接。
- **跳板机 / ProxyJump**：复杂 SSH 配置在 `~/.ssh/config` 里照常生效，`kitten ssh` 透传 ssh 参数。如果异常，先用裸 `ssh` 连通再排查。

## 局限

- 不是所有服务器都适合自动注入配置（受管主机、只读 home）。
- 远端也需要支持相应 shell 环境才能完整享受 shell integration。
- 本仓库不全局替换 `ssh`，只给常用开发服务器加 `kssh` 别名，按需手动用。

---

本文件由 chezmoi 管理，源在 `~/chezmoi/dot_config/kitty/docs/kitten-ssh.md`。