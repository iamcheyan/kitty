# Kitty Configuration (iamcheyan/kitty)

Personal GPU-accelerated [Kitty](https://sw.kovidgoyal.net/kitty/) terminal configuration, custom tab bar, tmux-style keybindings, session restore, and Kitten extensions.

## 🔒 仓库可见性与管理原则

* **仓库可见性**：**PUBLIC（公开）**
* **独立仓库**：本仓库是独立的公开 Git 仓库，可作为个人 Kitty 终端配置分享，供他人参考、Fork 或独立克隆使用。
* **Chezmoi 联动**：在主 dotfiles 仓库（`iamcheyan/chezmoi`）中，通过 `.chezmoiexternal.toml` 将本仓库挂载并自动部署到 `~/.config/kitty`。

## 目录结构

```text
~/.config/kitty/ (https://github.com/iamcheyan/kitty.git)
├── kitty.conf              # 核心主配置：字体、配色、窗口行为与快捷键映射
├── tab_bar.py              # 100% 满宽等分顶栏、SSH 状态高亮与永久编号绘制
├── search-launcher.sh      # 正则搜索启动器（调起 search.py）
├── search.py               # Scrollback 历史正则搜索 Kitten
├── session_watcher.py      # 会话自动保存与恢复全局 Watcher
├── kitty-smart-paste       # 智能图片粘贴脚本（检测图片自动保存路径并注入）
├── scroll_mark.py          # 滚动标记跳转扩展
├── current-theme.conf      # 当前激活主题配色
├── docs/                   # 完整技术设计文档与快捷键速查表
│   ├── cheatsheet.txt      # 全英文快捷键速查表 (Ctrl+p ?)
│   ├── keybindings-design.md # 快捷键体系设计与全字母冲突分析
│   ├── tab-title.md        # 顶栏标题算法与 SSH 高亮设计
│   ├── kitty-overview.md   # 功能总览与架构说明
│   ├── search-kitten.md    # 搜索 Kitten 说明
│   ├── hints-kitten.md     # Hints 屏幕选词取链接说明
│   └── session-restore.md  # 会话恢复原理与 Watcher 机制
├── README.md               # 项目总览与独立安装使用说明
└── AGENTS.md               # 本文件：智能体与协作管理规范
```

## Agent / 维护工作流

1. **直接编辑与推送**：
   * 在本地 `~/.config/kitty` 或本仓库源码目录中直接修改配置。
   * 修改后直接提交并推送到 GitHub：
     ```bash
     cd ~/.config/kitty
     git add .
     git commit -m "feat: description of changes"
     git push origin main
     ```
2. **热重载与生效**：
   * 在 Kitty 中按 **`Ctrl + P` 松开按 `r`**（或执行 `kitty @ load-config`）即可就地热重载最新配置。
3. **Chezmoi 自动同步**：
   * 主 dotfiles 仓库在执行 `chezmoi apply` 时会自动检测本仓库：
     * 若 `~/.config/kitty` 不存在，则自动执行 `git clone`。
     * 若已存在，则根据更新周期自动执行 `git pull`。
4. **安全规范**：
   * 本仓库为公开仓库，**严禁添加任何 API Key、密码、个人 Token 等敏感信息**。
