/* ========================================================
   html-visual-editor - Editor core runtime
   Inject INSIDE a script block near the end of the body

   REQUIRED customizations in the target HTML:
   1. Define PAGE_ELEMENT_TO_PANEL mapping (see below)
   2. Define PRESETS (theme objects)
   3. Define DEFAULT_COLORS (for reset)
   4. Define SIZE_BOUNDS (clamp min/max for each size var)

   NOTE: never mix single-line and block comments in the same area.
   A bare-text line after a single-line-comment line crashes the
   script in the browser. See MEMORY 2026-05-07.
   ======================================================== */

/* =====================================================
   CORE PRESENTATION SCRIPTS
   ===================================================== */

const slides = document.querySelectorAll('.slide');
const reveals = document.querySelectorAll('.reveal');
const dots = document.querySelectorAll('.nav-dot');

function updateVisibility() {
    try {
        const trigger = window.innerHeight * 0.85;
        reveals.forEach(el => {
            if (el.getBoundingClientRect().top < trigger) el.classList.add('visible');
        });

        let current = 0;
        slides.forEach((s, i) => {
            const rect = s.getBoundingClientRect();
            if (rect.top <= 0 && rect.bottom > 0) current = i;
        });
        dots.forEach((d, i) => d.classList.toggle('active', i === current));
    } catch(err) {
        console.warn('[updateVisibility]', err);
    }
}

/* === 立即让所有 reveal 元素可见 ===
   不等滚动触发——页面一打开就显示全部内容，
   动画效果仅在首次滚动时生效 */
function revealAllNow() {
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
}

window.addEventListener('scroll', updateVisibility, { passive: true });
window.addEventListener('load', () => {
    try {
        updateVisibility();
        revealAllNow();
        if (slides[0]) slides[0].scrollIntoView();
        if (typeof loadFromStorage === 'function') loadFromStorage();
    } catch(err) {
        console.warn('[load handler]', err);
    }
});
// Run immediately too (in case load fires before this runs)
revealAllNow();
updateVisibility();

/* FAILSAFE: 1.5s 后如果仍有 .reveal 元素不可见，启用 CSS 兜底 */
setTimeout(() => {
    const invisible = [...document.querySelectorAll('.reveal')].filter(el => !el.classList.contains('visible'));
    if (invisible.length > 0) {
        console.warn(`[failsafe] ${invisible.length} .reveal elements still hidden, enabling CSS fallback`);
        document.documentElement.classList.add('reveal-fallback');
    }
}, 1500);

/* Keyboard nav + E key for edit mode */
document.addEventListener('keydown', e => {
    // Edit mode shortcuts
    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        saveToStorage();
        return;
    }
    if (e.key.toLowerCase() === 'e' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        // Don't toggle if user is typing in a contenteditable element
        if (document.activeElement.getAttribute('contenteditable') !== 'true') {
            toggleEditMode();
        }
        return;
    }
    // Navigation (only when not editing text)
    if (document.activeElement.getAttribute('contenteditable') !== 'true') {
        if (e.key === 'ArrowDown' || e.key === ' ' || e.key === 'PageDown') {
            e.preventDefault();
            const idx = [...slides].findIndex(s => s.getBoundingClientRect().top >= -1 && s.getBoundingClientRect().bottom > 1);
            if (idx < slides.length - 1) slides[idx + 1].scrollIntoView({ behavior: 'smooth' });
        } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
            e.preventDefault();
            const idx = [...slides].findIndex(s => s.getBoundingClientRect().top >= -1 && s.getBoundingClientRect().bottom > 1);
            if (idx > 0) slides[idx - 1].scrollIntoView({ behavior: 'smooth' });
        }
    }
});


/* =====================================================
   EDIT MODE ENGINE
   ===================================================== */

/* STORAGE_KEY: 必须每个 HTML 文件**唯一**，否则不同 html 之间会通过 localStorage
   互相污染（尤其是 file:// 协议下所有本地 html 共享同一个 origin）。
   策略：用 location.pathname + document.title 哈希，每个文件天然隔离。 */
function _editorStorageKey() {
    const raw = (location.pathname || '') + '|' + (document.title || '');
    // 简单 djb2 哈希
    let h = 5381;
    for (let i = 0; i < raw.length; i++) {
        h = ((h << 5) + h + raw.charCodeAt(i)) | 0;
    }
    return 'html-visual-editor::' + (h >>> 0).toString(36) + '::' + (raw.length & 0xffff).toString(36);
}
const STORAGE_KEY = _editorStorageKey();

/* =====================================================
   UNDO / HISTORY SYSTEM
   Captures snapshot before each meaningful change.
   Up to 30 steps (can increase if needed).
   ===================================================== */
const history = [];          // array of { type, data } snapshots
const MAX_HISTORY = 30;

function pushHistory(type, data) {
    // Deduplicate: skip if same as last entry
    const last = history[history.length - 1];
    if (last && last.type === type && JSON.stringify(last.data) === JSON.stringify(data)) return;
    history.push({ type, data });
    if (history.length > MAX_HISTORY) history.shift();
    updateUndoBtn();
}

function updateUndoBtn() {
    const btn = document.getElementById('btnUndo');
    if (btn) btn.disabled = history.length === 0;
}

/** Lightweight toast notification */
function showToast(msg, duration = 2000) {
    let toast = document.getElementById('editHint');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'editHint';
        toast.style.cssText = 'position:fixed;bottom:3rem;left:50%;transform:translateX(-50%);z-index:9997;padding:7px 18px;background:rgba(0,0,0,0.85);border:1px solid rgba(255,255,255,0.15);border-radius:100px;font-family:var(--font-body,system-ui);font-size:12px;color:#fff;pointer-events:none;white-space:nowrap;opacity:0;transition:opacity 0.3s';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = '1';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => { toast.style.opacity = '0'; }, duration);
}

function undoLast() {
    if (history.length === 0) return;
    const { type, data } = history.pop();
    updateUndoBtn();

    if (type === 'color') {
        document.documentElement.style.setProperty(data.varName, data.oldVal);
        // Sync UI
        document.querySelectorAll(`.color-row input[data-var="${data.varName}"]`).forEach(input => {
            const row = input.closest('.color-row');
            row.querySelector('.color-hex').value = data.oldVal.toUpperCase();
            row.querySelector('.color-swatch').style.background = data.oldVal;
            if (input.type === 'color') input.value = data.oldVal;
        });
    } else if (type === 'text') {
        const el = document.querySelector(`[data-editable="${data.id}"]`) ||
                   document.querySelectorAll('[data-editable]')[data.idx];
        if (el) {
            el.innerHTML = data.oldText;
            el.normalize();
        }
    } else if (type === 'size') {
        document.documentElement.style.setProperty(data.varName, data.oldVal);
        const slider = document.querySelector(`[data-var="${data.varName}"]`);
        if (slider) {
            const match = data.oldVal.match(/clamp\([^,]+,\s*([^,]+)/);
            if (match) slider.value = parseFloat(match[1]);
        }
    } else if (type === 'preset') {
        Object.entries(data.oldStyles).forEach(([v, val]) => {
            document.documentElement.style.setProperty(v, val);
        });
        // Sync all UI controls
        document.querySelectorAll('.color-row').forEach(row => {
            const ci = row.querySelector('input[type="color"]');
            const hi = row.querySelector('.color-hex');
            const sw = row.querySelector('.color-swatch');
            const vn = ci?.dataset.var;
            if (vn && data.oldStyles[vn] !== undefined) {
                const v = data.oldStyles[vn];
                if (ci) ci.value = v.startsWith('#') ? v : '#888888';
                if (hi) hi.value = v.startsWith('#') ? v.toUpperCase() : v;
                if (sw) sw.style.background = v.startsWith('#') ? v : '#888888';
            }
        });
    }

    // Brief flash to confirm undo
    document.body.style.transition = 'opacity 0.1s';
    document.body.style.opacity = '0.7';
    setTimeout(() => { document.body.style.opacity = ''; }, 150);
    showToast('↩ 已撤销上一步', 1500);
}

// === applyColor/applyHex/applyPreset defined below with full history support ===
document.addEventListener('focusin', e => {
    if (!e.target.hasAttribute('data-editable') || !e.target.getAttribute('contenteditable')) return;
    if (e.target.dataset._savedText !== undefined) return;
    e.target.dataset._savedText = e.target.innerHTML.trim();
});

/** Capture on blur */
document.addEventListener('blur', e => {
    if (!e.target.hasAttribute('data-editable')) return;
    const saved = e.target.dataset._savedText;
    if (saved !== undefined && saved !== e.target.innerHTML.trim()) {
        const idx = [...document.querySelectorAll('[data-editable]')].indexOf(e.target);
        pushHistory('text', { idx, oldText: saved });
    }
    delete e.target.dataset._savedText;
}, true);

// Default values for reset
/* 默认值——host HTML 可在 editor-core.js 之后用
   Object.assign(DEFAULT_COLORS, { ...你的色板... }); 覆盖
   或直接重新赋值 window.DEFAULT_COLORS = { ... }; */
var DEFAULT_COLORS = window.DEFAULT_COLORS = window.DEFAULT_COLORS || {
    '--accent': '#FF5722',
    '--card-bg': '#FF5722',
    '--bg-primary': '#1a1a1a',
    '--text-primary': '#ffffff',
    '--text-secondary': '#b0b0b0',
    '--text-on-card': '#1a1a1a',
    '--safe-green': '#00E676',
    '--warn-yellow': '#FFD600',
    '--danger-red': '#FF1744'
};

var PRESETS = window.PRESETS = window.PRESETS || {
    'bold-signal': {
        '--accent': '#FF5722', '--card-bg': '#FF5722', '--card-alt': '#FF7043',
        '--bg-primary': '#1a1a1a', '--bg-gradient': 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a2e 100%)',
        '--text-primary': '#ffffff', '--text-on-card': '#1a1a1a', '--text-secondary': '#b0b0b0',
        '--accent-glow': 'rgba(255, 87, 34, 0.25)',
        '--safe-green': '#00E676', '--warn-yellow': '#FFD600', '--danger-red': '#FF1744'
    },
    'ocean-blue': {
        '--accent': '#3B82F6', '--card-bg': '#2563EB', '--card-alt': '#3B82F6',
        '--bg-primary': '#0c1929', '--bg-gradient': 'linear-gradient(135deg, #0c1929 0%, #1a2744 50%, #0f172a 100%)',
        '--text-primary': '#e2e8f0', '--text-on-card': '#ffffff', '--text-secondary': '#94a3b8',
        '--accent-glow': 'rgba(59, 130, 246, 0.25)',
        '--safe-green': '#34D399', '--warn-yellow': '#FBBF24', '--danger-red': '#F87171'
    },
    'forest': {
        '--accent': '#22C55E', '--card-bg': '#16A34A', '--card-alt': '#22C55E',
        '--bg-primary': '#0a1612', '--bg-gradient': 'linear-gradient(135deg, #0a1612 0%, #142319 50%, #0d1a14 100%)',
        '--text-primary': '#ecfdf5', '--text-on-card': '#ffffff', '--text-secondary': '#86efac',
        '--accent-glow': 'rgba(34, 197, 94, 0.25)',
        '--safe-green': '#4ADE80', '--warn-yellow': '#FACC15', '--danger-red': '#FB7185'
    },
    'royal-purple': {
        '--accent': '#A78BFA', '--card-bg': '#8B5CF6', '--card-alt': '#A78BFA',
        '--bg-primary': '#131026', '--bg-gradient': 'linear-gradient(135deg, #131026 0%, #1e1a3d 50%, #0f0d1a 100%)',
        '--text-primary': '#ede9fe', '--text-on-card': '#ffffff', '--text-secondary': '#c4b5fd',
        '--accent-glow': 'rgba(167, 139, 250, 0.25)',
        '--safe-green': '#34D399', '--warn-yellow': '#FBBF24', '--danger-red': '#FB7185'
    },
    'rose-gold': {
        '--accent': '#F472B6', '--card-bg': '#EC4899', '--card-alt': '#F472B6',
        '--bg-primary': '#1a1216', '--bg-gradient': 'linear-gradient(135deg, #1a1216 0%, #2d1a24 50%, #1a1218 100%)',
        '--text-primary': '#fce7f3', '--text-on-card': '#ffffff', '--text-secondary': '#f9a8d4',
        '--accent-glow': 'rgba(244, 114, 182, 0.25)',
        '--safe-green': '#34D399', '--warn-yellow': '#FCD34D', '--danger-red': '#FCA5A5'
    },
    'mono-dark': {
        '--accent': '#e5e5e5', '--card-bg': '#404040', '--card-alt': '#525252',
        '--bg-primary': '#0a0a0a', '--bg-gradient': 'linear-gradient(135deg, #0a0a0a 0%, #171717 50%, #0d0d0d 100%)',
        '--text-primary': '#fafafa', '--text-on-card': '#fafafa', '--text-secondary': '#a3a3a3',
        '--accent-glow': 'rgba(229, 229, 229, 0.15)',
        '--safe-green': '#aaaaaa', '--warn-yellow': '#999999', '--danger-red': '#888888'
    }
};

/** Toggle edit mode on/off */
function toggleEditMode() {
    const isEdit = !document.body.classList.contains('edit-mode');
    document.body.classList.toggle('edit-mode', isEdit);

    // Toggle contenteditable on all marked elements
    document.querySelectorAll('[data-editable]').forEach(el => {
        el.setAttribute('contenteditable', isEdit ? 'true' : 'false');
    });

    // Update toolbar button state
    const btn = document.getElementById('btnToggleEdit');
    if (btn) btn.classList.toggle('active', isEdit);
    document.getElementById('btnEditText').textContent = isEdit ? '退出编辑' : '编辑';

    // Show/hide hint
    const hint = document.getElementById('editHint');
    hint.classList.toggle('visible', isEdit);
    setTimeout(() => hint.classList.remove('visible'), 3500);

    // Auto-focus first editable element for immediate typing
    if (isEdit) {
        setTimeout(() => {
            const firstEditable = document.querySelector('[data-editable]');
            if (firstEditable) {
                firstEditable.focus();
                // Place cursor at end of existing text
                const range = document.createRange();
                const sel = window.getSelection();
                range.selectNodeContents(firstEditable);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
            }
        }, 100);
    }
}

/** Apply color from color picker */
function applyColor(input) {
    const val = input.value;
    const varName = input.dataset.var;
    document.documentElement.style.setProperty(varName, val);

    // Update sibling hex input and swatch
    const row = input.closest('.color-row');
    const hexInput = row.querySelector('.color-hex');
    const swatch = row.querySelector('.color-swatch');
    if (hexInput) hexInput.value = val.toUpperCase();
    if (swatch) swatch.style.background = val;

    // Sync related variables
    syncRelatedVars(varName, val);
}

/** Preview color on drag (before releasing) */
function previewColor(input) {
    applyColor(input);
}

/** Apply color from hex text input */
function applyHex(input) {
    let val = input.value.trim();
    if (!val.startsWith('#')) val = '#' + val;
    if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        const varName = input.dataset.var;
        document.documentElement.style.setProperty(varName, val.toUpperCase());
        const row = input.closest('.color-row');
        const colorInput = row.querySelector('input[type="color"]');
        const swatch = row.querySelector('.color-swatch');
        if (colorInput) colorInput.value = val;
        if (swatch) swatch.style.background = val;
        syncRelatedVars(varName, val.toUpperCase());
    }
}

/** Sync accent → card-bg / accent-glow etc. */
function syncRelatedVars(varName, val) {
    if (varName === '--accent') {
        document.documentElement.style.setProperty('--card-bg', val);
        document.documentElement.style.setProperty('--accent-glow', val + '40'); // rough alpha
        // Also update card-bg UI
        const cbRow = document.querySelector('[data-var="--card-bg"]?.closest(".color-row")');
        if (cbRow) {
            cbRow.querySelector('.color-swatch').style.background = val;
            cbRow.querySelector('input[type="color"]').value = val;
            cbRow.querySelector('.color-hex').value = val.toUpperCase();
        }
    }
    if (varName === '--bg-primary') {
        // Rebuild gradient from new bg
        const grad = `linear-gradient(135deg, ${val} 0%, ${lighten(val, 20)} 50%, ${lighten(val, 10)} 100%)`;
        document.documentElement.style.setProperty('--bg-gradient', grad);
    }
}

/** Simple color lightener helper */
function lighten(hex, pct) {
    let r = parseInt(hex.slice(1,3), 16);
    let g = parseInt(hex.slice(3,5), 16);
    let b = parseInt(hex.slice(5,7), 16);
    r = Math.min(255, Math.floor(r + (255 - r) * pct / 100));
    g = Math.min(255, Math.floor(g + (255 - g) * pct / 100));
    b = Math.min(255, Math.floor(b + (255 - b) * pct / 100));
    return '#' + [r,g,b].map(x => x.toString(16).padStart(2,'0')).join('');
}

/** Apply a preset theme */
function applyPreset(name) {
    const p = PRESETS[name];
    if (!p) {
        console.warn(`[html-visual-editor] PRESETS["${name}"] not found. Available:`, Object.keys(PRESETS));
        return;
    }

    // Capture current state of all CSS vars touched by this preset for undo
    const oldStyles = {};
    Object.keys(p).forEach(v => {
        oldStyles[v] = getComputedStyle(document.documentElement).getPropertyValue(v).trim();
    });
    if (typeof pushHistory === 'function') pushHistory('preset', { oldStyles });

    Object.entries(p).forEach(([varName, val]) => {
        document.documentElement.style.setProperty(varName, val);
    });

    // Update all UI controls to match preset
    document.querySelectorAll('.color-row').forEach(row => {
        const colorInput = row.querySelector('input[type="color"]');
        const hexInput = row.querySelector('.color-hex');
        const swatch = row.querySelector('.color-swatch');
        const varName = colorInput?.dataset.var;
        if (varName && p[varName]) {
            const v = p[varName];
            if (colorInput) colorInput.value = v.startsWith('#') ? v : '#888888';
            if (hexInput) hexInput.value = v.startsWith('#') ? v.toUpperCase() : v;
            if (swatch) swatch.style.background = v.startsWith('#') ? v : '#888888';
        }
    });
}

/** Known safe clamp bounds for each size variable
    NOTE: clamp max MUST exceed slider max, or clamp() caps the value silently */
var SIZE_BOUNDS = window.SIZE_BOUNDS = window.SIZE_BOUNDS || {
    '--title-size': { min: '2rem',   max: '12rem' },
    '--h2-size':    { min: '1.4rem', max: '10rem' },
    '--body-size':  { min: '0.75rem', max: '4rem' },
    '--small-size': { min: '0.65rem', max: '3rem'  },
    '--stat-size':  { min: '1rem',    max: '10rem' },
    '--hero-size':  { min: '2rem',    max: '16rem' },
};

// =====================================================
//    ✦✦✦  REVERSE MAPPING: PAGE ELEMENT → PANEL CONTROL  ✦✦✦
//    Hover/click a page element → show tooltip pointing to panel
// =====================================================

/**
 * Page element class → list of panel controls (multiple dimensions per element)
 * 每个元素可能在多个维度上被调整：颜色 + 字号 + 布局
 * ⚠️ 此处所有 row 文案 MUST 与面板里实际存在的 slider-name / color-label 一字不差！
 * 顺序按重要性排列，悬浮提示会并列列出
 */
var PAGE_ELEMENT_TO_PANEL = window.PAGE_ELEMENT_TO_PANEL = window.PAGE_ELEMENT_TO_PANEL || {
    // ========== Slide 1: TITLE ==========
    '.section-num':          [
        { tab: '颜色', row: '强调色 Accent' },
        { tab: '字号', row: '小字 Small' },
    ],
    '.main-title':           [
        { tab: '字号', row: '主标题 Title' },
        { tab: '颜色', row: '主文字 Text' },
        { tab: '布局', row: '标题区 Title' },
    ],
    '.main-title .highlight':[
        { tab: '颜色', row: '强调色 Accent' },
        { tab: '字号', row: '主标题 Title' },
    ],
    '.subtitle':             [
        { tab: '字号', row: '正文 Body' },
        { tab: '颜色', row: '次要文字 Secondary' },
        { tab: '布局', row: '副标题 Subtitle' },
    ],
    '.title-card':           [
        { tab: '颜色', row: '卡片底色 Card BG' },
    ],
    '.score-label':          [
        { tab: '字号', row: '小字 Small' },
        { tab: '颜色', row: '卡内反色 On-Card' },
    ],
    '.score-big':            [
        { tab: '字号', row: '超大数字 Hero（封面分数）' },
        { tab: '颜色', row: '卡内反色 On-Card' },
    ],
    '.verdict':              [
        { tab: '颜色', row: '卡内反色 On-Card' },
    ],

    // ========== Slide 2: SCORECARD GRID ==========
    '.grid-label':           [
        { tab: '颜色', row: '强调色 Accent' },
        { tab: '字号', row: '小字 Small' },
    ],
    '.grid-title':           [
        { tab: '字号', row: '二级标题 H2' },
        { tab: '颜色', row: '主文字 Text' },
        { tab: '布局', row: '正文区 Body' },
    ],
    '.score-grid':           [
        { tab: '布局', row: '卡片间距 Gap' },
        { tab: '布局', row: '网格最大宽度' },
    ],
    '.score-card':           [
        { tab: '布局', row: '卡片内边距 Padding' },
        { tab: '布局', row: '卡片间距 Gap' },
    ],
    '.score-card-icon':      [
        { tab: '颜色', row: '主文字 Text' },
    ],
    '.score-card-name':      [
        { tab: '字号', row: '正文 Body' },
        { tab: '颜色', row: '主文字 Text' },
    ],
    '.score-card-score':     [
        { tab: '字号', row: '大数字 Stat（统计/评分）' },
        { tab: '颜色', row: '安全绿 Safe' },
        { tab: '颜色', row: '警告黄 Warn' },
        { tab: '颜色', row: '危险红 Danger' },
    ],
    '.score-card-desc':      [
        { tab: '字号', row: '小字 Small' },
        { tab: '颜色', row: '次要文字 Secondary' },
        { tab: '布局', row: '描述文字 Desc' },
    ],
    '.tag-safe':             [
        { tab: '颜色', row: '安全绿 Safe' },
    ],
    '.tag-warn':             [
        { tab: '颜色', row: '警告黄 Warn' },
    ],
    '.tag-danger':           [
        { tab: '颜色', row: '危险红 Danger' },
    ],

    // ========== Slide 3: VERDICT ==========
    '.verdict-badge':        [
        { tab: '颜色', row: '安全绿 Safe' },
        { tab: '字号', row: '小字 Small' },
    ],
    '.verdict-title':        [
        { tab: '字号', row: '主标题 Title' },
        { tab: '颜色', row: '主文字 Text' },
    ],
    '.verdict-subtitle':     [
        { tab: '字号', row: '正文 Body' },
        { tab: '颜色', row: '次要文字 Secondary' },
        { tab: '布局', row: '正文区 Body' },
    ],
    '.verdict-stats':        [
        { tab: '布局', row: '数字间距 Stats Gap' },
    ],
    '.stat-num':             [
        { tab: '字号', row: '大数字 Stat（统计/评分）' },
        { tab: '颜色', row: '强调色 Accent' },
    ],
    '.stat-label':           [
        { tab: '字号', row: '小字 Small' },
        { tab: '颜色', row: '次要文字 Secondary' },
    ],

    // ========== Navigation ==========
    '.nav-dot':              [
        { tab: '颜色', row: '强调色 Accent' },
    ],
};

/** Page element hover tooltip (reverse mapping) */
let _pageTooltip = null;
let _pinnedTooltip = false;     // 用户点击后被"固定"
let _pinnedSourceEl = null;     // 当前固定tooltip绑定的页面元素

/** Tab name (中文) → tab id 映射 */
const TAB_NAME_TO_ID = {
    '颜色': 'colors',
    '预设': 'presets',
    '布局': 'layout',
    '字号': 'size',
};

/** Tab name → 颜色编码 */
const TAB_COLORS = {
    '颜色': '#FF7043',
    '字号': '#64B5F6',
    '布局': '#81C784',
    '预设': '#BA68C8',
};

/** 根据 tab+row 找到对应面板控件（slider 或 color-row） */
function findPanelControl(tabName, rowName) {
    const tabId = TAB_NAME_TO_ID[tabName];
    if (!tabId) return null;
    const tabContent = document.getElementById('tab-' + tabId);
    if (!tabContent) return null;

    // 颜色tab：根据 .color-label 文本匹配
    const colorRows = tabContent.querySelectorAll('.color-row');
    for (const row of colorRows) {
        const label = row.querySelector('.color-label');
        if (label && label.textContent.trim() === rowName) return row;
    }

    // 字号/布局tab：根据 .slider-name 文本匹配
    const sliderRows = tabContent.querySelectorAll('.slider-row');
    for (const row of sliderRows) {
        const name = row.querySelector('.slider-name');
        if (name && name.textContent.trim() === rowName) return row;
    }

    return null;
}

/** 跳到指定面板控件：切换tab + 滚动到位 + 临时高亮 */
function jumpToPanelControl(tabName, rowName) {
    const tabId = TAB_NAME_TO_ID[tabName];
    if (tabId && typeof switchPanelTab === 'function') {
        switchPanelTab(tabId);
    }
    // 等tab切换动画后再滚动
    setTimeout(() => {
        const ctrl = findPanelControl(tabName, rowName);
        if (!ctrl) return;
        ctrl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // 临时高亮3秒
        ctrl.style.transition = 'background 0.3s, box-shadow 0.3s';
        const oldBg = ctrl.style.background;
        const oldShadow = ctrl.style.boxShadow;
        ctrl.style.background = 'rgba(255, 200, 50, 0.18)';
        ctrl.style.boxShadow = '0 0 0 2px rgba(255, 200, 50, 0.6), 0 0 16px rgba(255,200,50,0.4)';
        ctrl.style.borderRadius = '8px';
        setTimeout(() => {
            ctrl.style.background = oldBg;
            ctrl.style.boxShadow = oldShadow;
        }, 2400);
    }, 60);
}

/** Render multi-line tooltip showing all adjustable dimensions */
function showPageElementTooltip(el, infoList, x, y, opts = {}) {
    // 如果已有固定tooltip，且不是正在创建固定tooltip，则不覆盖
    if (_pinnedTooltip && !opts.replacePinned) return;

    clearPageTooltip();

    const tip = document.createElement('div');
    tip.className = 'panel-highlight-tooltip';
    tip.dataset.pinned = opts.pinned ? '1' : '0';

    // Header
    const headerHtml = `
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.08);">
            <span style="font-size:11px;color:rgba(255,200,50,0.85);font-weight:600;letter-spacing:0.04em;">
                ${opts.pinned ? '📌 已固定 · 点击下方跳转面板' : '↖ 此处可调整：'}
            </span>
            ${opts.pinned ? '<button class="tt-close-btn" style="background:none;border:none;color:rgba(255,255,255,0.5);cursor:pointer;font-size:14px;padding:0 4px;line-height:1;">✕</button>' : '<span style="font-size:10px;color:rgba(255,200,50,0.55);">按 <kbd style="background:rgba(255,255,255,0.1);padding:1px 5px;border-radius:3px;font-family:monospace;">P</kbd> 固定</span>'}
        </div>`;

    // Rows — each clickable, jumps to panel
    const rowsHtml = infoList.map((info, i) => {
        const tagColor = TAB_COLORS[info.tab] || 'rgba(255,200,50,0.9)';
        return `
        <div class="tt-row" data-tab="${info.tab}" data-row="${info.row.replace(/"/g, '&quot;')}"
             style="display:flex;align-items:center;gap:8px;padding:6px 8px;margin:2px -4px;border-radius:6px;cursor:${opts.pinned ? 'pointer' : 'default'};transition:background 0.15s;">
            <span style="display:inline-block;padding:2px 8px;border-radius:4px;background:${tagColor}22;border:1px solid ${tagColor}88;color:${tagColor};font-size:10.5px;font-weight:600;flex-shrink:0;">${info.tab}</span>
            <span style="color:rgba(255,255,255,0.88);font-size:12px;">${info.row}</span>
            ${opts.pinned ? '<span style="margin-left:auto;color:rgba(255,200,50,0.6);font-size:11px;">→</span>' : ''}
        </div>`;
    }).join('');

    tip.innerHTML = headerHtml + rowsHtml;

    tip.style.cssText = `
        position: fixed;
        z-index: 10002;
        background: rgba(20, 20, 20, 0.97);
        border: 1px solid ${opts.pinned ? 'rgba(255, 200, 50, 0.7)' : 'rgba(255, 200, 50, 0.4)'};
        border-radius: 10px;
        padding: 10px 14px;
        font-family: var(--font-body, sans-serif);
        color: rgba(255, 255, 255, 0.9);
        pointer-events: ${opts.pinned ? 'auto' : 'none'};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        box-shadow: 0 6px 24px rgba(0,0,0,0.5)${opts.pinned ? ', 0 0 0 3px rgba(255,200,50,0.15)' : ''};
        line-height: 1.4;
        min-width: 200px;
        max-width: 320px;
    `;

    document.body.appendChild(tip);
    _pageTooltip = tip;

    // 固定模式下绑定行点击事件
    if (opts.pinned) {
        tip.querySelectorAll('.tt-row').forEach(row => {
            row.addEventListener('mouseenter', () => row.style.background = 'rgba(255,255,255,0.06)');
            row.addEventListener('mouseleave', () => row.style.background = '');
            row.addEventListener('click', () => {
                jumpToPanelControl(row.dataset.tab, row.dataset.row);
            });
        });
        const closeBtn = tip.querySelector('.tt-close-btn');
        if (closeBtn) closeBtn.addEventListener('click', () => {
            _pinnedTooltip = false;
            _pinnedSourceEl = null;
            clearPageTooltip();
            // 同时清除页面元素的固定高亮
            document.querySelectorAll('.pinned-page-el').forEach(el => el.classList.remove('pinned-page-el'));
        });
    }

    // 测量真实尺寸再定位
    const rect = tip.getBoundingClientRect();
    const tipW = rect.width;
    const tipH = rect.height;
    let posX = x + 18;
    let posY = y - 10;
    if (posX + tipW > window.innerWidth - 10) posX = x - tipW - 18;
    if (posY < 10) posY = 10;
    if (posY + tipH > window.innerHeight - 10) posY = window.innerHeight - tipH - 10;
    tip.style.left = posX + 'px';
    tip.style.top = posY + 'px';
}

function clearPageTooltip() {
    if (_pageTooltip) {
        _pageTooltip.remove();
        _pageTooltip = null;
    }
}

/** Find ALL panel control info applicable to this element (collect from element + ancestors) */
function findPanelInfo(el) {
    const collected = [];
    const seenKeys = new Set();
    let current = el;

    while (current && current !== document.body) {
        for (const selector of Object.keys(PAGE_ELEMENT_TO_PANEL)) {
            try {
                if (current.matches && current.matches(selector)) {
                    const items = PAGE_ELEMENT_TO_PANEL[selector];
                    // Support both single-object (legacy) and array forms
                    const list = Array.isArray(items) ? items : [items];
                    list.forEach(item => {
                        const key = (item.tab || '') + '|' + (item.row || '');
                        if (!seenKeys.has(key)) {
                            seenKeys.add(key);
                            collected.push(item);
                        }
                    });
                }
            } catch(_) { /* invalid selector — skip */ }
        }
        current = current.parentElement;
    }

    return collected.length > 0 ? collected : null;
}

/** Init reverse mapping: page element hover → show panel hint */
function initPageElementHighlights() {
    // 触发热区：所有 PAGE_ELEMENT_TO_PANEL 里的选择器 + data-editable 元素
    // 这样不管 host HTML 是 slides 结构还是单页文档结构都能工作
    const selectors = new Set();
    selectors.add('[data-editable]');  // 所有可编辑元素都该能触发
    Object.keys(PAGE_ELEMENT_TO_PANEL || {}).forEach(sel => selectors.add(sel));
    const selectorString = [...selectors].join(', ');

    let targets;
    try {
        targets = document.querySelectorAll(selectorString);
    } catch(err) {
        console.warn('[html-visual-editor] selector error, using fallback:', err);
        targets = document.querySelectorAll('[data-editable]');
    }

    // 记录鼠标当前悬停的目标和坐标，供 P 键固定使用
    let _hoverTarget = null;
    let _hoverX = 0, _hoverY = 0;

    targets.forEach(el => {
        if (el.closest('.edit-panel') || el.closest('.edit-toolbar')) return;

        // hover → 临时显示
        el.addEventListener('mouseover', (e) => {
            if (!document.body.classList.contains('edit-mode')) return;
            if (_pinnedTooltip) return;
            _hoverTarget = e.target;
            _hoverX = e.clientX; _hoverY = e.clientY;
            const infoList = findPanelInfo(e.target);
            if (infoList && infoList.length > 0) {
                showPageElementTooltip(e.target, infoList, e.clientX, e.clientY);
            }
        });

        // mousemove → 跟随鼠标
        el.addEventListener('mousemove', (e) => {
            _hoverTarget = e.target;
            _hoverX = e.clientX; _hoverY = e.clientY;
            if (_pinnedTooltip) return;
            if (_pageTooltip && !_pageTooltip.contains(e.target)) {
                const rect = _pageTooltip.getBoundingClientRect();
                const tipW = rect.width;
                const tipH = rect.height;
                let posX = e.clientX + 18;
                let posY = e.clientY - 10;
                if (posX + tipW > window.innerWidth - 10) posX = e.clientX - tipW - 18;
                if (posY < 10) posY = 10;
                if (posY + tipH > window.innerHeight - 10) posY = window.innerHeight - tipH - 10;
                _pageTooltip.style.left = posX + 'px';
                _pageTooltip.style.top = posY + 'px';
            }
        });

        // mouseout → 清除（仅当没固定时）
        el.addEventListener('mouseout', (e) => {
            if (_pinnedTooltip) return;
            if (!_pageTooltip || !_pageTooltip.contains(e.relatedTarget)) {
                clearPageTooltip();
            }
        });
    });

    // 全局 P 键监听 → 固定/解锁当前tooltip
    document.addEventListener('keydown', (e) => {
        if (!document.body.classList.contains('edit-mode')) return;
        // 不在文字编辑时
        if (document.activeElement && document.activeElement.getAttribute('contenteditable') === 'true') return;
        if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
        if (e.key.toLowerCase() !== 'p') return;

        e.preventDefault();
        e.stopPropagation();

        if (_pinnedTooltip) {
            // 解锁
            _pinnedTooltip = false;
            _pinnedSourceEl = null;
            clearPageTooltip();
            document.querySelectorAll('.pinned-page-el').forEach(p => p.classList.remove('pinned-page-el'));
            return;
        }

        // 固定当前 hover
        if (_hoverTarget) {
            const infoList = findPanelInfo(_hoverTarget);
            if (infoList && infoList.length > 0) {
                _pinnedTooltip = true;
                _pinnedSourceEl = _hoverTarget;
                document.querySelectorAll('.pinned-page-el').forEach(p => p.classList.remove('pinned-page-el'));
                _hoverTarget.classList.add('pinned-page-el');
                showPageElementTooltip(_hoverTarget, infoList, _hoverX, _hoverY, { pinned: true, replacePinned: true });
            }
        }
    });

    // 点击 tooltip 外部（且非面板）→ 取消固定
    document.addEventListener('click', (e) => {
        if (!_pinnedTooltip) return;
        if (_pageTooltip && _pageTooltip.contains(e.target)) return;
        if (e.target.closest('.edit-panel') || e.target.closest('.edit-toolbar')) return;
        // 点其它有映射的元素 → 重新固定到那里
        const mapped = e.target.closest('[data-editable], .score-card, .nav-dot, .title-card, .verdict-stats, .stat-item, .score-grid, .grid-header, .verdict-badge');
        if (mapped) {
            const infoList = findPanelInfo(e.target);
            if (infoList && infoList.length > 0) {
                document.querySelectorAll('.pinned-page-el').forEach(p => p.classList.remove('pinned-page-el'));
                _pinnedSourceEl = e.target;
                e.target.classList.add('pinned-page-el');
                showPageElementTooltip(e.target, infoList, e.clientX, e.clientY, { pinned: true, replacePinned: true });
            }
            return;
        }
        // 否则取消固定
        _pinnedTooltip = false;
        _pinnedSourceEl = null;
        clearPageTooltip();
        document.querySelectorAll('.pinned-page-el').forEach(p => p.classList.remove('pinned-page-el'));
    });
}

/* =====================================================
   ✦✦✦  PANEL → PAGE ELEMENT MAPPING  ✦✦✦
   Hover a panel row → the page elements it controls glow
   ===================================================== */

/**
 * CSS var → page element selectors
 * Used for hover/click highlighting
 * 格式: "CSS变量名": "选择器1, 选择器2, ..."
 */
var CSS_VAR_TO_ELEMENTS = window.CSS_VAR_TO_ELEMENTS = window.CSS_VAR_TO_ELEMENTS || {
    // 强调色 Accent → 所有橙色调元素（标题前缀/标签/导航点）
    '--accent':       '.section-num, .grid-label, .main-title .highlight, .nav-dot.active, .score-card-icon, .stat-num',

    // 卡片底色 Card BG → title-card背景
    '--card-bg':      '.title-card',

    // 安全绿 Safe → 所有绿色文字元素
    '--safe-green':   '.tag-safe, .verdict-badge, .verdict-badge::before',

    // 警告黄 Warn → 警告标签
    '--warn-yellow':  '.tag-warn',

    // 危险红 Danger → 危险标签
    '--danger-red':   '.tag-danger',

    // 背景色 → 全局背景（仅在编辑模式下高亮body）
    '--bg-primary':   'body',

    // 主文字 → 主要文字（排除卡片内的反色文字）
    '--text-primary': '.main-title, .score-card-name, .score-card-icon, .grid-title',

    // 次要文字 → 辅助说明文字
    '--text-secondary': '.subtitle, .score-card-desc, .verdict-subtitle, .stat-label',
};

/**
 * Layout slider target → human-readable label
 * Maps the slider's data-target selector to a friendly name
 */
var LAYOUT_TARGET_LABELS = window.LAYOUT_TARGET_LABELS = window.LAYOUT_TARGET_LABELS || {
    '.title-left':           '主标题区',
    '.subtitle':             '副标题',
    '.grid-title, .verdict-subtitle': '正文区',
    '.score-card-desc':      '评分卡描述',
};

/* Track active highlight + tooltip */
let _activeHighlightEls = [];
let _activeTooltip = null;
let _lastHighlightedControl = null;

/** Highlight page elements controlled by a panel row */
function highlightPageElements(els, label) {
    clearHighlights();

    els.forEach(el => {
        if (el) el.classList.add('panel-highlight');
    });
    _activeHighlightEls = els;

    // Show tooltip near cursor area (slide viewport center)
    showHighlightTooltip(label);
}

/** Clear all active highlights */
function clearHighlights() {
    _activeHighlightEls.forEach(el => {
        if (el) el.classList.remove('panel-highlight');
    });
    _activeHighlightEls = [];
    if (_activeTooltip) {
        _activeTooltip.remove();
        _activeTooltip = null;
    }
}

/** Show a tooltip near the panel row */
function showHighlightTooltip(text) {
    if (_activeTooltip) _activeTooltip.remove();
    const tip = document.createElement('div');
    tip.className = 'panel-highlight-tooltip';
    tip.textContent = text;
    document.body.appendChild(tip);
    _activeTooltip = tip;

    // Position: right of panel, vertically centered in viewport
    const panel = document.getElementById('editPanel');
    const panelRect = panel ? panel.getBoundingClientRect() : { right: 310, top: 0, height: window.innerHeight };
    const viewH = window.innerHeight;

    // Place tooltip to the left of the panel (inside panel area would overlap controls)
    // Position it at the right edge of panel, vertically centered
    tip.style.right = (window.innerWidth - panelRect.right + 8) + 'px';
    tip.style.top = Math.max(10, Math.min(window.innerHeight - 40, viewH / 2 - 15)) + 'px';
}

/** Get target elements for a given CSS var name */
function getTargetsForVar(varName) {
    const selector = CSS_VAR_TO_ELEMENTS[varName];
    if (!selector) return [];
    return [...document.querySelectorAll(selector)].filter(el =>
        !el.closest('.edit-toolbar') && !el.closest('.edit-panel') && !el.closest('.nav-dots') && !el.closest('.keyboard-hint')
    );
}

/** Init panel highlight bindings — call once on load */
function initPanelHighlights() {
    // Color rows: hover → highlight, leave → clear
    document.querySelectorAll('.color-row').forEach(row => {
        const varName = row.querySelector('[data-var]')?.dataset.var;
        if (!varName) return;

        row.addEventListener('mouseover', () => {
            const labelEl = row.querySelector('.color-label');
            const label = labelEl ? labelEl.textContent.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '').trim() : varName;
            const els = getTargetsForVar(varName);
            highlightPageElements(els, label + ' ← 当前行控制');
            _lastHighlightedControl = row;
        });

        row.addEventListener('mouseout', (e) => {
            // Only clear if mouse actually left the row (not entering a child)
            if (!row.contains(e.relatedTarget)) {
                clearHighlights();
                _lastHighlightedControl = null;
            }
        });
    });

    // Layout sliders: hover → highlight data-target elements
    document.querySelectorAll('.slider-row input[type="range"]').forEach(slider => {
        const target = slider.dataset.target;
        if (!target) return;

        slider.closest('.slider-row').addEventListener('mouseover', () => {
            const labelEl = slider.closest('.slider-row').querySelector('.slider-name');
            const label = labelEl ? labelEl.textContent.trim() : target;
            const els = [...document.querySelectorAll(target)].filter(el =>
                !el.closest('.edit-panel') && !el.closest('.edit-toolbar')
            );
            highlightPageElements(els, label + ' ← 当前行控制');
        });

        slider.closest('.slider-row').addEventListener('mouseout', (e) => {
            if (!slider.closest('.slider-row').contains(e.relatedTarget)) {
                clearHighlights();
            }
        });
    });

    // Size sliders: hover → highlight elements using the CSS var
    document.querySelectorAll('.slider-row input[data-var]').forEach(slider => {
        const varName = slider.dataset.var;
        if (!varName || slider.dataset.target) return; // skip layout sliders (already handled above)

        slider.closest('.slider-row').addEventListener('mouseover', () => {
            const labelEl = slider.closest('.slider-row').querySelector('.slider-name');
            const label = labelEl ? labelEl.textContent.trim() : varName;
            // Highlight all elements that inherit this CSS var (approximate via tag + class)
            const varMap = {
                '--title-size':  '.main-title, .title-left, .verdict-title',
                '--h2-size':     'h2, .grid-title',
                '--body-size':   '.subtitle, .verdict-subtitle, .score-card-desc',
                '--small-size':  '.score-label, .section-num, .grid-label, .tag-safe, .tag-warn, .tag-danger, .verdict-badge',
            };
            const selector = varMap[varName] || 'p, span, div';
            const els = [...document.querySelectorAll(selector.split(', '))].filter(el =>
                !el.closest('.edit-panel') && !el.closest('.edit-toolbar')
            );
            highlightPageElements(els, label + ' ← 当前行控制');
        });

        slider.closest('.slider-row').addEventListener('mouseout', (e) => {
            if (!slider.closest('.slider-row').contains(e.relatedTarget)) {
                clearHighlights();
            }
        });
    });
}

/** Apply size slider change */
function applySize(slider, displayId, unit) {
    const val = parseFloat(slider.value);
    const varName = slider.dataset.var;
    // Build new clamp() using known bounds — never rely on getComputedStyle regex
    const bounds = SIZE_BOUNDS[varName];
    if (bounds) {
        const newVal = `clamp(${bounds.min}, ${val}${unit}, ${bounds.max})`;
        document.documentElement.style.setProperty(varName, newVal);
    } else {
        // Fallback: simple vw-only value
        document.documentElement.style.setProperty(varName, `${val}${unit}`);
    }
    document.getElementById(displayId).textContent = `${val} ${unit}`;
}

/** Switch panel tabs */
/** Apply layout slider (width/padding) to target elements */
function applyLayout(slider, displayId) {
    const val = parseInt(slider.value);
    const unit = slider.dataset.unit || 'px';
    const prop = slider.dataset.prop || 'max-width';
    const targets = document.querySelectorAll(slider.dataset.target);
    targets.forEach(el => {
        el.style[prop] = `${val}${unit}`;
    });
    document.getElementById(displayId).textContent = `${val}${unit}`;
}

function switchPanelTab(tabName) {
    document.querySelectorAll('.panel-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
    document.querySelectorAll('.panel-tab-content').forEach(c => c.classList.toggle('active', c.id === 'tab-' + tabName));
}

/** Save state to localStorage */
function saveToStorage() {
    // Collect all CSS custom property overrides — 用 DEFAULT_COLORS 的 keys 而非硬编码
    const styles = {};
    const varsToSave = (typeof DEFAULT_COLORS === 'object' && DEFAULT_COLORS)
        ? Object.keys(DEFAULT_COLORS)
        : ['--accent','--card-bg','--bg-primary','--text-primary','--text-secondary','--safe-green','--warn-yellow','--danger-red'];
    varsToSave.forEach(v => {
        const val = getComputedStyle(document.documentElement).getPropertyValue(v).trim();
        if (val) styles[v] = val;
    });

    // Collect all edited text content
    const texts = {};
    const editables = document.querySelectorAll('[data-editable]');
    editables.forEach((el, i) => {
        texts['el_' + i] = el.innerHTML.trim();
    });

    // Page signature: 用于 load 时校验"是不是同一份文档"
    // 由元素总数 + 各元素的 class 列表组成（结构指纹）
    const signature = {
        editableCount: editables.length,
        // 取前16个元素的 class 名作为结构指纹（够用且不大）
        classFingerprint: [...editables].slice(0, 16).map(el => el.className || '').join('|'),
        title: document.title || '',
        path: location.pathname || '',
    };

    const state = { signature, styles, texts, savedAt: new Date().toISOString(), version: 2 };
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        showSaveIndicator(true);
    } catch(e) {
        alert('保存失败：localStorage 可能已满或不可用');
    }
}

/** Load state from localStorage */
function loadFromStorage() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const state = JSON.parse(raw);

        // ⚠️  防污染校验：只有在文档"指纹"匹配时才恢复内容
        // 这样即使 STORAGE_KEY 哈希碰撞或同名文件覆盖，也不会错位赋值
        const editables = document.querySelectorAll('[data-editable]');
        const sig = state.signature;
        if (sig) {
            const currentFingerprint = [...editables].slice(0, 16).map(el => el.className || '').join('|');
            const mismatch = (
                sig.editableCount !== editables.length ||
                sig.classFingerprint !== currentFingerprint ||
                (sig.title && sig.title !== document.title)
            );
            if (mismatch) {
                console.warn('[html-visual-editor] localStorage 与当前文档不匹配，跳过恢复以防内容污染。',
                    { saved: sig, current: { editableCount: editables.length, title: document.title } });
                // 删掉污染的旧条目
                try { localStorage.removeItem(STORAGE_KEY); } catch(_) {}
                return;
            }
        } else {
            // 旧版本（v1）没有 signature，直接拒绝恢复并清掉
            console.warn('[html-visual-editor] 旧版本 localStorage 数据，跳过恢复。');
            try { localStorage.removeItem(STORAGE_KEY); } catch(_) {}
            return;
        }

        // Restore colors
        if (state.styles) {
            Object.entries(state.styles).forEach(([v, val]) => {
                document.documentElement.style.setProperty(v, val);
            });
            // Update UI controls
            document.querySelectorAll('.color-row').forEach(row => {
                const ci = row.querySelector('input[type="color"]');
                const hi = row.querySelector('.color-hex');
                const sw = row.querySelector('.color-swatch');
                const vn = ci?.dataset.var;
                if (vn && state.styles[vn]) {
                    const v = state.styles[vn];
                    if (ci) ci.value = v.startsWith('#') ? v : '#888888';
                    if (hi) hi.value = v.startsWith('#') ? v.toUpperCase() : v;
                    if (sw) sw.style.background = v.startsWith('#') ? v : '#888888';
                }
            });
        }

        // Restore texts
        if (state.texts) {
            editables.forEach((el, i) => {
                if (state.texts['el_' + i] !== undefined) {
                    el.innerHTML = state.texts['el_' + i];
                }
            });
        }
    } catch(e) {
        console.warn('Failed to load saved state:', e);
    }
}

/** Show save indicator briefly */
function showSaveIndicator(ok) {
    const el = document.getElementById('saveIndicator');
    el.textContent = ok ? '已保存 ✓' : '保存失败';
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2000);
}

/** Export current HTML as downloadable file */
function exportHTML() {
    // Collect current state
    const clone = document.documentElement.cloneNode(true);

    // Remove edit UI elements from export
    clone.querySelectorAll('.edit-toolbar, .edit-panel, .edit-hint').forEach(el => el.remove());
    // Remove contenteditable attributes and markers
    clone.querySelectorAll('[contenteditable]').forEach(el => el.removeAttribute('contenteditable'));
    clone.querySelectorAll('[data-editable]').forEach(el => el.removeAttribute('data-editable'));
    // Remove reveal animation delays (optional cleanup)
    clone.querySelectorAll('[class*="reveal-delay"]').forEach(el => {
        el.className = el.className.replace(/\s*reveal-delay-\d/g, '');
    });

    const htmlStr = '<!DOCTYPE html>\n' + clone.outerHTML;
    const blob = new Blob([htmlStr], { type: 'text/html;charset=utf-8' });

    // Try modern link click approach first
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'presentation-export.html';
    a.style.display = 'none';

    // Attempt click, fall back tomsSaveOrOpenBlob for older browsers
    document.body.appendChild(a);
    try {
        // Modern browsers: programmatic click works
        var evt = new MouseEvent('click', { view: window, bubbles: true, cancelable: true });
        a.dispatchEvent(evt);
    } catch (e) {
        // Fallback: use msSaveOrOpenBlob (IE/Edge) or navigate
        try {
            window.navigator.msSaveOrOpenBlob(blob, 'presentation-export.html');
        } catch (e2) {
            // Last resort: open in new tab for copy-paste
            var win = window.open(url, '_blank');
            if (win) {
                win.focus();
                setTimeout(() => {
                    alert('请在新窗口中按 ⌘S / Ctrl+S 保存为 .html 文件');
                }, 500);
            }
        }
    }
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    showSaveIndicator(true);
}

/** Reset everything to defaults */
function resetAll() {
    if (!confirm('确定要恢复所有默认设置吗？（颜色和文字都会重置）')) return;

    // Reset CSS variables (remove overrides → CSS defaults restored)
    Object.entries(DEFAULT_COLORS).forEach(([v, val]) => {
        document.documentElement.style.removeProperty(v);
    });
    // Also remove size overrides
    ['--title-size','--h2-size','--h3-size','--body-size','--small-size','--bg-gradient','--accent-glow'].forEach(v => {
        document.documentElement.style.removeProperty(v);
    });

    // Update color UI controls back to defaults
    document.querySelectorAll('.color-row').forEach(row => {
        const ci = row.querySelector('input[type="color"]');
        const hi = row.querySelector('.color-hex');
        const sw = row.querySelector('.color-swatch');
        const vn = ci?.dataset.var;
        if (vn && DEFAULT_COLORS[vn]) {
            ci.value = DEFAULT_COLORS[vn];
            hi.value = DEFAULT_COLORS[vn];
            sw.style.background = DEFAULT_COLORS[vn];
        }
    });

    // Reset size slider UI
    const sizeSliders = {
        'val-title':  { slider: document.querySelector('[data-var="--title-size"]'), val: 6 },
        'val-h2':     { slider: document.querySelector('[data-var="--h2-size"]'),    val: 3.5 },
        'val-body':   { slider: document.querySelector('[data-var="--body-size"]'), val: 1.5 },
        'val-small':  { slider: document.querySelector('[data-var="--small-size"]'), val: 1 },
        'val-stat':   { slider: document.querySelector('[data-var="--stat-size"]'), val: 4 },
        'val-hero':   { slider: document.querySelector('[data-var="--hero-size"]'), val: 8 },
    };
    Object.entries(sizeSliders).forEach(([id, { slider, val }]) => {
        if (slider) slider.value = val;
        const el = document.getElementById(id);
        if (el) el.textContent = val + ' rem';
    });

    // Reload page to fully reset text content
    location.reload();
}

/** Init highlight bindings on load */
document.addEventListener('DOMContentLoaded', () => {
    initPanelHighlights();
    initPageElementHighlights();
});
