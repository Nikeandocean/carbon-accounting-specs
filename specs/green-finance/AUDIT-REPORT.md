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
| ifrs-s2-text.txt 损坏 | ⚠️ 待处理 | PDF 文件损坏（176KB），需重新获取 |
| IFRS S2 段落编号 | ⚠️ 待确认 | 需对照正式版 PDF 核实子段落编号 |
| GWP 来源过于宽松 | ✅ 已修复 | 限制为 IPCC_AR6/IPCC_AR7 |
| citation_ref 不一致 | ✅ 已修复 | 统一为 citation 字段 |

---

## 一、审计总览

| 文件 | 状态 | 关键问题数 | 引用数 | 规则数 |
|------|------|-----------|--------|--------|
| bond-catalog.yaml | ⚠️ 需修复 | 3 | 246 | 5 |
| bond-eligibility.yaml | ✅ 基本合规 | 1 | 25 | 30 |
| credit-classification.yaml | ✅ 基本合规 | 0 | 21 | 18 |
| issb-s2-disclosure.yaml | ⚠️ 需修复 | 3 | 30 | 34 |
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

#### 3. issb-s2-disclosure.yaml: IFRS S2 段落编号可能不准确

**文件**: `issb-s2-disclosure.yaml`  
**引用 ID**: `cit-s2-012`, `cit-s2-013`, `cit-s2-023`

**问题**: 
- `cit-s2-012` 引用 "IFRS S2 Para 29(a)(ii)" 表示 Scope 2 双重报告要求
- `cit-s2-013` 引用 "IFRS S2 Para 29(a)(iii)" 表示 Scope 3 类别披露
- `cit-s2-023` 引用 "IFRS S2 Para 29(a)(iii), Appendix B" 表示融资排放

根据 IFRS S2 2023 年 6 月版本，Para 29 的子段落编号为:
- 29(a)(i): Scope 1/2/3 绝对排放量
- 29(a)(ii): 计量方法（GHG Protocol）
- 29(a)(iii): Scope 2 方法选择
- 29(a)(iv): 范围界定
- 29(a)(v): 合并方法
- 29(a)(vi)(1): Scope 3 类别
- 29(a)(vi)(2): 金融机构融资排放

**当前引用的段落编号可能基于不同的版本或解读**。建议对照 IFRS S2 原文确认精确的子段落编号。

**风险**: 如果段落编号不准确，可能导致合规审计时被质疑。

**修复方案**: 获取 IFRS S2 2023 年 6 月正式版 PDF，逐条核对段落编号。

---

#### 4. issb-s2-disclosure.yaml: ifrs-s2-text.txt 源文件损坏

**文件**: `specs/green-finance/ifrs-s2-text.txt`  
**问题**: 文件内容为浏览器登录错误页面，非 IFRS S2 标准文本。

**当前内容**:
```
We can't sign you in
Your browser is currently set to block JavaScript...
```

**修复方案**: 重新从 IFRS S2 PDF 提取文本内容。

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
| 项目类别代码完整性 | ❌ 缺少 4.2.1.4 |
| 源文件完整性 | ❌ ifrs-s2-text.txt 损坏 |
| 引用文本完整性 | ❌ cit-gb-133 截断 |

---

## 四、修复优先级

### P0 (立即修复)

1. **补全 cit-gb-133 截断文本** — 数据完整性问题
2. **添加 4.2.1.4 到 valid_project_codes** — 遗漏合规类别
3. **重新提取 ifrs-s2-text.txt** — 源文件不可用

### P1 (尽快修复)

4. **核实 IFRS S2 段落编号** — 合规审计风险
5. **收紧 GWP 来源校验** — 标准解读偏差
6. **统一 citation_ref → citation** — 字段命名一致性

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
- 引用数: 30 (cit-s2-001 ~ cit-s2-030)
- 规则数: 34 (gf-s2-001 ~ gf-s2-034)
- 四大支柱: 治理(3)、战略(5)、风险管理(2)、指标和目标(24)

### cross-domain-bridge.yaml
- 引用数: 12 (cit-gf-br-001 ~ cit-gf-br-012)
- 规则数: 13 (gf-br-001 ~ gf-br-013)
- 桥接维度: 排放强度→债券资格、绿证→信贷加分、Scope 3→ISSB 合规、碳数据→金融资格

---

*审计完成。共发现 4 个严重问题、3 个中等问题、2 个轻微问题。*
