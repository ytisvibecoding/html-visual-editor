#!/usr/bin/env python3
"""
generate_panel.py -- 面板生成模块 (v15 public package)
基于 ParseResult + ScanResult 生成 panel DOM、toolbar DOM 和 window.X 常量。

对应规范: R1-R6, R12, R14, 附录 C (LABEL_FOR), 附录 D Steps 3-7,11
"""

import os
import re
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PanelConfig:
    """面板生成结果"""
    color_rows: list       # [{var, label, default_value}]
    preset_themes: dict    # {name: {var: value}} -- FLAT
    layout_sliders: list   # [{target, prop, unit, min, max, default, label, key}]
    size_sliders: list     # [{target, prop, label, min, max, default, unit, key}]
    panel_html: str        # 渲染好的完整 panel DOM
    toolbar_html: str      # 定制后的 toolbar DOM
    constants_js: str      # window.DEFAULT_COLORS / PRESETS / SIZE_BOUNDS / PAGE_ELEMENT_TO_PANEL / CSS_VAR_TO_ELEMENTS
    label_for: dict        # LABEL_FOR single-source-of-truth


# 面板相关的路径
ASSETS_DIR = Path(__file__).parent.parent / 'assets'
PRESETS_DIR = Path(__file__).parent.parent / 'presets'

# ============================================================
# LABEL_FOR: single-source-of-truth (附录 C)
# {(tab_name, key): label_string}
# tab_name: '颜色' / '字号' / '布局'
# key: 颜色 tab 用 '--var-name'；字号/布局 tab 用 selector 字符串
# ============================================================
LABEL_FOR = {}

# 金版已知变量名 -> 语义 label 映射（启发式兜底）
GOLD_VAR_LABELS = {
    '--accent': '主色调 Accent',
    '--accent-soft': '主色浅 Accent Soft',
    '--warm': '暖色 Warm',
    '--warm-soft': '暖色浅 Warm Soft',
    '--gold': '金色 Gold',
    '--gold-soft': '金色浅 Gold Soft',
    '--sage': '青绿 Sage',
    '--sage-soft': '青绿浅 Sage Soft',
    '--bg': '页面底色 BG',
    '--ink': '主文字 Ink',
    '--ink-2': '次文字 Ink-2',
    '--ink-3': '辅文字 Ink-3',
    '--line': '分割线 Line',
    '--line-2': '分割线浅 Line-2',
}

# 颜色分段规则：哪些变量属于「主题色板」，其余归「文字色」
THEME_COLOR_PREFIXES = {'accent', 'warm', 'gold', 'sage', 'bg', 'primary', 'secondary'}
TEXT_COLOR_PREFIXES = {'ink', 'text', 'line', 'border'}

# ============================================================
# SEMANTIC_ALIAS: preset 命名 → host 实际命名候选 (P0-1 修复)
# 按优先级取第一个存在的 host 变量做映射
# ============================================================
SEMANTIC_ALIAS = {
    # 主色调系列
    '--accent':      ['--accent', '--primary', '--blue', '--theme', '--main', '--brand'],
    '--accent-soft': ['--accent-soft', '--accent-light', '--primary-light', '--blue-light', '--theme-light'],
    # 暖色 / 强调
    '--warm':        ['--warm', '--orange', '--accent-2', '--secondary', '--red'],
    '--warm-soft':   ['--warm-soft', '--orange-light', '--red-light'],
    # 金色 / 警示
    '--gold':        ['--gold', '--yellow', '--warning', '--amber'],
    '--gold-soft':   ['--gold-soft', '--yellow-light'],
    # 文字
    '--ink':         ['--ink', '--text', '--text-primary', '--fg', '--foreground', '--text-1'],
    '--ink-2':       ['--ink-2', '--text-muted', '--text-secondary', '--gray', '--text-2'],
    '--ink-3':       ['--ink-3', '--text-light', '--text-tertiary', '--gray-light', '--text-3'],
    # 边框 / 分割
    '--line':        ['--line', '--border', '--divider', '--separator'],
    '--line-2':      ['--line-2', '--border-light'],
    # 背景
    '--bg':          ['--bg', '--background', '--page-bg', '--body-bg'],
    '--bg-card':     ['--bg-card', '--card-bg', '--surface'],
    # 状态色
    '--success':     ['--success', '--green', '--ok'],
    '--success-soft':['--success-soft', '--green-light'],
    '--danger':      ['--danger', '--red', '--error'],
    '--danger-soft': ['--danger-soft', '--red-light'],
    # 青绿（金版有 sage）
    '--sage':        ['--sage', '--green', '--teal', '--mint'],
    '--sage-soft':   ['--sage-soft', '--green-light', '--teal-light'],
}


def _map_preset_to_host_vars(preset_vars: dict, host_var_names: set) -> dict:
    """
    把语义命名的 preset 映射到 host 实际变量名。
    优先级：完全同名 > SEMANTIC_ALIAS 候选。
    """
    mapped = {}
    used_targets = set()  # 避免一个 host 变量被多个 preset 变量映射

    # 第一轮：完全同名
    for var, val in preset_vars.items():
        if var in host_var_names:
            mapped[var] = val
            used_targets.add(var)

    # 第二轮：SEMANTIC_ALIAS 映射
    for var, val in preset_vars.items():
        if var in mapped:
            continue
        candidates = SEMANTIC_ALIAS.get(var, [])
        for candidate in candidates:
            if candidate in host_var_names and candidate not in used_targets:
                mapped[candidate] = val
                used_targets.add(candidate)
                break

    return mapped


# 预设按钮文案 emoji+中文名 (R5.3)
PRESET_DISPLAY_NAMES = {
    'original': '🍀 原版（湖绿）',
    'tencent-blue': '🔵 腾讯蓝',
    'newsprint': '📰 报纸灰',
    'night': '🌙 夜间模式',
    'warm-sepia': '📜 暖棕',
    'executive-navy': '🔵 深海商务',
    'linear-dusk': '🟣 幕光紫',
    'notion-journal': '📒 手帐暖白',
    'arc-gradient': '🌈 彩虹弧光',
    'moss-earth': '🌿 苔藓大地',
    'raycast-noir': '🔥 炭火暗夜',
}


def _parse_size_value(value: str) -> dict:
    """解析尺寸值，返回 {value, unit, min, max}"""
    value = value.strip()
    clamp_match = re.match(r'clamp\(\s*([\d.]+)([\w%]+)\s*,\s*[^,]+\s*,\s*([\d.]+)([\w%]+)\s*\)', value)
    if clamp_match:
        min_val = float(clamp_match.group(1))
        unit = clamp_match.group(2)
        max_val = float(clamp_match.group(3))
        default_val = (min_val + max_val) / 2
        return {'default': default_val, 'min': min_val, 'max': max_val, 'unit': unit}

    num_match = re.match(r'^([\d.]+)\s*(px|em|rem|vw|vh|%)$', value)
    if num_match:
        num = float(num_match.group(1))
        unit = num_match.group(2)
        if unit == 'px':
            min_val = max(8, num * 0.4)
            max_val = num * 3
        elif unit in ('em', 'rem'):
            min_val = max(0.5, num * 0.4)
            max_val = num * 3
        else:
            min_val = max(1, num * 0.3)
            max_val = num * 3
        return {'default': num, 'min': round(min_val, 2), 'max': round(max_val, 2), 'unit': unit}

    return {'default': 16, 'min': 8, 'max': 72, 'unit': 'px'}


def _load_builtin_presets() -> dict:
    """加载内置预设"""
    presets_file = PRESETS_DIR / 'builtin.json'
    if presets_file.exists():
        try:
            with open(presets_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _generate_color_row_html(var_name: str, label: str, default_value: str) -> str:
    """生成单行颜色控件 HTML (R2.2)"""
    hex_value = default_value if re.match(r'^#[0-9a-fA-F]{3,8}$', default_value) else '#888888'
    if len(hex_value) == 4:
        hex_value = f'#{hex_value[1]*2}{hex_value[2]*2}{hex_value[3]*2}'
    hex_upper = hex_value.upper()

    return f'''        <div class="color-row">
            <span class="color-label">{label}</span>
            <div class="color-swatch" style="background:{hex_value};"><input type="color" value="{hex_value}" data-var="{var_name}" onchange="applyColor(this)" oninput="previewColor(this)"></div>
            <input type="text" class="color-hex" value="{hex_upper}" data-var="{var_name}" onchange="applyHex(this)">
        </div>'''


def _generate_slider_html(label: str, key: str, target: str, prop: str, unit: str,
                           min_val, max_val, step, default_val) -> str:
    """
    生成通用 slider HTML (R3.1 / R4.1)
    金版结构: slider-row > slider-label > (slider-name + slider-val[id]) + input[oninput=applyLayout]
    """
    display_val = f"{default_val}{unit}" if unit else str(default_val)
    return f'''        <div class="slider-row">
            <div class="slider-label">
                <span class="slider-name">{label}</span>
                <span class="slider-val" id="val-{key}">{display_val}</span>
            </div>
            <input type="range" min="{min_val}" max="{max_val}" step="{step}" value="{default_val}" data-target="{target}" data-prop="{prop}" data-unit="{unit}" oninput="applyLayout(this, 'val-{key}')">
        </div>'''


def _classify_color_section(var_name: str) -> str:
    """根据变量名判断属于 主题色板 还是 文字色"""
    name = var_name.lstrip('-')
    first_part = name.split('-')[0] if '-' in name else name
    if first_part in TEXT_COLOR_PREFIXES:
        return '文字色'
    return '主题色板'


def _generate_heuristic_label(var_name: str) -> str:
    """启发式生成 label (R2.3 格式: 中文语义 英文PascalCase)"""
    if var_name in GOLD_VAR_LABELS:
        return GOLD_VAR_LABELS[var_name]

    name = var_name.lstrip('-')
    parts = re.split(r'[-_]', name)
    parts = [w for w in parts if w]

    # 中文映射
    WORD_MAP = {
        'primary': '主色', 'secondary': '次色', 'accent': '主色调',
        'bg': '页面底色', 'background': '背景', 'text': '文字',
        'card': '卡片', 'surface': '表面', 'border': '边框',
        'title': '标题', 'body': '正文', 'heading': '标题',
        'blue': '蓝色', 'red': '红色', 'green': '绿色', 'purple': '紫色',
        'orange': '橙色', 'yellow': '黄色', 'pink': '粉色', 'white': '白色',
        'black': '黑色', 'gray': '灰色', 'grey': '灰色', 'dark': '深色',
        'light': '浅色', 'muted': '弱化', 'subtle': '淡化',
        'ink': '文字', 'warm': '暖色', 'gold': '金色', 'sage': '青绿',
        'soft': '浅', 'line': '分割线',
        'color': '色', 'hover': '悬停', 'active': '激活',
        'success': '成功', 'warning': '警告', 'danger': '危险', 'info': '信息',
        'link': '链接', 'shadow': '阴影', 'radius': '圆角',
    }

    zh_parts = []
    for p in parts:
        zh_parts.append(WORD_MAP.get(p.lower(), p))
    zh_label = ''.join(zh_parts)

    en_label = ' '.join(w.capitalize() for w in parts)

    return f"{zh_label} {en_label}"


def _try_llm_labels(variables_info: list) -> dict:
    """
    尝试调用 LLM 生成语义化 label (Step 10)。
    返回 {var_name: label_string} 或 None（降级到启发式）。
    """
    import os

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    api_type = 'anthropic'
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY', '')
        api_type = 'openai'
    if not api_key:
        print("  [warning] 未配置 LLM API，使用启发式 label，可能不如人工命名优雅")
        return None

    # Load prompt template
    prompt_path = PRESETS_DIR / 'llm_label_prompt.txt'
    if not prompt_path.exists():
        print("  [warning] 缺少 llm_label_prompt.txt，降级到启发式")
        return None

    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    variables_json = json.dumps(variables_info, ensure_ascii=False, indent=2)
    prompt = prompt_template.replace('{variables_json}', variables_json)

    try:
        import requests

        if api_type == 'anthropic':
            resp = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                },
                json={
                    'model': 'claude-sonnet-4-20250514',
                    'max_tokens': 1024,
                    'messages': [{'role': 'user', 'content': prompt}],
                },
                timeout=30,
            )
            if resp.status_code == 200:
                content = resp.json()['content'][0]['text']
                return json.loads(content)
        elif api_type == 'openai':
            resp = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 1024,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                # Extract JSON from possible markdown wrapping
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
    except Exception as e:
        print(f"  [warning] LLM 调用失败 ({e})，降级到启发式")
        return None

    print("  [warning] LLM 返回异常，降级到启发式")
    return None


def _build_label_for(parse_result, scan_result) -> dict:
    """
    构建 LABEL_FOR single-source-of-truth (附录 C)。
    先尝试 LLM，失败则用启发式。
    """
    global LABEL_FOR
    LABEL_FOR = {}

    color_vars = [v for v in parse_result.variables if v.semantic == 'color']

    # 尝试 LLM labeling
    variables_info = []
    for v in color_vars:
        usages = parse_result.var_to_selectors.get(v.name, [])
        selectors = [sel for sel, prop in usages]
        variables_info.append({
            'name': v.name,
            'value': v.raw_value,
            'used_in': selectors[:5],
        })

    llm_labels = _try_llm_labels(variables_info)

    # 颜色 tab labels
    for v in color_vars:
        if llm_labels and v.name in llm_labels:
            label = llm_labels[v.name]
        else:
            label = _generate_heuristic_label(v.name)
        LABEL_FOR[('颜色', v.name)] = label

    # 字号 tab labels: 从 scan_result 推断
    # 查找 host 中实际的文本元素，生成 slider 配置
    _build_size_labels(parse_result, scan_result)

    # 布局 tab labels: 从 scan_result 推断
    _build_layout_labels(parse_result, scan_result)

    return LABEL_FOR


def _build_size_labels(parse_result, scan_result):
    """为字号 tab 构建 LABEL_FOR 条目"""
    from bs4 import BeautifulSoup

    present = scan_result.present_elements or {}

    # 按金版规范 R3.2-R3.4，为每种文本元素建立一条 slider
    # 需要用真实 DOM 选择器
    TAG_LABEL_MAP = {
        'h1': ('主标题 Title (h1)', 'h1'),
        'h2': ('二级标题 H2', 'h2'),
        'h3': ('卡片标题 H3', 'h3'),
        'h4': ('四级标题 H4', 'h4'),
        'p': ('正文 Body', 'body'),
        'li': ('列表项 List', 'list'),
    }

    # 尝试找到真实的限定选择器
    for elem in scan_result.elements:
        if not elem.is_text:
            continue
        tag = elem.tag if hasattr(elem, 'tag') else elem.selector.split()[-1].split('.')[0].split(':')[0]
        if tag in TAG_LABEL_MAP and tag in present:
            label, key = TAG_LABEL_MAP[tag]
            selector = elem.selector
            # Use the element's actual selector as data-target
            existing_key = ('字号', selector)
            if existing_key not in LABEL_FOR:
                LABEL_FOR[existing_key] = label

    # 确保至少覆盖 present 中有的 tags（如果没从 elements 里找到）
    for tag in ['h1', 'h2', 'h3', 'p']:
        if tag in present:
            label, key = TAG_LABEL_MAP.get(tag, (tag, tag))
            # Check if we already have a label for this tag
            found = False
            for (tab, sel), lab in LABEL_FOR.items():
                if tab == '字号' and (sel == tag or sel.endswith(f' {tag}')):
                    found = True
                    break
            if not found:
                LABEL_FOR[('字号', tag)] = label


def _build_layout_labels(parse_result, scan_result):
    """为布局 tab 构建 LABEL_FOR 条目"""
    from bs4 import BeautifulSoup

    # 按 R4.2 必含维度列表
    LAYOUT_DIMS = [
        ('页面宽度 Page Width', '.page', 'max-width', 'px', 640, 1400, 20, 960, 'page-w'),
        ('页面左右内距', '.page', 'padding-left', 'px', 16, 120, 4, 56, 'page-pad'),
        ('段落最大宽 Lead', '.masthead .lead, .section-intro', 'max-width', 'px', 400, 960, 10, 680, 'lead-w'),
        ('章节间距 Section Gap', 'section', 'margin-bottom', 'px', 16, 120, 4, 68, 'sec-gap'),
        ('中台卡片间距 ZT Gap', '.zt-grid', 'gap', 'px', 4, 40, 2, 14, 'zt-gap'),
        ('卡片内边距 Card Padding', '.zt-card', 'padding', 'px', 8, 40, 2, 20, 'card-pad'),
    ]

    for label, target, prop, unit, min_v, max_v, step, default, key in LAYOUT_DIMS:
        LABEL_FOR[('布局', target)] = label


def generate_panel(parse_result, scan_result) -> PanelConfig:
    """根据分析结果生成完整的面板配置。"""

    # Step 11: 构建 LABEL_FOR
    label_for = _build_label_for(parse_result, scan_result)

    # === 颜色行 ===
    color_vars = [v for v in parse_result.variables if v.semantic == 'color']
    color_rows = []
    for v in color_vars:
        label = label_for.get(('颜色', v.name), _generate_heuristic_label(v.name))
        color_rows.append({
            'var': v.name,
            'label': label,
            'default_value': v.raw_value
        })

    # === 字号滑块 (R3) ===
    size_sliders = _build_size_sliders(parse_result, scan_result, label_for)

    # === 布局滑块 (R4) ===
    layout_sliders = _build_layout_sliders(parse_result, scan_result, label_for)

    # === 预设主题 (R5) ===
    preset_themes = _build_presets(color_rows)

    # === 生成 Panel HTML ===
    panel_html = _build_panel_html(color_rows, size_sliders, layout_sliders, preset_themes)

    # === 生成 Toolbar HTML (R14) ===
    toolbar_html = _build_toolbar_html(scan_result.page_structure, scan_result.has_nav_dots)

    # === 生成 window.X 常量 JS ===
    constants_js = _build_constants_js(
        color_rows, size_sliders, preset_themes,
        scan_result.page_element_to_panel,
        scan_result.css_var_to_elements
    )

    return PanelConfig(
        color_rows=color_rows,
        preset_themes=preset_themes,
        layout_sliders=layout_sliders,
        size_sliders=size_sliders,
        panel_html=panel_html,
        toolbar_html=toolbar_html,
        constants_js=constants_js,
        label_for=label_for
    )


def _build_size_sliders(parse_result, scan_result, label_for) -> list:
    """
    构建字号 slider 列表 (R3)。

    v15 修复: 不再硬编码 [h1, h2, h3, h4, p, li] 6 个 fallback slider。
    改为从 parse_result.rules 反推所有声明了 font-size 的 CSS 规则，
    每条规则生成一个 slider（去重 / 验证 / 跳过编辑器自身选择器）。
    """
    from bs4 import BeautifulSoup
    html_src = scan_result._html if hasattr(scan_result, '_html') else ''
    soup = BeautifulSoup(html_src, 'html.parser') if html_src else None

    # 编辑器自身的 selector 前缀，反推时跳过
    EDITOR_SELECTOR_KEYWORDS = (
        'toolbar', 'edit-panel', 'edit-hint', 'panel-tab', 'panel-section',
        'panel-actions', 'panel-close', 'panel-header', 'panel-title',
        'color-row', 'color-label', 'color-swatch', 'color-hex',
        'slider-row', 'slider-label', 'slider-name', 'slider-val',
        'preset-row', 'preset-btn', 'action-btn', 'toolbar-btn',
        'btn-icon', 'save-indicator', 'toolbar-divider',
        'html-visual-editor',
    )

    sliders = []
    seen_selectors = set()
    used_keys = set()

    # v15: 清除可能由 _build_size_labels 旧逻辑留下的 字号 LABEL_FOR 条目
    # 我们只信任本函数从 CSS 反推出的 (selector, label)
    stale_keys = [k for k in label_for if isinstance(k, tuple) and len(k) == 2 and k[0] == '字号']
    for k in stale_keys:
        del label_for[k]
    # 同步清理全局 LABEL_FOR（_build_label_for 写过的）
    try:
        for k in [kk for kk in LABEL_FOR if isinstance(kk, tuple) and len(kk) == 2 and kk[0] == '字号']:
            del LABEL_FOR[k]
    except Exception:
        pass

    def _make_key(selector: str) -> str:
        """Generate a safe DOM id-friendly key from selector."""
        k = re.sub(r'[^\w]+', '-', selector).strip('-').lower()
        if not k:
            k = 'size'
        # Ensure uniqueness
        base = k
        i = 2
        while k in used_keys:
            k = f"{base}-{i}"
            i += 1
        used_keys.add(k)
        return k

    def _bounds_for(default_px: float) -> dict:
        """从默认字号推算 slider 范围 (0.5x ~ 2x)"""
        default_px = float(default_px)
        min_v = max(8, round(default_px * 0.5))
        max_v = max(min_v + 4, round(default_px * 2))
        step = 0.5 if default_px <= 14 else 1
        return {'min': min_v, 'max': max_v, 'step': step}

    # 主循环：从 CSS 规则反推
    rules = getattr(parse_result, 'rules', None) or []
    for rule in rules:
        props = getattr(rule, 'properties', {}) or {}
        if 'font-size' not in props:
            continue

        selector = (getattr(rule, 'selector', '') or '').strip()
        if not selector:
            continue

        # 去掉 CSS 注释 /* ... */ (selector 里偶尔被解析器捎进来)
        selector = re.sub(r'/\*.*?\*/', '', selector, flags=re.DOTALL).strip()
        # 归一化空白（换行 / 多空格 → 单空格）
        selector = re.sub(r'\s+', ' ', selector)
        if not selector:
            continue

        # 跳过编辑器自身 selector
        sel_lower = selector.lower()
        if any(kw in sel_lower for kw in EDITOR_SELECTOR_KEYWORDS):
            continue

        # 多选择器组（用逗号分隔）拆开处理
        for sub_sel in [s.strip() for s in selector.split(',') if s.strip()]:
            # 跳过 @-rule / pseudo-only
            if sub_sel.startswith('@') or sub_sel.startswith(':root'):
                continue

            # 验证选择器在 host DOM 中真实存在
            if soup is not None:
                try:
                    found = soup.select(sub_sel)
                    if not found:
                        continue
                except Exception:
                    continue

            if sub_sel in seen_selectors:
                continue
            seen_selectors.add(sub_sel)

            # 解析默认字号 (例如 "28px" / "1.2em" / "clamp(...)" )
            fs_value = props['font-size'].strip()
            parsed = _parse_size_value(fs_value)
            default_px = parsed['default']
            unit = parsed['unit'] if parsed['unit'] in ('px', 'em', 'rem') else 'px'

            bounds = _bounds_for(default_px)

            label = _generate_size_label(sub_sel)
            label_for[('字号', sub_sel)] = label

            sliders.append({
                'target': sub_sel,
                'prop': 'font-size',
                'label': label,
                'min': bounds['min'],
                'max': bounds['max'],
                'default': default_px,
                'unit': unit,
                'step': bounds['step'],
                'key': _make_key(sub_sel),
            })

    # 排序：按默认字号从大到小
    sliders.sort(key=lambda s: -float(s['default']))

    return sliders


# ============================================================
# 字号 slider label 推断 (v15)
# ============================================================
SIZE_SLIDER_LABEL_MAP = {
    # header 体系
    '.header h1':                ('主标题 Header H1', 'header-h1'),
    '.header .subtitle':         ('副标题 Subtitle', 'subtitle'),
    '.header .meta':             ('元信息 Meta', 'meta'),
    # section 体系
    '.section h2':               ('章节标题 Section H2', 'section-h2'),
    '.section h3':               ('三级标题 Section H3', 'section-h3'),
    '.section p':                ('正文 Body', 'body'),
    # stat-card 数字看板
    '.stat-card .number':        ('数字大字 Stat Number', 'stat-number'),
    '.stat-card .label':         ('数字标签 Stat Label', 'stat-label'),
    # 表格
    'th':                        ('表头 Table Header', 'th'),
    'td':                        ('单元格 Table Cell', 'td'),
    'table':                     ('表格 Table', 'table'),
    # badge / ptag
    '.badge':                    ('状态徽章 Badge', 'badge'),
    '.ptag':                     ('优先级标签 Priority Tag', 'ptag'),
    # 组织盒子
    '.org-box h4':               ('组织标题 Org H4', 'org-h4'),
    '.org-box .role':            ('角色 Role', 'org-role'),
    '.org-box ul li':            ('组织列表 Org List', 'org-list'),
    # 时间轴
    '.timeline-item .t-date':    ('时间轴日期 Timeline Date', 'timeline-date'),
    '.timeline-item .t-content': ('时间轴内容 Timeline Content', 'timeline-content'),
    # next-card
    '.next-card .num':           ('Next 数字 Next Num', 'next-num'),
    '.next-card .desc':          ('Next 描述 Next Desc', 'next-desc'),
    '.next-card .detail':        ('Next 细节 Next Detail', 'next-detail'),
    # 其它
    '.footer':                   ('页脚 Footer', 'footer'),
    '.support-item':             ('支持项 Support Item', 'support-item'),
    '.summary-banner':           ('汇总条 Summary Banner', 'summary-banner'),
    # 裸 heading（金版兜底）
    'h1': ('主标题 H1', 'h1'),
    'h2': ('二级标题 H2', 'h2'),
    'h3': ('三级标题 H3', 'h3'),
    'h4': ('四级标题 H4', 'h4'),
    'h5': ('五级标题 H5', 'h5'),
    'h6': ('六级标题 H6', 'h6'),
    'p':  ('正文 Body', 'body'),
    'li': ('列表项 List', 'list'),
    'body': ('页面正文 Page Body', 'page-body'),
}


_CHINESE_LABEL_WORDS = {
    'header': '头部', 'footer': '页脚', 'subtitle': '副标题',
    'meta': '元信息', 'section': '章节', 'card': '卡片',
    'stat': '数字', 'number': '数字', 'label': '标签',
    'badge': '徽章', 'tag': '标签', 'org': '组织', 'role': '角色',
    'timeline': '时间轴', 'date': '日期', 'content': '内容',
    'next': 'Next', 'num': '数字', 'desc': '描述', 'detail': '细节',
    'summary': '汇总', 'banner': '横幅', 'support': '支持', 'item': '项',
    'title': '标题', 'body': '正文', 'list': '列表', 'box': '盒子',
    'grid': '网格', 'row': '行', 'col': '列', 'block': '块',
    'page': '页面', 'main': '主体', 'side': '侧栏', 'aside': '侧栏',
    'nav': '导航', 'menu': '菜单', 'btn': '按钮', 'button': '按钮',
    'link': '链接', 'text': '文字', 'lead': '导语', 'intro': '简介',
    'caption': '说明', 'note': '备注', 'tip': '提示', 'hint': '提示',
    'name': '名称', 'value': '值', 'desc': '描述',
}


def _generate_size_label(selector: str) -> str:
    """
    根据选择器生成中英双语 label (v15)。
    优先查 SIZE_SLIDER_LABEL_MAP；否则按选择器最后一段做启发式中文化。
    """
    sel = selector.strip()
    if sel in SIZE_SLIDER_LABEL_MAP:
        return SIZE_SLIDER_LABEL_MAP[sel][0]

    # 取最后一段做语义推断
    last = sel.split()[-1] if ' ' in sel else sel
    last = last.split('>')[-1].strip()

    # 拆出 class / tag
    # 形如 .foo-bar / .foo / div.bar / h2 / .a.b
    classes = re.findall(r'\.([\w-]+)', last)
    tag_match = re.match(r'^([a-zA-Z][\w-]*)', last)
    tag = tag_match.group(1) if tag_match else ''

    # 用 classes + tag 拼 label
    name_parts = []
    for cls in classes:
        name_parts.extend(re.split(r'[-_]', cls))
    if tag and tag.lower() not in {'div', 'span'}:
        name_parts.append(tag)
    name_parts = [p for p in name_parts if p]

    if not name_parts:
        # 兜底：用整个 selector
        name_parts = [re.sub(r'[^\w]+', '-', sel).strip('-') or 'size']

    zh = ''.join(_CHINESE_LABEL_WORDS.get(p.lower(), p) for p in name_parts)
    en = ' '.join(w.capitalize() for w in name_parts)
    return f"{zh} {en}"


def _build_layout_sliders(parse_result, scan_result, label_for) -> list:
    """
    构建布局 slider 列表 (R4)。
    必含 6 条: 页面宽度/左右内距/段落最大宽/章节间距/卡片间距/卡片内边距。
    对每条 slider，验证 data-target 在 host DOM 中可 querySelector 到，否则用 fallback 替换 (P0-2)。
    """
    from bs4 import BeautifulSoup
    html_src = scan_result._html if hasattr(scan_result, '_html') else ''
    soup = BeautifulSoup(html_src, 'html.parser') if html_src else None

    LAYOUT_DIMS = [
        {'label': '页面宽度 Page Width', 'target': '.page', 'prop': 'max-width', 'unit': 'px', 'min': 640, 'max': 1400, 'step': 20, 'default': 960, 'key': 'page-w', 'section': '页面尺寸'},
        {'label': '页面左右内距', 'target': '.page', 'prop': 'padding-left', 'unit': 'px', 'min': 16, 'max': 120, 'step': 4, 'default': 56, 'key': 'page-pad', 'section': '页面尺寸'},
        {'label': '段落最大宽 Lead', 'target': '.masthead .lead, .section-intro', 'prop': 'max-width', 'unit': 'px', 'min': 400, 'max': 960, 'step': 10, 'default': 680, 'key': 'lead-w', 'section': '页面尺寸'},
        {'label': '章节间距 Section Gap', 'target': 'section', 'prop': 'margin-bottom', 'unit': 'px', 'min': 16, 'max': 120, 'step': 4, 'default': 68, 'key': 'sec-gap', 'section': '章节间距'},
        {'label': '中台卡片间距 ZT Gap', 'target': '.zt-grid', 'prop': 'gap', 'unit': 'px', 'min': 4, 'max': 40, 'step': 2, 'default': 14, 'key': 'zt-gap', 'section': '卡片网格'},
        {'label': '卡片内边距 Card Padding', 'target': '.zt-card', 'prop': 'padding', 'unit': 'px', 'min': 8, 'max': 40, 'step': 2, 'default': 20, 'key': 'card-pad', 'section': '卡片网格'},
    ]

    sliders = []
    for dim in LAYOUT_DIMS:
        original_target = dim['target']
        if soup is not None:
            resolved = _resolve_layout_target(original_target, soup)
            if resolved:
                dim = dict(dim)
                dim['target'] = resolved
            else:
                # 无法解析时仍保留原 target（避免 6 条 slider 数量缩水）
                pass
        sliders.append(dim)

    return sliders


def _build_presets(color_rows: list) -> dict:
    """
    构建 PRESETS flat 格式 (R5.1, R5.2)。
    先用 SEMANTIC_ALIAS 把 preset 的语义命名映射到 host 实际命名，
    再过滤为 DEFAULT_COLORS 的子集。(P0-1 修复)
    """
    builtin = _load_builtin_presets()
    default_var_keys = {row['var'] for row in color_rows}

    preset_themes = {}
    for name, data in builtin.items():
        if isinstance(data, dict):
            # 支持 {vars: {...}} 嵌套格式
            vars_dict = data.get('vars', data)
            if not isinstance(vars_dict, dict):
                continue

            # 先做语义映射：preset 命名 -> host 实际变量名
            # 只保留 -- 开头的有效变量
            preset_vars_clean = {
                k: v for k, v in vars_dict.items() if isinstance(k, str) and k.startswith('--')
            }
            mapped = _map_preset_to_host_vars(preset_vars_clean, default_var_keys)

            if mapped:
                preset_themes[name] = mapped
            else:
                # 即使全没映射到，也保留空字典以便提示
                print(f"  [warning] preset '{name}' 无法映射到 host 任何变量，跳过")

    return preset_themes


def _build_panel_html(color_rows: list, size_sliders: list, layout_sliders: list, preset_themes: dict) -> str:
    """组装完整的 panel HTML"""
    template_path = ASSETS_DIR / 'panel.template.html'
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    else:
        template = _get_fallback_panel_template()

    # === 颜色 tab 内容 (R2.1: 多 section) ===
    theme_colors = []
    text_colors = []
    for row in color_rows:
        section = _classify_color_section(row['var'])
        html = _generate_color_row_html(row['var'], row['label'], row['default_value'])
        if section == '文字色':
            text_colors.append(html)
        else:
            theme_colors.append(html)

    color_tab_parts = []
    if theme_colors:
        color_tab_parts.append('    <div class="panel-section">')
        color_tab_parts.append('        <div class="panel-section-title">主题色板</div>')
        color_tab_parts.extend(theme_colors)
        color_tab_parts.append('    </div>')
    if text_colors:
        color_tab_parts.append('    <div class="panel-section">')
        color_tab_parts.append('        <div class="panel-section-title">文字色</div>')
        color_tab_parts.extend(text_colors)
        color_tab_parts.append('    </div>')
    if not color_tab_parts:
        color_tab_parts.append('    <p class="empty-hint">未检测到颜色变量</p>')

    color_tab_content = '\n'.join(color_tab_parts)

    # === 字号 tab 内容 (R3) ===
    size_tab_parts = []
    if size_sliders:
        size_tab_parts.append('    <div class="panel-section">')
        size_tab_parts.append('        <div class="panel-section-title">标题大小倍率</div>')
        for s in size_sliders:
            size_tab_parts.append(_generate_slider_html(
                s['label'], s['key'], s['target'], s['prop'], s['unit'],
                s['min'], s['max'], s['step'], s['default']
            ))
        size_tab_parts.append('    </div>')
    else:
        size_tab_parts.append('    <p class="empty-hint">未检测到文本元素</p>')
    size_tab_content = '\n'.join(size_tab_parts)

    # === 布局 tab 内容 (R4.4: 3 个子分段) ===
    layout_tab_parts = []
    sections_map = {}  # section_name -> [slider_html]
    for s in layout_sliders:
        sec = s.get('section', '间距与布局')
        if sec not in sections_map:
            sections_map[sec] = []
        sections_map[sec].append(_generate_slider_html(
            s['label'], s['key'], s['target'], s['prop'], s['unit'],
            s['min'], s['max'], s['step'], s['default']
        ))
    for sec_name, slider_htmls in sections_map.items():
        layout_tab_parts.append('    <div class="panel-section">')
        layout_tab_parts.append(f'        <div class="panel-section-title">{sec_name}</div>')
        layout_tab_parts.extend(slider_htmls)
        layout_tab_parts.append('    </div>')
    if not layout_tab_parts:
        layout_tab_parts.append('    <p class="empty-hint">未检测到布局元素</p>')
    layout_tab_content = '\n'.join(layout_tab_parts)

    # === 预设按钮 (R5.3, R5.4: 无 LLM 占位) ===
    preset_html_parts = []
    for name in preset_themes:
        display = PRESET_DISPLAY_NAMES.get(name, name)
        preset_html_parts.append(
            f'            <button class="preset-btn" onclick="applyPreset(\'{name}\')">{display}</button>'
        )
    presets_html = '\n'.join(preset_html_parts)

    # 填充模板
    panel_html = template.replace('{{COLOR_TAB_CONTENT}}', color_tab_content)
    panel_html = panel_html.replace('{{SIZE_TAB_CONTENT}}', size_tab_content)
    panel_html = panel_html.replace('{{LAYOUT_TAB_CONTENT}}', layout_tab_content)
    panel_html = panel_html.replace('{{PRESET_BUTTONS}}', presets_html)

    return panel_html


def _build_toolbar_html(page_structure: str, has_nav_dots: bool) -> str:
    """生成 toolbar HTML (R14: 金版文案)"""
    toolbar = '''<!-- ======== EDIT TOOLBAR ======== -->
<div class="edit-toolbar" id="editToolbar">
    <button class="toolbar-btn" id="btnToggleEdit" onclick="toggleEditMode()" title="切换编辑模式 (E)">
        <span class="btn-icon">✏️</span>
        <span id="btnEditText">编辑</span>
    </button>
    <div class="toolbar-divider"></div>
    <button class="toolbar-btn" onclick="saveToStorage()" title="保存 (⌘S)">
        <span class="btn-icon">💾</span>
        保存
    </button>
    <button class="toolbar-btn" id="btnUndo" onclick="undoLast()" title="撤销上一步 (⌘Z)" disabled>
        <span class="btn-icon">↩</span>
        撤销
    </button>
    <div class="toolbar-divider"></div>
    <button class="toolbar-btn" onclick="exportHTML()" title="导出为文件">
        <span class="btn-icon">📥</span>
        导出
    </button>
    <button class="toolbar-btn" onclick="resetAll()" title="重置为默认值">
        <span class="btn-icon">🔄</span>
        重置
    </button>
    <span class="save-indicator" id="saveIndicator">已保存 ✓</span>
</div>'''

    if page_structure == 'slides':
        toolbar += '''

<!-- Navigation -->
<nav class="nav-dots" id="navDots"></nav>
<div class="keyboard-hint">← → or Space to navigate · 按 E 切换编辑模式 · 编辑时按 P 固定提示</div>'''

    return toolbar


# Layout slider target fallback chains (P0-2 修复)
# 如果 host DOM 中找不到原 target, 尝试这些 fallback 选择器
LAYOUT_TARGET_FALLBACKS = {
    '.page':                            ['body > .page', '.page', '.container', '.wrapper', 'main', 'body'],
    '.masthead .lead, .section-intro':  ['.lead', '.section-intro', '.intro', '.subtitle', '.summary-banner', '.desc'],
    'section':                          ['section', '.section', 'article', '.timeline-item'],
    '.zt-grid':                         ['.zt-grid', '.grid', '.card-grid', '.cards', '.stat-row', '.org-chart', '.next-steps'],
    '.zt-card':                         ['.zt-card', '.card', '.goal-card', '.item', '.stat-card', '.next-card', '.org-box', '.support-item'],
}


def _resolve_layout_target(target: str, soup) -> str:
    """
    给定一个布局 slider 的 data-target, 返回 host DOM 中能查得到的选择器（保持逗号组合）。
    优先原 target 中能 select 到的部分；都不行则用 LAYOUT_TARGET_FALLBACKS 找替代。
    返回 '' 表示无可用选择器。
    """
    if soup is None:
        return target

    # 原 target 拆开后过滤
    valid_parts = []
    for sel in target.split(','):
        sel = sel.strip()
        if not sel:
            continue
        try:
            if soup.select(sel):
                valid_parts.append(sel)
        except Exception:
            pass
    if valid_parts:
        return ', '.join(valid_parts)

    # 找 fallback
    candidates = LAYOUT_TARGET_FALLBACKS.get(target, [])
    for cand in candidates:
        try:
            if soup.select(cand):
                return cand
        except Exception:
            continue
    return ''


def _add_layout_targets_to_pem(layout_sliders: list, pem: dict, soup=None) -> None:
    """
    P0-2 修复: 把布局 slider 的 data-target 反向索引到 PAGE_ELEMENT_TO_PANEL，
    让 PEM 包含 '布局' tab。原地修改 pem。
    如果传入 soup，会跳过 DOM 中匹配不到的 selector（满足 SC-03）。
    """
    for slider in layout_sliders:
        targets = slider.get('target', '')
        label = slider.get('label', '')
        if not targets or not label:
            continue
        for sel in targets.split(','):
            sel = sel.strip()
            if not sel:
                continue
            # 跳过无法 querySelector 到的 selector，避免触发 SC-03
            if soup is not None:
                try:
                    if not soup.select(sel):
                        continue
                except Exception:
                    continue
            if sel not in pem:
                pem[sel] = []
            if not any(it.get('row') == label and it.get('tab') == '布局' for it in pem[sel]):
                pem[sel].append({'tab': '布局', 'row': label})


def _add_size_targets_to_pem(size_sliders: list, pem: dict, soup=None) -> None:
    """
    P0-2 修复: 把字号 slider 的 data-target 反向索引到 PAGE_ELEMENT_TO_PANEL，
    确保 '字号' tab 在 PEM 里有对应项。原地修改 pem。
    """
    for slider in size_sliders:
        targets = slider.get('target', '')
        label = slider.get('label', '')
        if not targets or not label:
            continue
        for sel in targets.split(','):
            sel = sel.strip()
            if not sel:
                continue
            if soup is not None:
                try:
                    if not soup.select(sel):
                        continue
                except Exception:
                    continue
            if sel not in pem:
                pem[sel] = []
            if not any(it.get('row') == label and it.get('tab') == '字号' for it in pem[sel]):
                pem[sel].append({'tab': '字号', 'row': label})


def _build_constants_js(color_rows: list, size_sliders: list, preset_themes: dict,
                        page_element_to_panel: dict, css_var_to_elements: dict) -> str:
    """
    生成 window.X 常量注入代码。
    R5.1: PRESETS flat
    R6: DEFAULT_COLORS
    R7: PAGE_ELEMENT_TO_PANEL [{tab, row}]
    R8: CSS_VAR_TO_ELEMENTS 字符串
    R9: SIZE_BOUNDS 空对象
    R12: 无 fallback 函数, 无 adapter IIFE, 无 LLM_PRESET_HOOK
    """
    # DEFAULT_COLORS
    default_colors = {}
    for row in color_rows:
        default_colors[row['var']] = row['default_value']

    # SIZE_BOUNDS: 金版用空对象 (R9)
    size_bounds = {}

    # PRESETS: flat 格式 (R5.1)
    presets = preset_themes if preset_themes else {}

    js_parts = [
        '// === html-visual-editor v12 自动生成常量 ===',
        f'window.DEFAULT_COLORS = {json.dumps(default_colors, ensure_ascii=False)};',
        '',
        f'window.PRESETS = {json.dumps(presets, ensure_ascii=False)};',
        '',
        f'window.SIZE_BOUNDS = {json.dumps(size_bounds, ensure_ascii=False)};',
        '',
        f'window.PAGE_ELEMENT_TO_PANEL = {json.dumps(page_element_to_panel, ensure_ascii=False)};',
        '',
        f'window.CSS_VAR_TO_ELEMENTS = {json.dumps(css_var_to_elements, ensure_ascii=False)};',
    ]

    return '\n'.join(js_parts)


def _get_fallback_panel_template() -> str:
    """内联 panel 模板兜底"""
    return '''<!-- ======== EDIT PANEL (sidebar) ======== -->
<div class="edit-panel" id="editPanel">
    <div class="panel-header">
        <span class="panel-title">🎨 样式面板</span>
        <button class="panel-close-btn" onclick="toggleEditMode()">✕</button>
    </div>
    <div class="panel-tabs">
        <button class="panel-tab active" data-tab="colors" onclick="switchPanelTab('colors')">颜色</button>
        <button class="panel-tab" data-tab="presets" onclick="switchPanelTab('presets')">预设</button>
        <button class="panel-tab" data-tab="layout" onclick="switchPanelTab('layout')">布局</button>
        <button class="panel-tab" data-tab="size" onclick="switchPanelTab('size')">字号</button>
    </div>
    <div class="panel-tab-content active" id="tab-colors">
{{COLOR_TAB_CONTENT}}
    </div>
    <div class="panel-tab-content" id="tab-presets">
        <div class="panel-section">
            <div class="panel-section-title">一键换肤</div>
            <div class="preset-row">
{{PRESET_BUTTONS}}
            </div>
        </div>
    </div>
    <div class="panel-tab-content" id="tab-layout">
{{LAYOUT_TAB_CONTENT}}
    </div>
    <div class="panel-tab-content" id="tab-size">
{{SIZE_TAB_CONTENT}}
    </div>
    <div class="panel-actions">
        <button class="action-btn action-btn-primary" onclick="exportHTML()">⬇️ 导出为 .html 文件</button>
        <button class="action-btn action-btn-secondary" onclick="saveToStorage()">💾 保存到浏览器本地</button>
        <button class="action-btn action-btn-secondary" onclick="resetAll()">🔄 恢复默认设置</button>
    </div>
</div>'''
