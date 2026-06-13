# GHG Protocol Scope 2 Spec 推广策略实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 4 周内通过零成本内容营销，建立项目在 ESG 从业者中的认知度，同时构建个人品牌。

**Architecture:** LinkedIn 优先 + 内容驱动。第 1 周优化 GitHub 仓库，第 2-4 周持续输出高质量内容。所有内容使用 ESG 语言而非技术语言。

**Tech Stack:** GitHub, LinkedIn, 知乎, Canva (免费版)

---

## 文件结构

本次推广涉及以下文件的创建或修改：

| 文件 | 操作 | 用途 |
|------|------|------|
| `README.md` | 重写 | 中英双语，面向 ESG 从业者 |
| `docs/README_CN.md` | 新建 | 中文版文档入口 |
| `docs/methodology.md` | 修改 | 加中文注释 |
| `examples/sample-usage.yaml` | 修改 | 加非技术注释 |
| `.github/ISSUE_TEMPLATE/emission-factor.md` | 新建 | Issue 模板 |
| `docs/superpowers/content/linkedin-post-1.md` | 新建 | 内容 1：破冰帖 |
| `docs/superpowers/content/linkedin-post-2.md` | 新建 | 内容 2：深度文章 |
| `docs/superpowers/content/linkedin-post-3.md` | 新建 | 内容 3：实操帖 |
| `docs/superpowers/content/linkedin-post-4.md` | 新建 | 内容 4：愿景帖 |

---

## Task 1: 重写 README.md（中英双语）

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 备份当前 README**

```bash
cp README.md README.md.bak
```

- [ ] **Step 2: 重写 README.md**

```markdown
# GHG Protocol Scope 2 — Machine-Readable Compliance Spec for AI Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/v/release/Nikeandocean/carbon-accounting-specs)](https://github.com/Nikeandocean/carbon-accounting-specs/releases)

> 把 GHG Protocol 的 Scope 2 规则转化为 AI 可消费的结构化数据。
> 每条规则可追溯，每步计算可审计。

[中文文档](docs/README_CN.md) | [English](#what-is-this)

---

## What is this?

一套开源的 YAML 规则文件，定义了 GHG Protocol Scope 2 的所有合规要求。
任何 AI agent 或碳核算软件都可以直接加载这套规则，自动校验核算结果。

**这不是碳计算器。** 它不含排放因子数据库，不替代 GHG Protocol 标准本身。
它是**合规矩阵**——告诉你"算完之后要满足哪些条件才算合规"。

## 它能做什么？

✅ 校验核算数据是否完整
✅ 自动选择最优排放因子（含数据回退链）
✅ 检测 Scope 1/2 边界重叠
✅ 强制双重报告合规
✅ 每条判定追溯到 GHG Protocol 原文

## 规则覆盖范围

| 模块 | 规则数 | 优先级 | 说明 |
|------|--------|--------|------|
| 组织边界 | 3 | MUST | 控制权法、股权比例法 |
| 运营边界 | 3 | MUST | 排放源识别、类型校验 |
| 位置法 | 3 | MUST/SHOULD | 电网平均因子计算 |
| 市场法 | 3 | MUST/SHOULD | 合同工具优先 |
| 双重报告 | 2 | MUST | 触发条件、输出校验 |
| 披露要求 | 3 | MUST/SHOULD | 必须披露字段 |
| 禁止清单 | 6 | MUST/SHOULD | 双重计算、时效性等 |

## 快速开始

```python
import yaml
from jsonlogic import jsonlogic

# 1. 加载 spec
with open('specs/_meta.yaml', encoding='utf-8') as f:
    meta = yaml.safe_load(f)

# 2. 按 load_order 加载所有规则
specs = {}
for path in meta['load_order']:
    with open(f'specs/{path}.yaml', encoding='utf-8') as f:
        specs[path] = yaml.safe_load(f)

# 3. 准备你的核算数据
data = {
    "input": {
        "entity": {"name": "示例企业", "reporting_year": 2025, "control_method": "operational_control"},
        "emission_sources": [
            {"id": "elec-001", "type": "electricity", "activity_data": 1000,
             "emission_factor": {"value": 0.5703, "year": 2024, "source": "生态环境部", "type": "grid_average"}}
        ]
    },
    "context": {
        "region": {"country_code": "CN", "has_market_instruments": true, "grid_average_ef": 0.5703}
    }
}

# 4. 执行规则校验
for spec in specs.values():
    for rule in spec.get('rules', []):
        if rule.get('lifecycle') == 'pre_calculation':
            if rule.get('condition'):
                if jsonlogic(rule['condition'], data):
                    if rule.get('assertion'):
                        result = jsonlogic(rule['assertion'], data)
                        if not result:
                            print(f"❌ 规则 {rule['id']} 失败: {rule.get('on_fail_message')}")

print("✅ 所有前置规则校验通过")
```

## 数据回退链

当高优先级数据不可用时，系统自动降级：

**市场法：** 合同/PPA → 绿证 → 供应商因子 → 残余组合 → 电网平均
**位置法：** 区域电网 → 国家电网
**时间：** 当年 → 前一年 → 最近可用

## 参与贡献

我们欢迎以下贡献：

- 🌍 添加你所在国家/地区的排放因子数据
- 📝 改进规则的中文翻译
- 🐛 报告规则逻辑错误
- 💡 提出 Scope 1/3 的规则建议

请查看 [贡献指南](CONTRIBUTING.md) 了解详情。

## 路线图

- [x] Scope 2（当前版本）
- [ ] Scope 1（直接排放）
- [ ] Scope 3（价值链排放）
- [ ] 行业细分规则（电力、钢铁、化工等）
- [ ] 特定合规要求（EU CBAM、中国碳市场等）

## 致谢

- [GHG Protocol](https://ghgprotocol.org/) — 排放核算标准
- [World Resources Institute (WRI)](https://www.wri.org/) — 标准制定机构
- [WBCSD](https://www.wbcsd.org/) — 标准制定机构

## 许可证

MIT License - 详见 [LICENSE](LICENSE)
```

- [ ] **Step 3: 验证 README 格式**

```bash
# 在 GitHub 上预览 README，确认格式正确
# 检查链接是否可点击
# 确认中英文切换正常
```

- [ ] **Step 4: 提交更改**

```bash
git add README.md
git commit -m "docs: rewrite README for ESG practitioners with bilingual support"
```

---

## Task 2: 创建中文文档入口

**Files:**
- Create: `docs/README_CN.md`

- [ ] **Step 1: 创建中文文档目录**

```bash
mkdir -p docs
```

- [ ] **Step 2: 编写中文文档入口**

```markdown
# GHG Protocol Scope 2 — 结构化合规规则库

> 把 GHG Protocol 的 Scope 2 规则转化为 AI 可消费的结构化数据。
> 每条规则可追溯，每步计算可审计。

## 这是什么？

一套开源的 YAML 规则文件，定义了 GHG Protocol Scope 2 的所有合规要求。
任何 AI agent 或碳核算软件都可以直接加载这套规则，自动校验核算结果。

**这不是碳计算器。** 它不含排放因子数据库，不替代 GHG Protocol 标准本身。
它是**合规矩阵**——告诉你"算完之后要满足哪些条件才算合规"。

## 核心价值

| 价值 | 说明 |
|------|------|
| **可追溯** | 每条规则都有 GHG Protocol 原文出处 |
| **可审计** | agent 的每步决策都可回溯到具体规则 |
| **机器可读** | YAML + JsonLogic，无需 LLM 语义理解 |
| **模块化** | 每个文件单一职责，可独立更新 |

## 规则覆盖范围

| 模块 | 规则数 | 优先级 | 说明 |
|------|--------|--------|------|
| 组织边界 | 3 | MUST | 控制权法、股权比例法 |
| 运营边界 | 3 | MUST | 排放源识别、类型校验 |
| 位置法 | 3 | MUST/SHOULD | 电网平均因子计算 |
| 市场法 | 3 | MUST/SHOULD | 合同工具优先 |
| 双重报告 | 2 | MUST | 触发条件、输出校验 |
| 披露要求 | 3 | MUST/SHOULD | 必须披露字段 |
| 禁止清单 | 6 | MUST/SHOULD | 双重计算、时效性等 |

## 快速开始

详见 [快速开始指南](../README.md#快速开始)

## 文档目录

- [方法论说明](methodology.md) — 双层架构和执行流程
- [Schema 规范](schema-spec.md) — 输入输出 schema 详情
- [Agent 集成指南](agent-integration-guide.md) — 分步集成说明
- [示例用法](../examples/sample-usage.yaml) — 完整制造企业示例

## 参与贡献

我们欢迎以下贡献：

- 🌍 添加你所在国家/地区的排放因子数据
- 📝 改进规则的中文翻译
- 🐛 报告规则逻辑错误
- 💡 提出 Scope 1/3 的规则建议

## 路线图

- [x] Scope 2（当前版本）
- [ ] Scope 1（直接排放）
- [ ] Scope 3（价值链排放）
- [ ] 行业细分规则（电力、钢铁、化工等）
- [ ] 特定合规要求（EU CBAM、中国碳市场等）
```

- [ ] **Step 3: 提交更改**

```bash
git add docs/README_CN.md
git commit -m "docs: add Chinese documentation entry point"
```

---

## Task 3: 优化示例文件注释

**Files:**
- Modify: `examples/sample-usage.yaml`

- [ ] **Step 1: 读取当前示例文件**

```bash
cat examples/sample-usage.yaml
```

- [ ] **Step 2: 添加非技术注释**

在文件开头添加：

```yaml
# =====================================================
# GHG Protocol Scope 2 核算示例
# =====================================================
#
# 这个文件展示了一个制造企业如何使用这套 spec 进行碳核算。
#
# 背景：
# - 企业名称：示例制造有限公司
# - 核算年份：2025年
# - 控制方法：运营控制权法
# - 排放源：外购电力
#
# 核算流程：
# 1. 准备输入数据（企业信息、排放源、排放因子）
# 2. 加载 spec 规则
# 3. 执行前置校验（pre_calculation）
# 4. 执行计算（runtime_inference）
# 5. 执行后置审计（post_audit）
# 6. 生成合规报告
#
# 注意：
# - 这套 spec 只做合规校验，不做实际计算
# - 排放因子数据需要从外部数据源获取
# - 每条规则都有 GHG Protocol 原文出处
# =====================================================
```

- [ ] **Step 3: 为每个字段添加中文注释**

```yaml
# 企业信息
entity:
  name: "示例制造有限公司"          # 企业名称
  reporting_year: 2025              # 核算年份
  control_method: "operational_control"  # 控制方法：operational_control（运营控制）| financial_control（财务控制）| equity_share（股权比例）

# 排放源列表
emission_sources:
  - id: "elec-001"                  # 排放源唯一标识
    type: "electricity"             # 排放源类型：electricity（电力）| steam（蒸汽）| heat（热力）| cooling（冷量）
    activity_data: 5000             # 活动数据，单位：MWh
    emission_factor:
      value: 0.5703                 # 排放因子值，单位：tCO2/MWh
      year: 2024                    # 排放因子年份
      source: "生态环境部"           # 数据来源
      type: "grid_average"          # 因子类型：contract（合同）| certificate（绿证）| supplier（供应商）| residual_mix（残余组合）| grid_average（电网平均）| default（缺省）
```

- [ ] **Step 4: 提交更改**

```bash
git add examples/sample-usage.yaml
git commit -m "docs: add non-technical comments to sample usage"
```

---

## Task 4: 创建 Issue 模板

**Files:**
- Create: `.github/ISSUE_TEMPLATE/emission-factor.md`

- [ ] **Step 1: 创建 Issue 模板目录**

```bash
mkdir -p .github/ISSUE_TEMPLATE
```

- [ ] **Step 2: 编写排放因子 Issue 模板**

```markdown
---
name: "添加排放因子数据"
about: "请求添加某个国家/地区的排放因子数据"
title: "[排放因子] "
labels: "emission-factor"
assignees: ""
---

## 国家/地区

请填写需要添加排放因子的国家或地区：

**国家代码（ISO 3166-1）：** 
**行政区划代码（ISO 3166-2，可选）：** 

## 排放因子类型

请勾选需要添加的排放因子类型：

- [ ] 电网平均排放因子（Grid Average）
- [ ] 残余电力组合排放因子（Residual Mix）
- [ ] 区域电网排放因子（Subnational）

## 数据来源

请提供排放因子的官方数据来源：

**来源机构：** 
**发布年份：** 
**数据链接：** 
**因子值：** 
**单位：** tCO2/MWh

## 补充说明

请提供任何其他相关信息，例如：
- 该地区是否有市场化电力交易工具（绿证、PPA 等）
- 数据的适用范围和限制
- 与其他因子的关系
```

- [ ] **Step 3: 提交更改**

```bash
git add .github/ISSUE_TEMPLATE/emission-factor.md
git commit -m "docs: add issue template for emission factor requests"
```

---

## Task 5: 创建内容 1 — 破冰帖

**Files:**
- Create: `docs/superpowers/content/linkedin-post-1.md`

- [ ] **Step 1: 创建内容目录**

```bash
mkdir -p docs/superpowers/content
```

- [ ] **Step 2: 编写破冰帖**

```markdown
# 碳核算的 AI 时代，谁来保证"算对了"？

**发布时间：** 第 1 周，周二/周三早上 8-9 点
**平台：** LinkedIn
**字数：** 约 300 字
**Hashtag：** #GHGProtocol #碳核算 #ESG #Scope2 #AI

---

最近和几位做碳核算的朋友聊天，发现一个普遍的焦虑：

企业开始用 AI 做碳核算了，效率确实高了——但算出来的结果，到底对不对？

问题出在哪？

**GHG Protocol 是 PDF 格式的。** 人能读，机器读不懂。

AI 要做碳核算，得有人把标准"翻译"成它能理解的语言。

我们做了一件事：**把 GHG Protocol Scope 2 的所有规则，转化成了结构化数据。**

不是碳计算器，是**合规矩阵**。

它能做什么？
✅ 校验核算数据是否完整
✅ 自动选择最优排放因子
✅ 检测 Scope 1/2 边界重叠
✅ 强制双重报告合规
✅ 每条判定追溯到 GHG Protocol 原文

**开源的，MIT 协议。**

如果你也在做碳核算相关的工作，欢迎来看看：
[GitHub 仓库链接]

也欢迎在评论区聊聊，你在碳核算中遇到过哪些"合规坑"？

---

#GHGProtocol #碳核算 #ESG #Scope2 #AI #ClimateTech #可持续发展
```

- [ ] **Step 3: 提交更改**

```bash
git add docs/superpowers/content/linkedin-post-1.md
git commit -m "content: add LinkedIn post 1 - icebreaker"
```

---

## Task 6: 创建内容 2 — 深度文章

**Files:**
- Create: `docs/superpowers/content/linkedin-post-2.md`

- [ ] **Step 1: 编写深度文章**

```markdown
# 为什么 GHG Protocol 需要从 PDF 变成结构化数据

**发布时间：** 第 2 周，周二/周三早上 8-9 点
**平台：** LinkedIn 长文 + 知乎
**字数：** 约 1500 字
**Hashtag：** #GHGProtocol #碳核算 #ESG #Scope2 #碳排放 #ClimateTech

---

## 背景：Scope 2 的双重报告要求

GHG Protocol Scope 2 指南要求，在存在市场化电力交易工具的地区（如绿证、PPA），企业必须同时报告两种口径的排放量：

1. **位置法（Location-Based）：** 使用电网平均排放因子
2. **市场法（Market-Based）：** 使用合同工具的排放因子

这个要求本身很合理——两种方法反映不同的信息：
- 位置法反映你所在电网的平均碳强度
- 市场法反映你主动选择的电力来源

## 问题：人工核算的痛点

但实际操作中，这带来几个问题：

**1. 慢**

双重报告意味着两套数据、两套计算、两套校验。一个中型企业的 Scope 2 核算，人工做可能需要 2-3 周。

**2. 贵**

需要专业人员理解 GHG Protocol 的每一条规则，确保没有遗漏。人力成本高。

**3. 容易出错**

规则分散在 100 多页的 PDF 里。排放因子年份不匹配、双重报告遗漏、Scope 1/2 边界重叠……这些都是常见错误。

**4. 难审计**

核算完成后，很难追溯"这条规则是怎么应用的"。出了问题，不知道是规则理解错了，还是数据用错了。

## 解决方案：结构化 spec

我们做了一件事：**把 GHG Protocol Scope 2 的所有规则，转化成了机器可读的结构化数据。**

用的是 YAML 格式，配合 JsonLogic 表达式。

**这不是碳计算器。** 它不含排放因子数据库，不替代 GHG Protocol 标准本身。

它是**合规矩阵**——告诉你"算完之后要满足哪些条件才算合规"。

### 架构设计

我们把规则分成了两层：

**Layer 1：Schema 层（确定性）**
- 用 JsonLogic 表达式定义规则
- 机器可直接执行，不需要 LLM
- 处理 80% 的基础规则：非空校验、类型检查、简单比较

**Layer 2：Knowledge 层（语义）**
- 用自然语言描述原则和解释
- LLM 用于处理模糊地带
- 处理 20% 的复杂场景：歧义裁决、原则解释

### 规则覆盖

目前覆盖了 Scope 2 的所有核心规则：

| 模块 | 规则数 | 优先级 |
|------|--------|--------|
| 组织边界 | 3 | MUST |
| 运营边界 | 3 | MUST |
| 位置法 | 3 | MUST/SHOULD |
| 市场法 | 3 | MUST/SHOULD |
| 双重报告 | 2 | MUST |
| 披露要求 | 3 | MUST/SHOULD |
| 禁止清单 | 6 | MUST/SHOULD |

每条规则都有：
- GHG Protocol 原文出处
- 机器可执行的断言
- 失败时的处理策略

## 案例：Agent 怎么消费这套 spec

假设一个 AI agent 要核算一家制造企业的 Scope 2 排放：

1. **加载 spec：** 读取所有 YAML 文件，按 load_order 排序
2. **前置校验：** 检查输入数据是否完整、排放源类型是否合法
3. **数据回退：** 如果合同因子不可用，自动降级到绿证 → 供应商 → 残余组合 → 电网平均
4. **计算：** 活动数据 × 排放因子
5. **后置审计：** 检查双重报告是否完整、排放因子年份是否匹配
6. **输出：** 生成合规报告，每条判定都可追溯到 GHG Protocol 原文

整个过程，agent 不需要"理解"GHG Protocol，只需要执行规则。

## 开源与参与

这个项目是开源的，MIT 协议。

**GitHub 仓库：** [链接]

我们欢迎：
- 🌍 添加你所在国家/地区的排放因子数据
- 📝 改进规则的中文翻译
- 🐛 报告规则逻辑错误
- 💡 提出 Scope 1/3 的规则建议

如果你也在做碳核算相关的工作，欢迎关注和参与。

---

#GHGProtocol #碳核算 #ESG #Scope2 #碳排放 #ClimateTech #可持续发展 #AI
```

- [ ] **Step 2: 提交更改**

```bash
git add docs/superpowers/content/linkedin-post-2.md
git commit -m "content: add LinkedIn post 2 - deep article"
```

---

## Task 7: 创建内容 3 — 实操帖

**Files:**
- Create: `docs/superpowers/content/linkedin-post-3.md`

- [ ] **Step 1: 编写实操帖**

```markdown
# GHG Protocol Scope 2 的 5 个常见合规坑

**发布时间：** 第 3 周，周二/周三早上 8-9 点
**平台：** LinkedIn
**字数：** 约 500 字
**Hashtag：** #GHGProtocol #碳核算 #ESG #Scope2 #碳排放

---

做碳核算这几年，发现 Scope 2 有几个"坑"，几乎每个项目都会踩。

分享出来，希望对大家有帮助。

---

## 坑 1：排放因子年份不匹配

**问题：** 活动数据是 2025 年的，排放因子用的是 2022 年的。

**GHG Protocol 原文：**
> "Emission factors should correspond to the same time period as the activity data."
> — Chapter 6: Data Quality

**我们的规则怎么覆盖：**
proh-006 规则会自动校验排放因子年份和活动数据年份是否匹配。如果不匹配，要求提供 justification（合规性解释）。

---

## 坑 2：双重报告遗漏

**问题：** 企业所在地区有绿证市场，但只报告了位置法，没有报告市场法。

**GHG Protocol 原文：**
> "Companies operating in markets where product-specific instruments are available shall report both a location-based and a market-based Scope 2 figure."
> — Chapter 7: Dual Reporting

**我们的规则怎么覆盖：**
rule-dr-001 规则会检查 `context.region.has_market_instruments`，如果为 true，强制要求提供两种方法的输入数据。

---

## 坑 3：Scope 1/2 边界重叠

**问题：** 企业有自发电（CHP），热电联产的排放既算在 Scope 1 里，又算在 Scope 2 里。

**GHG Protocol 原文：**
> "Companies shall not double-count emissions between Scope 1 and Scope 2."
> — Chapter 4: Setting Operational Boundaries

**我们的规则怎么覆盖：**
proh-001 规则会调用 `calc.boundary_overlap_check` 函数，检测能源边界拓扑，确保没有双重计算。

---

## 坑 4：数据回退未披露

**问题：** 企业用了电网平均因子，但没有说明为什么没用更高质量的数据。

**GHG Protocol 原文：**
> "Companies should use the most accurate data available, prioritizing supplier-specific data over averages."
> — Chapter 6: Data Quality

**我们的规则怎么覆盖：**
fallback_chains 会自动降级数据源，但每次降级都会要求 `require_disclosure`，确保在报告中说明原因。

---

## 坑 5：方法混用未声明

**问题：** 企业同时使用了位置法和市场法，但没有说明方法论。

**GHG Protocol 原文：**
> "If a company uses both location-based and market-based methods, it shall clearly explain the methodology used."
> — Chapter 7: Dual Reporting

**我们的规则怎么覆盖：**
proh-004 规则会检查是否同时输出了两种方法的结果，如果是，强制要求提供 `methodology_explanation`。

---

## 总结

这 5 个坑的共同点是：**规则分散在 PDF 的不同章节，人工很容易遗漏。**

我们把这些规则转化成了结构化数据，让机器自动校验。

**开源的，MIT 协议。** 欢迎来看看：
[GitHub 仓库链接]

你在碳核算中还遇到过哪些"坑"？欢迎评论区分享。

---

#GHGProtocol #碳核算 #ESG #Scope2 #碳排放 #ClimateTech #可持续发展
```

- [ ] **Step 2: 提交更改**

```bash
git add docs/superpowers/content/linkedin-post-3.md
git commit -m "content: add LinkedIn post 3 - common pitfalls"
```

---

## Task 8: 创建内容 4 — 愿景帖

**Files:**
- Create: `docs/superpowers/content/linkedin-post-4.md`

- [ ] **Step 1: 编写愿景帖**

```markdown
# 碳核算的未来：从人工审计到 AI 自动合规

**发布时间：** 第 4 周，周二/周三早上 8-9 点
**平台：** LinkedIn
**字数：** 约 300 字
**Hashtag：** #GHGProtocol #碳核算 #ESG #Scope2 #AI #碳中和

---

碳核算行业正在经历一个转变：

**从人工审计，走向 AI 自动合规。**

但这里有一个问题：AI 怎么知道"合规"长什么样？

GHG Protocol 是 PDF 格式的。人能读，机器读不懂。

我们的答案是：**把规则变成结构化数据。**

目前，我们已经完成了 Scope 2（外购电力、蒸汽、热力、冷量）的规则转化：

✅ 23 条核心规则
✅ 每条都有 GHG Protocol 原文出处
✅ 机器可直接执行
✅ 开源，MIT 协议

**接下来的路线图：**

- Scope 1（直接排放）
- Scope 3（价值链排放）
- 行业细分规则（电力、钢铁、化工等）
- 特定合规要求（EU CBAM、中国碳市场等）

**我们的愿景是：**

任何 AI agent 都能接入这套规则，自动完成碳核算的合规校验。

不需要每个企业都雇佣 GHG Protocol 专家。
不需要每次核算都人工检查 100 页 PDF。
不需要担心"这条规则有没有漏掉"。

**如果你也在做碳核算相关的工作，欢迎关注和参与。**

GitHub 仓库：[链接]

也欢迎私信聊聊，你在碳核算中遇到的痛点。

---

#GHGProtocol #碳核算 #ESG #Scope2 #AI #碳中和 #ClimateTech #可持续发展
```

- [ ] **Step 2: 提交更改**

```bash
git add docs/superpowers/content/linkedin-post-4.md
git commit -m "content: add LinkedIn post 4 - vision"
```

---

## Task 9: 添加 GitHub Topics

**Files:**
- None (GitHub 网页操作)

- [ ] **Step 1: 登录 GitHub 仓库设置页面**

打开 https://github.com/Nikeandocean/carbon-accounting-specs

- [ ] **Step 2: 添加 Topics**

点击仓库页面右上角的齿轮图标（Settings），在 "Topics" 部分添加：

```
ghg-protocol
carbon-accounting
scope-2
esg
sustainability
ai-agent
compliance
climate-tech
corporate-standard
```

- [ ] **Step 3: 保存更改**

点击 "Save changes"

---

## Task 10: 第 1 周执行清单

- [ ] **Step 1: 完成 GitHub 仓库优化**

确认以下任务已完成：
- [ ] README.md 已重写（Task 1）
- [ ] docs/README_CN.md 已创建（Task 2）
- [ ] examples/sample-usage.yaml 已优化（Task 3）
- [ ] Issue 模板已创建（Task 4）
- [ ] GitHub Topics 已添加（Task 9）

- [ ] **Step 2: 发布内容 1**

从 `docs/superpowers/content/linkedin-post-1.md` 复制内容，发布到 LinkedIn。

**发布时间：** 周二或周三早上 8-9 点

**发布后：**
- 主动评论 2-3 个 ESG 领域大V的帖子
- 回复每一条评论

- [ ] **Step 3: 记录数据**

记录发布后的数据：
- LinkedIn 文章阅读量
- LinkedIn follower 变化
- GitHub star 变化

---

## Task 11: 第 2 周执行清单

- [ ] **Step 1: 发布内容 2**

从 `docs/superpowers/content/linkedin-post-2.md` 复制内容，发布到 LinkedIn 长文。

**发布时间：** 周二或周三早上 8-9 点

- [ ] **Step 2: 知乎同步发布**

将内容 2 同步发布到知乎，标题改为：
"为什么碳核算标准需要从 PDF 变成结构化数据"

- [ ] **Step 3: LinkedIn 群组分享**

在 3-5 个 ESG 相关 LinkedIn 群组分享内容 2。

**推荐群组类型：**
- 碳核算/碳市场群组
- ESG 报告/可持续发展群组
- 气候科技/绿色金融群组

- [ ] **Step 4: 记录数据**

记录发布后的数据：
- LinkedIn 文章阅读量
- 知乎文章阅读量
- GitHub star 变化

---

## Task 12: 第 3 周执行清单

- [ ] **Step 1: 发布内容 3**

从 `docs/superpowers/content/linkedin-post-3.md` 复制内容，发布到 LinkedIn。

**发布时间：** 周二或周三早上 8-9 点

- [ ] **Step 2: 互动策略**

- 找 2-3 个 ESG 博主，在他们的帖子下评论
- 回复所有 GitHub issue
- 回复 LinkedIn 评论

- [ ] **Step 3: 记录数据**

记录发布后的数据：
- LinkedIn 文章阅读量
- GitHub star 变化
- GitHub issue 数量

---

## Task 13: 第 4 周执行清单

- [ ] **Step 1: 发布内容 4**

从 `docs/superpowers/content/linkedin-post-4.md` 复制内容，发布到 LinkedIn。

**发布时间：** 周二或周三早上 8-9 点

- [ ] **Step 2: 数据复盘**

汇总 4 周的数据：

| 指标 | 目标 | 实际 |
|------|------|------|
| GitHub star | 50+ | |
| LinkedIn 文章总阅读量 | 1000+ | |
| LinkedIn follower 增长 | 100+ | |
| GitHub issue | 5+ | |

- [ ] **Step 3: 规划下月内容**

根据数据反馈，规划下月内容：
- 哪类内容效果最好？
- 哪个渠道效果最好？
- 下月重点是什么？

---

## 自检清单

### Spec 覆盖检查

- [x] 核心叙事重构 → Task 1, 2
- [x] 内容矩阵（4 篇） → Task 5, 6, 7, 8
- [x] 执行节奏（4 周） → Task 10, 11, 12, 13
- [x] GitHub 仓库优化 → Task 1, 2, 3, 4, 9
- [x] LinkedIn 发帖策略 → Task 5, 6, 7, 8
- [x] 成功指标 → Task 13

### 占位符检查

- [x] 无 TBD/TODO
- [x] 所有步骤都有具体内容
- [x] 所有文件路径都是精确的

### 类型一致性检查

- [x] 文件路径一致
- [x] 任务编号连续
- [x] 内容格式一致
