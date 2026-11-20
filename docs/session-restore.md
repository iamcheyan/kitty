# Kitty 多实例会话保存与恢复

每次从默认终端启动 Kitty 都会创建一个**独立 Kitty 进程和 OS 窗口**。每个进程各自保存自己的 tab、pane、布局、工作目录和可恢复的前台命令。所有 Kitty 进程退出后，下次启动会把每份快照分别启动回来，保留它们原来的窗口边界。

源码位于 `~/chezmoi/dot_config/kitty/`；启动入口是 `~/chezmoi/dot_local/bin/executable_kitty-launch`。

## 预期行为

| 启动前状态 | 动作 | 结果 |
|---|---|---|
| Kitty 未运行，也没有快照 | 打开默认终端 | 启动一个新的 Kitty 进程 |
| 已有 Kitty 运行 | 再打开默认终端 | 再启动一个独立 Kitty 进程，不聚焦或复用旧进程 |
| 所有 Kitty 均退出，有多个进程快照 | 冷启动 Kitty | 每份快照启动一个独立进程/OS 窗口；每个进程内部恢复自己的 OS 窗口、tab 和 pane |

例如，进程 A 有两个 tab，进程 B 有一个 tab。它们运行时分别保存为 `sessions/kitty-A.kitty` 和 `sessions/kitty-B.kitty`。全部退出后再次启动，A 和 B 会各自恢复成独立 Kitty 窗口，不会被压到同一个进程。

## 启动入口

用户级 `kitty.desktop` 的 `Exec` 指向 `~/.local/bin/kitty-launch`。脚本检测到 Kitty 已运行时使用 `--session none` 启动新进程；冷启动时才读取快照。直接从其他入口执行系统 `kitty` 命令会绕过这套冷启动恢复流程。

脚本用 `~/.config/kitty/.kitty-launch.lock` 防止两个冷启动请求同时消费同一批快照。恢复时它逐个启动独立 Kitty 进程，并等待每个进程的远控 socket 可用、对应快照写回后再清除旧快照。任何一个恢复启动未完成，旧快照都会留下供下次重试。

## 保存与恢复内容

Kitty 0.48+ 的 `save_as_session` 官方动作负责序列化，每个 watcher 只写自己的 `sessions/kitty-<pid>.kitty`。OS 窗口边界、tab、pane、布局比例、标题、工作目录和 shell integration 记录的前台命令都由 Kitty 处理。

这里恢复的是启动命令和终端布局，不是屏幕截图或进程内存。滚动历史、未提交输入、剪贴板和 IME 状态不会恢复。通过 `--use-foreground-process` 保存的前台命令会在恢复时重新运行；退出前台命令时请确认重复运行安全。

`session_merge.py` 的名字为历史遗留：它现在只准备待恢复的快照清单、登记新进程 PID，并在恢复完成后清理旧快照，不再把不同 Kitty 进程扁平化合并。`last_session.kitty` 只用于迁移旧版单文件快照。

## 运行时文件

| 文件 | 用途 |
|---|---|
| `~/.config/kitty/sessions/kitty-<pid>.kitty` | 每个 Kitty 进程独立的活动快照 |
| `~/.config/kitty/sessions/.restore-manifest` | 当前冷启动准备恢复的快照清单 |
| `~/.config/kitty/sessions/.restore-pids` | 本轮恢复启动的新 Kitty PID |
| `~/.config/kitty/sessions/.restore-legacy.kitty` | 旧版统一快照的临时迁移副本 |
| `~/.config/kitty/last_session.kitty` | 旧版本兼容快照，不是多实例恢复的主要数据源 |
| `/tmp/kitty-session-watcher.log` | watcher 诊断日志 |

这些运行时文件不入 Git。Watcher 不会因其他 Kitty 启动或退出而删除快照；只在新一代进程确认恢复完整后，清理本轮消费的旧快照。

## 排查

```sh
# watcher 保存记录
cat /tmp/kitty-session-watcher.log

# 每个进程快照及其 tab 数
for file in ~/.config/kitty/sessions/kitty-*.kitty; do
  [ -f "$file" ] || continue
  printf '%s: ' "$file"
  grep -c '^new_tab' "$file" || true
done

# 默认终端入口
xdg-terminal-exec --print-id --print-path --print-cmd
```

Watcher 配置在 Kitty 启动时加载。更新 `kitty-launch` 或 watcher 后，后续启动会使用新脚本；修改 Kitty 配置本身则需要完全退出 Kitty 后重新启动。

本文件由 chezmoi 管理，源文件为 `~/chezmoi/dot_config/kitty/docs/session-restore.md`。
