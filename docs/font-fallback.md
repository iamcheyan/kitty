# 字体回退链（symbol_map）— CJK 与 Emoji

## 当前状态：暂不启用

这项配置曾在本机 Kitty 中试用，但启用后出现 zsh 字符显示异常和方块光标问题，因此已从 `kitty.conf.tmpl` 回滚。当前使用原来的 `Adwaita Mono` 配置，优先保证终端稳定。

下面保留原理、候选字体和回滚方案，后续如重新尝试，应先在独立 Kitty 实例中验证。

主字体 `Adwaita Mono` 是等宽英文字体，不含中文、日文、韩文、Emoji。Kitty 的 `symbol_map` 让指定 Unicode 范围用别的字体渲染，这样中文不会变方框、Emoji 不显示乱码、中英文混排更整齐。

```text
# CJK 统一表意文字、扩展、部首、标点、全角符号、假名 → Hiragino Sans GB
symbol_map U+3000-U+303F Hiragino Sans GB
symbol_map U+3040-U+309F Hiragino Sans GB
symbol_map U+30A0-U+30FF Hiragino Sans GB
symbol_map U+3400-U+4DBF Hiragino Sans GB
symbol_map U+4E00-U+9FFF Hiragino Sans GB
symbol_map U+F900-U+FAFF Hiragino Sans GB
symbol_map U+FF00-U+FFEF Hiragino Sans GB
symbol_map U+20000-U+2A6DF Hiragino Sans GB
symbol_map U+2A700-U+2B73F Hiragino Sans GB
symbol_map U+2B740-U+2B81F Hiragino Sans GB
symbol_map U+2B820-U+2CEAF Hiragino Sans GB
# Emoji 与杂项符号 → Apple Color Emoji
symbol_map U+2600-U+26FF Apple Color Emoji
symbol_map U+2700-U+27BF Apple Color Emoji
symbol_map U+1F000-U+1F02F Apple Color Emoji
symbol_map U+1F0A0-U+1F0FF Apple Color Emoji
symbol_map U+1F100-U+1F1FF Apple Color Emoji
symbol_map U+1F200-U+1FAFF Apple Color Emoji
```

## 字体选择依据

配置前先用 `fc-list` 探测本机实际安装的字体（macOS）：

```sh
fc-list :lang=zh family 2>/dev/null | sort -u | head -20
fc-list | grep -i 'emoji\|apple color emoji' | head -10
fc-list | grep -i 'hiragino\|pingfang\|noto.*cjk' | head -20
```

本机确认存在：

- **`Hiragino Sans GB`** — 简体中文 + CJK 表意文字，macOS 自带。`PingFang SC` 在本机 `fc-list` 里没有出现（系统字体未挂到 fontconfig），所以选 Hiragino Sans GB。
- **`Apple Color Emoji`** — macOS 系统彩色 Emoji 字体。

覆盖的 Unicode 范围：

| 范围 | 内容 | 字体 |
|---|---|---|
| `U+3000-U+303F` | CJK 标点符号 | Hiragino Sans GB |
| `U+3040-U+309F` | 平假名 | Hiragino Sans GB |
| `U+30A0-U+30FF` | 片假名 | Hiragino Sans GB |
| `U+3400-U+4DBF` | CJK 扩展 A | Hiragino Sans GB |
| `U+4E00-U+9FFF` | CJK 统一表意文字（基本） | Hiragino Sans GB |
| `U+F900-U+FAFF` | CJK 兼容表意文字 | Hiragino Sans GB |
| `U+FF00-U+FFEF` | 全角/半角形式 | Hiragino Sans GB |
| `U+20000-U+2CEAF` | CJK 扩展 B/C/D/E | Hiragino Sans GB |
| `U+2600-U+27BF` | 杂项符号 + 装饰符号（ ☀ ☂ ✂ 等） | Apple Color Emoji |
| `U+1F000-U+1FAFF` | Emoji（😀 🎉 等） | Apple Color Emoji |

## 排障

- **中文还是方框**：确认 `~/.config/kitty/kitty.conf` 有 `symbol_map` 行（`grep symbol_map ~/.config/kitty/kitty.conf`），并已 `chezmoi apply --force` + 重载 Kitty。
- **字体名拼错**：Kitty 找不到字体名时会静默回退。用 `fc-list | grep -i 'Hiragino Sans GB'` 确认名称完全一致（区分大小写、空格）。
- **彩色 Emoji 宽度不对**：彩色 Emoji 是变宽字形，在等宽终端里可能和单元格对不齐，这是 Kitty 已知行为，不影响功能。
- **换机器后字体不存在**：Linux 上没有 Hiragino Sans GB / Apple Color Emoji。Linux 机器上可改用 `Sarasa Mono SC`（CJK）+ `Noto Color Emoji`。本模板目前未按 OS 分支区分 symbol_map，需要的话用 `{{ if eq .chezmoi.os "darwin" }}` 包住。

## 局限

- `symbol_map` 按精确 Unicode 范围匹配；不在列出的范围里的字形（如某些少数民族文字）仍走主字体，可能还是方框。按需追加范围。
- 主字体 `Adwaita Mono` 与 Hiragino Sans GB 的字宽不完全一致，中英文混排时列宽可能有微小错位。

---

本文件由 chezmoi 管理，源在 `~/chezmoi/dot_config/kitty/docs/font-fallback.md`。