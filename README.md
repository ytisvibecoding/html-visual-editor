# html-visual-editor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Latest](https://img.shields.io/github/v/release/ytisvibecoding/html-visual-editor)](https://github.com/ytisvibecoding/html-visual-editor/releases)

**给 AI Agent 用的 Skill：把任意静态 HTML 变成可视化编辑版**
**An AI Agent Skill: turn any static HTML into a visually editable page**

点文字直接改 · 调颜色字号布局 · 复制风格 prompt 给 AI 重写 CSS · 一键导出干净 HTML
Click-to-edit text · adjust colors/fonts/layout · copy style prompts for AI · clean one-click export

```text
┌─── 你的 HTML ───────────────────────────────┐ ┌── 样式面板 ─────┐
│  Click any text to edit                     │ │ 颜色 Colors     │
│  Hover → see adjustable props               │ │ 风格 Styles     │
│  Press P to pin · swatch + value + extract  │ │ 布局 Layout     │
│  Toolbar: 编辑 · 撤销 · 导出 · 中 / EN       │ │ 字号 Font Size  │
└─────────────────────────────────────────────┘ └─────────────────┘
```

---

## ⚡ 怎么用 / How to use

**这是一个给 AI Agent 用的 skill**，你不用懂代码，**对你的 AI 说人话就行**：
This is a skill for AI agents — you don't need to code. **Just talk to your AI in plain language:**

```
> 帮我把这个 HTML 做成可视化编辑版
> Make this HTML visually editable
> 给这份报告加个样式面板，我想调颜色和字号
> Add a style panel to this page so I can tweak colors and fonts
> 用 html-visual-editor 处理 ~/Downloads/report.html
> Use html-visual-editor on ~/Downloads/report.html
```

AI 会自动调起这个 skill，跑完后你会拿到一个 `*-editable.html` 文件，直接双击打开就有工具栏和样式面板。
Your agent will invoke this skill automatically; you'll get a `*-editable.html` file — open it and start editing visually.

---

## 📦 装到你的 AI Agent / Install into your AI agent

### 选项 A：从 Skill 商店一键安装 / Install from a skill marketplace（推荐）

- **[ClawHub](https://clawhub.ai/ytisvibecoding/html-editor)** — 直接打开链接，点 Install。/ Open the link and click Install.
- **[SkillHub](https://skillhub.cn/skill/html-editor)** — 直接打开链接，点安装。/ Open the link and click Install.
- **CodeBuddy / WorkBuddy** — 在 skill marketplace 里搜索 `html-editor` 安装。/ Search `html-editor` in the in-app marketplace.

> 备注：商店里的名字是 `html-editor`（GitHub 仓库名是 `html-visual-editor`，对应同一个 skill）/ Note: the marketplace listing is `html-editor`; the GitHub repo is `html-visual-editor` — same skill.

装完直接对 agent 说："**帮我把这个 HTML 做成可编辑版**"。
After install, just say to your agent: "**Make this HTML editable.**"

### 选项 B：让 AI 帮你手动装 / Let your AI install it manually

对 AI 说这句话（一字不差复制即可）/ Copy this verbatim to your AI:

> **请帮我安装这个 AI Agent skill：https://github.com/ytisvibecoding/html-visual-editor
> 这是一个 html visual editor，让我可以用样式面板可视化编辑任意 HTML。
> 请克隆仓库，并把整个目录拷贝到我当前 Agent 的 skills 路径下，命名为 `html-visual-editor`。
> 装完告诉我怎么调用。**

> **Please install this AI Agent skill: https://github.com/ytisvibecoding/html-visual-editor
> It's an html-visual-editor that lets me visually edit any HTML through a style panel.
> Clone the repo and copy the whole directory into my current agent's skills folder, named `html-visual-editor`.
> Tell me how to invoke it after installing.**

AI 会自动判断路径（WorkBuddy → `~/.workbuddy/skills/`，Claude Code → `~/.claude/skills/`，Cursor → 项目目录，等等）。
The AI will figure out the right path (WorkBuddy → `~/.workbuddy/skills/`, Claude Code → `~/.claude/skills/`, Cursor → project dir, etc.).

### 选项 C：脱开 Agent 直接命令行用 / Use directly from CLI (without an agent)

```bash
git clone https://github.com/ytisvibecoding/html-visual-editor.git
cd html-visual-editor
pip install beautifulsoup4
python scripts/adapt.py /path/to/your-report.html
open /path/to/your-report-editable.html
```

---

## ✨ 装好以后能做什么 / What you get after installing

| | |
|---|---|
| 🖱️ **就地文字编辑** Inline text editing | 点页面任何文字直接改，支持撤销 / Click any text to edit, with undo |
| 🎨 **颜色面板** Color panel | 扫 DOM 实测用色：top 5 文字色 / top 4 背景 / top 3 边框。蓝主题红主题绿主题都自动适配 / Scans the DOM, ranks colors by actual usage — works for any theme |
| 🔤 **字号面板** Font-size panel | ≤10 项滑块，分 3 组（标题 / 正文 / 辅助）/ ≤10 sliders auto-grouped into Heading / Body / Auxiliary |
| 📐 **布局面板** Layout panel | 7 项：页面宽度 / 内距 / 段落宽 / **行高** / 章节间距 / 卡片间距 / 卡片内距 |
| 🎭 **6 张风格 Prompt 卡** Style Prompts | 点击 → 把完整 prompt（色板 + 氛围 + 硬约束）复制给 AI，让 AI 重写整份 CSS / Click → copy a full style prompt to clipboard, paste to any AI |
| 📌 **Pinned 元素弹窗** Pinned tooltip | Hover 看可调项；按 P 固定；漏色一键提取为变量 / Hover for props, press P to pin, missing colors → one-click extract |
| 🌐 **可拖动工具栏 + 中 / EN 双显** | 工具栏可拖；两种语言永远同时可见，激活态高亮 / Draggable toolbar; both languages always visible |
| 📤 **导出干净版** Export Clean | 一键剥离编辑器；inline `var()` 还原为 hex，剪贴到 Notion / 邮件不丢色 / One-click clean export; `var()` restored to hex (clipboard-safe) |

---

## 📺 看下 demo / See it in action

让 AI 处理仓库自带的 demo（不需要你提供 HTML）/ Ask your agent to try the bundled demo:

> 用 html-visual-editor 处理一下它仓库里的 `examples/demo-report.html`，给我看看效果
> Use html-visual-editor on its bundled `examples/demo-report.html` and show me

或者命令行 / Or directly:

```bash
python scripts/adapt.py examples/demo-report.html --force
open examples/demo-report-editable.html
```

---

## 📋 兼容性 / Compatibility

| Level | 条件 / Condition | 结果 / Result |
|---|---|---|
| **A** ✅ | `<style>` + 5+ CSS 变量 / CSS variables in `:root` | 全自动效果最佳 / Full auto, best results |
| **B** ⚠️ | 变量少 / 外链 CSS / Tailwind | 文字编辑 + 数据驱动颜色仍可用 / Text editing + data-driven colors still work |
| **C** ⚠️ | inline style 主导 / Mostly inline styles | 文字编辑可用；建议先让 AI 把 inline 重构为 CSS 变量 / Text editing works; ask AI to refactor inline → vars first |

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

## 🤖 LLM 增强标签（可选）/ Optional: LLM-enhanced labels

不配置也能跑（启发式命名兜底）。配置后变量名更语义化。/ Works without any key; with a key, CSS variable labels become semantic.

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

完整版本历史请见 [Releases](https://github.com/ytisvibecoding/html-visual-editor/releases) / Full version history on [Releases](https://github.com/ytisvibecoding/html-visual-editor/releases).

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
- `extract_solid_hex_to_vars()`：硬编码 hex 自动提取为 CSS 变量
- 滑块状态持久化 / 动态 PEM

### v1.0.0 (2026-05-24)
- 首次发布 / Initial release

</details>

---

## 📄 License

[MIT](LICENSE) — 个人 / 商业用途均免费 / free for personal and commercial use.
