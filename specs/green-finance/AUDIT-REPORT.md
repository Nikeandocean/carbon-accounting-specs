# 绿色金融 Spec 审计报告

**审计日期**: 2026-06-22  
**审计范围**: `specs/green-finance/` 目录下全部 5 个 YAML spec 文件  
**审计方法**: 逐条比对原文件文本 + 结构完整性检查 + 跨文件一致性验证  
**修复状态**: P0 全部修复 ✅, P1 全部修复 ✅

---

## 修复记录

| 问题 | 状态 | 修复内容 |
|------|------|---------|
| cit-gb-133 截断 | ✅ 已修复 | 补全 "25 年内不高于15%。" |
| 缺少 4.2.1.4 | ✅ 已修复 | 添加到 valid_project_codes，计数更新为 249 |
| ifrs-s2-text.txt 损坏 | ✅ 已修复 | 替换为 ISSB 2026 正式版 PDF |
| IFRS S2 段落编号系统性错位 | ✅ 已修复 | 修正 20 条 citation 段落引用，v3.0.0 |
| 缺失强制段落引用和规则 | ✅ 已修复 | 新增 50 条 citation + 39 条规则，v3.1.0 |
| December 2025修正案未覆盖 | ✅ 已修复 | 新增 Para 29A-C 引用和规则，v3.1.0 |
| cit-s2-016/017 碳信用文本不准确 | ✅ 已修复 | 更新为 Para 36(e) 实际内容，v3.1.0 |
| cit-s2-012 Scope 2 断言过严 | ✅ 已修复 | 改为 location-based + 合同工具信息，v3.1.0 |
| Appendix B 覆盖不完整 | ✅ 已修复 | 新增 42 条 citation + 26 条规则，v3.2.0 |
| GWP 来源过于宽松 | ✅ 已修复 | 限制为 IPCC_AR6/IPCC_AR7 |
| citation_ref 不一致 | ✅ 已修复 | 统一为 citation 字段 |

---

## 一、审计总览

| 文件 | 状态 | 关键问题数 | 引用数 | 规则数 |
|------|------|-----------|--------|--------|
| bond-catalog.yaml | ⚠️ 需修复 | 3 | 246 | 5 |
| bond-eligibility.yaml | ✅ 基本合规 | 1 | 25 | 30 |
| credit-classification.yaml | ✅ 基本合规 | 0 | 21 | 18 |
| issb-s2-disclosure.yaml | ✅ 已修复 | 0 | 122 | 99 |
| cross-domain-bridge.yaml | ✅ 基本合规 | 0 | 12 | 13 |

---

## 二、关键发现

### 🔴 严重问题 (Critical)

#### 1. bond-catalog.yaml: cit-gb-133 引用文本截断

**文件**: `bond-catalog.yaml`  
**引用 ID**: `cit-gb-133`  
**问题**: 引用文本在句子中间被截断，缺失约 20 个字符。

**当前文本** (末尾):
```
...薄膜电池组件衰减率首年不高于5%，后续每年不高于0.4%，2
```

**应为** (完整):
```
...薄膜电池组件衰减率首年不高于5%，后续每年不高于0.4%，25年内不高于15%。
```

**来源文件**: `green-bond-catalog-text.txt` 第 914-915 行

**修复方案**: 补全截断文本。

---

#### 2. bond-catalog.yaml: 缺少项目类别代码 4.2.1.4

**文件**: `bond-catalog.yaml`, 规则 `gbc-001`  
**问题**: `valid_project_codes` 列表中缺少代码 `4.2.1.4`（生态功能区建设维护和运营）。

**来源文件**: `green-bond-catalog-text.txt` 第 1193-1197 行明确列出:
```
4.2.1.4. 生态功能区建设维护和运营
对生态功能区和生态功能退化的区域进行的治理、修复和保护工程建设...
```

**注意**: `cit-gb-172` 的引用文本中包含了 4.2.1.3 和 4.2.1.4 的内容合并，但代码列表中遗漏了 4.2.1.4。

**修复方案**: 
1. 在 `gbc-001` 规则的 `assertion.in` 列表中添加 `"4.2.1.4"`
2. 更新 `catalog_summary.valid_project_codes` 从 248 改为 249
3. 考虑为 4.2.1.4 添加独立的 citation（当前与 4.2.1.3 合并在 cit-gb-172 中）

---

#### 3. issb-s2-disclosure.yaml: IFRS S2 段落编号系统性错位

**文件**: `issb-s2-disclosure.yaml`  
**状态**: ✅ 已修复 (v3.0.0)

**问题**: YAML 基于早期草案，30 条 citation 的段落编号与 ISSB 2026 正式版 PDF 不符。

**修复内容** (20 条段落引用修正):
- 治理: Para 5(a)->6(a), 5(b)->6(b)
- 战略: Para 10->15(a)-(b), 12->10, 18->22
- 风险管理: Para 22->25(a), 23->25(c)
- Para 29 子段落: 29(a)(ii)->29(a)(v), 29(a)(iii)->29(a)(vi), 29(b)->29(a)(iii), 29(c)->29(a)(ii), 29(d)->29(b), 29(e)->29(c), 29(f)->29(d), 29(g)->29(e)
- 目标: Para 35->33(a)-(h), 37->34(a)
- 过渡: Para 61->Appendix C

**新增 December 2025 修正案覆盖**:
- Para 29A: Scope 3 Category 15 融资排放限制
- Para 29B: 衍生品处理披露
- Para 29C: Category 15 总排放和小计披露

---

#### 4. issb-s2-disclosure.yaml: ifrs-s2-text.txt 源文件损坏

**文件**: `specs/green-finance/ifrs-s2-text.txt`  
**问题**: 文件内容为浏览器登录错误页面，非 IFRS S2 标准文本。  
**状态**: ✅ 已修复  
**修复**: 删除损坏文件，替换为 ISSB 2026 正式版 PDF:
- `issb-2026-a-ifrs-s2-climate-related-disclosures.pdf` (IFRS S2)
- `issb-2026-a-ifrs-s1-general-requirements-for-disclosure-of-sustainability-related-financial-information.pdf` (IFRS S1)

---

### 🟡 中等问题 (Warning)

#### 5. issb-s2-disclosure.yaml: GWP 来源校验过于宽松

**文件**: `issb-s2-disclosure.yaml`, 规则 `gf-s2-016`  
**问题**: 规则允许 `IPCC_AR4`, `IPCC_AR5`, `IPCC_AR6` 三种 GWP 来源。

**IFRS S2 原文** (cit-s2-011):
> "An entity shall use GWP values from the most recent IPCC Assessment Report"

IFRS S2 发布于 2023 年 6 月，当时最新的 IPCC 评估报告是 AR6 (2021)。标准要求使用"最新"评估报告，而非任选其一。

**风险**: AR4 (2007) 的 GWP 值已过时，使用 AR4 可能不符合"最新"要求。

**修复方案**: 将允许值限制为 `["IPCC_AR6"]`，或添加说明注释解释为何允许旧版本。

---

#### 6. issb-s2-disclosure.yaml: citation_ref 字段命名不一致

**文件**: `issb-s2-disclosure.yaml`  
**问题**: 该文件使用 `citation_ref` 字段引用 citation，而其他文件（bond-eligibility.yaml, credit-classification.yaml, cross-domain-bridge.yaml）使用 `citation` 字段。

**影响**: 如果 schema 验证器期望统一的字段名，可能导致解析错误。

**修复方案**: 统一为 `citation` 字段，或在 schema 中明确支持两种字段名。

---

#### 7. bond-eligibility.yaml: L2 类别代码映射缺乏文档

**文件**: `bond-eligibility.yaml`  
**问题**: 规则使用 L2 类别代码（如 `C3.1`, `C5.2`）而非源文件的标准代码（如 `3.2.2.2`, `5.3.1.1`）。这种映射关系未在文件中记录。

**示例**:
| L2 代码 | 源文件代码 | 项目名称 |
|---------|-----------|---------|
| C3.1 | 3.2.2.2 | 太阳能利用设施建设运营 |
| C3.2 | 3.2.2.1 | 风力发电设施建设运营 |
| C5.2 | 5.3.1.1 | 污水处理设施建设运营 |

**风险**: 如果映射关系有误，规则将应用于错误的项目类别。

**修复方案**: 在文件中添加 L2 代码映射表的注释或独立 section。

---

### 🟢 轻微问题 (Info)

#### 8. bond-catalog.yaml: 31 个引用编号存在间隔

**文件**: `bond-catalog.yaml`  
**问题**: 引用编号从 `cit-gb-003` 到 `cit-gb-279`，但存在 31 个间隔（如 026, 029, 057 等）。

**原因**: 部分类别合并引用（如 4.2.1.3 和 4.2.1.4 合并为 cit-gb-172），或部分类别无独立引用。

**影响**: 不影响功能，但增加了维护复杂度。

---

#### 9. cross-domain-bridge.yaml: 部分引用来源较为宽泛

**文件**: `cross-domain-bridge.yaml`  
**问题**: 部分 citation 的 section 引用较为宽泛，如:
- `cit-gf-br-001`: "绿色债券指引 第三章 募集资金使用"
- `cit-gf-br-004`: "绿色电力证书认购实施细则 第八条"

这些引用未提供具体的文号或发布机构，增加了溯源难度。

---

## 三、结构完整性验证

### ✅ 通过检查

| 检查项 | 结果 |
|--------|------|
| YAML 语法有效性 | ✅ 全部 5 个文件通过 |
| 引用 ID 唯一性 | ✅ 无重复 ID |
| 规则 ID 唯一性 | ✅ 无重复 ID |
| 引用引用完整性 | ✅ 所有规则引用的 citation ID 均存在 |
| 依赖关系完整性 | ✅ 所有 dependencies 引用的 spec 路径有效 |
| 规则生命周期覆盖 | ✅ pre_calculation / runtime_inference / post_audit 均有覆盖 |

### ❌ 未通过检查

| 检查项 | 结果 |
|--------|------|
| 项目类别代码完整性 | ✅ 已补全 4.2.1.4 |
| 源文件完整性 | ✅ ISSB 2026 PDF 已获取 |
| 引用文本完整性 | ✅ cit-gb-133 已补全 |

---

## 四、修复优先级

### P0 (立即修复)

1. ~~**补全 cit-gb-133 截断文本**~~ ✅ 已完成
2. ~~**添加 4.2.1.4 到 valid_project_codes**~~ ✅ 已完成
3. ~~**重新提取 ifrs-s2-text.txt**~~ ✅ 已完成（替换为 ISSB 2026 PDF）

### P1 (尽快修复)

4. ~~**核实 IFRS S2 段落编号**~~ ✅ 已完成 (v3.0.0, 20 条修正)
5. ~~**收紧 GWP 来源校验**~~ ✅ 已完成
6. ~~**统一 citation_ref → citation**~~ ✅ 已完成

### P2 (建议改进)

7. **添加 L2 代码映射文档** — 可维护性
8. **补全 4.2.1.4 独立 citation** — 引用粒度
9. **完善 cross-domain-bridge 引用来源** — 可追溯性

---

## 五、各文件详细统计

### bond-catalog.yaml
- 引用数: 246 (cit-gb-003 ~ cit-gb-279, 31 个间隔)
- 规则数: 5 (gbc-001 ~ gbc-005)
- 项目类别: 248 个有效代码 (应为 249)
- 顶层分类: 6 个 (节能环保、清洁生产、清洁能源、生态环境、基础设施绿色升级、绿色服务)

### bond-eligibility.yaml
- 引用数: 25 (cit-gbe-001 ~ cit-gbe-025)
- 规则数: 30 (gbe-001 ~ gbe-030)
- 覆盖领域: 清洁能源、节能环保、清洁生产、生态环境、基础设施、绿色服务

### credit-classification.yaml
- 引用数: 21 (cit-gf-cc-001 ~ cit-gf-cc-021)
- 规则数: 18 (gf-cc-001 ~ gf-cc-018)
- 分类体系: 12 大类 + 3 个战略性新兴产业

### issb-s2-disclosure.yaml
- 引用数: 122 (cit-s2-001 ~ cit-s2-122)
- 规则数: 99 (gf-s2-001 ~ gf-s2-099)
- 四大支柱: 治理(10)、战略(22)、风险管理(7)、指标和目标(34)、附录B(26)
- 版本: v3.2.0 (2026-06-22)

### cross-domain-bridge.yaml
- 引用数: 12 (cit-gf-br-001 ~ cit-gf-br-012)
- 规则数: 13 (gf-br-001 ~ gf-br-013)
- 桥接维度: 排放强度→债券资格、绿证→信贷加分、Scope 3→ISSB 合规、碳数据→金融资格

---

*审计完成。共发现 4 个严重问题、3 个中等问题、2 个轻微问题。*
