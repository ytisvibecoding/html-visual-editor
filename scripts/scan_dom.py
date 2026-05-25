#!/usr/bin/env python3
"""
scan_dom.py -- DOM 扫描模块 (v15 public package)
扫描 HTML body 中的可编辑元素，推断编辑维度，
生成 PAGE_ELEMENT_TO_PANEL 映射 [{tab, row}, ...] 和 CSS_VAR_TO_ELEMENTS 反查索引（字符串格式）。

对应规范: R7.1-R7.4, R8
"""

import re
from dataclasses import dataclass, field
from typing import Literal
from bs4 import BeautifulSoup, NavigableString


# 可编辑的文本标签
EDITABLE_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'span',
                 'a', 'td', 'th', 'blockquote', 'figcaption', 'label',
                 'strong', 'em', 'b', 'i', 'small', 'dt', 'dd', 'caption'}

# 容器标签
CONTAINER_TAGS = {'div', 'section', 'article', 'main', 'header', 'footer',
                  'aside', 'nav', 'ul', 'ol', 'figure', 'details'}

# 容器语义 class（模糊匹配）
CONTAINER_CLASSES = {'card', 'container', 'section', 'grid', 'wrapper',
                     'panel', 'hero', 'stat', 'box', 'group', 'block',
                     'row', 'col', 'column', 'tile', 'item', 'list'}

# 最大元素扫描数量
MAX_ELEMENTS = 500


@dataclass
class EditableElement:
    """一个可编辑元素的描述"""
    selector: str
    tag: str
    classes: list
    text_content: str
    is_text: bool
    is_container: bool
    used_vars: list
    editable_dims: list


@dataclass
class ScanResult:
    """DOM 扫描结果"""
    elements: list            # list[EditableElement]
    page_structure: str       # 'slides' | 'single-page' | 'sections' | 'article'
    has_nav_dots: bool
    page_element_to_panel: dict   # {sel: [{tab, row}, ...]}  -- R7.1 新格式
    css_var_to_elements: dict     # {var: "sel1, sel2"}        -- R8 字符串格式
    present_elements: dict = None  # {tag: computed_font_size}
    _html: str = ''               # 原始 HTML（用于布局 slider 解析 fallback）


def has_direct_text(el) -> bool:
    """判断元素是否有直接文本内容（非子元素文本）"""
    for child in el.children:
        if isinstance(child, NavigableString):
            text = child.strip()
            if text and len(text) > 1:
                return True
    return False


def best_selector(el) -> str:
    """
    为元素生成最优 CSS 选择器 (R7.2)
    优先用 .parent-class child-tag / .specific-class 组合，避免 nth-of-type。
    """
    tag = el.name
    classes = el.get('class', [])
    el_id = el.get('id', '')

    # 有 id 的情况（排除动态 id）
    if el_id and not re.match(r'^(__|js-|react-|vue-|ng-|html-visual-editor)', el_id):
        return f'#{el_id}'

    # 有语义化 class
    if classes:
        semantic_classes = [c for c in classes
                          if not re.match(r'^(p|m|w|h|text|bg|border|flex|grid|gap|rounded|shadow)-', c)
                          and len(c) > 2]
        if semantic_classes:
            # 尝试带父类组合选择器增强精确度
            parent = el.parent
            if parent and parent.name not in ('body', 'html', '[document]'):
                parent_classes = parent.get('class', [])
                parent_semantic = [c for c in parent_classes
                                   if not re.match(r'^(p|m|w|h|text|bg|border|flex|grid|gap|rounded|shadow)-', c)
                                   and len(c) > 2]
                if parent_semantic:
                    return f'.{parent_semantic[0]} .{semantic_classes[0]}'
            return f'.{semantic_classes[0]}'
        if classes:
            return f'.{classes[0]}'

    # 没有 class，用父元素 class + 子 tag（R7.2 推荐写法）
    parent = el.parent
    if parent and parent.name not in ('body', 'html', '[document]'):
        parent_classes = parent.get('class', [])
        parent_semantic = [c for c in parent_classes
                           if not re.match(r'^(p|m|w|h|text|bg|border|flex|grid|gap|rounded|shadow)-', c)
                           and len(c) > 2]
        if parent_semantic:
            return f'.{parent_semantic[0]} {tag}'
        # 检查祖父
        grandparent = parent.parent
        if grandparent and grandparent.name not in ('body', 'html', '[document]'):
            gp_classes = grandparent.get('class', [])
            gp_semantic = [c for c in gp_classes
                           if not re.match(r'^(p|m|w|h|text|bg|border|flex|grid|gap|rounded|shadow)-', c)
                           and len(c) > 2]
            if gp_semantic:
                return f'.{gp_semantic[0]} {tag}'

    # 最后兜底：纯 tag（不用 nth-of-type，按 R7.2 禁止）
    return tag


def find_vars_for_element(el, selector: str, parse_result) -> list:
    """找出元素使用的 CSS 变量（通过匹配 CSS 规则）"""
    used_vars = []
    el_classes = el.get('class', [])
    el_id = el.get('id', '')
    el_tag = el.name

    for rule in parse_result.rules:
        rule_sel = rule.selector.strip()
        matched = False

        if rule_sel == el_tag:
            matched = True
        elif rule_sel.startswith('.'):
            cls = rule_sel.split('.')[1].split(':')[0].split(' ')[0]
            if cls in el_classes:
                matched = True
        elif rule_sel.startswith('#') and el_id:
            if rule_sel.split(':')[0].split(' ')[-1] == f'#{el_id}':
                matched = True
        elif '.' in rule_sel and not rule_sel.startswith('.'):
            parts = rule_sel.split('.')
            tag = parts[0].split(' ')[-1].split(':')[0]
            cls = parts[1].split(':')[0].split(' ')[0]
            if tag == el_tag and cls in el_classes:
                matched = True
        elif ' ' in rule_sel:
            last_part = rule_sel.split()[-1]
            if last_part == el_tag:
                matched = True
            elif last_part.startswith('.'):
                cls = last_part[1:].split(':')[0]
                if cls in el_classes:
                    matched = True

        if matched:
            used_vars.extend(rule.referenced_vars)

    return list(set(used_vars))


def infer_dimensions(el, used_vars: list, parse_result) -> list:
    """推断元素的可编辑维度"""
    dims = []
    var_semantics = {v.name: v.semantic for v in parse_result.variables}

    for var in used_vars:
        sem = var_semantics.get(var, 'other')
        if sem == 'color' and 'color' not in dims:
            dims.append('color')
        elif sem == 'size' and 'font-size' not in dims:
            dims.append('font-size')
        elif sem == 'spacing' and 'layout' not in dims:
            dims.append('layout')

    if el.name in CONTAINER_TAGS and 'layout' not in dims:
        dims.append('layout')

    return dims


def detect_page_structure(soup) -> tuple:
    """检测页面结构类型"""
    body = soup.body
    if not body:
        return 'single-page', False

    slides = body.find_all(class_=re.compile(r'slide|page|screen', re.I))
    if len(slides) >= 2:
        return 'slides', True

    nav_dots = body.find(class_=re.compile(r'nav-dot|dot|indicator', re.I))
    has_nav = nav_dots is not None

    sections = body.find_all(['section', 'article'])
    if len(sections) >= 3:
        return 'sections', has_nav

    if body.find('article') or body.find(class_=re.compile(r'article|post|content', re.I)):
        return 'article', has_nav

    return 'single-page', has_nav


def _build_css_var_to_elements_from_css(parse_result) -> dict:
    """
    从 parsed CSS 构建 CSS_VAR_TO_ELEMENTS（R8）。
    扫描 CSS 规则中 var(--xxx) 引用，包含伪元素选择器。
    返回 {var_name: "sel1, sel2, sel3"} 字符串格式。
    """
    var_selectors = {}  # var_name -> set of selectors
    for rule in parse_result.rules:
        sel = rule.selector.strip()
        if sel.startswith(':root') or sel.startswith('html') or sel == '*':
            continue
        for prop_name, prop_value in rule.properties.items():
            for var_ref in re.findall(r'var\((--[\w-]+)', prop_value):
                if var_ref not in var_selectors:
                    var_selectors[var_ref] = set()
                var_selectors[var_ref].add(sel)

    # R8: value 是逗号分隔的字符串
    result = {}
    for var_name, sels in var_selectors.items():
        result[var_name] = ', '.join(sorted(sels))
    return result


def scan_dom(html_content: str, parse_result, label_for: dict = None) -> ScanResult:
    """
    扫描 HTML DOM，生成可编辑元素列表和映射。

    label_for: 来自 generate_panel 的 LABEL_FOR dict
               {(tab_name, key): label_string}
               用于填充 page_element_to_panel 的 row 字段。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    body = soup.body
    if not body:
        return ScanResult(
            elements=[], page_structure='single-page',
            has_nav_dots=False, page_element_to_panel={},
            css_var_to_elements={}, _html=html_content
        )

    page_structure, has_nav_dots = detect_page_structure(soup)

    elements = []
    seen_selectors = set()
    count = 0

    for el in body.descendants:
        if count >= MAX_ELEMENTS:
            break
        if not hasattr(el, 'name') or el.name is None:
            continue
        if el.name in ['script', 'style', 'link', 'meta', 'br', 'hr', 'img', 'svg', 'path', 'input', 'button', 'select', 'textarea']:
            continue

        selector = best_selector(el)
        if selector in seen_selectors:
            continue

        is_text = el.name in EDITABLE_TAGS and has_direct_text(el)

        el_classes = el.get('class', [])
        is_container = (el.name in CONTAINER_TAGS and
                       (any(cls.lower() in CONTAINER_CLASSES
                            for cls in el_classes) or
                        has_direct_text(el) is False))

        if not is_text and not is_container:
            continue

        used_vars = find_vars_for_element(el, selector, parse_result)
        dims = infer_dimensions(el, used_vars, parse_result)
        text = el.get_text(strip=True)[:50] if is_text else ''

        elements.append(EditableElement(
            selector=selector,
            tag=el.tag if hasattr(el, 'tag') else el.name,
            classes=list(el_classes),
            text_content=text,
            is_text=is_text,
            is_container=is_container,
            used_vars=used_vars,
            editable_dims=dims
        ))
        seen_selectors.add(selector)
        count += 1

    # R7: 构建 PAGE_ELEMENT_TO_PANEL [{tab, row}, ...]
    page_element_to_panel = {}
    if label_for is None:
        label_for = {}

    color_vars_set = {v.name for v in parse_result.variables if v.semantic == 'color'}
    # Build reverse lookup: var_name -> label in 颜色 tab
    var_to_color_label = {}
    for (tab, key), label in label_for.items():
        if tab == '颜色':
            var_to_color_label[key] = label

    # Build reverse lookup: selector -> labels in 字号/布局 tab
    sel_to_size_label = {}
    sel_to_layout_label = {}
    for (tab, key), label in label_for.items():
        if tab == '字号':
            # key is a selector string (possibly comma-separated)
            for s in key.split(','):
                sel_to_size_label[s.strip()] = label
        elif tab == '布局':
            for s in key.split(','):
                sel_to_layout_label[s.strip()] = label

    for elem in elements:
        if not elem.is_text and not elem.used_vars:
            continue

        items = []

        # 颜色维度: match element's used vars to color labels
        for var_name in elem.used_vars:
            if var_name in var_to_color_label:
                row_label = var_to_color_label[var_name]
                item = {'tab': '颜色', 'row': row_label}
                if item not in items:
                    items.append(item)

        # 字号维度: check if this selector is a target in 字号 tab
        for sel_key, label in sel_to_size_label.items():
            # Check if the element's selector matches any of the targets
            if _selector_matches_element(elem.selector, sel_key, soup):
                item = {'tab': '字号', 'row': label}
                if item not in items:
                    items.append(item)

        # 布局维度: check if this selector is a target in 布局 tab
        for sel_key, label in sel_to_layout_label.items():
            if _selector_matches_element(elem.selector, sel_key, soup):
                item = {'tab': '布局', 'row': label}
                if item not in items:
                    items.append(item)

        if items:
            page_element_to_panel[elem.selector] = items

    # R8: CSS_VAR_TO_ELEMENTS 字符串格式, 从 CSS 规则构建（含伪元素）
    css_var_to_elements = _build_css_var_to_elements_from_css(parse_result)

    # 检测 present_elements
    SIZING_TAGS = ['h1', 'h2', 'h3', 'h4', 'p', 'li', 'blockquote', 'button', 'span']
    present_elements = {}
    for tag in SIZING_TAGS:
        found = body.find_all(tag, limit=3)
        if found:
            font_size = None
            for found_el in found:
                style = found_el.get('style', '')
                fs_match = re.search(r'font-size:\s*([\d.]+)(px|em|rem|pt)', style)
                if fs_match:
                    font_size = f"{fs_match.group(1)}{fs_match.group(2)}"
                    break
            if not font_size:
                for rule in parse_result.rules:
                    if rule.selector.strip() == tag or rule.selector.strip().endswith(' ' + tag):
                        for prop_name, prop_val in rule.properties.items():
                            if 'font-size' in prop_name:
                                fs_match = re.search(r'([\d.]+)(px|em|rem|pt)', prop_val)
                                if fs_match:
                                    font_size = f"{fs_match.group(1)}{fs_match.group(2)}"
                                    break
                        if font_size:
                            break
            present_elements[tag] = font_size

    return ScanResult(
        elements=elements,
        page_structure=page_structure,
        has_nav_dots=has_nav_dots,
        page_element_to_panel=page_element_to_panel,
        css_var_to_elements=css_var_to_elements,
        present_elements=present_elements,
        _html=html_content
    )


def _selector_matches_element(elem_selector: str, target_selector: str, soup) -> bool:
    """Check if an element's selector matches/overlaps with a target selector."""
    # Exact match
    if elem_selector == target_selector:
        return True
    # Check if elem_selector is a child/descendant of target_selector
    # e.g. elem ".masthead h1" matches target ".masthead h1"
    # or elem ".masthead" is contained in target ".masthead .lead, .section-intro"
    es_parts = elem_selector.strip().split()
    ts_parts = target_selector.strip().split()
    # If target is a simple tag and elem ends with that tag
    if len(ts_parts) == 1 and len(es_parts) >= 1:
        if es_parts[-1] == ts_parts[0] or es_parts[-1].split('.')[0] == ts_parts[0]:
            return True
    # If they share the same last class/tag
    if len(es_parts) >= 1 and len(ts_parts) >= 1:
        if es_parts[-1] == ts_parts[-1]:
            return True
    return False
