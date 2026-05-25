# html-visual-editor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Turn any static HTML into a visually editable page — no code changes needed.**

Click text to edit inline, adjust colors/fonts/layout from a side panel, apply preset themes, and export the result as a new HTML file.

把任意静态 HTML 变成「可视化编辑版」：点文字直接改，右侧面板调颜色、字号、布局和主题预设，最后导出新 HTML。

```text
┌─────────────────────────────── Page Content ───────────────────────────────┐ ┌── Style Panel ──┐
│  Titles / paragraphs / tables / cards / timelines — all clickable          │ │ Colors          │
│  Hover → hints; Click hint → jump to control                              │ │ Presets         │
│                                                                            │ │ Layout          │
│  Toolbar: Edit / Save / Undo / Export / Reset                              │ │ Font Size       │
└────────────────────────────────────────────────────────────────────────────┘ └─────────────────┘
```

## ✨ Highlights

| Feature | Description |
|---------|-------------|
| 🖱️ **Inline text editing** | Auto-marks headings, paragraphs, tables, labels, stat cards as editable |
| 🎨 **Color panel** | Reads CSS variables; even extracts hardcoded gradient colors into adjustable variables |
| 🔤 **Font size sliders** | Scans host CSS `font-size` rules → generates precise sliders per selector |
| 📐 **Layout sliders** | Page width, padding, section/card spacing — all mapped to real DOM selectors |
| 🎭 **6 preset themes** | Deep Ocean · Twilight Purple · Warm White · Rainbow Arc · Moss Earth · Charcoal Night |
| 🔗 **Bidirectional jump** | Hover element → see adjustable props; click hint → panel jumps to the right control |
| ✅ **34 sanity checks** | Auto-verify mapping, presets, coverage, injection order before writing output |
| 🤖 **Optional LLM labels** | Smarter variable names with Anthropic/OpenAI API (falls back to heuristics) |

## 🚀 Quick Start

```bash
pip install beautifulsoup4
python html-visual-editor/scripts/adapt.py your-report.html
open your-report-editable.html
```

**快捷开始（中文）**：只需一行命令，即可把静态 HTML 变成可视化编辑版。

### Specify output path

```bash
python html-visual-editor/scripts/adapt.py your-report.html -o output.html --force
```

### Skip sanity checks (for complex layouts)

```bash
python html-visual-editor/scripts/adapt.py your-report.html --force --skip-checks
```

> ⚠️ `--skip-checks` forces output even if some checks fail. Review the result manually.

## 📺 Demo

```bash
python html-visual-editor/scripts/adapt.py html-visual-editor/examples/demo-report.html --force --verbose
open html-visual-editor/examples/demo-report-editable.html
```

## 🔧 How It Works

```text
HTML
  ↓ parse_css.py       →  Extract CSS variables, font-size, colors, selectors
  ↓ scan_dom.py         →  Scan DOM, build element → panel mapping
  ↓ generate_panel.py   →  Generate color/font/layout/preset panels + window.X constants
  ↓ inject.py           →  Inject toolbar, panel, editor-core CSS/JS, mark data-editable
  ↓ verify.py           →  Run 34 sanity checks; abort if critical issues found
  → Output: *-editable.html
```

## 📋 Compatibility Levels

| Level | Condition | Result |
|-------|-----------|--------|
| **A** ✅ | `<style>` + 5+ CSS variables in `:root` | Full auto — best results |
| **B** ⚠️ | Few variables, external CSS, or Tailwind | Degraded — text editing + partial panels work |
| **C** ❌ | Mostly inline styles, canvas/iframe | Refused — not worth auto-adapting |

## 🛠️ Install as AI Agent Skill

Works with **WorkBuddy**, **CodeBuddy**, **Claude Code**, **Cursor**, or any AI coding agent:

```bash
# WorkBuddy / CodeBuddy
cp -r html-visual-editor/ ~/.workbuddy/skills/html-visual-editor/

# Claude Code
cp -r html-visual-editor/ ~/.claude/skills/html-visual-editor/

# Cursor / Other agents
# Place in project dir, reference scripts/adapt.py in your agent rules
```

Then tell your agent:

> "把这个 HTML 做成可编辑版" / "Make this HTML editable" / "Add a style panel to this page"

## 🤖 LLM-Enhanced Labels (Optional)

Without any API key, the tool works fine with heuristic naming. If environment variables are available, it uses LLM to generate semantic labels (e.g. "主色调 Accent" instead of "蓝色 Blue").

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # or
export OPENAI_API_KEY=sk-...
```

## 📁 File Structure

```text
html-visual-editor/
├── SKILL.md                  # Detailed usage guide (详细使用说明)
├── README.md                 # This file
├── LICENSE                   # MIT
├── assets/                   # Editor core CSS/JS & panel template
│   ├── editor-core.css
│   ├── editor-core.js
│   └── panel.template.html
├── presets/                  # 6 themes + LLM label prompt
│   ├── builtin.json
│   └── llm_label_prompt.txt
├── scripts/                  # Core engine modules
│   ├── adapt.py              # Main entry point
│   ├── parse_css.py          # CSS parser
│   ├── scan_dom.py           # DOM scanner
│   ├── generate_panel.py     # Panel config generator
│   ├── inject.py             # HTML injector
│   ├── verify.py             # 34 sanity checks
│   └── utils/
│       └── diagnose_css.py
└── examples/                 # Anonymized demo HTML
    └── demo-report.html
```

## 📝 Changelog

### v1.1.0 (2025-05-25)

- **Solid color extraction**: `extract_solid_hex_to_vars()` extracts hardcoded non-gradient colors (color/background/border) into CSS variables — color variable count increased from ~6 to ~30
- **`--force` cleanup**: `--force` now strips old injection artifacts *before* parsing/scanning, preventing stale data leaks
- **appB16 demoted to WARNING**: sections < 2 no longer fails the build; outputs a warning instead
- **appB21 DOM-based verification**: uses `soup.select()` to validate DOM element existence, eliminating false positives from CSS-only references (dead code)
- **Slider state persistence**: layout/font-size slider positions are saved to localStorage v3 format and restored on reload
- **Complete color save/restore**: `saveToStorage()` iterates all `.color-row input[data-var]` instead of relying on hardcoded DEFAULT_COLORS keys
- **Preset prefix matching**: `_map_preset_to_host_vars()` adds a 3rd-pass prefix pattern match (--text-N / --bg-N / --line-N) for better cross-file preset coverage
- **Dynamic PEM (Panel-Element Mapping)**: removed all 17 hardcoded gold-edition selectors from `editor-core.js` (SIZE_BOUNDS, PAGE_ELEMENT_TO_PANEL, CSS_VAR_TO_ELEMENTS, LAYOUT_TARGET_LABELS now fall back dynamically)
- **Source annotation**: `_html` parameter in `generate_panel.py` now documented as "scan_dom HTML snapshot"

### v1.0.0 (2025-05-24)

- Initial release — turn any static HTML into a visually editable page

## 🗺️ Roadmap

- [ ] Image editing (replace/resize images from panel)
- [ ] Drag-and-drop layout reordering
- [ ] More preset themes (community contributions welcome!)
- [ ] Browser extension version
- [ ] Undo history with branch visualization

## 🤝 Contributing

PRs are welcome! Please:

1. Fork → Branch → PR
2. Run `python scripts/adapt.py examples/demo-report.html --verbose` to verify nothing breaks
3. Keep the MIT license header in new files

## 📄 License

[MIT](LICENSE) — free for personal and commercial use.

---

**中文说明**

### 核心功能

- **就地文字编辑**：自动给正文、标题、表格、标签、数字卡片等文本元素加可编辑能力
- **颜色面板**：自动读取 CSS 变量；渐变里的硬编码色也会被提取成可调变量
- **字号面板**：从 host CSS 的 `font-size` 规则反推 slider，覆盖不同文字层级
- **布局面板**：页面宽度、段落宽度、章节间距、卡片间距、卡片内距等一键调
- **6 套主题**：深海商务、幕光紫、手帐暖白、彩虹弧光、苔藓大地、炭火暗夜
- **34 项自检**：映射、预设、字号覆盖率、可编辑覆盖率、注入顺序全部自动检查

### 安装为 Skill

把整个 `html-visual-editor/` 目录放到对应工具可读取的位置：

| 工具 | 路径 |
|------|------|
| WorkBuddy / CodeBuddy | `~/.workbuddy/skills/html-visual-editor/` |
| Claude Code | `~/.claude/skills/html-visual-editor/` |
| Cursor / 其它 Agent | 项目目录或任意稳定路径，规则中引用 `scripts/adapt.py` |
| 手动使用 | `python /path/to/scripts/adapt.py <html>` |

### 实操原则

- 优先运行 `adapt.py`，不要手写 panel
- 不修改 `assets/editor-core.js`，所有适配逻辑放在 scripts 和 window.X 常量里
- 生成结果要先人工抽查：文字是否都可编辑、字号 tab 是否覆盖不同文字层级、预设是否明显生效
