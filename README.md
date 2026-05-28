# html-visual-editor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Latest](https://img.shields.io/github/v/release/ytisvibecoding/html-visual-editor)](https://github.com/ytisvibecoding/html-visual-editor/releases)

> **把任意静态 HTML 变成可视化编辑版 · 点文字直接改 · 调颜色字号布局 · 让 AI 帮你重塑样式 · 一键导出**

> **Turn any static HTML into a visually editable page** — click to edit text, tweak colors/fonts/layout in a side panel, copy style prompts for AI to restyle, one-click clean export.

```text
┌─── Page Content ────────────────────────────┐ ┌── Style Panel ──┐
│  Click any text to edit                     │ │ Colors          │
│  Hover element → see adjustable props       │ │ Style Prompts   │
│  Press P to pin → swatch + value + extract  │ │ Layout          │
│  Toolbar: Edit · Undo · Export · 中 / EN    │ │ Font Size       │
└─────────────────────────────────────────────┘ └─────────────────┘
```

---

## 🚀 30 秒上手 / Get started in 30s

**需要 Python 3.9+ 和 `beautifulsoup4`，仅此而已 / Only requires Python 3.9+ and `beautifulsoup4`**

```bash
git clone https://github.com/ytisvibecoding/html-visual-editor.git
cd html-visual-editor
pip install beautifulsoup4

# 把你的 HTML 变成可视化编辑版 / Make your HTML visually editable
python scripts/adapt.py /path/to/your-report.html

# 打开生成的 *-editable.html，开始编辑 / Open the *-editable.html, start editing
open /path/to/your-report-editable.html
```

完成。`your-report-editable.html` 旁边会多出一个工具栏和右侧样式面板。
Done. A toolbar and side panel will appear next to your report.

---

## ✨ 能做什么 / What it does

| | |
|---|---|
| 🖱️ **就地文字编辑** Inline text editing | 点页面任何文字直接改，支持撤销 / Click any text to edit; supports undo |
| 🎨 **颜色面板** Color panel | 扫 DOM 实测用色，列出 top 5 文字色 / top 4 背景 / top 3 边框。蓝主题红主题绿主题都自动适配 / Scans the DOM, ranks colors by actual usage — works for any theme |
| 🔤 **字号面板** Font-size panel | 自动归类 ≤10 项滑块，分 3 组（标题 / 正文 / 辅助）/ ≤10 sliders auto-grouped into Heading / Body / Auxiliary |
| 📐 **布局面板** Layout panel | 7 项：页面宽度 / 内距 / 段落宽 / **行高** / 章节间距 / 卡片间距 / 卡片内距 / 7 sliders incl. Line Height |
| 🎭 **6 张风格 Prompt 卡** Style Prompts | 点击 → 把"色板 + 氛围 + 硬约束"一整段 prompt 复制给 AI，让 AI 重写 CSS / Click → copy a complete style prompt to clipboard, paste to any AI |
| 📌 **Pinned 元素弹窗** Pinned tooltip | Hover 看可调项；按 P 固定；漏色一键提取为变量 / Hover for adjustable props; press P to pin; missing colors get a one-click extract button |
| 🌐 **可拖动工具栏 + 中 / EN 双显** | 工具栏可拖到任意位置；两种语言永远同时可见，激活态高亮 / Draggable toolbar; both languages always visible, active state highlighted |
| 📤 **导出干净版** Export Clean | 一键剥离编辑器；inline `var()` 还原为 hex，剪贴到 Notion / 邮件不丢色 / One-click clean export; inline `var()` restored to hex (clipboard-safe) |
| ✅ **20+ Sanity Checks** | 出错不输出文件，避免坏件 / Won't output broken files |

---

## 📺 试一下 demo / Try the demo

```bash
python scripts/adapt.py examples/demo-report.html --force
open examples/demo-report-editable.html
```

---

## 🛠️ 作为 AI Agent Skill 安装 / Install as an AI Agent Skill

This tool ships as a Skill for AI coding agents. 把整个仓库目录拷贝到你的 Agent skills 路径即可：

```bash
# 1. 先把仓库 clone 到本地 / Clone the repo
git clone https://github.com/ytisvibecoding/html-visual-editor.git
cd html-visual-editor

# 2. 拷贝到你的 Agent skills 目录 / Copy to your agent's skills folder
# WorkBuddy / CodeBuddy：
mkdir -p ~/.workbuddy/skills/html-visual-editor && cp -r ./* ~/.workbuddy/skills/html-visual-editor/

# Claude Code：
mkdir -p ~/.claude/skills/html-visual-editor && cp -r ./* ~/.claude/skills/html-visual-editor/

# Cursor / 其它 Agent：放到项目目录，在规则中引用 scripts/adapt.py / Place in project dir, reference scripts/adapt.py in your agent rules
```

然后用自然语言让 Agent 调它 / Then ask your agent in plain language:

> "把这个 HTML 做成可编辑版" / "Make this HTML editable" / "Add a style panel to this page"

也可以从 [ClawHub](https://clawhub.ai/) 等 skill 商店直接安装最新版。
Also installable from skill marketplaces like ClawHub.

---

## 🔧 工作原理 / How it works

```text
HTML ──► parse_css.py        抽取 CSS 变量 / font-size / 颜色 / 选择器
     ──► scan_dom.py         按字符数 / 元素数实测聚合颜色用法（top-N）
     ──► generate_panel.py   生成 颜色 / 字号 / 布局 面板 + 风格 Prompt 卡
     ──► inject.py           注入 toolbar + 面板 + editor-core.js/css
     ──► verify.py           跑 20+ sanity checks，过不了不出文件
     ──► your-report-editable.html
```

---

## 📋 兼容性 / Compatibility

| Level | 条件 / Condition | 结果 / Result |
|---|---|---|
| **A** ✅ | `<style>` + 5+ CSS 变量 / `<style>` block with 5+ CSS variables in `:root` | 全自动效果最佳 / Full auto, best results |
| **B** ⚠️ | 变量少 / 外链 CSS / Tailwind / Few vars, external CSS, Tailwind | 文字编辑 + 数据驱动颜色仍可用 / Text editing + data-driven colors still work |
| **C** ⚠️ | inline style 主导 / Mostly inline styles | 文字编辑可用；建议先用 Style Prompt 让 AI 把 inline 重构为变量 / Text editing works; use Style Prompt to refactor inline → vars first |

---

## 🤖 LLM 增强标签（可选）/ Optional: LLM-enhanced labels

不配置也能跑（启发式命名兜底）。配置后变量名更语义化。/ Works without any key (heuristic naming fallback); with a key, CSS variable labels become semantic.

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # 或 / or
export OPENAI_API_KEY=sk-...
```

---

## 🗺️ Roadmap

- [ ] 图片编辑 / Image editing (replace, resize)
- [ ] 拖拽排版 / Drag-and-drop layout reordering
- [ ] 更多预设主题 / More preset themes (PRs welcome!)
- [ ] 浏览器插件版 / Browser extension
- [ ] Undo 历史分支 / Undo branch visualization

---

## 🤝 参与贡献 / Contributing

PR 欢迎 / PRs welcome:

1. Fork → Branch → PR
2. 跑通 `python scripts/adapt.py examples/demo-report.html --verbose`
3. 新文件保留 MIT 头 / Keep MIT header in new files

---

## 📦 Changelog

完整版本历史请见 [GitHub Releases](https://github.com/ytisvibecoding/html-visual-editor/releases) / Full version history on [Releases](https://github.com/ytisvibecoding/html-visual-editor/releases).

<details>
<summary>展开历史版本 / Expand history</summary>

### v1.8.4 (2026-05-28)
- Pinned 提取按钮按颜色来源分流：inline 写死 → 一键提取为 `var()`；CSS 规则 / 继承 / 复杂表达式 → 复制提示让 AI 改
- Pinned extract button now branches by source: inline → one-click variable; CSS rule / inheritance / complex → copy AI prompt

### v1.8.3 (2026-05-28)
- 工具栏语言切换改为 `中 / EN` 双显，激活态高亮
- 颜色行 label 去角色前缀（section title 已经标明 Text / Bg / Border）
- 一键提取（ε 方案）：智能命名 + 用户改名 + DOM inline 改为 `var()`，画面立即联动
- 导出时 inline `var()` 还原为 hex（剪贴到 Notion / 邮件不丢色）

### v1.8.2 (2026-05-27)
- 导出干净版不再残留 pinned 弹窗 DOM
- Pinned 弹窗每行加色块 + 数值；漏色提示 + 一键提取按钮

### v1.8.1 (2026-05-26)
- 颜色 label 加角色前缀；风格卡片加 flow hint
- 字号 family pattern 加固（裸 tag 直命中）

### v1.8.0 (2026-05-26)
- **颜色面板完全数据驱动**：scan_dom 按 DOM 文字字符数 / 元素数实测聚合，输出 top-N
- 频次语义命名：主要 / 次要 / 强调 / 装饰 / 偶用，跨主题通用

### v1.7.0 (2026-05-26)
- Colors 38 → ≤12；Size 25 → ≤10；Layout 新增行高
- 「导出干净版 Export Clean」（方案 B：保留 data-editable 便于二次 adapt）

### v1.6.x (2026-05-26)
- 6 套 MECE 场景风格替代旧 SaaS 配色
- Undo / tooltip / 重复清理修复

### v1.5.0 (2026-05-26)
- **风格切换从"改 CSS"改为"复制 Prompt 给 AI"** — 6 张卡片，点击复制完整 prompt（色板 + 氛围 + 硬约束）到剪贴板

### v1.4.0 (2026-05-26)
- 可拖动工具栏（位置 localStorage 持久化）
- i18n: `data-i18n` + 自动检测 `navigator.language`

### v1.3.0 ~ v1.2.0 (2026-05-26)
- 对比度修正 / 渐变色提取 / 状态恢复

### v1.1.0 (2026-05-25)
- `extract_solid_hex_to_vars()`：硬编码 hex 自动提取为 CSS 变量（颜色变量数 ~6 → ~30）
- 滑块状态持久化 / 动态 PEM

### v1.0.0 (2026-05-24)
- 首次发布 / Initial release

</details>

---

## 📄 License

[MIT](LICENSE) — 个人 / 商业用途均免费 / free for personal and commercial use.
