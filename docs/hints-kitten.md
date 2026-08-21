# Hints Kitten — 屏幕选词（URL / 路径 / 行号）

Hints Kitten 扫描当前终端屏幕，把 URL、文件路径、行号等标注成可选字母，按对应字母即可执行（打开、编辑、复制）。不用鼠标拖选，也不会因为路径太长而选错。

## 本仓库绑定

按 `ctrl+p` 松开，再按对应键（沿用 tmux 前缀风格，不与已有 `ctrl+p>` 绑定冲突）：

| 键 | 作用 | 命令 |
|---|---|---|
| `ctrl+p` `u` | 屏幕选 URL，用浏览器打开 | `kitten hints --type url` |
| `ctrl+p` `f` | 屏幕选文件路径，用 nvim 打开 | `kitten hints --type path --program nvim` |
| `ctrl+p` `y` | 屏幕选一行文本，复制到剪贴板 | `kitten hints --type line --program @` |

`u` = URL，`f` = file，`y` = yank（复制）。

`--program @` 表示把选中内容复制到剪贴板（`@` 是 Kitty 里剪贴板的占位符）。

## 怎么用

1. 终端屏幕上出现了 URL / 路径 / 日志行。
2. 按 `ctrl+p` 松开，再按 `u` / `f` / `y`。
3. Kitty 在每个匹配项旁标一个字母。
4. 按对应字母选中并执行。

## 配置位置

`kitty.conf.tmpl` 里 `# ===== Hints / Search / Scroll Marks =====` 一节。原来注释掉的 `alt+p` / `alt+f` / `alt+l` 旧绑定已删除，统一到 `ctrl+p>` 前缀下。

```text
map ctrl+p>u kitten hints --type url
map ctrl+p>f kitten hints --type path --program nvim
map ctrl+p>y kitten hints --type line --program @
```

## 排障

- **按键无反应**：确认 `chezmoi apply --force` 已执行，`~/.config/kitty/kitty.conf` 里有对应 `map` 行。改配置后需重载（`kitty @ load-config` 或重启 Kitty）才生效；本仓库约定只改源 + apply，不自动重载。
- **没有标注字母出现**：当前屏幕没有匹配 `--type` 的内容。`url` 只匹配屏幕已显示的 URL，不搜 scrollback。
- **打开 URL 用了错误的程序**：`--type url` 用系统默认浏览器；想换程序用 `--program <cmd>`。
- **nvim 不在 PATH**：`--program nvim` 找不到 nvim 会报错。确认 `which nvim` 能找到。
- **想选别的类型**：Kitty 还支持 `--type hash`（Git commit）、`--type ip`、`--type regex --regex <pattern>` 等，详见 `kitten hints --help`。

## 局限

- 只扫屏幕已显示内容，不搜整个 scrollback。
- 屏幕内容很多时标注字母可能密集。
- 复杂正则类型比普通文本略慢。

---

本文件由 chezmoi 管理，源在 `~/chezmoi/dot_config/kitty/docs/hints-kitten.md`。