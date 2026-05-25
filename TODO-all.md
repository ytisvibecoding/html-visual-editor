# html-visual-editor 修复 TODO 总表
> 更新于 2026-05-25

---

## 一、变量提取与验证（原有 TODO 1-5）

### TODO 1: 非渐变硬编码颜色提取遗漏（核心问题，优先级最高）
- **文件**: `scripts/inject.py`（新增函数）+ `scripts/adapt.py`（调用）
- **问题**: `extract_gradient_hex_to_vars` 只提取渐变中的 hex，非渐变颜色属性（color/background/border 等）中的硬编码 hex 完全被忽略
- **数据**: presentation-export-2.html 中，渐变提取 6 种，非渐变遗漏 25+ 种
- **修复**: 新增 `extract_solid_hex_to_vars`，与 `extract_gradient_hex_to_vars` 并列
  1. 遍历 CSS 规则，找颜色属性中的 hex
  2. 跳过渐变（已处理）、极端色、编辑器自选器
  3. 同色合并，按属性推断命名：color → --text-N，background → --bg-N，border → --line-N
  4. 替换原 CSS 中的 hex 为 var(--xxx)，新变量追加到 :root
  5. 在 adapt.py 中于 extract_gradient_hex_to_vars 之后调用
- **依赖**: 无；修复后连带解决 appB16

### TODO 2: appB16 降级为 warning
- **文件**: `scripts/verify.py`
- **问题**: 即使提取正常后，极少数 HTML 可能确实只有 1 组颜色
- **修复**: sections < 2 时 passed=True 但 message 标 warning，不计入 error
- **依赖**: TODO 1 完成后验证

### TODO 3: appB21 覆盖率计算 bug
- **文件**: `scripts/verify.py`
- **问题**: 分母包含编辑器自样式(13)和 CSS 死代码(18)，实际 18/18=100%
- **修复**: 排除编辑器 style；对剩余规则用 soup.select() 验证 DOM 存在性
- **依赖**: TODO 1+4 完成后验证

### TODO 4: --force 应在 parse 之前清理旧注入
- **文件**: `scripts/adapt.py`
- **问题**: _strip_old_injection 在 inject() 中调用，太晚；parse/scan 在脏 HTML 上运行
- **修复**: --force 时提前到 extract_gradient_hex_to_vars 之前调用
- **依赖**: 无

### TODO 5: _build_size_sliders 的 _html 来源加注释
- **文件**: `scripts/generate_panel.py`
- **修复**: 注释说明 _html 是 scan_dom 时的 HTML 快照
- **依赖**: 随时

---

## 二、保存持久性（新增 TODO 6-7）

### TODO 6: 字号/布局修改不保存到 localStorage
- **文件**: `assets/editor-core.js`
- **问题**: saveToStorage 只保存 DEFAULT_COLORS keys 的 CSS 变量 + data-editable 文本。字号和布局滑块通过 applyLayout 直接修改 el.style[prop]（inline style），这些修改不会被 saveToStorage 捕获
- **复现**: 调整字号/布局 → 点保存 → 刷新页面 → 字号/布局回到原始值
- **修复方案**:
  1. saveToStorage 新增"布局状态"收集：遍历所有 slider-row 的 input[type=range]，记录 {data-target, data-prop, data-unit, value}
  2. loadFromStorage 恢复时：对每条记录执行 querySelector(target).style[prop] = val+unit
  3. 同步更新显示值（slider-val）

### TODO 7: 颜色修改也不完整保存——只保存 DEFAULT_COLORS keys
- **文件**: `assets/editor-core.js`
- **问题**: saveToStorage 用 `Object.keys(DEFAULT_COLORS)` 决定保存哪些变量。但 TODO 1 修复后会新增大量颜色变量（--text-N, --bg-N, --line-N），这些不在 DEFAULT_COLORS 中
- **修复方案**: saveToStorage 应遍历所有 .color-row 的 data-var，而非仅依赖 DEFAULT_COLORS keys

---

## 三、预设换肤（新增 TODO 8-9）

### TODO 8: 预设换肤只影响渐变，非渐变颜色不变
- **文件**: `scripts/generate_panel.py`（_build_presets）+ `assets/editor-core.js`（applyPreset）
- **问题**: 这是 TODO 1 的直接后果。原始 HTML 中非渐变 hex 没被替换为 var()，所以即使 preset 成功 setProperty 改了 CSS 变量值，那些没引用 var() 的元素视觉上不会变
- **修复**: TODO 1 修复后，extract_solid_hex_to_vars 会把所有非渐变 hex 替换为 var()，预设换肤自然生效
- **依赖**: TODO 1

### TODO 9: 预设变量名与 host 变量名映射不完整
- **文件**: `scripts/generate_panel.py`（SEMANTIC_ALIAS + _map_preset_to_host_vars）
- **问题**: 预设用语义命名（--accent, --ink, --bg），但 TODO 1 提取的新变量名（--hero-bg-2, --img-slot-bg-3, --text-N）不在 SEMANTIC_ALIAS 候选中。预设只能映射到少量变量
- **修复方案**:
  1. SEMANTIC_ALIAS 增加 --bg-N / --text-N / --line-N 系列候选
  2. 或改进 extract_solid_hex_to_vars 的命名策略：尽量用语义名（--bg-primary 而非 --bg-2）
  3. 或让 preset 支持通配符映射（--accent 匹配所有包含 accent/primary 的变量）
- **依赖**: TODO 1

---

## 四、交互映射（新增 TODO 10）

### TODO 10: hover 映射（PEM）对非金版 HTML 覆盖不完整
- **文件**: `scripts/scan_dom.py` + `assets/editor-core.js`
- **问题**: 
  - editor-core.js 中有 25 条硬编码的 PEM 条目（金版专用选择器如 .section-num, .main-title）
  - Python 动态生成的 PEM 通过 window.PAGE_ELEMENT_TO_PANEL 覆盖硬编码（|| 运算符）
  - 但动态 PEM 只对"有 CSS 变量引用"的元素生成映射；纯硬编码颜色的元素（TODO 1 修复前）不会被映射
  - 即使 TODO 1 修复后，有些页面的元素选择器可能不在 PEM 中
- **影响**: 点击页面元素时，部分元素不会出现"可调整项"的 tooltip
- **修复方案**:
  1. TODO 1 修复后，更多元素会有 CSS 变量引用 → PEM 条目自然增加
  2. 对 data-editable 元素，始终生成至少包含"颜色"维度的 PEM 条目（因为颜色面板覆盖了所有元素可能涉及的颜色变量）
  3. 清理 editor-core.js 中的硬编码 PEM（改为完全动态生成，不再有 fallback）
- **依赖**: TODO 1

---

## 执行优先级

| 顺序 | TODO | 类型 | 影响 | 依赖 |
|------|------|------|------|------|
| **1** | TODO 1 | 功能缺陷 | 核心提取遗漏 | 无 |
| **2** | TODO 4 | 功能缺陷 | 脏 HTML 干扰 | 无 |
| **3** | TODO 7 | 功能缺陷 | 颜色保存不完整 | TODO 1 |
| **4** | TODO 6 | 功能缺陷 | 字号/布局不保存 | 无 |
| **5** | TODO 8 | 功能缺陷 | 预设换肤无效 | TODO 1 |
| **6** | TODO 9 | 功能缺陷 | 预设映射不全 | TODO 1 |
| **7** | TODO 2 | 防御性 | appB16 阻断 | TODO 1 |
| **8** | TODO 3 | 验证准确性 | appB21 误判 | TODO 1+4 |
| **9** | TODO 10 | 体验 | hover 映射不全 | TODO 1 |
| **10** | TODO 5 | 可读性 | 注释缺失 | 随时 |
