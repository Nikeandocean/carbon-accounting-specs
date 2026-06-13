# GHG Protocol Scope 2 Spec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a complete, machine-parseable YAML spec for GHG Protocol Scope 2 carbon accounting, ready for GitHub publication.

**Architecture:** Dual-layer design (Schema Config + Knowledge Base) with dual-engine (JsonLogic + External Functions). The spec defines rules, fallback chains, and validation logic that any agent framework can consume.

**Tech Stack:** YAML, JSON Schema, JsonLogic expressions, Git

---

## File Structure

```
specs/
├── _meta.yaml
├── principles/
│   ├── organizational-boundary.yaml
│   ├── operational-boundary.yaml
│   ├── data-quality-hierarchy.yaml
│   └── emission-attribution.yaml
├── methods/
│   ├── location-based.yaml
│   ├── market-based.yaml
│   └── dual-reporting.yaml
├── reporting/
│   └── disclosure-requirements.yaml
└── constraints/
    └── prohibitions.yaml

schemas/
├── equity-share-input.json
├── equity-share-output.json
├── operational-control-input.json
├── operational-control-output.json
├── financial-control-input.json
├── financial-control-output.json
├── boundary-overlap-input.json
└── boundary-overlap-output.json

docs/
├── README.md
├── LICENSE
├── methodology.md
├── schema-spec.md
└── agent-integration-guide.md

examples/
└── sample-usage.yaml
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `specs/` directory structure
- Create: `schemas/` directory
- Create: `docs/` directory
- Create: `examples/` directory

- [ ] **Step 1: Create directory structure**

```bash
cd /d/Users/TaoYan/rules_for_spec_driven_agent
mkdir -p specs/principles
mkdir -p specs/methods
mkdir -p specs/reporting
mkdir -p specs/constraints
mkdir -p schemas
mkdir -p docs
mkdir -p examples
```

- [ ] **Step 2: Verify structure**

Run: `find . -type d | grep -E "(specs|schemas|docs|examples)" | sort`
Expected:
```
./docs
./examples
./schemas
./specs
./specs/constraints
./specs/methods
./specs/principles
./specs/reporting
```

---

## Task 2: Meta Schema (`_meta.yaml`)

**Files:**
- Create: `specs/_meta.yaml`

- [ ] **Step 1: Write _meta.yaml header and source standard**

```yaml
id: "ghg-protocol/scope2"
name: "GHG Protocol Scope 2 企业外购电力、蒸汽核算规范"
version: "1.0.0"

source_standard:
  name: "GHG Protocol Corporate Accounting and Reporting Standard"
  scope: "Scope 2: Indirect Emissions from Purchased Electricity, Steam, Heat, and Cooling"
  publisher: "World Resources Institute (WRI) & WBCSD"
  original_version: "2015"
  url: "https://ghgprotocol.org/scope-2-guidance"

applicability:
  entity_types: ["企业", "组织", "政府机构"]
  geographic_scope: "全球"
  excluded: ["产品级LCA", "项目级减排"]
```

- [ ] **Step 2: Add expression engines definition**

Append to `specs/_meta.yaml`:

```yaml

# 表达式引擎定义
expression_engines:
  jsonlogic:
    version: "2.0"
    scope: "基础规则：非空校验、类型检查、简单比较、集合操作"
  external_functions:
    scope: "复杂拓扑：组织边界、股权穿透、控制权计算"
    registry:
      - id: "calc.equity_share"
        description: "按股权比例法计算子公司排放分摊"
        input_schema: "schemas/equity-share-input.json"
        output_schema: "schemas/equity-share-output.json"
      - id: "calc.operational_control"
        description: "按运营控制权法判定排放归属"
        input_schema: "schemas/operational-control-input.json"
        output_schema: "schemas/operational-control-output.json"
      - id: "calc.financial_control"
        description: "按财务控制权法判定合并范围"
        input_schema: "schemas/financial-control-input.json"
        output_schema: "schemas/financial-control-output.json"
      - id: "calc.boundary_overlap_check"
        description: "检测Scope 1与Scope 2的能源边界重叠（含CHP自发电、热电联产等场景）"
        input_schema: "schemas/boundary-overlap-input.json"
        output_schema: "schemas/boundary-overlap-output.json"
```

- [ ] **Step 3: Add rule lifecycle definition**

Append to `specs/_meta.yaml`:

```yaml

# 规则生命周期分层
rule_lifecycle:
  stages:
    - id: "pre_calculation"
      name: "前置约束"
      description: "计算前必须满足的条件（输入校验、边界确认）"
      timing: "before_computation"
    - id: "runtime_inference"
      name: "运行时推导"
      description: "计算过程中的动态决策（方法选择、因子选择）"
      timing: "during_computation"
    - id: "post_audit"
      name: "后置审计"
      description: "计算完成后的合规性断言（输出校验、双重报告校验）"
      timing: "after_computation"
```

- [ ] **Step 4: Add on_fail actions definition**

Append to `specs/_meta.yaml`:

```yaml

# on_fail动作定义
on_fail_actions:
  raise_fatal:
    description: "终止计算，抛出合规异常"
    agent_behavior: "停止所有后续计算，输出错误详情"
  raise_warning:
    description: "继续计算，生成审计日志"
    agent_behavior: "记录warning，继续执行"
  log_info:
    description: "记录日志，不干预"
    agent_behavior: "仅记录，不影响流程"
  mark_unavailable:
    description: "标记数据不可用，不立即终止，由后续cross_method_validation统一裁决"
    agent_behavior: |
      1. 设置状态标记（如 market_based.data_available = false）
      2. 记录fatal级别日志
      3. 继续执行其他流程
      4. 由post_audit阶段的cross_method_validation决定最终处理
  require_justification:
    description: "要求合规性解释（Comply or Explain），支持实例级隔离"
    agent_behavior: |
      1. 检查justification是否存在，优先级：
         a. 实例级：input.justifications["{rule_id}@{instance_path}"]
         b. 全局级：input.justifications[rule_id]
      2. 若存在且非空：
         - 将severity降级为warning
         - 记录justification到审计日志（含instance_path）
         - 继续计算
      3. 若不存在或为空：
         - 将severity升级为fatal
         - 终止计算
    instance_isolation_example: |
      # justifications支持两种粒度：
      justifications:
        "proh-006": "全局理由：2026年官方因子尚未发布"
        "proh-006@emission_sources[1].id": "该网点位于偏远地区，仅能获取2024年因子"
```

- [ ] **Step 5: Add conflict resolution strategy**

Append to `specs/_meta.yaml`:

```yaml

# 冲突解决策略
conflict_resolution:
  strategy: "local_overrides_global"
  description: "本地法规优先于通用标准"
  hierarchy:
    - level: 1
      scope: "enterprise_specific"
      description: "企业特定规则（最高优先级）"
    - level: 2
      scope: "industry_specific"
      description: "行业特定规则"
    - level: 3
      scope: "regional_specific"
      description: "地区/国家特定规则"
    - level: 4
      scope: "global_standard"
      description: "GHG Protocol通用规则（最低优先级）"
  override_mechanics:
    - rule: "本地规则可覆盖global_rules中的SHOULD和MAY规则"
    - rule: "本地规则不可覆盖global_rules中的MUST规则，除非有明确的法规冲突声明"
    - rule: "覆盖时必须记录overridden_by和override_reason"
```

- [ ] **Step 6: Add input schema definition**

Append to `specs/_meta.yaml`:

```yaml

# 输入数据Schema
input_schema:
  context:
    region:
      type: "object"
      required: true
      properties:
        country_code:
          type: "string"
          format: "ISO_3166-1_alpha-2"
          description: "国家代码（如CN、US、DE）"
        subnational_code:
          type: "string"
          format: "ISO_3166-2"
          description: "行政区划代码（如CN-BJ、CN-GD）"
          nullable: true
        has_market_instruments:
          type: "boolean"
          description: |
            该地区是否存在市场化电力交易工具（绿证、PPA、I-REC等）
            注意：只要该国/地区存在任何能够改变电力环境属性的合同工具市场，
            不论企业自身是否购买，该字段都必须为true。
            维护规则：由context数据库统一维护，企业不可自行覆盖。
        grid_average_ef:
          type: "number"
          unit: "tCO2/MWh"
          description: "电网平均排放因子"
          nullable: true
        residual_mix_ef:
          type: "number"
          unit: "tCO2/MWh"
          description: "残余电力组合排放因子"
          nullable: true
    emission_factors:
      type: "object"
      properties:
        current_year:
          type: "number"
          nullable: true
        previous_year:
          type: "number"
          nullable: true
        latest_available:
          type: "number"
          nullable: true
        latest_year:
          type: "integer"
          nullable: true
  input:
    entity:
      type: "object"
      required: true
      properties:
        name:
          type: "string"
        reporting_year:
          type: "integer"
        control_method:
          type: "string"
          enum: ["financial_control", "operational_control", "equity_share"]
    emission_sources:
      type: "array"
      items:
        type: "object"
        properties:
          id:
            type: "string"
          type:
            type: "string"
            enum: ["electricity", "steam", "heat", "cooling"]
          activity_data:
            type: "number"
            unit: "MWh"
          emission_factor:
            type: "object"
            properties:
              value:
                type: "number"
              year:
                type: "integer"
              source:
                type: "string"
              type:
                type: "string"
                enum: ["contract", "certificate", "supplier", "residual_mix", "grid_average", "default"]
    justifications:
      type: "object"
      description: |
        合规性解释（Comply or Explain），支持两级粒度：
        - 全局级：key为rule_id，适用于所有实例
        - 实例级：key为"{rule_id}@{instance_path}"，适用于特定排放源
        优先级：实例级 > 全局级
      additionalProperties:
        type: "string"
      examples:
        - "proh-006": "全局理由：2026年官方因子尚未发布"
        - "proh-006@emission_sources[1].id": "该网点位于偏远地区，仅能获取2024年因子"
```

- [ ] **Step 7: Add load order and global rules**

Append to `specs/_meta.yaml`:

```yaml

load_order:
  - principles/organizational-boundary
  - principles/operational-boundary
  - principles/data-quality-hierarchy
  - principles/emission-attribution
  - methods/location-based
  - methods/market-based
  - methods/dual-reporting
  - reporting/disclosure-requirements
  - constraints/prohibitions

global_rules:
  - id: "global-001"
    name: "完整性原则"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "pre_calculation"
    scope: "scope2_only"
    condition: {"!=": [{"var": "input.emission_sources.identified"}, null]}
    assertion:
      "all": [
        {"var": "input.emission_sources.identified"},
        {
          "and": [
            {"!=": [{"var": "activity_data"}, null]},
            {"!=": [{"var": "emission_factor"}, null]}
          ]
        }
      ]
    on_fail: "raise_fatal"
    on_fail_message: "存在已识别但未提供数据的排放源"
    citation: "GHG Protocol Corporate Standard, Chapter 4"

  - id: "global-002"
    name: "一致性原则"
    priority: "MUST"
    severity: "warning"
    layer: "schema"
    lifecycle: "post_audit"
    assertion:
      "or": [
        {"==": [{"var": "input.accounting_method"}, {"var": "context.previous_year.accounting_method"}]},
        {"!=": [{"var": "input.justifications.global-002"}, null]}
      ]
    on_fail: "require_justification"
    on_fail_message: "核算方法与上年度不一致，需在报告中说明变更原因"
    citation: "GHG Protocol Corporate Standard, Chapter 4"

  - id: "global-003"
    name: "透明度原则"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "post_audit"
    assertion:
      "and": [
        {"!=": [{"var": "input.assumptions"}, null]},
        {"!=": [{"var": "input.methodology_rationale"}, null]},
        {"!=": [{"var": "input.data_sources"}, null]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "缺少假设、方法选择或数据来源的说明，无法通过审计"
    citation: "GHG Protocol Corporate Standard, Chapter 4"

versioning:
  scheme: "semver"
  rules:
    major: "规则语义变更（MUST变SHOULD等）"
    minor: "新增规则或文件"
    patch: "修正措辞、补充引用"
```

- [ ] **Step 8: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('specs/_meta.yaml'))"`
Expected: No output (valid YAML)

- [ ] **Step 9: Commit**

```bash
git add specs/_meta.yaml
git commit -m "feat: add _meta.yaml with engines, lifecycle, and input schema"
```

---

## Task 3: Organizational Boundary Spec

**Files:**
- Create: `specs/principles/organizational-boundary.yaml`

- [ ] **Step 1: Write organizational boundary header**

```yaml
meta:
  id: "scope2/organizational-boundary"
  version: "1.0.0"
  source: "GHG Protocol Corporate Standard"
  source_ref: "https://ghgprotocol.org/corporate-standard"
  layer: "schema"
  description: "组织边界确定规则：控制权法、股权比例法"

citations:
  - id: "cit-ob-001"
    text: "Companies shall select and consistently use one of two approaches for consolidating GHG emissions: the equity share approach or the financial control approach or the operational control approach."
    page: 18
    section: "Chapter 3: Setting Organizational Boundaries"
```

- [ ] **Step 2: Add organizational boundary rules**

Append to `specs/principles/organizational-boundary.yaml`:

```yaml

rules:
  - id: "rule-ob-001"
    name: "组织边界核算"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "pre_calculation"
    condition: {"!=": [{"var": "input.subsidiaries"}, null]}
    computation:
      function: "calc.equity_share"
      params:
        subsidiaries: {"var": "input.subsidiaries"}
        ownership_data: {"var": "input.ownership_structure"}
        control_type: {"var": "input.control_method"}
    assertion: {"!=": [{"var": "computation.result.boundary_emissions"}, null]}
    on_fail: "raise_fatal"
    on_fail_message: "组织边界计算失败，无法确定合并范围"
    citation: "cit-ob-001"
    
  - id: "rule-ob-002"
    name: "控制权法判定"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "pre_calculation"
    condition: {"==": [{"var": "input.control_method"}, "operational_control"]}
    computation:
      function: "calc.operational_control"
      params:
        subsidiaries: {"var": "input.subsidiaries"}
        control_indicators: {"var": "input.control_indicators"}
    assertion: {"!=": [{"var": "computation.result.controlled_entities"}, null]}
    on_fail: "raise_fatal"
    on_fail_message: "运营控制权判定失败"
    citation: "cit-ob-001"
    
  - id: "rule-ob-003"
    name: "股权比例法判定"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "pre_calculation"
    condition: {"==": [{"var": "input.control_method"}, "equity_share"]}
    computation:
      function: "calc.equity_share"
      params:
        subsidiaries: {"var": "input.subsidiaries"}
        ownership_data: {"var": "input.ownership_structure"}
    assertion: {"!=": [{"var": "computation.result.equity_share_emissions"}, null]}
    on_fail: "raise_fatal"
    on_fail_message: "股权比例法计算失败"
    citation: "cit-ob-001"

dependencies: []

conflicts_with: []
```

- [ ] **Step 3: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('specs/principles/organizational-boundary.yaml'))"`
Expected: No output (valid YAML)

- [ ] **Step 4: Commit**

```bash
git add specs/principles/organizational-boundary.yaml
git commit -m "feat: add organizational boundary spec with control methods"
```

---

## Task 4: Operational Boundary Spec

**Files:**
- Create: `specs/principles/operational-boundary.yaml`

- [ ] **Step 1: Write operational boundary header and citations**

```yaml
meta:
  id: "scope2/operational-boundary"
  version: "1.0.0"
  source: "GHG Protocol Corporate Standard"
  source_ref: "https://ghgprotocol.org/corporate-standard"
  layer: "schema"
  description: "运营边界确定规则：Scope 1/2/3划分"

citations:
  - id: "cit-op-001"
    text: "Companies shall report Scope 1 and Scope 2 emissions. Companies may also report Scope 3 emissions."
    page: 25
    section: "Chapter 4: Setting Operational Boundaries"
    
  - id: "cit-op-002"
    text: "Scope 2 accounts for GHG emissions from the generation of purchased or acquired electricity, steam, heating, and cooling consumed by the reporting company."
    page: 27
    section: "Chapter 4: Scope 2 Emissions"
```

- [ ] **Step 2: Add operational boundary rules**

Append to `specs/principles/operational-boundary.yaml`:

```yaml

rules:
  - id: "rule-op-001"
    name: "Scope 2排放源识别"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "pre_calculation"
    assertion:
      "and": [
        {"!=": [{"var": "input.emission_sources"}, null]},
        {">": [{"var": "input.emission_sources.length"}, 0]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "未识别任何Scope 2排放源"
    citation: "cit-op-002"
    
  - id: "rule-op-002"
    name: "排放源类型校验"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "pre_calculation"
    assertion:
      "all": [
        {"var": "input.emission_sources"},
        {"in": [{"var": "type"}, ["electricity", "steam", "heat", "cooling"]]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "排放源类型必须为electricity、steam、heat或cooling"
    citation: "cit-op-002"
    
  - id: "rule-op-003"
    name: "活动数据正数校验"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "pre_calculation"
    assertion:
      "all": [
        {"var": "input.emission_sources"},
        {">": [{"var": "activity_data"}, 0]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "活动数据必须为正数"
    citation: "cit-op-001"

dependencies:
  - ref: "principles/organizational-boundary"
    relation: "applies_within"

conflicts_with: []
```

- [ ] **Step 3: Validate and commit**

Run: `python -c "import yaml; yaml.safe_load(open('specs/principles/operational-boundary.yaml'))"`

```bash
git add specs/principles/operational-boundary.yaml
git commit -m "feat: add operational boundary spec with scope 2 source identification"
```

---

## Task 5: Data Quality Hierarchy Spec

**Files:**
- Create: `specs/principles/data-quality-hierarchy.yaml`

- [ ] **Step 1: Write data quality hierarchy header**

```yaml
meta:
  id: "scope2/data-quality-hierarchy"
  version: "1.0.0"
  source: "GHG Protocol Scope 2 Guidance"
  source_ref: "https://ghgprotocol.org/scope-2-guidance"
  layer: "schema"
  description: "数据质量层级与回退机制"

citations:
  - id: "cit-dq-001"
    text: "Companies should use the most accurate data available, prioritizing supplier-specific data over averages, and averages over defaults."
    page: 35
    section: "Chapter 6: Data Quality"
```

- [ ] **Step 2: Add market-based fallback chain**

Append to `specs/principles/data-quality-hierarchy.yaml`:

```yaml

fallback_chains:
  market_based:
    name: "市场法数据回退链"
    description: "当高优先级数据不可用时，按序降级"
    chain:
      - level: 1
        name: "合同/PPA"
        data_type: "contract_emission_factor"
        condition: {"!=": [{"var": "input.contract_ef"}, null]}
        on_match:
          action: "use_value"
          log_level: "info"
          message: "使用合同排放因子"
        on_null:
          action: "proceed_to_next"
          
      - level: 2
        name: "绿色电力证书"
        data_type: "renewable_energy_certificate"
        condition: {"!=": [{"var": "input.rec_ef"}, null]}
        on_match:
          action: "use_value"
          log_level: "info"
          message: "使用绿证排放因子"
        on_null:
          action: "proceed_to_next"
          
      - level: 3
        name: "供应商排放因子"
        data_type: "supplier_specific_factor"
        condition: {"!=": [{"var": "input.supplier_ef"}, null]}
        on_match:
          action: "use_value"
          log_level: "info"
          message: "使用供应商排放因子"
        on_null:
          action: "proceed_to_next"
          
      - level: 4
        name: "残余电力组合"
        data_type: "residual_mix_factor"
        condition: {"!=": [{"var": "context.region.residual_mix_ef"}, null]}
        on_match:
          action: "use_value_with_warning"
          log_level: "warning"
          message: "使用残余电力组合因子，数据质量降级"
          require_disclosure: true
          disclosure_key: "proh-006"
        on_null:
          action: "proceed_to_next"
          
      - level: 5
        name: "电网平均排放因子"
        data_type: "grid_average_factor"
        condition: {"!=": [{"var": "context.region.grid_average_ef"}, null]}
        on_match:
          action: "use_value_with_warning"
          log_level: "warning"
          message: "回退至电网平均因子，请在报告中说明原因"
          require_disclosure: true
          disclosure_key: "proh-006"
        on_null:
          action: "mark_unavailable"
          log_level: "fatal"
          message: "市场法所有数据源均不可用"
          set_state: "market_based.data_available = false"
```

- [ ] **Step 3: Add location-based fallback chain**

Append to `specs/principles/data-quality-hierarchy.yaml`:

```yaml

  location_based:
    name: "位置法数据回退链"
    chain:
      - level: 1
        name: "区域电网排放因子"
        data_type: "subnational_grid_factor"
        condition: {"!=": [{"var": "context.region.subnational_ef"}, null]}
        on_match:
          action: "use_value"
          log_level: "info"
          message: "使用区域电网排放因子"
        on_null:
          action: "proceed_to_next"
          
      - level: 2
        name: "国家电网排放因子"
        data_type: "national_grid_factor"
        condition: {"!=": [{"var": "context.country.grid_ef"}, null]}
        on_match:
          action: "use_value"
          log_level: "warning"
          message: "使用国家电网排放因子，精度降级"
          require_disclosure: true
          disclosure_key: "proh-006"
        on_null:
          action: "raise_fatal"
          message: "无可用的电网排放因子数据"
```

- [ ] **Step 4: Add time-based fallback chain**

Append to `specs/principles/data-quality-hierarchy.yaml`:

```yaml

  time_based_fallback:
    name: "排放因子时效性回退"
    description: "当当年因子不可用时的降级策略"
    chain:
      - level: 1
        name: "当年排放因子"
        data_type: "current_year_factor"
        condition: {"!=": [{"var": "context.emission_factors.current_year"}, null]}
        on_match:
          action: "use_value"
          log_level: "info"
          message: "使用当年排放因子"
        on_null:
          action: "proceed_to_next"
          
      - level: 2
        name: "前一年排放因子"
        data_type: "previous_year_factor"
        condition: {"!=": [{"var": "context.emission_factors.previous_year"}, null]}
        on_match:
          action: "use_value_with_warning"
          log_level: "warning"
          message: "当年因子不可用，使用前一年因子"
          require_disclosure: true
          disclosure_key: "proh-006"
        on_null:
          action: "proceed_to_next"
          
      - level: 3
        name: "最近可用排放因子"
        data_type: "latest_available_factor"
        condition: {"!=": [{"var": "context.emission_factors.latest_available"}, null]}
        on_match:
          action: "use_value_with_warning"
          log_level: "warning"
          message: "使用最近可用因子，距核算期存在时滞"
          require_disclosure: true
          disclosure_key: "proh-006"
        on_null:
          action: "raise_fatal"
          message: "无任何可用的排放因子数据"
```

- [ ] **Step 5: Add cross-method validation**

Append to `specs/principles/data-quality-hierarchy.yaml`:

```yaml

# 横向联动校验
cross_method_validation:
  - id: "cross-val-001"
    name: "市场法兜底联动"
    priority: "MUST"
    severity: "warning"
    layer: "schema"
    lifecycle: "post_audit"
    condition:
      "and": [
        {"==": [{"var": "market_based.fallback_level"}, 5]},
        {"!=": [{"var": "location_based.result"}, null]}
      ]
    assertion:
      "or": [
        {"==": [{"var": "market_based.emission_factor.source"}, {"var": "location_based.emission_factor.source"}]},
        {
          "and": [
            {"==": [{"var": "market_based.emission_factor.type"}, "residual_mix"]},
            {"==": [{"var": "location_based.emission_factor.type"}, "grid_average"]},
            {"!=": [{"var": "input.justifications.cross-val-001"}, null]}
          ]
        }
      ]
    on_fail: "require_justification"
    on_fail_message: "市场法已回退至电网平均因子，但与位置法数据源不一致，请说明原因"
    
  - id: "cross-val-002"
    name: "双重报告完整性保障"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "post_audit"
    condition:
      "and": [
        {"==": [{"var": "context.region.has_market_instruments"}, true]},
        {"==": [{"var": "market_based.data_available"}, false]},
        {"==": [{"var": "location_based.data_available"}, false]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "位置法和市场法数据均不可用，无法完成双重报告"
    
  - id: "cross-val-003"
    name: "市场法不可用时的降级策略"
    priority: "MUST"
    severity: "warning"
    layer: "schema"
    lifecycle: "post_audit"
    condition:
      "and": [
        {"==": [{"var": "context.region.has_market_instruments"}, true]},
        {"==": [{"var": "market_based.data_available"}, false]},
        {"==": [{"var": "location_based.data_available"}, true]}
      ]
    action: "fallback_to_location_based"
    action_description: |
      市场法数据完全不可用时，允许将位置法结果同时作为市场法结果报告，
      但必须在报告中明确披露：
      1. 市场法数据不可用的原因
      2. 使用位置法结果替代市场法结果
      3. 该替代对排放总量的影响
    require_disclosure: true
    disclosure_key: "cross-val-003"
    on_fail: "require_justification"
    on_fail_message: "市场法数据不可用，使用位置法结果替代，必须披露原因"

dependencies: []

conflicts_with: []
```

- [ ] **Step 6: Validate and commit**

Run: `python -c "import yaml; yaml.safe_load(open('specs/principles/data-quality-hierarchy.yaml'))"`

```bash
git add specs/principles/data-quality-hierarchy.yaml
git commit -m "feat: add data quality hierarchy with fallback chains and cross-validation"
```

---

## Task 6: Emission Attribution Spec

**Files:**
- Create: `specs/principles/emission-attribution.yaml`

- [ ] **Step 1: Write emission attribution spec**

```yaml
meta:
  id: "scope2/emission-attribution"
  version: "1.0.0"
  source: "GHG Protocol Scope 2 Guidance"
  source_ref: "https://ghgprotocol.org/scope-2-guidance"
  layer: "knowledge"
  description: "排放归属原则"

citations:
  - id: "cit-ea-001"
    text: "Scope 2 emissions are physically produced at the facility where electricity is generated. However, for corporate accounting purposes, these emissions are attributed to the consumer of the electricity."
    page: 28
    section: "Chapter 5: Tracking and Reporting"

rules:
  - id: "rule-ea-001"
    name: "消费者归属原则"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "knowledge"
    statement: "Scope 2排放归属于电力消费者，而非发电设施"
    interpretation_guidance: "在集团核算中，各子公司按各自用电量分别归属排放"
    citation: "cit-ea-001"
    
  - id: "rule-ea-002"
    name: "地理归属原则"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "knowledge"
    statement: "排放因子应使用电力消费所在地的电网因子，而非发电厂所在地"
    interpretation_guidance: "跨国企业需按各国用电量分别计算"
    citation: "cit-ea-001"

dependencies:
  - ref: "principles/organizational-boundary"
    relation: "constrained_by"

conflicts_with: []
```

- [ ] **Step 2: Validate and commit**

Run: `python -c "import yaml; yaml.safe_load(open('specs/principles/emission-attribution.yaml'))"`

```bash
git add specs/principles/emission-attribution.yaml
git commit -m "feat: add emission attribution spec"
```

---

## Task 7: Location-Based Method Spec

**Files:**
- Create: `specs/methods/location-based.yaml`

- [ ] **Step 1: Write location-based method spec**

```yaml
meta:
  id: "scope2/location-based"
  version: "1.0.0"
  source: "GHG Protocol Scope 2 Guidance"
  source_ref: "https://ghgprotocol.org/scope-2-guidance"
  layer: "schema"
  description: "基于位置法（Location-Based Method）"

citations:
  - id: "cit-lb-001"
    text: "The location-based method reflects the average emissions intensity of grids on which energy consumption occurs, including reflecting, where applicable, the contractual instruments (including tradable certificates) that are available on that grid."
    page: 28
    section: "Chapter 6: Scope 2 Guidance"
    
  - id: "cit-lb-002"
    text: "Under the location-based method, companies use grid average emission factor data to calculate their Scope 2 emissions."
    page: 30
    section: "Chapter 6: Location-Based Method"

rules:
  - id: "rule-lb-001"
    name: "位置法适用条件"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "runtime_inference"
    condition: {"==": [{"var": "input.method"}, "location_based"]}
    assertion:
      "and": [
        {"!=": [{"var": "input.activity_data"}, null]},
        {">": [{"var": "input.activity_data"}, 0]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "位置法计算需要有效的活动数据"
    citation: "cit-lb-001"
    
  - id: "rule-lb-002"
    name: "电网因子选择"
    type: "requirement"
    priority: "SHOULD"
    severity: "warning"
    layer: "schema"
    lifecycle: "runtime_inference"
    assertion:
      "or": [
        {"!=": [{"var": "input.emission_factor.source"}, "default"]},
        {"!=": [{"var": "input.justifications.rule-lb-002"}, null]}
      ]
    on_fail: "require_justification"
    on_fail_message: "应优先使用区域电网因子而非国家平均因子"
    citation: "cit-lb-002"
    
  - id: "rule-lb-003"
    name: "位置法计算公式"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "knowledge"
    statement: "排放量 = 活动数据(MWh) × 电网排放因子(tCO2/MWh)"
    citation: "cit-lb-002"

dependencies:
  - ref: "principles/data-quality-hierarchy"
    relation: "constrained_by"
  - ref: "principles/emission-attribution"
    relation: "applies_within"

conflicts_with:
  - ref: "methods/market-based"
    resolution: "两种方法均需报告，不可互相替代"
```

- [ ] **Step 2: Validate and commit**

Run: `python -c "import yaml; yaml.safe_load(open('specs/methods/location-based.yaml'))"`

```bash
git add specs/methods/location-based.yaml
git commit -m "feat: add location-based method spec"
```

---

## Task 8: Market-Based Method Spec

**Files:**
- Create: `specs/methods/market-based.yaml`

- [ ] **Step 1: Write market-based method spec**

```yaml
meta:
  id: "scope2/market-based"
  version: "1.0.0"
  source: "GHG Protocol Scope 2 Guidance"
  source_ref: "https://ghgprotocol.org/scope-2-guidance"
  layer: "schema"
  description: "基于市场法（Market-Based Method）"

citations:
  - id: "cit-mb-001"
    text: "The market-based method reflects emissions from electricity that companies have purposefully chosen (or their electricity provider has purposefully chosen on their behalf). It derives emission factors from contractual instruments."
    page: 31
    section: "Chapter 6: Market-Based Method"
    
  - id: "cit-mb-002"
    text: "The market-based Scope 2 figure shall be calculated using any supplier-specific emission factor from the companies' electricity suppliers, or from contractual instruments."
    page: 33
    section: "Chapter 6: Market-Based Method"

rules:
  - id: "rule-mb-001"
    name: "市场法适用条件"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "runtime_inference"
    condition: {"==": [{"var": "input.method"}, "market_based"]}
    assertion:
      "and": [
        {"!=": [{"var": "input.activity_data"}, null]},
        {">": [{"var": "input.activity_data"}, 0]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "市场法计算需要有效的活动数据"
    citation: "cit-mb-001"
    
  - id: "rule-mb-002"
    name: "合同工具优先"
    type: "recommendation"
    priority: "SHOULD"
    severity: "warning"
    layer: "schema"
    lifecycle: "runtime_inference"
    assertion:
      "or": [
        {"!=": [{"var": "input.emission_factor.type"}, "grid_average"]},
        {"!=": [{"var": "input.justifications.rule-mb-002"}, null]}
      ]
    on_fail: "require_justification"
    on_fail_message: "应优先使用合同工具（绿证、PPA）而非电网平均因子"
    citation: "cit-mb-002"
    
  - id: "rule-mb-003"
    name: "市场法计算公式"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "knowledge"
    statement: "排放量 = 活动数据(MWh) × 合同排放因子(tCO2/MWh)"
    citation: "cit-mb-002"

dependencies:
  - ref: "principles/data-quality-hierarchy"
    relation: "constrained_by"
  - ref: "principles/emission-attribution"
    relation: "applies_within"

conflicts_with:
  - ref: "methods/location-based"
    resolution: "两种方法均需报告，不可互相替代"
```

- [ ] **Step 2: Validate and commit**

Run: `python -c "import yaml; yaml.safe_load(open('specs/methods/market-based.yaml'))"`

```bash
git add specs/methods/market-based.yaml
git commit -m "feat: add market-based method spec"
```

---

## Task 9: Dual Reporting Spec

**Files:**
- Create: `specs/methods/dual-reporting.yaml`

- [ ] **Step 1: Write dual reporting spec**

```yaml
meta:
  id: "scope2/dual-reporting"
  version: "1.0.0"
  source: "GHG Protocol Scope 2 Guidance"
  source_ref: "https://ghgprotocol.org/scope-2-guidance"
  layer: "schema"
  description: "双重报告强制规则"

citations:
  - id: "cit-dr-001"
    text: "Companies operating in markets where product-specific instruments (e.g., EACs, PPAs) are available shall report both a location-based and a market-based Scope 2 figure."
    page: 34
    section: "Chapter 7: Dual Reporting"

rules:
  - id: "rule-dr-001"
    name: "双重报告触发"
    type: "constraint"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "pre_calculation"
    condition: {"==": [{"var": "context.region.has_market_instruments"}, true]}
    assertion:
      "and": [
        {"!=": [{"var": "input.location_based_input"}, null]},
        {"!=": [{"var": "input.market_based_input"}, null]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "该地区要求双重报告，但未提供两种方法的输入数据"
    citation: "cit-dr-001"
    
  - id: "rule-dr-002"
    name: "双重报告输出校验"
    type: "constraint"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "post_audit"
    condition:
      "and": [
        {"==": [{"var": "context.region.has_market_instruments"}, true]},
        {"==": [{"var": "computation.status"}, "completed"]}
      ]
    assertion:
      "and": [
        {"!=": [{"var": "output.location_based_result"}, null]},
        {"!=": [{"var": "output.market_based_result"}, null]},
        {"!=": [{"var": "output.methodology_explanation"}, null]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "双重报告输出不完整"
    citation: "cit-dr-001"

dependencies:
  - ref: "methods/location-based"
    relation: "applies_within"
  - ref: "methods/market-based"
    relation: "applies_within"

conflicts_with: []
```

- [ ] **Step 2: Validate and commit**

Run: `python -c "import yaml; yaml.safe_load(open('specs/methods/dual-reporting.yaml'))"`

```bash
git add specs/methods/dual-reporting.yaml
git commit -m "feat: add dual reporting spec"
```

---

## Task 10: Disclosure Requirements Spec

**Files:**
- Create: `specs/reporting/disclosure-requirements.yaml`

- [ ] **Step 1: Write disclosure requirements spec**

```yaml
meta:
  id: "scope2/disclosure-requirements"
  version: "1.0.0"
  source: "GHG Protocol Scope 2 Guidance"
  source_ref: "https://ghgprotocol.org/scope-2-guidance"
  layer: "schema"
  description: "报告披露要求"

citations:
  - id: "cit-dr-001"
    text: "Companies shall disclose the methodologies, assumptions, and data sources used to calculate Scope 2 emissions."
    page: 38
    section: "Chapter 8: Reporting Requirements"

rules:
  - id: "rule-disc-001"
    name: "必须披露字段"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "post_audit"
    assertion:
      "and": [
        {"!=": [{"var": "output.total_scope2_emissions"}, null]},
        {"!=": [{"var": "output.methodology"}, null]},
        {"!=": [{"var": "output.emission_factor_source"}, null]},
        {"!=": [{"var": "output.reporting_period"}, null]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "报告缺少必要披露字段"
    citation: "cit-dr-001"
    
  - id: "rule-disc-002"
    name: "双重报告披露"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "post_audit"
    condition: {"==": [{"var": "context.region.has_market_instruments"}, true]}
    assertion:
      "and": [
        {"!=": [{"var": "output.location_based_emissions"}, null]},
        {"!=": [{"var": "output.market_based_emissions"}, null]},
        {"!=": [{"var": "output.methodology_explanation"}, null]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "双重报告必须包含两种方法的排放量和方法论说明"
    citation: "cit-dr-001"
    
  - id: "rule-disc-003"
    name: "数据质量披露"
    type: "recommendation"
    priority: "SHOULD"
    severity: "warning"
    layer: "schema"
    lifecycle: "post_audit"
    assertion:
      "or": [
        {"!=": [{"var": "output.data_quality_assessment"}, null]},
        {"!=": [{"var": "input.justifications.rule-disc-003"}, null]}
      ]
    on_fail: "require_justification"
    on_fail_message: "建议披露数据质量评估"
    citation: "cit-dr-001"

dependencies:
  - ref: "methods/dual-reporting"
    relation: "constrained_by"

conflicts_with: []
```

- [ ] **Step 2: Validate and commit**

Run: `python -c "import yaml; yaml.safe_load(open('specs/reporting/disclosure-requirements.yaml'))"`

```bash
git add specs/reporting/disclosure-requirements.yaml
git commit -m "feat: add disclosure requirements spec"
```

---

## Task 11: Prohibitions Spec

**Files:**
- Create: `specs/constraints/prohibitions.yaml`

- [ ] **Step 1: Write prohibitions spec header**

```yaml
meta:
  id: "scope2/prohibitions"
  version: "1.0.0"
  source: "GHG Protocol Scope 2 Guidance"
  source_ref: "https://ghgprotocol.org/scope-2-guidance"
  layer: "hybrid"
  description: "核算过程中绝对禁止的行为"

citations:
  - id: "cit-pr-001"
    text: "Companies shall not double-count emissions between Scope 1 and Scope 2."
    page: 25
    section: "Chapter 4: Setting Operational Boundaries"
    
  - id: "cit-pr-002"
    text: "Companies should disclose any emission sources excluded from the inventory and the reasons for exclusion."
    page: 26
    section: "Chapter 4: Setting Operational Boundaries"
    
  - id: "cit-pr-003"
    text: "If a company uses both location-based and market-based methods, it shall clearly explain the methodology used."
    page: 34
    section: "Chapter 7: Dual Reporting"
    
  - id: "cit-pr-004"
    text: "When measured data is available, companies should prioritize it over default emission factors."
    page: 35
    section: "Chapter 6: Data Quality"
    
  - id: "cit-pr-005"
    text: "Emission factors should correspond to the same time period as the activity data. When current year factors are unavailable, companies may use the most recent available factors with appropriate disclosure."
    page: 36
    section: "Chapter 6: Data Quality"
```

- [ ] **Step 2: Add proh-001 (double counting)**

Append to `specs/constraints/prohibitions.yaml`:

```yaml

prohibitions:
  - id: "proh-001"
    name: "禁止双重计算"
    priority: "MUST"
    severity: "fatal"
    layer: "hybrid"
    lifecycle: "pre_calculation"
    assertion:
      "none": [
        {"var": "input.scope2_emission_sources"},
        {"in": [{"var": "id"}, {"var": "input.scope1_emission_sources.id"}]}
      ]
    computation:
      function: "calc.boundary_overlap_check"
      params:
        scope1_sources: {"var": "input.scope1_emission_sources"}
        scope2_sources: {"var": "input.scope2_emission_sources"}
        energy_flows: {"var": "input.energy_flow_graph"}
        chp_assets: {"var": "input.chp_assets"}
    post_computation_assertion:
      "and": [
        {"==": [{"var": "computation.result.overlap_detected"}, false]},
        {"==": [{"var": "computation.result.boundary_violations"}, []]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "检测到Scope 1与Scope 2存在能源边界重叠或ID重复，构成双重计算"
    citation: "cit-pr-001"
```

- [ ] **Step 3: Add proh-002 through proh-006**

Append to `specs/constraints/prohibitions.yaml`:

```yaml

  - id: "proh-002"
    name: "排放源完整性建议"
    type: "recommendation"
    priority: "SHOULD"
    severity: "info"
    layer: "knowledge"
    statement: "建议纳入所有已识别的排放源"
    citation: "cit-pr-002"

  - id: "proh-003"
    name: "排除披露强制"
    type: "constraint"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "pre_calculation"
    condition: {"!=": [{"var": "input.excluded_emission_sources"}, null]}
    assertion:
      "all": [
        {"var": "input.excluded_emission_sources"},
        {
          "and": [
            {"!=": [{"var": "exclusion_reason"}, null]},
            {"==": [{"var": "disclosed_in_report"}, true]}
          ]
        }
      ]
    on_fail: "raise_fatal"
    on_fail_message: "存在排放源排除但未披露原因，违反GHG Protocol合规要求"
    citation: "cit-pr-002"

  - id: "proh-004"
    name: "方法混用声明"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "post_audit"
    condition:
      "and": [
        {"!=": [{"var": "output.location_based_result"}, null]},
        {"!=": [{"var": "output.market_based_result"}, null]}
      ]
    assertion:
      "and": [
        {"==": [{"var": "output.methodology_declaration"}, true]},
        {"!=": [{"var": "output.methodology_explanation"}, null]}
      ]
    on_fail: "raise_fatal"
    on_fail_message: "同时使用位置法和市场法但未声明方法论"
    citation: "cit-pr-003"

  - id: "proh-005"
    name: "缺省因子使用建议"
    type: "recommendation"
    priority: "SHOULD"
    severity: "warning"
    layer: "hybrid"
    lifecycle: "runtime_inference"
    condition:
      "and": [
        {"!=": [{"var": "input.measured_data"}, null]},
        {"==": [{"var": "input.emission_factor.type"}, "default"]}
      ]
    on_fail: "raise_warning"
    on_fail_message: "存在实测数据但使用了缺省排放因子"
    statement: "当有实测数据可用时，应优先使用实测数据"
    citation: "cit-pr-004"

  - id: "proh-006"
    name: "排放因子时效性"
    type: "requirement"
    priority: "SHOULD"
    severity: "warning"
    layer: "schema"
    lifecycle: "runtime_inference"
    condition: {"!=": [{"var": "input.activity_data.year"}, null]}
    assertion:
      "or": [
        {"==": [{"var": "input.emission_factor.year"}, {"var": "input.activity_data.year"}]},
        {
          "and": [
            {"==": [{"var": "input.emission_factor.is_latest_available"}, true]},
            {"!=": [{"var": "input.justifications.proh-006"}, null]}
          ]
        }
      ]
    on_fail: "require_justification"
    on_fail_message: "排放因子年份与活动数据年份不匹配。如使用滞后因子，必须披露原因。"
    fallback_trigger: "principles/data-quality-hierarchy/time_based_fallback"
    citation: "cit-pr-005"
```

- [ ] **Step 4: Validate and commit**

Run: `python -c "import yaml; yaml.safe_load(open('specs/constraints/prohibitions.yaml'))"`

```bash
git add specs/constraints/prohibitions.yaml
git commit -m "feat: add prohibitions spec with boundary check and justification support"
```

---

## Task 12: JSON Schema Files

**Files:**
- Create: `schemas/equity-share-input.json`
- Create: `schemas/equity-share-output.json`
- Create: `schemas/operational-control-input.json`
- Create: `schemas/operational-control-output.json`
- Create: `schemas/financial-control-input.json`
- Create: `schemas/financial-control-output.json`
- Create: `schemas/boundary-overlap-input.json`
- Create: `schemas/boundary-overlap-output.json`

- [ ] **Step 1: Create equity-share-input.json**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Equity Share Input",
  "description": "Input schema for equity share calculation",
  "type": "object",
  "required": ["subsidiaries", "ownership_data"],
  "properties": {
    "subsidiaries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name"],
        "properties": {
          "id": {"type": "string"},
          "name": {"type": "string"},
          "country": {"type": "string"}
        }
      }
    },
    "ownership_data": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["subsidiary_id", "ownership_percentage"],
        "properties": {
          "subsidiary_id": {"type": "string"},
          "ownership_percentage": {
            "type": "number",
            "minimum": 0,
            "maximum": 100
          }
        }
      }
    },
    "control_type": {
      "type": "string",
      "enum": ["financial_control", "operational_control", "equity_share"]
    }
  }
}
```

- [ ] **Step 2: Create equity-share-output.json**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Equity Share Output",
  "description": "Output schema for equity share calculation",
  "type": "object",
  "required": ["boundary_emissions", "controlled_entities"],
  "properties": {
    "boundary_emissions": {
      "type": "number",
      "description": "Total emissions within organizational boundary (tCO2e)"
    },
    "controlled_entities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "name": {"type": "string"},
          "ownership_percentage": {"type": "number"},
          "emissions_share": {"type": "number"}
        }
      }
    }
  }
}
```

- [ ] **Step 3: Create remaining schema files**

Create `schemas/operational-control-input.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Operational Control Input",
  "type": "object",
  "required": ["subsidiaries", "control_indicators"],
  "properties": {
    "subsidiaries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name"],
        "properties": {
          "id": {"type": "string"},
          "name": {"type": "string"}
        }
      }
    },
    "control_indicators": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["subsidiary_id", "has_operational_control"],
        "properties": {
          "subsidiary_id": {"type": "string"},
          "has_operational_control": {"type": "boolean"},
          "evidence": {"type": "string"}
        }
      }
    }
  }
}
```

Create `schemas/operational-control-output.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Operational Control Output",
  "type": "object",
  "required": ["controlled_entities"],
  "properties": {
    "controlled_entities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "name": {"type": "string"},
          "has_operational_control": {"type": "boolean"}
        }
      }
    }
  }
}
```

Create `schemas/financial-control-input.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Financial Control Input",
  "type": "object",
  "required": ["subsidiaries", "financial_data"],
  "properties": {
    "subsidiaries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name"],
        "properties": {
          "id": {"type": "string"},
          "name": {"type": "string"}
        }
      }
    },
    "financial_data": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["subsidiary_id", "has_financial_control"],
        "properties": {
          "subsidiary_id": {"type": "string"},
          "has_financial_control": {"type": "boolean"},
          "ownership_percentage": {"type": "number"}
        }
      }
    }
  }
}
```

Create `schemas/financial-control-output.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Financial Control Output",
  "type": "object",
  "required": ["consolidated_entities"],
  "properties": {
    "consolidated_entities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "name": {"type": "string"},
          "has_financial_control": {"type": "boolean"}
        }
      }
    }
  }
}
```

Create `schemas/boundary-overlap-input.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Boundary Overlap Input",
  "description": "Input schema for Scope 1/2 boundary overlap detection",
  "type": "object",
  "required": ["scope1_sources", "scope2_sources"],
  "properties": {
    "scope1_sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id"],
        "properties": {
          "id": {"type": "string"},
          "type": {"type": "string"},
          "description": {"type": "string"}
        }
      }
    },
    "scope2_sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id"],
        "properties": {
          "id": {"type": "string"},
          "type": {"type": "string"},
          "description": {"type": "string"}
        }
      }
    },
    "energy_flows": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source_id": {"type": "string"},
          "target_id": {"type": "string"},
          "flow_type": {"type": "string"}
        }
      }
    },
    "chp_assets": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "fuel_input": {"type": "number"},
          "electricity_output": {"type": "number"},
          "heat_output": {"type": "number"}
        }
      }
    }
  }
}
```

Create `schemas/boundary-overlap-output.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Boundary Overlap Output",
  "description": "Output schema for Scope 1/2 boundary overlap detection",
  "type": "object",
  "required": ["overlap_detected", "boundary_violations"],
  "properties": {
    "overlap_detected": {
      "type": "boolean",
      "description": "Whether any overlap was detected"
    },
    "boundary_violations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "scope1_source_id": {"type": "string"},
          "scope2_source_id": {"type": "string"},
          "violation_type": {
            "type": "string",
            "enum": ["id_duplicate", "energy_flow_overlap", "chp_boundary_issue"]
          },
          "description": {"type": "string"}
        }
      }
    }
  }
}
```

- [ ] **Step 4: Validate JSON Schema files**

Run: `python -c "import json; [json.load(open(f)) for f in ['schemas/equity-share-input.json', 'schemas/equity-share-output.json', 'schemas/operational-control-input.json', 'schemas/operational-control-output.json', 'schemas/financial-control-input.json', 'schemas/financial-control-output.json', 'schemas/boundary-overlap-input.json', 'schemas/boundary-overlap-output.json']]"`

Expected: No output (valid JSON)

- [ ] **Step 5: Commit**

```bash
git add schemas/
git commit -m "feat: add JSON Schema files for external functions"
```

---

## Task 13: Documentation

**Files:**
- Create: `docs/README.md`
- Create: `docs/methodology.md`
- Create: `docs/schema-spec.md`
- Create: `docs/agent-integration-guide.md`

- [ ] **Step 1: Create README.md**

```markdown
# GHG Protocol Scope 2 Carbon Accounting Spec

A machine-parseable YAML specification for GHG Protocol Scope 2 carbon accounting, designed to drive carbon accounting agents.

## Overview

This specification implements the GHG Protocol Corporate Standard for Scope 2 (Indirect Emissions from Purchased Electricity, Steam, Heat, and Cooling). It provides:

- **Deterministic rules** (Layer 1) using JsonLogic and External Functions
- **Knowledge base** (Layer 2) with citations and interpretation guidance
- **Fallback chains** for data quality hierarchy
- **Cross-method validation** for dual reporting compliance

## Structure

```
specs/
├── _meta.yaml              # Master configuration
├── principles/             # Core accounting principles
├── methods/                # Location-based and market-based methods
├── reporting/              # Disclosure requirements
└── constraints/            # Prohibitions and compliance rules

schemas/
└── *.json                  # JSON Schema for external functions
```

## Quick Start

1. Load `_meta.yaml` to get engine definitions and load order
2. Follow `load_order` to process files sequentially
3. Execute rules based on `lifecycle` stage
4. Use `fallback_chains` for emission factor selection
5. Run `cross_method_validation` in post-audit phase

## For Agent Developers

See [Agent Integration Guide](agent-integration-guide.md) for detailed integration instructions.

## License

[MIT License](../LICENSE)
```

- [ ] **Step 2: Create methodology.md**

```markdown
# Methodology

## Dual-Layer Architecture

### Layer 1: Schema Config (Deterministic)
- JsonLogic expressions for basic rules
- External Functions for complex topology
- Machine-executable without LLM

### Layer 2: Knowledge Base (Semantic)
- Citations from GHG Protocol
- Interpretation guidance for ambiguous cases
- Used by LLM when Schema layer is insufficient

## Dual-Engine Execution

### JsonLogic Engine
- Handles: null checks, type validation, comparisons, set operations
- 80% of all rules

### External Functions Engine
- Handles: organizational boundary, equity share, control methods
- 20% of rules requiring graph traversal

## Rule Lifecycle

1. **pre_calculation**: Input validation, boundary confirmation
2. **runtime_inference**: Method selection, factor selection
3. **post_audit**: Output validation, dual reporting check

## Fallback Chains

### Market-Based Chain
1. Contract/PPA → 2. REC → 3. Supplier → 4. Residual Mix → 5. Grid Average

### Location-Based Chain
1. Subnational → 2. National

### Time-Based Chain
1. Current Year → 2. Previous Year → 3. Latest Available

## Comply or Explain

Rules with `require_justification` action allow compliance through disclosure:
- Global justification: `input.justifications[rule_id]`
- Instance justification: `input.justifications["{rule_id}@{instance_path}"]`
```

- [ ] **Step 3: Create schema-spec.md**

```markdown
# Schema Specification

## Input Schema

### Context
- `region.country_code`: ISO 3166-1 alpha-2
- `region.subnational_code`: ISO 3166-2 (optional)
- `region.has_market_instruments`: boolean
- `region.grid_average_ef`: number (tCO2/MWh)
- `region.residual_mix_ef`: number (tCO2/MWh)
- `emission_factors.current_year`: number
- `emission_factors.previous_year`: number
- `emission_factors.latest_available`: number
- `emission_factors.latest_year`: integer

### Input
- `entity.name`: string
- `entity.reporting_year`: integer
- `entity.control_method`: enum
- `emission_sources[]`: array of emission sources
- `justifications`: object with rule_id keys

## Output Schema

- `total_scope2_emissions`: number
- `location_based_emissions`: number (if dual reporting)
- `market_based_emissions`: number (if dual reporting)
- `methodology`: string
- `emission_factor_source`: string
- `reporting_period`: string
- `data_quality_assessment`: object (optional)

## JsonLogic Expressions

Standard JsonLogic operators:
- `{"var": "path"}`: Variable access
- `{"==": [a, b]}`: Equality
- `{"!=": [a, b]}`: Inequality
- `{"and": [...]}`: Logical AND
- `{"or": [...]}`: Logical OR
- `{"all": [array, condition]}`: All elements match
- `{"none": [array, condition]}`: No elements match
```

- [ ] **Step 4: Create agent-integration-guide.md**

```markdown
# Agent Integration Guide

## Loading the Spec

```python
import yaml

# Load meta file
with open('specs/_meta.yaml') as f:
    meta = yaml.safe_load(f)

# Get load order
load_order = meta['load_order']

# Load files in order
specs = {}
for path in load_order:
    with open(f'specs/{path}.yaml') as f:
        specs[path] = yaml.safe_load(f)
```

## Executing Rules

### Lifecycle-Based Execution

```python
# Group rules by lifecycle
rules_by_lifecycle = {
    'pre_calculation': [],
    'runtime_inference': [],
    'post_audit': []
}

for spec in specs.values():
    for rule in spec.get('rules', []):
        lifecycle = rule.get('lifecycle', 'runtime_inference')
        rules_by_lifecycle[lifecycle].append(rule)

# Execute in order
for lifecycle in ['pre_calculation', 'runtime_inference', 'post_audit']:
    for rule in rules_by_lifecycle[lifecycle]:
        execute_rule(rule, context, input_data)
```

### JsonLogic Evaluation

```python
from jsonlogic import jsonlogic

def evaluate_condition(rule, data):
    condition = rule.get('condition')
    if condition is None:
        return True
    return jsonlogic(condition, data)

def evaluate_assertion(rule, data):
    assertion = rule.get('assertion')
    if assertion is None:
        return True
    return jsonlogic(assertion, data)
```

### Handling on_fail Actions

```python
def handle_on_fail(rule, result, input_data):
    on_fail = rule.get('on_fail')
    
    if on_fail == 'raise_fatal':
        raise ComplianceError(rule['on_fail_message'])
    
    elif on_fail == 'raise_warning':
        log_warning(rule['on_fail_message'])
    
    elif on_fail == 'require_justification':
        rule_id = rule['id']
        justification = get_justification(rule_id, input_data)
        if justification:
            log_warning(f"{rule['on_fail_message']} (justified: {justification})")
        else:
            raise ComplianceError(rule['on_fail_message'])
    
    elif on_fail == 'mark_unavailable':
        set_state(rule.get('set_state'))
        log_fatal(rule['on_fail_message'])
```

## Fallback Chain Execution

```python
def execute_fallback_chain(chain, context, input_data):
    for level in chain['chain']:
        condition = level['condition']
        if jsonlogic(condition, {'context': context, 'input': input_data}):
            # on_match
            action = level['on_match']['action']
            if action == 'use_value':
                return get_value(level['data_type'])
            elif action == 'use_value_with_warning':
                log_warning(level['on_match']['message'])
                return get_value(level['data_type'])
        else:
            # on_null
            action = level['on_null']['action']
            if action == 'proceed_to_next':
                continue
            elif action == 'raise_fatal':
                raise ComplianceError(level['on_null']['message'])
            elif action == 'mark_unavailable':
                set_state(level['on_null'].get('set_state'))
                return None
    
    raise ComplianceError("All fallback levels exhausted")
```

## External Function Calls

```python
def call_external_function(function_id, params, schemas):
    # Load input schema
    input_schema = load_schema(schemas[function_id]['input_schema'])
    
    # Validate params
    validate(params, input_schema)
    
    # Call function (implement based on your runtime)
    result = runtime.call(function_id, params)
    
    # Validate output
    output_schema = load_schema(schemas[function_id]['output_schema'])
    validate(result, output_schema)
    
    return result
```
```

- [ ] **Step 5: Commit documentation**

```bash
git add docs/
git commit -m "docs: add README, methodology, schema spec, and agent guide"
```

---

## Task 14: Example Usage

**Files:**
- Create: `examples/sample-usage.yaml`

- [ ] **Step 1: Create sample usage file**

```yaml
# Sample Usage: Manufacturing Company Scope 2 Calculation
# This example demonstrates how to use the spec for a typical manufacturing company

context:
  region:
    country_code: "CN"
    subnational_code: "CN-GD"
    has_market_instruments: true
    grid_average_ef: 0.5810
    residual_mix_ef: null
  emission_factors:
    current_year: 0.5703
    previous_year: 0.5810
    latest_available: 0.5810
    latest_year: 2025

input:
  entity:
    name: "Example Manufacturing Co., Ltd."
    reporting_year: 2026
    control_method: "operational_control"
  
  subsidiaries:
    - id: "sub-001"
      name: "Guangzhou Factory"
      country: "CN"
    - id: "sub-002"
      name: "Shenzhen Factory"
      country: "CN"
  
  ownership_structure:
    - subsidiary_id: "sub-001"
      ownership_percentage: 100
    - subsidiary_id: "sub-002"
      ownership_percentage: 80
  
  control_indicators:
    - subsidiary_id: "sub-001"
      has_operational_control: true
      evidence: "Full management control"
    - subsidiary_id: "sub-002"
      has_operational_control: true
      evidence: "Majority board control"
  
  emission_sources:
    - id: "src-001"
      type: "electricity"
      activity_data: 10000
      activity_data_unit: "MWh"
      emission_factor:
        value: 0.5703
        year: 2025
        source: "Guangdong Provincial Grid"
        type: "grid_average"
        is_latest_available: true
  
  location_based_input:
    activity_data: 10000
    emission_factor_source: "Guangdong Provincial Grid"
  
  market_based_input:
    activity_data: 10000
    contract_ef: null
    rec_ef: null
    supplier_ef: null
  
  assumptions: "Using provincial grid average factor as no specific contracts available"
  methodology_rationale: "Location-based method using latest available provincial factor"
  data_sources: "Guangdong Provincial Grid Emission Factor 2025"
  
  justifications:
    "proh-006": "2026年官方因子尚未发布，使用2025年最新可用因子"

# Expected output structure
expected_output:
  total_scope2_emissions: 5703
  location_based_emissions: 5703
  market_based_emissions: 5703
  methodology: "location_based"
  emission_factor_source: "Guangdong Provincial Grid 2025"
  reporting_period: "2026-01-01 to 2026-12-31"
```

- [ ] **Step 2: Validate and commit**

Run: `python -c "import yaml; yaml.safe_load(open('examples/sample-usage.yaml'))"`

```bash
git add examples/sample-usage.yaml
git commit -m "docs: add sample usage example"
```

---

## Task 15: Final Validation and Cleanup

- [ ] **Step 1: Validate all YAML files**

Run: `find specs -name "*.yaml" -exec python -c "import yaml; yaml.safe_load(open('{}'))" \;`

Expected: No errors

- [ ] **Step 2: Validate all JSON files**

Run: `find schemas -name "*.json" -exec python -c "import json; json.load(open('{}'))" \;`

Expected: No errors

- [ ] **Step 3: Verify file structure**

Run: `find specs schemas docs examples -type f | sort`

Expected:
```
docs/README.md
docs/agent-integration-guide.md
docs/methodology.md
docs/schema-spec.md
examples/sample-usage.yaml
schemas/boundary-overlap-input.json
schemas/boundary-overlap-output.json
schemas/equity-share-input.json
schemas/equity-share-output.json
schemas/financial-control-input.json
schemas/financial-control-output.json
schemas/operational-control-input.json
schemas/operational-control-output.json
specs/_meta.yaml
specs/constraints/prohibitions.yaml
specs/methods/dual-reporting.yaml
specs/methods/location-based.yaml
specs/methods/market-based.yaml
specs/principles/data-quality-hierarchy.yaml
specs/principles/emission-attribution.yaml
specs/principles/operational-boundary.yaml
specs/principles/organizational-boundary.yaml
specs/reporting/disclosure-requirements.yaml
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final validation and cleanup for v1.0.0 release"
```

---

## Self-Review Checklist

- [ ] All spec sections from design doc have corresponding tasks
- [ ] No placeholders (TBD, TODO, implement later)
- [ ] All YAML files have valid syntax
- [ ] All JSON Schema files have valid syntax
- [ ] Type consistency across files (e.g., rule IDs, function names)
- [ ] All citations reference valid source documents
- [ ] All JsonLogic expressions are syntactically correct
- [ ] All External Functions have input/output schemas
- [ ] Fallback chains have complete lifecycle hooks
- [ ] Cross-method validation covers all edge cases
- [ ] Documentation covers all major concepts
- [ ] Example demonstrates typical usage
