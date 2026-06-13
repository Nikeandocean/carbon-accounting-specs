# GHG Protocol Scope 2 Spec 设计文档

**日期**: 2026-06-13
**版本**: 1.3.0
**状态**: 深度压力测试通过（含边界微调），待实现

---

## 1. 项目目标

创建可驱动碳核算Agent的spec文档，将GHG Protocol Scope 2规则转化为机器可解析的结构化规范。

**产出物**: Spec文档本身（非Agent实现），发布至GitHub供任何agent框架消费。

**核心价值**: 让碳核算过程从"黑箱"变为"有据可查"——每条规则可追溯，每步计算可审计。

---

## 2. 架构设计：双层分离 + 双引擎

### 2.1 分层原则

```
Layer 1: Schema Config（确定性层）
├── 条件路由：condition / assertion
├── 数据回退链：fallback_chains
├── 表达式语言：JsonLogic（基础）+ External Functions（复杂拓扑）
└── 机器可直接执行，不依赖LLM语义理解

Layer 2: Knowledge Base（语义层）
├── 原文引用：citations
├── 原则解释：statement
├── 歧义裁决指南：interpretation_guidance
└── LLM用于处理Schema层无法覆盖的模糊地带
```

### 2.2 双引擎架构

| 引擎 | 适用范围 | 优势 |
|------|---------|------|
| **JsonLogic** | 基础规则：非空校验、类型检查、简单比较、集合操作 | 轻量、跨语言、所有语言都有库 |
| **External Functions** | 复杂拓扑：组织边界、股权穿透、控制权计算 | 表达力强，可处理图状结构 |

**选型理由**：JsonLogic处理80%的基础规则，External Functions处理20%的复杂拓扑逻辑，避免JsonLogic在复杂场景下的"表达力黑洞"。

### 2.3 表达式引擎注册

```yaml
# _meta.yaml 中的引擎定义
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

---

## 3. 范围与约束

| 维度 | 决策 |
|------|------|
| 合规标准 | GHG Protocol Corporate Standard |
| 排放范围 | Scope 2（外购电力、蒸汽、热力、制冷） |
| Spec格式 | YAML（JsonLogic表达式 + External Functions调用） |
| 详细程度 | 规则层（原则+方法），不含具体排放因子 |
| 适用实体 | 企业、组织、政府机构 |
| 地理范围 | 全球 |

---

## 4. 目录结构

```
specs/
├── _meta.yaml                      # 元数据、引擎定义、输入Schema、冲突策略
├── principles/
│   ├── organizational-boundary.yaml # 含External Functions调用
│   ├── operational-boundary.yaml
│   ├── data-quality-hierarchy.yaml  # 含fallback_chains + 横向联动
│   └── emission-attribution.yaml
├── methods/
│   ├── location-based.yaml
│   ├── market-based.yaml
│   └── dual-reporting.yaml          # 含生命周期分层
├── reporting/
│   └── disclosure-requirements.yaml
└── constraints/
    └── prohibitions.yaml            # 含require_justification动作
```

**命名规则**:
- 文件名: kebab-case，英文
- 目录名: 功能分组，复数形式
- `_meta.yaml`: 下划线前缀表示根级元文件

---

## 5. 文件内部结构（Production-Ready Skeleton）

```yaml
meta:
  id: "scope2/<file-name>"
  version: "1.0.0"
  source: "<标准名称>"
  source_ref: "<标准URL>"
  layer: "schema | knowledge | hybrid"

citations:
  - id: "cit-xxx"
    text: "<原文段落>"
    page: <页码>
    section: "<章节>"

rules:
  - id: "rule-xxx"
    name: "<规则名称>"
    type: "constraint | requirement | recommendation"
    priority: "MUST | SHOULD | MAY"
    severity: "fatal | warning | info"
    layer: "schema | knowledge"
    lifecycle: "pre_calculation | runtime_inference | post_audit"
    
    # Schema层：JsonLogic表达式
    condition: <JsonLogic表达式或null>
    assertion: <JsonLogic表达式或null>
    on_fail: "raise_fatal | raise_warning | log_info | require_justification"
    on_fail_message: "<失败提示>"
    
    # 复杂拓扑：External Function调用（可选）
    computation:
      function: "<函数ID>"
      params: <参数映射>
    
    # Knowledge层：自然语言（仅layer=knowledge或hybrid时使用）
    statement: "<自然语言描述>"
    interpretation_guidance: "<歧义裁决指南>"
    citation: "<引用ID>"
    
    # 冲突声明（可选）
    overrides:
      - ref: "<被覆盖规则ID>"
        reason: "<覆盖理由>"

fallback_chains:
  - name: "<回退链名称>"
    description: "<链用途说明>"
    chain:
      - level: <优先级数字>
        name: "<数据层级名称>"
        data_type: "<数据类型标识>"
        condition: <JsonLogic表达式>
        on_match:
          action: "use_value | use_value_with_warning"
          log_level: "info | warning"
          message: "<成功消息>"
          require_disclosure: <boolean>
          disclosure_key: "<关联的规则ID>"
        on_null:
          action: "proceed_to_next | raise_fatal | use_default"
          message: "<失败消息>"
          default_value: <仅当action=use_default时>

cross_method_validation:
  - id: "<联动校验规则ID>"
    name: "<规则名称>"
    priority: "MUST | SHOULD"
    severity: "fatal | warning"
    layer: "schema"
    condition: <JsonLogic表达式>
    assertion: <JsonLogic表达式>
    on_fail: "raise_fatal | require_justification"
    on_fail_message: "<失败提示>"

dependencies:
  - ref: "<文件路径>"
    relation: "applies_within | constrained_by | extends"

conflicts_with:
  - ref: "<文件路径>"
    resolution: "<冲突解决策略>"
```

---

## 6. 元文件设计

`_meta.yaml` 定义整个spec集合的"宪法序言":

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

---

## 7. 规则分类矩阵

| Priority | Violation Impact | Agent Action | 适用场景 |
|----------|-----------------|--------------|----------|
| **MUST** | Fatal | 终止计算 | 规则断言失败 = 合规不可行 |
| **MUST** | Require Justification | 检查解释→降级或终止 | Comply or Explain场景 |
| **SHOULD** | Warning | 继续计算+审计日志 | 建议性规则，偏离需记录 |
| **MAY** | Info | 记录日志 | 可选优化 |

**require_justification动作逻辑**：
```
if input.justifications[rule_id] exists AND not empty:
    severity → warning
    log justification
    continue
else:
    severity → fatal
    terminate
```

---

## 8. 规则生命周期分层

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent执行流程                            │
├─────────────────────────────────────────────────────────────┤
│  1. 加载阶段                                                │
│     → 解析所有规则，按lifecycle分类                          │
│                                                             │
│  2. pre_calculation阶段                                     │
│     → 执行所有lifecycle="pre_calculation"的规则              │
│     → 校验输入数据完整性                                     │
│     → 确认组织边界、运营边界                                 │
│                                                             │
│  3. runtime_inference阶段                                   │
│     → 执行计算，触发fallback_chains                          │
│     → 执行lifecycle="runtime_inference"的规则                │
│     → 动态选择方法和因子                                     │
│                                                             │
│  4. post_audit阶段                                          │
│     → 执行所有lifecycle="post_audit"的规则                   │
│     → 校验输出完整性                                         │
│     → 执行cross_method_validation                            │
│     → 生成审计日志                                           │
│                                                             │
│  5. 输出阶段                                                │
│     → 附带所有source_ref和citation                           │
│     → 输出所有warning和justification                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. 禁止清单设计

`constraints/prohibitions.yaml`:

```yaml
prohibitions:
  - id: "proh-001"
    name: "禁止双重计算"
    priority: "MUST"
    severity: "fatal"
    layer: "hybrid"
    lifecycle: "pre_calculation"
    # JsonLogic做基础ID检查
    assertion:
      "none": [
        {"var": "input.scope2_emission_sources"},
        {"in": [{"var": "id"}, {"var": "input.scope1_emission_sources.id"}]}
      ]
    # External Function做能源边界拓扑交叉检测
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
    citation: "GHG Protocol Scope 2 Guidance, Chapter 5"

  - id: "proh-002"
    name: "排放源完整性建议"
    type: "recommendation"
    priority: "SHOULD"
    severity: "info"
    layer: "knowledge"
    statement: "建议纳入所有已识别的排放源"
    citation: "GHG Protocol Corporate Standard, Chapter 4"

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
    citation: "GHG Protocol Corporate Standard, Chapter 4"

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
    citation: "GHG Protocol Scope 2 Guidance, Chapter 7"

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
    citation: "GHG Protocol Scope 2 Guidance, Chapter 6"

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
    citation: "GHG Protocol Scope 2 Guidance, Chapter 6"
```

---

## 10. 数据回退链设计

`principles/data-quality-hierarchy.yaml`:

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
          # 不直接raise_fatal，由cross_method_validation在post_audit阶段统一裁决

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
```

---

## 11. 双重报告强制

`methods/dual-reporting.yaml`:

```yaml
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
    citation: "GHG Protocol Scope 2 Guidance, Chapter 7"
    
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
    citation: "GHG Protocol Scope 2 Guidance, Chapter 7"
```

---

## 12. 组织边界计算（External Functions示例）

`principles/organizational-boundary.yaml`:

```yaml
rules:
  - id: "rule-ob-001"
    name: "组织边界核算"
    type: "requirement"
    priority: "MUST"
    severity: "fatal"
    layer: "schema"
    lifecycle: "pre_calculation"
    
    # 简单条件用JsonLogic
    condition: {"!=": [{"var": "input.subsidiaries"}, null]}
    
    # 复杂计算调用External Function
    computation:
      function: "calc.equity_share"
      params:
        subsidiaries: {"var": "input.subsidiaries"}
        ownership_data: {"var": "input.ownership_structure"}
        control_type: {"var": "input.control_method"}
    
    # 断言仍用JsonLogic校验结果
    assertion: {"!=": [{"var": "computation.result.boundary_emissions"}, null]}
    on_fail: "raise_fatal"
    on_fail_message: "组织边界计算失败，无法确定合并范围"
    citation: "GHG Protocol Corporate Standard, Chapter 3"
    
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
    citation: "GHG Protocol Corporate Standard, Chapter 3"
```

---

## 13. Agent消费流程

```
1. 加载阶段
   → 解析_meta.yaml，获取引擎定义、生命周期分层、输入Schema
   → 按load_order加载所有文件
   → 解析所有JsonLogic表达式为可执行对象
   → 注册External Functions
   → 按lifecycle分类规则

2. pre_calculation阶段
   → 执行所有lifecycle="pre_calculation"的规则
   → 校验输入数据是否符合input_schema
   → 执行组织边界计算（External Functions）
   → 确认运营边界
   → 检查禁止清单中的前置规则

3. runtime_inference阶段
   → 执行计算
   → 触发fallback_chains获取排放因子
   → 执行time_based_fallback处理时效性问题
   → 执行lifecycle="runtime_inference"的规则
   → 动态选择方法和因子

4. post_audit阶段
   → 执行所有lifecycle="post_audit"的规则
   → 校验输出完整性
   → 执行cross_method_validation
   → 检查双重报告完整性
   → 处理require_justification动作
   → 生成审计日志

5. 输出阶段
   → 附带所有source_ref和citation
   → 输出所有warning和justification
   → 输出审计日志
```

---

## 14. 发布策略

```
GitHub仓库结构：
carbon-accounting-specs/
├── README.md
├── LICENSE
├── specs/
│   └── scope2/
│       ├── _meta.yaml
│       ├── principles/
│       ├── methods/
│       ├── reporting/
│       └── constraints/
├── schemas/
│   ├── equity-share-input.json
│   ├── equity-share-output.json
│   ├── operational-control-input.json
│   ├── operational-control-output.json
│   ├── financial-control-input.json
│   ├── financial-control-output.json
│   ├── boundary-overlap-input.json
│   └── boundary-overlap-output.json
├── docs/
│   ├── methodology.md
│   ├── schema-spec.md
│   └── agent-integration-guide.md
├── examples/
│   └── sample-usage.yaml
└── engines/
    ├── python/
    └── jsonschema/
```

---

## 15. 未来扩展路径

```
v1.0: Scope 2 (当前)
  ↓
v2.0: + Scope 1 (直接排放)
  ↓
v3.0: + Scope 3 (价值链排放)
  ↓
v4.0: + 行业细分规则（电力、钢铁、化工等）
  ↓
v5.0: + EU CBAM、中国碳市场等特定合规要求
```

---

## 16. 设计原则

1. **可追溯性**: 每条规则必须有`source_ref`，指向原文出处
2. **可审计性**: agent的每步决策必须可回溯到具体规则
3. **机器可执行**: Layer 1使用JsonLogic + External Functions，无需LLM语义理解
4. **模块化**: 每个文件单一职责，可独立更新
5. **渐进式**: 从Scope 2开始，逐步扩展到Scope 1/3
6. **中立性**: Spec不绑定特定agent框架，保持通用性
7. **MUST的二元性**: MUST规则失败必须终止计算，require_justification除外
8. **生命周期分层**: 规则按pre_calculation/runtime_inference/post_audit分阶段执行
9. **本地优先**: 冲突解决采用local_overrides_global策略
10. **Comply or Explain**: 通过require_justification支持弹性合规
11. **实例级隔离**: justifications支持全局级和实例级（per emission source）两种粒度，避免单条解释豁免所有实例
12. **延迟熔断**: 回退链末端不直接raise_fatal，而是标记状态，由post_audit阶段的cross_method_validation统一裁决
13. **边界拓扑检测**: 涉及能源边界交叉的双重计算检测，必须调用external_functions进行图拓扑验证，JsonLogic集合操作不足以覆盖
