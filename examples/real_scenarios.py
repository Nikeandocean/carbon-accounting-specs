#!/usr/bin/env python3
"""
GHG Protocol Scope 2 真实场景测试

10 个真实企业场景，覆盖 spec 规则。
规则分三类：
  - schema层: assertion 检查 input/context/output 字段，可直接验证
  - 需外部函数: assertion 检查 computation.result.*，需运行 calc.* 函数
  - 知识层: layer=knowledge，仅参考不执行
"""

import yaml
import sys
import io
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================================
# JsonLogic
# ============================================================

def jsonlogic(data, rules):
    if not isinstance(rules, dict):
        return rules
    for op, args in rules.items():
        if op == "var":
            return get_var(data, args)
        elif op == "==":
            return jsonlogic(data, args[0]) == jsonlogic(data, args[1])
        elif op == "!=":
            l, r = jsonlogic(data, args[0]), jsonlogic(data, args[1])
            if l is None and r is None: return False
            if l is None or r is None: return True
            return l != r
        elif op == ">":
            l, r = jsonlogic(data, args[0]), jsonlogic(data, args[1])
            if l is None or r is None: return False
            return l > r
        elif op == "<":
            l, r = jsonlogic(data, args[0]), jsonlogic(data, args[1])
            if l is None or r is None: return False
            return l < r
        elif op == ">=":
            l, r = jsonlogic(data, args[0]), jsonlogic(data, args[1])
            if l is None or r is None: return False
            return l >= r
        elif op == "<=":
            l, r = jsonlogic(data, args[0]), jsonlogic(data, args[1])
            if l is None or r is None: return False
            return l <= r
        elif op == "and":
            return all(jsonlogic(data, a) for a in args)
        elif op == "or":
            return any(jsonlogic(data, a) for a in args)
        elif op == "not":
            return not jsonlogic(data, args)
        elif op == "in":
            return jsonlogic(data, args[0]) in jsonlogic(data, args[1])
        elif op == "all":
            arr = jsonlogic(data, args[0])
            if not isinstance(arr, list): return False
            return all(jsonlogic({**data, **item}, args[1]) for item in arr)
        elif op == "none":
            arr = jsonlogic(data, args[0])
            if not isinstance(arr, list): return True
            return not any(jsonlogic({**data, **item}, args[1]) for item in arr)
        elif op == "some":
            arr = jsonlogic(data, args[0])
            if not isinstance(arr, list): return False
            return any(jsonlogic({**data, **item}, args[1]) for item in arr)
        elif op == "+":
            vals = [jsonlogic(data, a) for a in args]
            if any(v is None for v in vals): return None
            return sum(vals)
        elif op == "-":
            return jsonlogic(data, args[0]) - jsonlogic(data, args[1])
        elif op == "*":
            return jsonlogic(data, args[0]) * jsonlogic(data, args[1])
        elif op == "/":
            return jsonlogic(data, args[0]) / jsonlogic(data, args[1])
    return rules


def get_var(data, path):
    if isinstance(path, str): keys = path.split(".")
    elif isinstance(path, list): keys = path
    else: return None
    current = data
    for key in keys:
        if isinstance(current, dict): current = current.get(key)
        elif isinstance(current, list):
            try: current = current[int(key)]
            except (ValueError, IndexError): return None
        else: return None
    return current


def load_spec(spec_dir: Path):
    meta_path = spec_dir / "_meta.yaml"
    with open(meta_path, encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    specs = {}
    for path in meta["load_order"]:
        fp = spec_dir / f"{path}.yaml"
        if fp.exists():
            with open(fp, encoding="utf-8") as f:
                specs[path] = yaml.safe_load(f)
    return meta, specs


def execute_rule(rule: Dict, data: Dict) -> tuple:
    if rule.get("layer") == "knowledge":
        return None, "knowledge"
    condition = rule.get("condition")
    if condition and not jsonlogic(data, condition):
        return None, "skip"
    assertion = rule.get("assertion")
    if assertion:
        passed = jsonlogic(data, assertion)
        if not passed and rule.get("on_fail") == "require_justification":
            justifications = data.get("input", {}).get("justifications", {})
            if rule.get("id") in justifications:
                return True, "justified"
        return passed, "PASS" if passed else f"FAIL: {rule.get('on_fail_message','')}"
    return None, "no_assertion"


@dataclass
class ScenarioResult:
    name: str
    passed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    unexpected: List[str] = field(default_factory=list)
    emissions: float = 0.0


def run_scenario(sc: Dict, specs: Dict, meta: Dict) -> ScenarioResult:
    data = sc["data"]
    result = ScenarioResult(name=sc["name"])
    for src in data.get("input", {}).get("emission_sources", []):
        result.emissions += src.get("activity_data", 0) * src.get("emission_factor", {}).get("value", 0)
    for src in data.get("input", {}).get("scope1_emission_sources", []):
        result.emissions += src.get("activity_data", 0) * src.get("emission_factor", {}).get("value", 0)
    result.emissions = round(result.emissions, 4)

    all_rules = [("global", r) for r in meta.get("global_rules", [])]
    for sp, spec in specs.items():
        for r in spec.get("rules", []):
            all_rules.append((sp, r))

    tested_rules = set()
    for _, rule in all_rules:
        rid = rule["id"]
        # 先在顶层执行
        passed, _ = execute_rule(rule, data)
        if passed is not None:
            tested_rules.add(rid)
            if passed: result.passed.append(rid)
            else: result.failed.append(rid)
        else:
            # 顶层跳过的规则，尝试逐源执行（针对 runtime_inference 规则）
            lifecycle = rule.get("lifecycle", "")
            if lifecycle == "runtime_inference":
                for src in data.get("input", {}).get("scope1_emission_sources", []):
                    src_data = {**data, "input": {**data["input"], **src}}
                    p, _ = execute_rule(rule, src_data)
                    if p is not None and rid not in tested_rules:
                        tested_rules.add(rid)
                        if p: result.passed.append(rid)
                        else: result.failed.append(rid)
            if rid not in tested_rules:
                result.skipped.append(rid)

    for rid in sc.get("expect_pass", []):
        if rid not in result.passed:
            result.unexpected.append(f"{rid} 应通过但{'失败' if rid in result.failed else '跳过'}")
    for rid in sc.get("expect_fail", []):
        if rid not in result.failed:
            result.unexpected.append(f"{rid} 应失败但{'通过' if rid in result.passed else '跳过'}")
    if sc.get("expect_emissions") is not None:
        if abs(result.emissions - sc["expect_emissions"]) > 0.01:
            result.unexpected.append(f"排放量预期 {sc['expect_emissions']}，实际 {result.emissions}")
    return result


# ============================================================
# 共用输出字段模板
# ============================================================

def make_output(base_year_method="market_based", **kwargs):
    """生成完整的 output 字段，满足所有 disclosure 规则"""
    out = {
        "total_scope2_emissions": None,
        "methodology": "GHG Protocol Scope 2",
        "emission_factor_source": "官方排放因子",
        "reporting_period": "2025年度",
        "location_based_emissions": None,
        "market_based_emissions": None,
        "methodology_explanation": None,
        "data_quality_assessment": None,
        "market_based": {"instrument_categories": [], "generation_technologies": []},
        "base_year": {"year": 2024, "method": base_year_method,
                      "recalculation_policy": "重大变更时重算",
                      "recalculation_triggers": ["边界变更", "方法变更"]},
        "reduction_target": None,
        "single_inventory_total": False,
    }
    out.update(kwargs)
    return out


# ============================================================
# 场景 1: 中国制造业双报告
# ============================================================

SCENARIO_1 = {
    "name": "中国制造业双报告",
    "desc": "华南汽车工厂 — 运营控制法、位置法+市场法双重报告、I-REC绿证",
    "data": {
        "input": {
            "entity": {"name": "华南汽车制造有限公司", "reporting_year": 2025},
            "control_method": "operational_control",
            "emission_sources": [
                {"id": "elec-grid-001", "type": "electricity", "activity_data": 50000,
                 "emission_factor": {"value": 0.5703, "year": 2025, "source": "生态环境部2025年区域电网排放因子", "type": "grid_average"}},
                {"id": "elec-rec-001", "type": "electricity", "activity_data": 20000,
                 "emission_factor": {"value": 0.0, "year": 2025, "source": "I-REC国际绿证", "type": "certificate",
                    "ghg_emission_rate_attribute": 0.0, "unique_claim": True, "retired_for_claims": True,
                    "vintage_match": True, "same_market": True, "claim_exclusively_transferred": True,
                    "certificates_retained": True, "based_on_delivered_electricity": True}},
                {"id": "steam-001", "type": "steam", "activity_data": 5000,
                 "emission_factor": {"value": 0.12, "year": 2025, "source": "工业园区蒸汽供应商", "type": "supplier",
                    "based_on_delivered_electricity": True}}
            ],
            "emission_factor": {"type": "grid_average"},  # 用于 cert 规则检查
            "method": "market_based",
            "assumptions": "使用广东省区域电网排放因子，绿证为I-REC国际证书",
            "methodology_rationale": "采用位置法和市场法双重报告，绿证覆盖26.7%用电量",
            "data_sources": "生态环境部2025年排放因子、I-REC注册系统",
            "location_based_input": {"activity_data": 75000},
            "market_based_input": {"activity_data": 75000},
            "justifications": {}
        },
        "output": make_output(
            total_scope2_emissions=29115.0,
            location_based_emissions=42772.5,
            market_based_emissions=29115.0,
            methodology_explanation="位置法使用电网平均因子，市场法使用I-REC绿证+电网因子",
            data_quality_assessment="数据质量良好",
            market_based={"instrument_categories": ["I-REC"], "generation_technologies": ["solar", "wind"]},
        ),
        "context": {"region": {"country_code": "CN", "subnational_code": "CN-GD",
                               "has_market_instruments": True, "grid_average_ef": 0.5703, "residual_mix_ef": 0.5500},
                    "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}}
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004", "global-005",
        "rule-op-001", "rule-op-002", "rule-op-003",
        "rule-lb-002", "rule-mb-001",
        "rule-dr-001", "rule-disc-001", "rule-disc-002", "rule-disc-003", "rule-disc-004",
        "rule-disc-005", "rule-disc-009", "rule-disc-010",
        "qc-001", "qc-002", "qc-003", "qc-004", "qc-005", "qc-006", "qc-007", "qc-009",
        "cert-002",
    ],
    "expect_fail": ["rule-mb-002"],  # 有 grid_average 源且无 justification
    "expect_emissions": 29115.0
}


# ============================================================
# 场景 2: 美国科技公司 PPA+REC
# ============================================================

SCENARIO_2 = {
    "name": "美国科技公司PPA+REC",
    "desc": "TechCorp数据中心 — 财务控制法、PPA+REC 100%可再生能源",
    "data": {
        "input": {
            "entity": {"name": "TechCorp Data Center", "reporting_year": 2025},
            "control_method": "financial_control",
            "emission_sources": [
                {"id": "elec-ppa-001", "type": "electricity", "activity_data": 80000,
                 "emission_factor": {"value": 0.0, "year": 2025, "source": "Virginia Solar PPA", "type": "contract",
                    "ghg_emission_rate_attribute": 0.0, "unique_claim": True, "retired_for_claims": True,
                    "vintage_match": True, "same_market": True, "claim_exclusively_transferred": True,
                    "certificates_retained": True, "based_on_delivered_electricity": True}},
                {"id": "elec-rec-001", "type": "electricity", "activity_data": 20000,
                 "emission_factor": {"value": 0.0, "year": 2025, "source": "PJM Green-e REC", "type": "certificate",
                    "ghg_emission_rate_attribute": 0.0, "unique_claim": True, "retired_for_claims": True,
                    "vintage_match": True, "same_market": True, "claim_exclusively_transferred": True,
                    "certificates_retained": True, "based_on_delivered_electricity": True}}
            ],
            "emission_factor": {"type": "contract"},
            "method": "market_based",
            "assumptions": "PPA + REC 实现 100% 可再生能源覆盖",
            "methodology_rationale": "通过长期PPA和Green-e认证REC实现零排放",
            "data_sources": "PJM-GATS注册系统、PPA合同",
            "location_based_input": {"activity_data": 100000},
            "market_based_input": {"activity_data": 100000},
            "justifications": {}
        },
        "output": make_output(
            total_scope2_emissions=0.0,  # global-005 要求 > 0，此场景预期失败
            location_based_emissions=38000.0,
            market_based_emissions=0.0,
            methodology_explanation="通过PPA和REC实现零排放",
            data_quality_assessment="数据质量优秀",
            market_based={"instrument_categories": ["PPA", "REC"], "generation_technologies": ["solar"]},
        ),
        "context": {"region": {"country_code": "US", "subnational_code": "US-VA",
                               "has_market_instruments": True, "grid_average_ef": 0.38, "residual_mix_ef": 0.36},
                    "emission_factors": {"current_year": 0.38, "previous_year": 0.39, "latest_available": 0.38, "latest_year": 2025}}
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004",
        "rule-op-001", "rule-op-002", "rule-op-003",
        "rule-lb-002", "rule-mb-001", "rule-mb-002",
        "rule-dr-001", "rule-disc-001", "rule-disc-002", "rule-disc-003", "rule-disc-004",
        "rule-disc-005", "rule-disc-009", "rule-disc-010",
        "qc-001", "qc-002", "qc-003", "qc-004", "qc-005", "qc-006", "qc-007", "qc-009",
        "cert-002",
    ],
    "expect_fail": ["global-005"],  # total_scope2_emissions == 0
    "expect_emissions": 0.0
}


# ============================================================
# 场景 3: 欧盟跨国集团 — 股权比例法
# ============================================================

SCENARIO_3 = {
    "name": "欧盟跨国集团",
    "desc": "EuroChem集团 — 股权比例法、德法双国运营、残余混合因子",
    "data": {
        "input": {
            "entity": {"name": "EuroChem Group AG", "reporting_year": 2025},
            "control_method": "equity_share",
            "emission_sources": [
                {"id": "elec-de-001", "type": "electricity", "activity_data": 30000,
                 "emission_factor": {"value": 0.380, "year": 2025, "source": "UBA Germany", "type": "grid_average",
                    "based_on_delivered_electricity": True}},
                {"id": "elec-fr-001", "type": "electricity", "activity_data": 20000,
                 "emission_factor": {"value": 0.055, "year": 2025, "source": "RTE France", "type": "grid_average",
                    "based_on_delivered_electricity": True}},
                {"id": "cooling-001", "type": "cooling", "activity_data": 2000,
                 "emission_factor": {"value": 0.03, "year": 2025, "source": "District cooling", "type": "supplier",
                    "based_on_delivered_electricity": True}}
            ],
            "emission_factor": {"type": "grid_average"},
            "method": "location_based",
            "assumptions": "股权比例法，法国子公司60%纳入合并范围",
            "methodology_rationale": "采用股权比例法合并，德法两国电网因子",
            "data_sources": "UBA、RTE官方排放因子",
            "location_based_input": {"activity_data": 52000},
            "market_based_input": {"activity_data": 52000},
            "justifications": {}
        },
        "output": make_output(
            base_year_method="location_based",
            total_scope2_emissions=12560.0,
            location_based_emissions=12560.0,
            market_based_emissions=12560.0,
            methodology_explanation="股权比例法合并德法两国",
            data_quality_assessment="数据质量良好",
        ),
        "context": {"region": {"country_code": "DE", "has_market_instruments": True,
                               "grid_average_ef": 0.380, "residual_mix_ef": 0.350},
                    "emission_factors": {"current_year": 0.380, "previous_year": 0.395, "latest_available": 0.380, "latest_year": 2025}}
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004", "global-005",
        "rule-op-001", "rule-op-002", "rule-op-003",
        "rule-lb-001", "rule-lb-002",
        "rule-dr-001", "rule-disc-001", "rule-disc-002", "rule-disc-003", "rule-disc-004",
        "rule-disc-005", "rule-disc-009", "rule-disc-010",
        "qc-006", "cert-002",
    ],
    "expect_fail": ["rule-mb-002"],
    "expect_emissions": 12560.0
}


# ============================================================
# 场景 4: 证书售出 — 风电场
# ============================================================

SCENARIO_4 = {
    "name": "证书售出场景",
    "desc": "北方风电场 — 自有发电证书售出、位置法+市场法使用电网因子",
    "data": {
        "input": {
            "entity": {"name": "北方风电有限公司", "reporting_year": 2025},
            "control_method": "operational_control",
            "emission_sources": [
                {"id": "wind-001", "type": "electricity", "activity_data": 10000,
                 "emission_factor": {"value": 0.5703, "year": 2025, "source": "电网平均因子（证书已售出）", "type": "grid_average",
                    "based_on_delivered_electricity": True}},
                {"id": "elec-purchase-001", "type": "electricity", "activity_data": 5000,
                 "emission_factor": {"value": 0.5703, "year": 2025, "source": "国家电网", "type": "grid_average",
                    "based_on_delivered_electricity": True}}
            ],
            "emission_factor": {"type": "grid_average", "source": "电网平均因子"},
            "method": "market_based",
            "generation_ownership": "owned_operated",
            "certificates_sold": True,
            "certificates_sold_from_owned_generation": True,
            "assumptions": "风电场REC证书已售出给第三方企业",
            "methodology_rationale": "证书售出后，自身只能使用电网平均因子",
            "data_sources": "国家电网排放因子",
            "location_based_input": {"activity_data": 15000},
            "market_based_input": {"activity_data": 15000},
            "justifications": {}
        },
        "output": make_output(
            total_scope2_emissions=8554.5,
            location_based_emissions=8554.5,
            market_based_emissions=8554.5,
            methodology_explanation="REC售出后市场法回退至电网平均",
            data_quality_assessment="数据质量良好",
            market_based={"instrument_categories": ["grid_average"], "generation_technologies": ["wind"]},
        ),
        "context": {"region": {"country_code": "CN", "has_market_instruments": True,
                               "grid_average_ef": 0.5703, "residual_mix_ef": 0.5500},
                    "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}}
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004", "global-005",
        "rule-op-001", "rule-op-002", "rule-op-003",
        "rule-lb-002", "rule-mb-001",
        "rule-dr-001", "rule-disc-001", "rule-disc-002", "rule-disc-003", "rule-disc-004",
        "rule-disc-005", "rule-disc-009", "rule-disc-010",
        "qc-001", "qc-002", "qc-003", "qc-004", "qc-005", "qc-006", "qc-007", "qc-009", "qc-010",
        "cert-002", "cert-004", "cert-008",
    ],
    "expect_fail": ["rule-mb-002"],
    "expect_emissions": 8554.5
}


# ============================================================
# 场景 5: 数据缺失回退
# ============================================================

SCENARIO_5 = {
    "name": "数据缺失回退",
    "desc": "西部矿业 — 当年因子缺失回退前一年、无市场化工具、Comply or Explain",
    "data": {
        "input": {
            "entity": {"name": "西部矿业加工厂", "reporting_year": 2025},
            "control_method": "operational_control",
            "emission_sources": [
                {"id": "elec-001", "type": "electricity", "activity_data": 8000,
                 "emission_factor": {"value": 0.5810, "year": 2024, "source": "2024年国家电网平均排放因子", "type": "grid_average",
                    "based_on_delivered_electricity": True}},
                {"id": "heat-001", "type": "heat", "activity_data": 1500,
                 "emission_factor": {"value": 0.15, "year": 2024, "source": "区域供热公司2024年数据", "type": "supplier",
                    "based_on_delivered_electricity": True}}
            ],
            "emission_factor": {"type": "grid_average"},
            "method": "location_based",
            "assumptions": "偏远地区，2025年排放因子尚未发布，使用2024年数据",
            "methodology_rationale": "该区域无市场化工具，仅使用位置法",
            "data_sources": "2024年国家电网排放因子、区域供热公司历史数据",
            "justifications": {
                "proh-006": "2025年官方排放因子尚未发布",
                "rule-lb-002": "该区域无区域电网因子，使用国家平均",
                "rule-disc-003": "偏远地区数据获取困难，将在后续补充",
                "rule-disc-008": "残余混合因子不可用",
                "qc-004": "无合同工具",
                "qc-008": "残余混合因子不可用"
            }
        },
        "output": make_output(
            base_year_method="location_based",
            total_scope2_emissions=4873.0,
            location_based_emissions=4873.0,
            methodology_explanation="该区域无市场化工具，仅使用位置法",
        ),
        "context": {"region": {"country_code": "CN", "subnational_code": "CN-XJ",
                               "has_market_instruments": False, "grid_average_ef": 0.5703, "residual_mix_ef": None},
                    "emission_factors": {"current_year": None, "previous_year": 0.5810, "latest_available": 0.5810, "latest_year": 2024}}
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004", "global-005",
        "rule-op-001", "rule-op-002", "rule-op-003",
        "rule-lb-001", "rule-lb-002",
        "rule-dr-003",
        "rule-disc-001", "rule-disc-003", "rule-disc-005", "rule-disc-008", "rule-disc-009", "rule-disc-010",
    ],
    "expect_fail": ["rule-mb-002"],
    "expect_emissions": 4873.0
}


# ============================================================
# 场景 6: 租赁资产 — 零售连锁
# ============================================================

SCENARIO_6 = {
    "name": "租赁资产",
    "desc": "全国连锁超市 — 150家租赁门店、运营控制权归承租方、绿证覆盖部分",
    "data": {
        "input": {
            "entity": {"name": "全国连锁超市有限公司", "reporting_year": 2025},
            "control_method": "operational_control",
            "leased_assets": [
                {"has_operational_control": True, "scope": "scope2", "exclusion_justification": None}
            ],
            "emission_sources": [
                {"id": "elec-stores-001", "type": "electricity", "activity_data": 25000,
                 "emission_factor": {"value": 0.5703, "year": 2025, "source": "国家电网平均排放因子", "type": "grid_average",
                    "based_on_delivered_electricity": True}},
                {"id": "elec-green-001", "type": "electricity", "activity_data": 5000,
                 "emission_factor": {"value": 0.0, "year": 2025, "source": "国内绿证", "type": "certificate",
                    "ghg_emission_rate_attribute": 0.0, "unique_claim": True, "retired_for_claims": True,
                    "vintage_match": True, "same_market": True, "claim_exclusively_transferred": True,
                    "certificates_retained": True, "based_on_delivered_electricity": True}},
                {"id": "heat-stores-001", "type": "heat", "activity_data": 3000,
                 "emission_factor": {"value": 0.12, "year": 2025, "source": "市政供暖", "type": "supplier",
                    "based_on_delivered_electricity": True}}
            ],
            "emission_factor": {"type": "grid_average"},
            "method": "market_based",
            "assumptions": "150家门店均为租赁物业，承租方拥有运营控制权",
            "methodology_rationale": "租赁资产默认承租方控制，纳入Scope 2",
            "data_sources": "国家电网排放因子、国内绿证交易平台、市政供暖公司",
            "location_based_input": {"activity_data": 33000},
            "market_based_input": {"activity_data": 33000},
            "justifications": {}
        },
        "output": make_output(
            total_scope2_emissions=14617.5,
            location_based_emissions=18817.5,
            market_based_emissions=14617.5,
            methodology_explanation="租赁资产默认承租方控制",
            data_quality_assessment="数据质量良好",
            market_based={"instrument_categories": ["绿证"], "generation_technologies": ["solar"]},
        ),
        "context": {"region": {"country_code": "CN", "has_market_instruments": True,
                               "grid_average_ef": 0.5703, "residual_mix_ef": 0.5500},
                    "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}}
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004", "global-005",
        "rule-ob-004", "rule-ob-005",
        "rule-op-001", "rule-op-002", "rule-op-003",
        "rule-lb-002", "rule-mb-001",
        "rule-dr-001", "rule-disc-001", "rule-disc-002", "rule-disc-003", "rule-disc-004",
        "rule-disc-005", "rule-disc-009", "rule-disc-010",
        "qc-001", "qc-002", "qc-003", "qc-004", "qc-005", "qc-006", "qc-007", "qc-009",
        "cert-002",
    ],
    "expect_fail": ["rule-mb-002"],
    "expect_emissions": 14617.5
}


# ============================================================
# 场景 7: CHP热电联产
# ============================================================

SCENARIO_7 = {
    "name": "CHP热电联产",
    "desc": "华东工业园区 — CHP热电联产、四种排放源、Scope 1/2边界重叠",
    "data": {
        "input": {
            "entity": {"name": "华东工业园区管理有限公司", "reporting_year": 2025},
            "control_method": "operational_control",
            "emission_sources": [
                {"id": "elec-grid-001", "type": "electricity", "activity_data": 15000,
                 "emission_factor": {"value": 0.5703, "year": 2025, "source": "国家电网", "type": "grid_average",
                    "based_on_delivered_electricity": True}},
                {"id": "steam-chp-001", "type": "steam", "activity_data": 8000,
                 "emission_factor": {"value": 0.10, "year": 2025, "source": "CHP系统蒸汽", "type": "supplier",
                    "based_on_delivered_electricity": True}},
                {"id": "heat-chp-001", "type": "heat", "activity_data": 4000,
                 "emission_factor": {"value": 0.08, "year": 2025, "source": "CHP系统热力", "type": "supplier",
                    "based_on_delivered_electricity": True}},
                {"id": "cooling-001", "type": "cooling", "activity_data": 1000,
                 "emission_factor": {"value": 0.04, "year": 2025, "source": "区域供冷系统", "type": "supplier",
                    "based_on_delivered_electricity": True}}
            ],
            "emission_factor": {"type": "grid_average"},
            "method": "market_based",
            "assumptions": "CHP系统同时产出电力和热力，存在Scope 1/2边界重叠",
            "methodology_rationale": "CHP蒸汽和热力的排放因子基于供应商数据",
            "data_sources": "国家电网、CHP系统运行数据、区域供冷公司",
            "location_based_input": {"activity_data": 28000},
            "market_based_input": {"activity_data": 28000},
            "justifications": {}
        },
        "output": make_output(
            total_scope2_emissions=9714.5,
            location_based_emissions=9714.5,
            market_based_emissions=9714.5,
            methodology_explanation="CHP蒸汽和热力排放因子基于供应商数据",
            data_quality_assessment="数据质量良好",
        ),
        "context": {"region": {"country_code": "CN", "has_market_instruments": True,
                               "grid_average_ef": 0.5703, "residual_mix_ef": 0.5500},
                    "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}}
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004", "global-005",
        "rule-op-001", "rule-op-002", "rule-op-003",
        "rule-lb-002", "rule-mb-001",
        "rule-dr-001", "rule-disc-001", "rule-disc-002", "rule-disc-003", "rule-disc-004",
        "rule-disc-005", "rule-disc-009", "rule-disc-010",
        "qc-006", "cert-002",
    ],
    "expect_fail": ["rule-mb-002"],
    "expect_emissions": 9714.5
}


# ============================================================
# 场景 8: 中国制造业 — 天然气锅炉 + 公司车队
# ============================================================

SCENARIO_8 = {
    "name": "中国制造业Scope1",
    "desc": "华南制造工厂 — 天然气锅炉固定燃烧 + 公司车队移动燃烧",
    "data": {
        "input": {
            "entity": {"name": "华南制造工厂", "reporting_year": 2025},
            "control_method": "operational_control",
            "scope1_emission_sources": [
                {"id": "boiler-001", "scope": "scope1", "type": "stationary_combustion",
                 "fuel_type": "natural_gas", "activity_data": 2000, "activity_unit": "tonnes",
                 "emission_factor": {"value": 2.0, "year": 2025, "source": "IPCC 2006", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"},
                {"id": "fleet-001", "scope": "scope1", "type": "mobile_combustion",
                 "fuel_type": "diesel", "activity_data": 50000, "activity_unit": "km",
                 "emission_factor": {"value": 0.0002, "year": 2025, "source": "IPCC 2006", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"}
            ],
            "emission_sources": [],
            "assumptions": "天然气锅炉和柴油车队排放",
            "methodology_rationale": "采用IPCC 2006排放因子",
            "data_sources": "IPCC 2006排放因子数据库",
            "justifications": {}
        },
        "output": {
            "total_scope1_emissions": 4010.0,
            "scope1_by_category": {
                "stationary_combustion": 4000.0,
                "mobile_combustion": 10.0
            }
        },
        "context": {
            "region": {"country_code": "CN"},
            "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}
        }
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004",
    ],
    "expect_fail": [],
    "expect_emissions": 4010.0
}


# ============================================================
# 场景 9: 化工厂 — 过程排放 + 冷媒泄漏
# ============================================================

SCENARIO_9 = {
    "name": "化工厂过程排放",
    "desc": "化工厂 — 水泥�ite过程排放 + HFC-134a冷媒泄漏逃逸排放",
    "data": {
        "input": {
            "entity": {"name": "东方化工有限公司", "reporting_year": 2025},
            "control_method": "operational_control",
            "scope1_emission_sources": [
                {"id": "process-001", "scope": "scope1", "type": "process",
                 "fuel_type": None, "activity_data": 10000, "activity_unit": "tonnes",
                 "emission_factor": {"value": 0.5, "year": 2025, "source": "IPCC 2006", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"},
                {"id": "hvac-001", "scope": "scope1", "type": "fugitive",
                 "fuel_type": None, "activity_data": 20, "activity_unit": "kg",
                 "emission_factor": {"value": 1.43, "year": 2025, "source": "IPCC AR5", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"}
            ],
            "emission_sources": [],
            "assumptions": "水泥窑过程排放和HFC-134a冷媒泄漏",
            "methodology_rationale": "过程排放基于产品产量，逃逸排放基于GWP=1430",
            "data_sources": "IPCC 2006、IPCC AR5 GWP值",
            "justifications": {}
        },
        "output": {
            "total_scope1_emissions": 5028.6,
            "scope1_by_category": {
                "process": 5000.0,
                "fugitive": 28.6
            }
        },
        "context": {
            "region": {"country_code": "CN"},
            "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}
        }
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004",
    ],
    "expect_fail": [],
    "expect_emissions": 5028.6
}


# ============================================================
# 场景 10: CHP热电联产 — Scope 1/2边界分配
# ============================================================

SCENARIO_10 = {
    "name": "CHP边界分配",
    "desc": "CHP热电联产设施 — 天然气燃烧分配Scope 1(热力)和Scope 2(电力)排放",
    "data": {
        "input": {
            "entity": {"name": "华东CHP能源有限公司", "reporting_year": 2025},
            "control_method": "operational_control",
            "scope1_emission_sources": [
                {"id": "chp-001", "scope": "scope1", "type": "stationary_combustion",
                 "fuel_type": "natural_gas", "activity_data": 3000, "activity_unit": "tonnes",
                 "emission_factor": {"value": 2.0, "year": 2025, "source": "IPCC 2006", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"},
                {"id": "boundary-check-001", "scope": "scope1", "type": "stationary_combustion",
                 "fuel_type": "natural_gas", "activity_data": 0, "activity_unit": "tonnes",
                 "emission_factor": {"value": 0, "year": 2025, "source": "CHP边界检查", "is_biomass": False},
                 "gwp_source": "IPCC_AR5",
                 "boundary_overlap_check": {"scope1_heat": 3000.0, "scope2_electricity": 3000.0, "total_fuel_emissions": 6000.0}}
            ],
            "emission_sources": [
                {"id": "elec-chp-001", "type": "electricity", "activity_data": 5000,
                 "emission_factor": {"value": 0.5703, "year": 2025, "source": "国家电网", "type": "grid_average",
                    "based_on_delivered_electricity": True}}
            ],
            "assumptions": "CHP系统同时产出电力和热力，存在Scope 1/2边界重叠",
            "methodology_rationale": "CHP排放按热电比分配至Scope 1和Scope 2",
            "data_sources": "IPCC 2006、CHP系统运行数据",
            "justifications": {}
        },
        "output": {
            "total_scope1_emissions": 6000.0,
            "total_scope2_emissions": 2851.5,
            "scope1_by_category": {
                "stationary_combustion": 6000.0
            }
        },
        "context": {
            "region": {"country_code": "CN", "has_market_instruments": True,
                       "grid_average_ef": 0.5703, "residual_mix_ef": 0.5500},
            "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}
        }
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004", "global-005",
        "rule-op-001", "rule-op-002", "rule-op-003",
    ],
    "expect_fail": [],
    "expect_emissions": 8851.5
}


# ============================================================
# 场景 11: 钢铁企业 — 过程排放 + 固定燃烧（基于宝武钢铁案例）
# ============================================================

SCENARIO_11 = {
    "name": "钢铁企业Scope1",
    "desc": "大型钢铁企业 — 高炉炼铁过程排放 + 焦炉煤气固定燃烧",
    "data": {
        "input": {
            "entity": {"name": "东方钢铁集团", "reporting_year": 2025},
            "control_method": "operational_control",
            "scope1_emission_sources": [
                {"id": "blast-furnace-001", "scope": "scope1", "type": "process",
                 "process_type": "iron_smelting", "activity_data": 5000000, "activity_unit": "tonnes",
                 "emission_factor": {"value": 1.35, "year": 2025, "source": "ipcc", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"},
                {"id": "coke-oven-001", "scope": "scope1", "type": "stationary_combustion",
                 "fuel_type": "coke_oven_gas", "activity_data": 800000, "activity_unit": "tonnes",
                 "emission_factor": {"value": 0.85, "year": 2025, "source": "ipcc", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"},
                {"id": "converter-gas-001", "scope": "scope1", "type": "stationary_combustion",
                 "fuel_type": "converter_gas", "activity_data": 200000, "activity_unit": "tonnes",
                 "emission_factor": {"value": 1.06, "year": 2025, "source": "ipcc", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"}
            ],
            "emission_sources": [
                {"id": "elec-grid-001", "type": "electricity", "activity_data": 500000,
                 "emission_factor": {"value": 0.5703, "year": 2025, "source": "生态环境部", "type": "grid_average"}}
            ],
            "assumptions": "高炉炼铁过程排放基于产品产量，焦炉煤气和转炉煤气燃烧排放",
            "methodology_rationale": "过程排放采用IPCC 2006钢铁行业指南，燃烧排放采用燃料特定因子",
            "data_sources": "IPCC 2006、企业能源统计台账",
            "justifications": {}
        },
        "output": {
            "total_scope1_emissions": 7750000.0,
            "scope1_by_category": {
                "stationary_combustion": 890000.0,
                "mobile_combustion": 0,
                "process": 6750000.0,
                "fugitive": 0
            },
            "methodology": "IPCC 2006 钢铁行业指南",
            "emission_factor_source": "IPCC 2006",
            "gas_by_gas_breakdown": {"co2": 7600000.0, "ch4": 100000.0, "n2o": 50000.0},
            "base_year": {"scope1_emissions": 7500000.0, "recalculation_policy": "股权边界变更法"}
        },
        "context": {
            "region": {"country_code": "CN"},
            "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}
        }
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004",
        "s1-cat-001", "s1-cat-002", "s1-cat-003",
        "s1-bound-001",
        "s1-disc-001", "s1-disc-002", "s1-disc-003", "s1-disc-004", "s1-disc-005", "s1-disc-007",
        "s1-qc-001", "s1-qc-002", "s1-qc-004",
        "s1-ctv-001",
    ],
    "expect_fail": [],
    "expect_emissions": 7927150.0
}


# ============================================================
# 场景 12: 制冷剂泄漏 — 逸散排放 + 合规错误检测
# ============================================================

SCENARIO_12 = {
    "name": "制冷剂泄漏逸散排放",
    "desc": "商业建筑 HVAC 系统 — R-410A/R-134a 冷媒泄漏，GWP 高值",
    "data": {
        "input": {
            "entity": {"name": "万达商业物业管理", "reporting_year": 2025},
            "control_method": "operational_control",
            "scope1_emission_sources": [
                {"id": "hvac-r410a-001", "scope": "scope1", "type": "fugitive",
                 "fuel_type": None, "activity_data": 150, "activity_unit": "kg",
                 "emission_factor": {"value": 2.088, "year": 2025, "source": "ipcc", "is_biomass": False},
                 "gwp_source": "IPCC_AR4"},
                {"id": "hvac-r134a-001", "scope": "scope1", "type": "fugitive",
                 "fuel_type": None, "activity_data": 80, "activity_unit": "kg",
                 "emission_factor": {"value": 1.43, "year": 2025, "source": "ipcc", "is_biomass": False},
                 "gwp_source": "IPCC_AR4"},
                {"id": "backup-gen-001", "scope": "scope1", "type": "stationary_combustion",
                 "fuel_type": "diesel", "activity_data": 50, "activity_unit": "tonnes",
                 "emission_factor": {"value": 2.68, "year": 2025, "source": "ipcc", "is_biomass": False},
                 "gwp_source": "IPCC_AR4"}
            ],
            "emission_sources": [],
            "assumptions": "商业建筑HVAC系统冷媒年泄漏率约10%，备用柴油发电机",
            "methodology_rationale": "逸散排放基于冷媒充注量和泄漏率，GWP采用IPCC AR4值",
            "data_sources": "IPCC AR4、设备维护记录",
            "justifications": {}
        },
        "output": {
            "total_scope1_emissions": 567.24,
            "scope1_by_category": {
                "stationary_combustion": 134.0,
                "mobile_combustion": 0,
                "process": 0,
                "fugitive": 433.24
            },
            "methodology": "排放因子法",
            "emission_factor_source": "IPCC AR4",
            "base_year": {"scope1_emissions": 520.0, "recalculation_policy": "股权边界变更法"}
        },
        "context": {
            "region": {"country_code": "CN"},
            "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}
        }
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004",
        "s1-cat-001", "s1-cat-002", "s1-cat-003",
        "s1-bound-001",
        "s1-disc-001", "s1-disc-002",
        "s1-qc-001", "s1-qc-002", "s1-qc-004",
        "s1-ctv-001",
    ],
    "expect_fail": [],
    "expect_emissions": 561.6
}


# ============================================================
# 场景 13: GWP 版本混用 — 合规错误检测
# ============================================================

SCENARIO_13 = {
    "name": "GWP版本混用错误",
    "desc": "企业混用 IPCC AR4 和 AR6 的 GWP 值 — 应触发一致性校验失败",
    "data": {
        "input": {
            "entity": {"name": "测试企业（错误场景）", "reporting_year": 2025},
            "control_method": "operational_control",
            "scope1_emission_sources": [
                {"id": "boiler-001", "scope": "scope1", "type": "stationary_combustion",
                 "fuel_type": "natural_gas", "activity_data": 1000, "activity_unit": "tonnes",
                 "emission_factor": {"value": 2.0, "year": 2025, "source": "ipcc", "is_biomass": False},
                 "gwp_source": "IPCC_AR4"},
                {"id": "hvac-001", "scope": "scope1", "type": "fugitive",
                 "fuel_type": None, "activity_data": 50, "activity_unit": "kg",
                 "emission_factor": {"value": 1.43, "year": 2025, "source": "ipcc", "is_biomass": False},
                 "gwp_source": "IPCC_AR6"}
            ],
            "emission_sources": [],
            "assumptions": "混用了不同版本的GWP值",
            "methodology_rationale": "部分使用AR4，部分使用AR6",
            "data_sources": "IPCC",
            "justifications": {}
        },
        "output": {
            "total_scope1_emissions": 2071.5,
            "scope1_by_category": {
                "stationary_combustion": 2000.0,
                "fugitive": 71.5
            },
            "methodology": "排放因子法",
            "emission_factor_source": "IPCC"
        },
        "context": {
            "region": {"country_code": "CN"},
            "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}
        }
    },
    "expect_pass": [
        "global-001", "global-002",
        "s1-cat-001", "s1-cat-002", "s1-cat-003",
    ],
    "expect_fail": [
        "s1-ctv-001",   # GWP 来源不一致
        "s1-qc-004",    # GWP 版本不一致
    ],
    "expect_emissions": 2071.5
}


# ============================================================
# 场景 14: 排放因子回退 — 缺省因子 + justification
# ============================================================

SCENARIO_14 = {
    "name": "排放因子回退场景",
    "desc": "企业使用缺省排放因子，通过 justification 解释",
    "data": {
        "input": {
            "entity": {"name": "西部矿业集团", "reporting_year": 2025},
            "control_method": "operational_control",
            "scope1_emission_sources": [
                {"id": "diesel-gen-001", "scope": "scope1", "type": "stationary_combustion",
                 "fuel_type": "diesel", "activity_data": 300, "activity_unit": "tonnes",
                 "emission_factor": {"value": 2.68, "year": 2024, "source": "default", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"},
                {"id": "fleet-001", "scope": "scope1", "type": "mobile_combustion",
                 "fuel_type": "diesel", "activity_data": 200000, "activity_unit": "km",
                 "emission_factor": {"value": 0.0002, "year": 2024, "source": "default", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"}
            ],
            "emission_sources": [],
            "assumptions": "偏远矿区无法获取设施特定因子，使用国家缺省值",
            "methodology_rationale": "采用IPCC缺省排放因子",
            "data_sources": "IPCC 2006 缺省因子数据库",
            "justifications": {
                "s1-sc-004": "矿区无燃料特定因子，使用IPCC缺省值",
                "s1-mc-003": "车辆未安装里程计，使用缺省车辆因子"
            }
        },
        "output": {
            "total_scope1_emissions": 844.0,
            "scope1_by_category": {
                "stationary_combustion": 804.0,
                "mobile_combustion": 40.0,
                "process": 0,
                "fugitive": 0
            },
            "methodology": "排放因子法（缺省因子）",
            "emission_factor_source": "IPCC 2006 缺省因子",
            "base_year": {"scope1_emissions": 800.0, "recalculation_policy": "股权边界变更法"}
        },
        "context": {
            "region": {"country_code": "CN"},
            "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}
        }
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004",
        "s1-cat-001", "s1-cat-002", "s1-cat-003",
        "s1-bound-001",
        "s1-sc-004",   # 有 justification，应通过
        "s1-disc-001", "s1-disc-002", "s1-disc-003", "s1-disc-004", "s1-disc-007",
        "s1-qc-001", "s1-qc-004",
    ],
    "expect_fail": [
        "s1-qc-002",   # EF source 是 "default"，不在允许列表
    ],
    "expect_emissions": 844.0
}


# ============================================================
# 场景 15: 生物质混合燃烧 — CO2 排除但 CH4/N2O 计入
# ============================================================

SCENARIO_15 = {
    "name": "生物质混合燃烧",
    "desc": "造纸厂 — 木质废料+煤炭混合燃烧，生物源CO2排除但CH4/N2O计入Scope 1",
    "data": {
        "input": {
            "entity": {"name": "华南造纸集团", "reporting_year": 2025},
            "control_method": "operational_control",
            "scope1_emission_sources": [
                {"id": "coal-001", "scope": "scope1", "type": "stationary_combustion",
                 "fuel_type": "coal", "activity_data": 10000, "activity_unit": "tonnes",
                 "is_biomass": False,
                 "emission_factor": {"value": 2.42, "year": 2025, "source": "ipcc", "is_biomass": False},
                 "gwp_source": "IPCC_AR5"},
                {"id": "biomass-001", "scope": "scope1", "type": "stationary_combustion",
                 "fuel_type": "wood_waste", "activity_data": 5000, "activity_unit": "tonnes",
                 "is_biomass": True,
                 "emission_factor": {"value": 0.39, "year": 2025, "source": "ipcc", "is_biomass": True},
                 "gwp_source": "IPCC_AR5"}
            ],
            "emission_sources": [],
            "assumptions": "木质废料燃烧CO2为生物源，CH4/N2O仍计入Scope 1",
            "methodology_rationale": "生物源CO2报告在Scope外，CH4/N2O报告在Scope 1",
            "data_sources": "IPCC 2006",
            "justifications": {}
        },
        "output": {
            "total_scope1_emissions": 26150.0,
            "scope1_by_category": {
                "stationary_combustion": 26150.0,
                "mobile_combustion": 0,
                "process": 0,
                "fugitive": 0
            },
            "methodology": "排放因子法",
            "emission_factor_source": "IPCC 2006",
            "biogenic_co2": 1950.0,
            "biogenic_co2_outside_scopes": True,
            "base_year": {"scope1_emissions": 25000.0, "recalculation_policy": "股权边界变更法"}
        },
        "context": {
            "region": {"country_code": "CN"},
            "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}
        }
    },
    "expect_pass": [
        "global-001", "global-002", "global-003", "global-004",
        "s1-cat-001", "s1-cat-002", "s1-cat-003",
        "s1-bound-001",
        "s1-disc-001", "s1-disc-002", "s1-disc-006",  # 生物质CO2单独报告
        "s1-qc-001", "s1-qc-002", "s1-qc-004",
        "s1-ctv-001",
    ],
    "expect_fail": [],
    "expect_emissions": 26150.0
}


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 70)
    print("GHG Protocol Scope 2 真实场景测试")
    print("=" * 70)

    spec_dir = Path(__file__).parent.parent / "specs"
    meta, specs = load_spec(spec_dir)
    print(f"\n📂 加载 {len(specs)} 个 spec 文件")

    scenarios = [SCENARIO_1, SCENARIO_2, SCENARIO_3, SCENARIO_4, SCENARIO_5, SCENARIO_6, SCENARIO_7,
                 SCENARIO_8, SCENARIO_9, SCENARIO_10, SCENARIO_11, SCENARIO_12, SCENARIO_13,
                 SCENARIO_14, SCENARIO_15]

    total_pass = total_fail = total_skip = total_unexpected = 0
    tested = set()

    for i, sc in enumerate(scenarios, 1):
        print(f"\n{'─' * 70}")
        print(f"📋 场景 {i}: {sc['name']}")
        print(f"   {sc['desc']}")
        print(f"{'─' * 70}")

        result = run_scenario(sc, specs, meta)
        tested.update(result.passed)
        tested.update(result.failed)

        if result.passed:
            print(f"\n   ✅ 通过 ({len(result.passed)}): {', '.join(result.passed)}")
        if result.failed:
            print(f"\n   ❌ 失败 ({len(result.failed)}): {', '.join(result.failed)}")
        print(f"\n   ⏭️  跳过: {len(result.skipped)} 条")
        print(f"   📊 排放量: {result.emissions} tCO2")

        if result.unexpected:
            print(f"\n   ⚠️  意外结果:")
            for u in result.unexpected:
                print(f"      {u}")

        total_pass += len(result.passed)
        total_fail += len(result.failed)
        total_skip += len(result.skipped)
        total_unexpected += len(result.unexpected)

    # 分析未覆盖规则
    all_rule_ids = set()
    for r in meta.get("global_rules", []):
        all_rule_ids.add(r["id"])
    for sp, spec in specs.items():
        for r in spec.get("rules", []):
            all_rule_ids.add(r["id"])
    untested = all_rule_ids - tested

    # 分类
    needs_computation = []
    knowledge = []
    needs_condition = []
    for sp, spec in specs.items():
        for r in spec.get("rules", []):
            if r["id"] in untested:
                if r.get("layer") == "knowledge":
                    knowledge.append(r["id"])
                elif "computation" in str(r.get("condition", "")) or "computation" in str(r.get("assertion", "")):
                    needs_computation.append(r["id"])
                else:
                    needs_condition.append(r["id"])

    print(f"\n{'=' * 70}")
    print(f"📊 总结")
    print(f"{'=' * 70}")
    print(f"   场景数:       {len(scenarios)}")
    print(f"   规则通过:     {total_pass}")
    print(f"   规则失败:     {total_fail}")
    print(f"   规则跳过:     {total_skip}")
    print(f"   测试覆盖:     {len(tested)} / {len(all_rule_ids)}")
    print(f"   意外结果:     {total_unexpected}")

    if untested:
        print(f"\n   未覆盖规则 ({len(untested)}):")
        if knowledge:
            print(f"     知识层(无assertion): {', '.join(sorted(knowledge))}")
        if needs_computation:
            print(f"     需外部函数:         {', '.join(sorted(needs_computation))}")
        if needs_condition:
            print(f"     需特定条件数据:     {', '.join(sorted(needs_condition))}")

    print()
    if total_unexpected == 0:
        print("✅ 所有场景结果符合预期！")
    else:
        print(f"⚠️  有 {total_unexpected} 个意外结果。")

    return total_unexpected == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
