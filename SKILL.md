---
name: html-visual-editor
version: "1.1.0"
description: "把任意静态 HTML 转成可视化编辑版：注入工具栏、颜色/字号/布局/预设面板、就地文字编辑、撤销保存导出、元素与面板双向跳转。适用于用户说可编辑版HTML、html可视化编辑、让html可编辑、样式面板、改html不写代码、所见即所得、点击直接编辑、把报告/页面/演示稿变成可调样式。"
agent_created: true
---

# html-visual-editor

把任意静态 HTML 升级成「可视化编辑版」：文字可直接点开编辑，右侧面板可调颜色、字号、布局和主题预设，改完可导出新的 HTML。

## 一行使用

```bash
python <skill-dir>/scripts/adapt.py <your-report.html>
# 输出：<your-report>-editable.html
```

指定输出路径：

```bash
python <skill-dir>/scripts/adapt.py <your-report.html> -o <your-report>-editable.html --force
```

依赖只有一个：

```bash
pip install beautifulsoup4
```

## 生成后的能力

打开生成的 `*-editable.html`，页面会多出左上工具栏和右侧样式面板：

- **文字编辑**：点击页面文字直接改；支持撤销、保存到浏览器、导出新 HTML。
- **颜色**：自动提取 `:root` CSS 变量；自动把渐变里的硬编码色提取成变量，例如 `linear-gradient(..., #003DA5)` 会变成可调色块。
- **字号**：逐条扫描 host CSS 的 `font-size` 规则，自动生成 slider；目标选择器使用真实组合选择器，例如 `.header h1`、`.stat-card .number`，避免裸 `h1/p/li` 误伤其它区域。
- **布局**：自动生成页面宽度、内距、章节间距、卡片间距等 slider，并映射到真实 DOM 选择器。
- **预设**：6 套内置主题一键切换：深海商务、幕光紫、手帐暖白、彩虹弧光、苔藓大地、炭火暗夜。
- **双向跳转**：hover 页面元素会提示可调项；点击提示会自动切到对应 tab 并高亮面板控件。

## 工作原理

```text
HTML
  ↓ parse_css.py
抽取 CSS 变量、font-size、background、color、选择器规则
  ↓ scan_dom.py
扫描 DOM、生成元素到面板的映射
  ↓ generate_panel.py
生成颜色/字号/布局/预设面板与 window.X 常量
  ↓ inject.py
注入 toolbar、panel、editor-core.css/js，并标记 data-editable
  ↓ verify.py
运行 34 项 sanity checks；失败则不产出坏件
```

## LLM 增强（可选）

不配置 API key 也能跑，启发式命名会兜底。若环境变量可用，会使用 LLM 给 CSS 变量生成更语义化的 label，例如「主色调 Accent」而不是「蓝色 Blue」。

支持的环境变量：

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

## 兼容性

- **Level A，全自动**：HTML 内有 `<style>`，且 `:root` 里有 5 个以上 CSS 变量；效果最好。
- **Level B，降级可用**：CSS 变量少、外链 CSS、Tailwind/utility class 较多；文字编辑和部分面板仍可用。
- **Level C，拒绝生成**：几乎全是 inline style、canvas/iframe 主导、或完全没有可分析样式；生成面板意义不大。

## 安装位置

把整个 `html-visual-editor/` 目录放到对应工具可读取的位置：

- WorkBuddy / CodeBuddy：`~/.workbuddy/skills/html-visual-editor/`
- Claude Code：`~/.claude/skills/html-visual-editor/` 或项目级 skills 目录
- Cursor：放到任意项目目录，并在规则或说明中引用 `scripts/adapt.py`
- 手动使用：直接运行 `python /path/to/html-visual-editor/scripts/adapt.py <html>`

## 快速 demo

```bash
python <skill-dir>/scripts/adapt.py <skill-dir>/examples/demo-report.html --force --verbose
open <skill-dir>/examples/demo-report-editable.html
```

## 质量守门

`adapt.py` 会自动运行 34 项检查，重点覆盖：

- panel label 与 `PAGE_ELEMENT_TO_PANEL` row 字符级一致
- `PRESETS` 为 flat 格式，且变量名能映射到 host CSS 变量
- 字号 slider 覆盖 host 中至少 80% 的 `font-size` 规则
- 字号 slider 禁止使用裸 `h1/p/li` 这类易误伤选择器
- `data-editable` 覆盖率达标
- 无 `applyFallbackSize` / `applyFallbackLayout` 等绕开核心引擎的 shim
- 打包后无个人绝对路径依赖

若检查失败，修源 HTML 或脚本，不要绕过检查。

## 文件结构

```text
html-visual-editor/
├── SKILL.md
├── README.md
├── LICENSE
├── assets/
│   ├── editor-core.css
│   ├── editor-core.js
│   └── panel.template.html
├── presets/
│   ├── builtin.json
│   └── llm_label_prompt.txt
├── scripts/
│   ├── adapt.py
│   ├── parse_css.py
│   ├── scan_dom.py
│   ├── generate_panel.py
│   ├── inject.py
│   ├── verify.py
│   └── utils/diagnose_css.py
└── examples/
    └── demo-report.html
```

## 实操原则

- 优先运行 `adapt.py`，不要手写 panel。
- 不修改 `assets/editor-core.js`，所有适配逻辑放在 scripts 和 window.X 常量里。
- 生成结果要先人工抽查：文字是否都可编辑、字号 tab 是否覆盖不同文字层级、预设是否明显生效。
