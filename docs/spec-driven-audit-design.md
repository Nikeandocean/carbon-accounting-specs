# Spec-Driven Audit 设计文档

**版本**: 1.0.0
**日期**: 2026-06-22
**状态**: Phase 1-3 已实现

---

## 核心理念

> **YAML spec 是合规要求的唯一真相来源，LLM agent 读取 spec 后引导用户完成整个审计流程。**

当前实现的问题：我们的 MCP 工具是"硬编码的检查函数"，而不是"spec 驱动的审计流程"。

---

## 当前状态 vs 完整概念

| 维度 | 当前实现 | 完整 Spec-Driven Audit |
|------|---------|----------------------|
| **Spec 角色** | 规则存储 | 活的知识库 + 执行引擎 |
| **Agent 交互** | 调用固定工具 | 读取 spec 后自主决策 |
| **数据收集** | 工具参数硬编码 | spec 定义输入 schema，agent 按 schema 收集 |
| **规则执行** | engine.py 执行 JsonLogic | agent 理解规则语义后选择执行策略 |
| **失败处理** | 返回错误信息 | agent 解释原因 + 引用原文 + 生成修复建议 |
| **报告生成** | 无 | 基于 spec 结构生成合规报告 |

---

## 缺失的关键能力

### 1. Spec 自描述能力

**问题**：当前 spec 对 agent 不够友好。Agent 需要理解：
- 这个 spec 覆盖什么领域？
- 需要哪些输入数据？
- 每条规则检查什么？
- 失败意味着什么？

**需要**：一个 `describe_spec` 工具，返回 spec 的结构化摘要：

```json
{
  "domain": "IFRS S2 Climate-related Disclosures",
  "scope": "治理、战略、风险管理、指标和目标",
  "input_schema": {
    "entity": {"name": "string", "reporting_year": "int", ...},
    "governance": {"climate_governance_body": "required", ...},
    ...
  },
  "requirements_summary": {
    "total": 99,
    "by_pillar": {"governance": 10, "strategy": 22, ...},
    "by_severity": {"fatal": 65, "warning": 34}
  }
}
```

### 2. 需求驱动的数据收集

**问题**：当前工具假设输入数据已存在。实际上，agent 应该：
1. 读取 spec 了解需要什么数据
2. 引导用户逐步提供
3. 验证数据完整性

**需要**：一个 `get_data_requirements` 工具：

```json
{
  "required_fields": [
    {"path": "output.governance.climate_governance_body", "rule": "gf-s2-001", "severity": "fatal"},
    {"path": "output.metrics.ghg.scope1_emissions_tco2e", "rule": "gf-s2-011", "severity": "fatal"},
    ...
  ],
  "optional_fields": [...],
  "conditional_fields": [
    {"condition": "is_financial_institution == true", "fields": ["financed_emissions_tco2e"]}
  ]
}
```

### 3. 差距分析（Gap Analysis）

**问题**：没有工具回答"我还缺什么数据？"

**需要**：一个 `analyze_gaps` 工具，输入已有数据，输出：

```json
{
  "coverage": 0.35,
  "missing_fatal": [
    {"field": "output.governance.climate_governance_body", "rule": "gf-s2-001", "priority": 1},
    ...
  ],
  "missing_warning": [...],
  "recommendations": [
    "首先收集治理机构信息（Para 6(a)要求）",
    "然后收集排放数据（Para 29(a)要求）",
    ...
  ]
}
```

### 4. 合规报告生成

**问题**：没有工具生成结构化的合规报告。

**需要**：一个 `generate_report` 工具：

```json
{
  "report_type": "issb_s2_compliance",
  "entity": "某企业",
  "date": "2026-06-22",
  "executive_summary": {
    "compliance_status": "partial",
    "coverage": 0.65,
    "critical_gaps": 5,
    "warnings": 8
  },
  "pillar_assessment": {
    "governance": {"status": "pass", "rules_checked": 10, "passed": 10},
    "strategy": {"status": "fail", "rules_checked": 22, "passed": 15, "failed": 7},
    ...
  },
  "detailed_findings": [...],
  "remediation_plan": [...]
}
```

### 5. 修复指导（Remediation Guidance）

**问题**：当前只说"规则失败"，不说"怎么修"。

**需要**：一个 `get_remediation` 工具：

```json
{
  "rule_id": "gf-s2-001",
  "failure": "未披露治理机构",
  "citation": "IFRS S2 Para 6(a): An entity shall disclose...",
  "remediation_steps": [
    "1. 确定负责监督气候风险的治理机构或个人",
    "2. 记录该机构的职责范围和授权",
    "3. 在报告中披露治理机构信息"
  ],
  "example_data": {
    "climate_governance_body": "董事会下设ESG委员会，由3名独立董事组成"
  }
}
```

---

## 实现架构

```
┌─────────────────────────────────────────────────────────┐
│                    LLM Agent (Claude)                    │
│                                                         │
│  1. 调用 describe_spec 了解需求                          │
│  2. 调用 get_data_requirements 收集数据清单               │
│  3. 引导用户提供数据                                      │
│  4. 调用 validate_data 执行规则                           │
│  5. 调用 analyze_gaps 识别缺口                            │
│  6. 调用 get_remediation 生成修复建议                     │
│  7. 调用 generate_report 输出报告                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              MCP Server (spec-driven-review)             │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Spec Loader │  │ Rule Engine │  │ Report Gen  │     │
│  │ (YAML→JSON) │  │ (JsonLogic) │  │ (模板渲染)   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│         │                │                │              │
│         ▼                ▼                ▼              │
│  ┌─────────────────────────────────────────────┐       │
│  │           YAML Spec Files (真相来源)          │       │
│  │  issb-s2-disclosure.yaml (122 citations,    │       │
│  │                           99 rules)          │       │
│  └─────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

---

## 实现进度

### Phase 1: Spec 自描述 ✅ 已实现

**工具**: `describe_spec`

**功能**:
- 返回 spec 的领域、覆盖范围、规则统计
- 按支柱/严重级别/生命周期分组
- 支持单个 spec 或全部 spec 的概览

**示例输出**:
```json
{
  "spec_id": "issb-s2-disclosure",
  "specs": [{
    "spec_id": "green-finance/issb-s2-disclosure",
    "title": "IFRS S2 Climate-related Disclosures (ISSB 2026)",
    "version": "3.2.0",
    "rules_count": 99,
    "citations_count": 122,
    "pillars": {
      "governance": 10,
      "strategy": 22,
      "risk_management": 7,
      "metrics": 34,
      "targets": 11,
      "scenario_analysis": 5,
      "appendix": 10
    }
  }],
  "totals": {"rules": 99, "citations": 122},
  "severity_breakdown": {"fatal": 65, "warning": 34},
  "lifecycle_breakdown": {"post_audit": 80, "pre_calculation": 5, "runtime_inference": 14}
}
```

### Phase 2: 需求驱动的数据收集 ✅ 已实现

**工具**: `get_data_requirements`

**功能**:
- 分析 spec 中所有规则的 condition 和 assertion
- 提取需要用户提供哪些数据字段
- 区分必填/选填/条件字段

**示例输出**:
```json
{
  "spec_id": "issb-s2-disclosure",
  "required_fields": [
    {
      "path": "output.governance.climate_governance_body",
      "rule_id": "gf-s2-001",
      "rule_name": "气候治理机构披露",
      "severity": "fatal",
      "lifecycle": "post_audit"
    },
    ...
  ],
  "optional_fields": [...],
  "conditional_fields": [...],
  "summary": {
    "required_count": 117,
    "optional_count": 43,
    "conditional_count": 15
  },
  "input_schema": {
    "output": {
      "governance": {
        "climate_governance_body": {"required": true, "rule": "gf-s2-001"},
        ...
      },
      ...
    }
  }
}
```

### Phase 3: 差距分析 + 数据验证 + 修复指导 + 报告生成 ✅ 已实现

**工具**:
- `analyze_gaps` - 差距分析
- `validate_data` - 数据验证
- `get_remediation` - 修复指导
- `generate_report` - 报告生成

**功能**:

#### analyze_gaps
- 输入已有数据，返回哪些要求已满足、哪些缺失
- 按严重级别分组（fatal/warning）
- 生成数据收集建议（按优先级排序）

#### validate_data
- 执行 spec 中所有规则
- 按支柱分组评估
- 返回完整的审计结果

#### get_remediation
- 返回规则的详细解释
- 关联的 citation 原文
- 修复步骤和示例数据

#### generate_report
- 执行所有规则并生成结构化报告
- 包含执行摘要、支柱评估、详细发现、修复计划
- 支持 JSON 和 Markdown 格式

---

## 关键设计原则

### 1. Spec 是唯一真相

所有规则、引用、要求都从 YAML 读取，不硬编码。

```python
# ❌ 硬编码
if entity.has_governance_body:
    pass

# ✅ Spec 驱动
for rule in spec.get("rules", []):
    assertion = rule.get("assertion", {})
    passed = jsonlogic(data, assertion)
```

### 2. Agent 是执行者

MCP 工具提供能力，agent 决定流程。

```python
# ❌ 工具控制流程
def audit_entity(data):
    check_governance(data)
    check_strategy(data)
    check_metrics(data)

# ✅ Agent 控制流程
# Agent 调用:
# 1. describe_spec("issb-s2-disclosure")
# 2. get_data_requirements("issb-s2-disclosure")
# 3. 引导用户提供数据...
# 4. validate_data("issb-s2-disclosure", data)
# 5. generate_report("issb-s2-disclosure", data)
```

### 3. 渐进式披露

先给摘要，用户需要时再给详情。

```python
# 第一步：概览
describe_spec("issb-s2-disclosure")
# → 返回：99 条规则，122 条引用，按支柱分组

# 第二步：详情（用户需要时）
get_data_requirements("issb-s2-disclosure")
# → 返回：117 个必填字段，43 个选填字段

# 第三步：具体规则（用户询问时）
get_remediation("issb-s2-disclosure", "gf-s2-001")
# → 返回：规则详情、citation 原文、修复步骤
```

### 4. 失败可解释

每个失败都关联 citation 原文和修复建议。

```json
{
  "rule_id": "gf-s2-001",
  "rule_name": "气候治理机构披露",
  "passed": false,
  "severity": "fatal",
  "message": "IFRS S2 Para 6(a): 须披露负责监督气候相关风险和机遇的治理机构或个人",
  "citation": {
    "id": "cit-s2-001",
    "text": "An entity shall disclose information about its governance body(s) or individual(s) responsible for oversight of climate-related risks and opportunities.",
    "section": "IFRS S2 Para 6(a)"
  },
  "remediation_steps": [
    "确定负责监督气候风险的治理机构或个人",
    "记录该机构的职责范围和授权",
    "在报告中披露治理机构信息"
  ],
  "example_data": {
    "climate_governance_body": "董事会下设ESG委员会，由3名独立董事组成"
  }
}
```

### 5. 报告可审计

生成的报告包含完整的执行轨迹。

```json
{
  "report_metadata": {
    "spec_id": "issb-s2-disclosure",
    "entity_name": "示例企业",
    "generated_at": "2026-06-22T10:30:00",
    "spec_version": "3.2.0"
  },
  "executive_summary": {
    "compliance_status": "fatal",
    "total_rules_checked": 75,
    "passed": 20,
    "warnings": 13,
    "critical_failures": 42,
    "coverage": 26.7
  },
  "pillar_assessments": {
    "governance": {"status": "fatal", "total": 6, "passed": 1, "failed": 5, "coverage": 16.7},
    "strategy": {"status": "fatal", "total": 31, "passed": 7, "failed": 24, "coverage": 22.6},
    ...
  },
  "critical_findings": [...],
  "warnings": [...],
  "remediation_plan": [...]
}
```

---

## MCP 工具清单

### Spec-Driven 审计工具（核心）

| 工具 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `describe_spec` | 描述 spec 结构 | spec_id | 领域、范围、统计 |
| `get_data_requirements` | 获取数据要求 | spec_id | 必填/选填/条件字段 |
| `analyze_gaps` | 差距分析 | spec_id, data | 覆盖率、缺失项、建议 |
| `validate_data` | 数据验证 | spec_id, data | 审计结果、支柱评估 |
| `get_remediation` | 修复指导 | spec_id, rule_id | 详情、citation、步骤 |
| `generate_report` | 生成报告 | spec_id, data | 合规报告（JSON/MD） |

### 域1 — 碳核算审查

| 工具 | 功能 |
|------|------|
| `audit_scope1` | 审查 Scope 1 直接排放 |
| `audit_scope2` | 审查 Scope 2 外购能源 |
| `audit_scope3` | 审查 Scope 3 供应链 |
| `get_rule` | 查询规则详情 |
| `list_rules` | 列出适用规则 |
| `explain_failure` | 解释失败原因 |

### 域2 — 绿色金融合规

| 工具 | 功能 |
|------|------|
| `check_green_bond` | 绿色债券资格检查 |
| `check_green_credit` | 绿色信贷分类 |
| `check_issb_s2` | ISSB S2 合规检查 |
| `classify_project` | 项目类别自动匹配 |
| `get_gf_rule` | 绿色金融规则详情 |

### 跨域审查

| 工具 | 功能 |
|------|------|
| `full_green_finance_audit` | 一站式绿色金融合规审查 |

---

## 审计工作流示例

### 场景：ISSB S2 气候披露合规审计

```
用户: 请帮我检查我们公司的 ISSB S2 合规情况

Agent:
1. 调用 describe_spec("issb-s2-disclosure")
   → 了解 spec 覆盖 99 条规则、122 条引用
   → 按支柱分组：治理(10)、战略(22)、风险管理(7)、指标(34)、目标(11)

2. 调用 get_data_requirements("issb-s2-disclosure")
   → 获取 117 个必填字段、43 个选填字段
   → 构建数据收集清单

3. 引导用户提供数据:
   Agent: "首先，请提供公司治理信息：
   - 负责监督气候风险的治理机构是什么？
   - 管理层在气候风险管理中的角色是什么？
   - 高管薪酬中与气候相关的比例是多少？"

4. 用户提供部分数据后:
   调用 analyze_gaps("issb-s2-disclosure", partial_data)
   → 覆盖率 35%，42 项严重缺失
   → 建议：首先收集治理机构信息（Para 6(a)要求）

5. 继续收集数据...

6. 数据完整后:
   调用 validate_data("issb-s2-disclosure", complete_data)
   → 执行 75 条规则，通过 20 条，警告 13 条，严重失败 42 条

7. 对于失败的规则:
   调用 get_remediation("issb-s2-disclosure", "gf-s2-005")
   → 返回：气候风险时间维度要求
   → citation: "IFRS S2 Para 10: ..."
   → 修复步骤：按短期、中期和长期披露气候风险

8. 生成最终报告:
   调用 generate_report("issb-s2-disclosure", data, "示例企业")
   → 合规状态：fatal
   → 覆盖率：26.7%
   → 支柱评估：治理(16.7%)、战略(22.6%)、风险管理(30.0%)
   → 修复计划：按优先级排序的修复建议
```

---

## 测试验证

### 测试脚本

`examples/test_spec_driven_audit.py` 演示完整的 spec-driven 审计工作流。

### 测试结果

```
Spec: issb-s2-disclosure
  规则数: 99
  引用数: 122

模拟数据验证:
  覆盖率: 20/75 (26.7%)
  通过: 20
  缺失 (fatal): 42
  缺失 (warning): 13

支柱评估:
  ✗ governance: 1/6 (16.7%)
  ✗ strategy: 7/31 (22.6%)
  ✗ risk_management: 3/10 (30.0%)
  ✗ metrics: 6/18 (33.3%)
  ✗ targets: 3/10 (30.0%)
```

---

## 未来扩展

### Phase 4: 多 Spec 联动

**目标**: 跨域审计能力（碳核算 + 绿色金融 + IFRS S2）

**场景**:
- 企业同时需要满足 GHG Protocol 和 ISSB S2 要求
- 绿色债券项目需要同时满足债券目录和碳核算要求
- 金融机构需要同时满足绿色信贷和 ISSB S2 融资排放要求

**实现**:
- `describe_spec` 支持多个 spec 的联合描述
- `validate_data` 支持多个 spec 的联合验证
- `generate_report` 生成跨域合规报告

### Phase 5: 语义搜索

**目标**: 用嵌入向量搜索 citation 和规则

**场景**:
- 用户问："有哪些关于 Scope 3 融资排放的要求？"
- Agent 用语义搜索找到相关 citation 和规则

**实现**:
- 为 citation 生成嵌入向量（用 text2vec-base-chinese）
- 新增 `search_citations(query)` 工具
- 支持自然语言查询

### Phase 6: 动态 Spec 更新

**目标**: 支持 spec 的动态更新和版本管理

**场景**:
- ISSB 发布新版本的 IFRS S2
- 用户需要更新 spec 并重新审计

**实现**:
- `update_spec(spec_id, new_version)` 工具
- 版本比较和变更追踪
- 自动重新审计

---

## 附录

### A. 文件结构

```
mcp_server/
├── __init__.py
├── __main__.py
├── server.py          # MCP 服务器入口
├── loader.py          # YAML spec 加载器
├── engine.py          # JsonLogic 规则执行引擎
├── tools_spec.py      # Spec-Driven 审计工具（核心）
├── tools_ghg.py       # 碳核算域工具
├── tools_gf.py        # 绿色金融域工具
└── bridge.py          # 跨域桥接工具

specs/
├── _meta.yaml         # 主配置
├── green-finance/
│   ├── issb-s2-disclosure.yaml  # IFRS S2 (122 citations, 99 rules)
│   ├── bond-catalog.yaml
│   ├── bond-eligibility.yaml
│   ├── credit-classification.yaml
│   └── cross-domain-bridge.yaml
├── scope1/
├── scope2/
├── scope3/
└── ...

examples/
├── test_spec_driven_audit.py  # Spec-Driven 审计工作流测试
├── validate.py
└── real_scenarios.py
```

### B. 依赖

- Python ≥ 3.11
- mcp (FastMCP)
- pyyaml
- jsonschema

### C. 参考

- [GHG Protocol Corporate Standard](https://ghgprotocol.org/corporate-standard)
- [IFRS S2 Climate-related Disclosures](https://www.ifrs.org/issued-standards/ifrs-sustainability-standards-navigator/ifrs-s2-climate-related-disclosures/)
- [JsonLogic](https://jsonlogic.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
