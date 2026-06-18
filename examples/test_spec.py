#!/usr/bin/env python3
"""
GHG Protocol Scope 2 Spec 全面测试

测试维度:
1. 所有生命周期阶段 (pre_calculation, runtime_inference, post_audit)
2. 所有排放源类型 (electricity, steam, heat, cooling)
3. 所有控制方法 (financial_control, operational_control, equity_share)
4. 双重报告 (location-based, market-based)
5. 数据回退链所有级别
6. 边界条件和异常场景
7. Comply or Explain 机制
8. Scope 1 排放源分类、固定燃烧、禁止清单
"""

import yaml
import json
import sys
import io
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================================
# JsonLogic 实现
# ============================================================

def jsonlogic(data, rules):
    """JsonLogic 实现"""
    if not isinstance(rules, dict):
        return rules

    for op, args in rules.items():
        if op == "var":
            return get_var(data, args)
        elif op == "==":
            return jsonlogic(data, args[0]) == jsonlogic(data, args[1])
        elif op == "!=":
            left = jsonlogic(data, args[0])
            right = jsonlogic(data, args[1])
            if left is None and right is None:
                return False
            if left is None or right is None:
                return True
            return left != right
        elif op == ">":
            left = jsonlogic(data, args[0])
            right = jsonlogic(data, args[1])
            if left is None or right is None:
                return False
            return left > right
        elif op == "<":
            left = jsonlogic(data, args[0])
            right = jsonlogic(data, args[1])
            if left is None or right is None:
                return False
            return left < right
        elif op == ">=":
            left = jsonlogic(data, args[0])
            right = jsonlogic(data, args[1])
            if left is None or right is None:
                return False
            return left >= right
        elif op == "<=":
            left = jsonlogic(data, args[0])
            right = jsonlogic(data, args[1])
            if left is None or right is None:
                return False
            return left <= right
        elif op == "and":
            return all(jsonlogic(data, a) for a in args)
        elif op == "or":
            return any(jsonlogic(data, a) for a in args)
        elif op == "not":
            return not jsonlogic(data, args)
        elif op == "in":
            val = jsonlogic(data, args[0])
            arr = jsonlogic(data, args[1])
            return val in arr
        elif op == "all":
            arr = jsonlogic(data, args[0])
            if not isinstance(arr, list):
                return False
            return all(jsonlogic({**data, **item}, args[1]) for item in arr)
        elif op == "none":
            arr = jsonlogic(data, args[0])
            if not isinstance(arr, list):
                return True
            return not any(jsonlogic({**data, **item}, args[1]) for item in arr)
        elif op == "some":
            arr = jsonlogic(data, args[0])
            if not isinstance(arr, list):
                return False
            return any(jsonlogic({**data, **item}, args[1]) for item in arr)
        elif op == "+":
            return sum(jsonlogic(data, a) for a in args)
        elif op == "-":
            return jsonlogic(data, args[0]) - jsonlogic(data, args[1])
        elif op == "*":
            return jsonlogic(data, args[0]) * jsonlogic(data, args[1])
        elif op == "/":
            return jsonlogic(data, args[0]) / jsonlogic(data, args[1])

    return rules


def get_var(data, path):
    """获取嵌套数据"""
    if isinstance(path, str):
        keys = path.split(".")
    elif isinstance(path, list):
        keys = path
    else:
        return None

    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list):
            try:
                current = current[int(key)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


# ============================================================
# 测试框架
# ============================================================

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    details: str = ""

class TestSuite:
    def __init__(self, name: str):
        self.name = name
        self.results: List[TestResult] = []
        self.passed = 0
        self.failed = 0

    def assert_true(self, name: str, condition: bool, message: str = ""):
        if condition:
            self.results.append(TestResult(name, True, "PASS"))
            self.passed += 1
        else:
            self.results.append(TestResult(name, False, f"FAIL: {message}"))
            self.failed += 1

    def assert_equal(self, name: str, actual: Any, expected: Any):
        if actual == expected:
            self.results.append(TestResult(name, True, "PASS"))
            self.passed += 1
        else:
            self.results.append(TestResult(name, False, f"FAIL: expected {expected}, got {actual}"))
            self.failed += 1

    def summary(self) -> str:
        total = self.passed + self.failed
        return f"[{self.name}] {self.passed}/{total} passed, {self.failed} failed"


# ============================================================
# 规则执行器
# ============================================================

def load_spec(spec_dir: Path):
    """加载所有 spec 文件"""
    meta_path = spec_dir / "_meta.yaml"
    with open(meta_path, encoding="utf-8") as f:
        meta = yaml.safe_load(f)

    specs = {}
    for path in meta["load_order"]:
        file_path = spec_dir / f"{path}.yaml"
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                specs[path] = yaml.safe_load(f)

    return meta, specs


def execute_rule(rule: Dict, data: Dict) -> tuple:
    """执行单个规则，返回 (passed, message)"""
    rule_id = rule.get("id", "unknown")

    # 跳过 knowledge 层
    if rule.get("layer") == "knowledge":
        return None, "跳过 knowledge 层"

    # 检查 condition
    condition = rule.get("condition")
    if condition:
        if not jsonlogic(data, condition):
            return None, "条件不满足，跳过"

    # 执行 assertion
    assertion = rule.get("assertion")
    if assertion:
        passed = jsonlogic(data, assertion)

        # 处理 require_justification 机制
        if not passed and rule.get("on_fail") == "require_justification":
            justifications = data.get("input", {}).get("justifications", {})
            if rule_id in justifications:
                # 有 justification，降级为 warning，视为通过
                return True, f"有justification，降级为warning"

        message = rule.get("on_fail_message", "")
        return passed, message

    return None, "无 assertion"


def calculate_emissions(sources: List[Dict]) -> List[Dict]:
    """计算排放量"""
    results = []
    for source in sources:
        activity = source.get("activity_data", 0)
        ef = source.get("emission_factor", {}).get("value", 0)
        emissions = activity * ef
        results.append({
            "id": source.get("id"),
            "type": source.get("type"),
            "activity_data": activity,
            "emission_factor": ef,
            "emissions_tCO2": round(emissions, 4)
        })
    return results


# ============================================================
# 测试数据生成器
# ============================================================

def make_base_data() -> Dict:
    """生成基础合规数据"""
    return {
        "input": {
            "entity": {
                "name": "测试企业",
                "reporting_year": 2025,
                "control_method": "operational_control"
            },
            "emission_sources": [],
            "assumptions": "测试假设",
            "methodology_rationale": "测试方法论",
            "data_sources": "测试数据源",
            "justifications": {}
        },
        "output": {
            "total_scope2_emissions": 2851.5
        },
        "context": {
            "region": {
                "country_code": "CN",
                "has_market_instruments": True,
                "grid_average_ef": 0.5703,
                "residual_mix_ef": 0.5500
            },
            "emission_factors": {
                "current_year": 0.5703,
                "previous_year": 0.5810,
                "latest_available": 0.5703,
                "latest_year": 2025
            }
        }
    }


def make_electricity_source(id: str = "elec-001", ef_value: float = 0.5703,
                            ef_year: int = 2025, ef_type: str = "grid_average") -> Dict:
    """生成电力排放源"""
    ef = {
        "value": ef_value,
        "year": ef_year,
        "source": "测试来源",
        "type": ef_type
    }
    # 为合同类型添加QC必要字段
    if ef_type == "contract":
        ef["ghg_emission_rate_attribute"] = 0.0
        ef["unique_claim"] = True
        ef["retired_for_claims"] = True
        ef["vintage_match"] = True
        ef["same_market"] = True
        ef["claim_exclusively_transferred"] = True
    return {
        "id": id,
        "type": "electricity",
        "activity_data": 5000,
        "emission_factor": ef
    }


def make_steam_source(id: str = "steam-001") -> Dict:
    """生成蒸汽排放源"""
    return {
        "id": id,
        "type": "steam",
        "activity_data": 1000,
        "emission_factor": {
            "value": 0.1,
            "year": 2025,
            "source": "测试来源",
            "type": "supplier"
        }
    }


def make_heat_source(id: str = "heat-001") -> Dict:
    """生成热力排放源"""
    return {
        "id": id,
        "type": "heat",
        "activity_data": 500,
        "emission_factor": {
            "value": 0.2,
            "year": 2025,
            "source": "测试来源",
            "type": "supplier"
        }
    }


def make_cooling_source(id: str = "cooling-001") -> Dict:
    """生成冷量排放源"""
    return {
        "id": id,
        "type": "cooling",
        "activity_data": 200,
        "emission_factor": {
            "value": 0.05,
            "year": 2025,
            "source": "测试来源",
            "type": "supplier"
        }
    }


# ============================================================
# 测试用例
# ============================================================

def test_all_emission_source_types(specs: Dict):
    """测试所有排放源类型"""
    suite = TestSuite("排放源类型")

    for source_type, make_func in [
        ("electricity", make_electricity_source),
        ("steam", make_steam_source),
        ("heat", make_heat_source),
        ("cooling", make_cooling_source),
    ]:
        data = make_base_data()
        data["input"]["emission_sources"] = [make_func()]

        # 执行运营边界规则
        for rule in specs.get("principles/operational-boundary", {}).get("rules", []):
            passed, msg = execute_rule(rule, data)
            if passed is not None:
                suite.assert_true(
                    f"{source_type} - {rule['id']}",
                    passed,
                    msg
                )

        # 计算排放量
        emissions = calculate_emissions(data["input"]["emission_sources"])
        suite.assert_true(
            f"{source_type} - 排放量计算",
            len(emissions) == 1 and emissions[0]["emissions_tCO2"] > 0,
            f"排放量应大于0"
        )

    return suite


def test_dual_reporting(specs: Dict):
    """测试双重报告"""
    suite = TestSuite("双重报告")

    # 场景1：有市场化工具的地区，应该触发双重报告
    data = make_base_data()
    data["input"]["emission_sources"] = [make_electricity_source()]
    data["input"]["location_based_input"] = {"activity_data": 5000}
    data["input"]["market_based_input"] = {"activity_data": 5000}

    for rule in specs.get("methods/dual-reporting", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(
                f"有市场化工具 - {rule['id']}",
                passed,
                msg
            )

    # 场景2：没有市场化工具的地区，不应触发双重报告
    data_no_market = make_base_data()
    data_no_market["context"]["region"]["has_market_instruments"] = False
    data_no_market["input"]["emission_sources"] = [make_electricity_source()]
    data_no_market["input"]["method"] = "location_based"

    for rule in specs.get("methods/dual-reporting", {}).get("rules", []):
        passed, msg = execute_rule(rule, data_no_market)
        if passed is not None:
            suite.assert_true(
                f"无市场化工具 - {rule['id']}",
                passed,
                msg
            )

    return suite


def test_data_fallback_chains(specs: Dict):
    """测试数据回退链"""
    suite = TestSuite("数据回退链")

    # 测试时间回退链
    data = make_base_data()
    data["input"]["emission_sources"] = [make_electricity_source()]

    # 场景1：当年因子可用
    fallback_spec = specs.get("principles/data-quality-hierarchy", {})
    time_chain = fallback_spec.get("fallback_chains", {}).get("time_based_fallback", {})

    for level in time_chain.get("chain", []):
        condition = level.get("condition")
        if condition:
            matches = jsonlogic(data, condition)
            suite.assert_true(
                f"时间回退 - 级别{level['level']} ({level['name']})",
                matches if level['level'] == 1 else not matches,
                f"级别1应匹配，其他不匹配"
            )
            if matches:
                break

    # 场景2：当年因子不可用，应降级到前一年
    data_old = make_base_data()
    data_old["context"]["emission_factors"]["current_year"] = None
    data_old["input"]["emission_sources"] = [make_electricity_source(ef_year=2024)]

    for level in time_chain.get("chain", []):
        condition = level.get("condition")
        if condition:
            matches = jsonlogic(data_old, condition)
            if matches:
                suite.assert_true(
                    f"时间回退降级 - 级别{level['level']} ({level['name']})",
                    level['level'] == 2,
                    f"当年因子不可用时应降级到级别2"
                )
                break

    return suite


def test_comply_or_explain(specs: Dict):
    """测试 Comply or Explain 机制"""
    suite = TestSuite("Comply or Explain")

    # 场景1：有 justification 时应通过
    data = make_base_data()
    data["input"]["emission_sources"] = [make_electricity_source(ef_year=2024)]
    data["input"]["justifications"] = {
        "proh-006": "2025年因子尚未发布",
        "rule-lb-002": "该区域无区域电网因子",
        "rule-mb-002": "该企业无合同工具",
        "rule-disc-003": "数据质量评估将在后续补充",
        "rule-disc-008": "残余混合因子不可用",
        "rule-disc-012": "年度消费量数据将在后续补充",
        "rule-disc-013": "工具特征信息将在后续补充",
        "qc-004": "工具vintage与报告期存在偏差",
        "qc-008": "残余混合因子不可用"
    }

    for spec in specs.values():
        for rule in spec.get("rules", []):
            if rule.get("on_fail") == "require_justification":
                passed, msg = execute_rule(rule, data)
                if passed is not None:
                    suite.assert_true(
                        f"有justification - {rule['id']}",
                        passed,
                        msg
                    )

    # 场景2：无 justification 时应失败
    # rule-lb-002: emission_factor.source="default" 且无 justification → 应失败
    # rule-mb-002: emission_factor.type="grid_average" 且无 justification → 应失败
    # qc-004: contract 类型且 vintage_match=False 且无 justification → 应失败
    data_no_justification = make_base_data()
    src_default = make_electricity_source(ef_type="grid_average")
    src_default["emission_factor"]["source"] = "default"
    src_contract = make_electricity_source(id="elec-contract", ef_type="contract")
    src_contract["emission_factor"]["vintage_match"] = False
    data_no_justification["input"]["emission_sources"] = [src_default, src_contract]
    # 不提供 justifications

    for spec in specs.values():
        for rule in spec.get("rules", []):
            if rule.get("on_fail") == "require_justification":
                passed, msg = execute_rule(rule, data_no_justification)
                if passed is not None:
                    # 无 justification 时 passed 为 False
                    suite.assert_true(
                        f"无justification - {rule['id']}",
                        not passed,
                        msg
                    )

    return suite


def test_location_based_method(specs: Dict):
    """测试位置法"""
    suite = TestSuite("位置法")

    data = make_base_data()
    data["input"]["method"] = "location_based"
    data["input"]["emission_sources"] = [make_electricity_source()]

    for rule in specs.get("methods/location-based", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(
                f"位置法 - {rule['id']}",
                passed,
                msg
            )

    return suite


def test_market_based_method(specs: Dict):
    """测试市场法"""
    suite = TestSuite("市场法")

    data = make_base_data()
    data["input"]["method"] = "market_based"
    data["input"]["emission_sources"] = [make_electricity_source(ef_type="contract")]

    for rule in specs.get("methods/market-based", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(
                f"市场法 - {rule['id']}",
                passed,
                msg
            )

    return suite


def test_prohibitions(specs: Dict):
    """测试禁止清单"""
    suite = TestSuite("禁止清单")

    data = make_base_data()
    data["input"]["emission_sources"] = [make_electricity_source()]

    for rule in specs.get("constraints/prohibitions", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(
                f"禁止清单 - {rule['id']}",
                passed,
                msg
            )

    return suite


def test_global_rules(specs: Dict, meta: Dict):
    """测试全局规则"""
    suite = TestSuite("全局规则")

    data = make_base_data()
    data["input"]["emission_sources"] = [make_electricity_source()]

    for rule in meta.get("global_rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(
                f"全局规则 - {rule['id']}",
                passed,
                msg
            )

    return suite


def test_emission_calculation():
    """测试排放量计算"""
    suite = TestSuite("排放量计算")

    # 测试单一排放源
    sources = [make_electricity_source()]
    emissions = calculate_emissions(sources)
    suite.assert_equal(
        "单一电力排放源",
        emissions[0]["emissions_tCO2"],
        2851.5
    )

    # 测试多种排放源
    sources_multi = [
        make_electricity_source("elec-001", ef_value=0.5703),
        make_steam_source(),
        make_heat_source(),
        make_cooling_source()
    ]
    emissions_multi = calculate_emissions(sources_multi)
    suite.assert_equal(
        "多种排放源数量",
        len(emissions_multi),
        4
    )

    # 验证每种类型的排放量
    for e in emissions_multi:
        suite.assert_true(
            f"{e['type']} 排放量 > 0",
            e["emissions_tCO2"] > 0,
            f"排放量应大于0"
        )

    # 测试零排放因子（绿证）
    sources_cert = [make_electricity_source(ef_value=0.0, ef_type="certificate")]
    emissions_cert = calculate_emissions(sources_cert)
    suite.assert_equal(
        "绿证零排放",
        emissions_cert[0]["emissions_tCO2"],
        0.0
    )

    return suite


def test_edge_cases(specs: Dict):
    """测试边界条件"""
    suite = TestSuite("边界条件")

    # 场景1：空排放源列表
    data_empty = make_base_data()
    data_empty["input"]["emission_sources"] = []

    for rule in specs.get("principles/operational-boundary", {}).get("rules", []):
        passed, msg = execute_rule(rule, data_empty)
        if passed is not None:
            # rule-op-001 应该失败（无排放源）
            # rule-op-002 和 rule-op-003 应该通过（空列表时 all() 返回 true）
            if rule["id"] == "rule-op-001":
                suite.assert_true(
                    f"空排放源 - {rule['id']}",
                    not passed,
                    msg
                )
            else:
                suite.assert_true(
                    f"空排放源 - {rule['id']}",
                    passed,
                    msg
                )

    # 场景2：活动数据为0
    data_zero = make_base_data()
    data_zero["input"]["emission_sources"] = [{
        "id": "elec-001",
        "type": "electricity",
        "activity_data": 0,
        "emission_factor": {"value": 0.5703, "year": 2025, "source": "测试", "type": "grid_average"}
    }]

    for rule in specs.get("principles/operational-boundary", {}).get("rules", []):
        passed, msg = execute_rule(rule, data_zero)
        if passed is not None:
            # rule-op-001 应该通过（有排放源）
            # rule-op-002 应该通过（类型有效）
            # rule-op-003 应该失败（活动数据为0）
            if rule["id"] == "rule-op-003":
                suite.assert_true(
                    f"活动数据为0 - {rule['id']}",
                    not passed,
                    msg
                )
            else:
                suite.assert_true(
                    f"活动数据为0 - {rule['id']}",
                    passed,
                    msg
                )

    # 场景3：无效排放源类型
    data_invalid_type = make_base_data()
    data_invalid_type["input"]["emission_sources"] = [{
        "id": "invalid-001",
        "type": "natural_gas",  # 不是 Scope 2 类型
        "activity_data": 1000,
        "emission_factor": {"value": 0.5, "year": 2025, "source": "测试", "type": "default"}
    }]

    for rule in specs.get("principles/operational-boundary", {}).get("rules", []):
        passed, msg = execute_rule(rule, data_invalid_type)
        if passed is not None:
            # rule-op-001 应该通过（有排放源）
            # rule-op-002 应该失败（类型无效）
            # rule-op-003 应该通过（活动数据>0）
            if rule["id"] == "rule-op-002":
                suite.assert_true(
                    f"无效排放源类型 - {rule['id']}",
                    not passed,
                    msg
                )
            else:
                suite.assert_true(
                    f"无效排放源类型 - {rule['id']}",
                    passed,
                    msg
                )

    return suite


# ============================================================
# Scope 1 测试数据生成器
# ============================================================

def make_scope1_base_data() -> Dict:
    return {
        "input": {
            "entity": {"name": "测试企业", "reporting_year": 2025, "control_method": "operational_control"},
            "scope1_emission_sources": [],
            "assumptions": "测试假设",
            "methodology_rationale": "测试方法论",
            "data_sources": "测试数据源",
            "justifications": {}
        },
        "output": {
            "total_scope1_emissions": 1000.0,
            "scope1_by_category": {
                "stationary_combustion": 800.0,
                "mobile_combustion": 150.0,
                "process": 50.0,
                "fugitive": 0.0
            },
            "methodology": "排放因子法",
            "emission_factor_source": "IPCC 2006",
            "gas_by_gas_breakdown": {"co2": 900.0, "ch4": 50.0, "n2o": 50.0},
            "uncertainty_assessment": {"methodology": "Monte Carlo", "confidence_level": 0.95},
            "base_year": {
                "scope1_emissions": 950.0,
                "recalculation_policy": "股权边界变更法"
            }
        },
        "context": {
            "region": {"country_code": "CN"},
            "emission_factors": {"current_year": 0.5703, "previous_year": 0.5810, "latest_available": 0.5703, "latest_year": 2025}
        }
    }


def make_stationary_source(id="boiler-001", fuel="natural_gas", ef_value=2.0, is_biomass=False):
    return {
        "id": id, "scope": "scope1", "type": "stationary_combustion",
        "fuel_type": fuel, "activity_data": 500, "activity_unit": "tonnes",
        "is_biomass": is_biomass,
        "emission_factor": {"value": ef_value, "year": 2025, "source": "ipcc", "is_biomass": is_biomass},
        "gwp_source": "IPCC_AR5"
    }


def make_mobile_source(id="fleet-001", fuel="diesel"):
    return {
        "id": id, "scope": "scope1", "type": "mobile_combustion",
        "fuel_type": fuel, "activity_data": 100000, "activity_unit": "km",
        "ownership": "company_owned",
        "is_biomass": False,
        "emission_factor": {"value": 0.0002, "year": 2025, "source": "ipcc", "is_biomass": False},
        "gwp_source": "IPCC_AR5"
    }


def make_fugitive_source(id="hvac-001", refrigerant="HFC-134a"):
    return {
        "id": id, "scope": "scope1", "type": "fugitive",
        "fuel_type": None, "activity_data": 50, "activity_unit": "kg",
        "is_biomass": False,
        "emission_factor": {"value": 1.43, "year": 2025, "source": "ipcc", "is_biomass": False},
        "gwp_source": "IPCC_AR5"
    }


def make_process_source(id="cement-001", process="cement_production"):
    return {
        "id": id, "scope": "scope1", "type": "process",
        "process_type": process, "activity_data": 10000, "activity_unit": "tonnes",
        "is_biomass": False,
        "emission_factor": {"value": 0.5, "year": 2025, "source": "ipcc", "is_biomass": False},
        "gwp_source": "IPCC_AR5"
    }


# ============================================================
# Scope 1 测试用例
# ============================================================

def test_scope1_emission_categories(specs: Dict):
    suite = TestSuite("Scope 1 排放源分类")
    data = make_scope1_base_data()
    data["input"]["scope1_emission_sources"] = [make_stationary_source()]
    for rule in specs.get("scope1/principles/emission-categories", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"排放源分类 - {rule['id']}", passed, msg)
    return suite


def test_scope1_stationary_combustion(specs: Dict):
    suite = TestSuite("Scope 1 固定燃烧")
    data = make_scope1_base_data()
    data["input"]["scope1_emission_sources"] = [make_stationary_source()]
    for rule in specs.get("scope1/methods/stationary-combustion", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"固定燃烧 - {rule['id']}", passed, msg)
    return suite


def test_scope1_mobile_combustion(specs: Dict):
    suite = TestSuite("Scope 1 移动燃烧")
    data = make_scope1_base_data()
    mobile_src = make_mobile_source()
    data["input"]["scope1_emission_sources"] = [mobile_src]
    data["input"]["mobile_combustion_sources"] = [{**mobile_src, "ownership": "company_owned"}]
    for rule in specs.get("scope1/methods/mobile-combustion", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"移动燃烧 - {rule['id']}", passed, msg)
    return suite


def test_scope1_process_emissions(specs: Dict):
    suite = TestSuite("Scope 1 工业过程")
    data = make_scope1_base_data()
    data["input"]["scope1_emission_sources"] = [make_process_source()]
    data["output"]["process_emission_details"] = [{"process_type": "cement_production", "emissions": 5000.0}]
    for rule in specs.get("scope1/methods/process-emissions", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"工业过程 - {rule['id']}", passed, msg)
    return suite


def test_scope1_fugitive_emissions(specs: Dict):
    suite = TestSuite("Scope 1 逸散排放")
    data = make_scope1_base_data()
    data["input"]["scope1_emission_sources"] = [make_fugitive_source()]
    for rule in specs.get("scope1/methods/fugitive-emissions", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"逸散排放 - {rule['id']}", passed, msg)
    return suite


def test_scope1_operational_boundary(specs: Dict):
    suite = TestSuite("Scope 1 运营边界")
    data = make_scope1_base_data()
    data["input"]["scope1_emission_sources"] = [make_stationary_source()]
    for rule in specs.get("scope1/principles/operational-boundary", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"运营边界 - {rule['id']}", passed, msg)
    return suite


def test_scope1_data_quality(specs: Dict):
    suite = TestSuite("Scope 1 数据质量")
    data = make_scope1_base_data()
    data["input"]["scope1_emission_sources"] = [make_stationary_source()]
    for rule in specs.get("scope1/principles/data-quality-hierarchy", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"数据质量 - {rule['id']}", passed, msg)
    return suite


def test_scope1_cross_type_validation(specs: Dict):
    suite = TestSuite("Scope 1 跨类型校验")
    data = make_scope1_base_data()
    data["input"]["scope1_emission_sources"] = [
        make_stationary_source(),
        make_mobile_source(),
        make_process_source(),
        make_fugitive_source()
    ]
    for rule in specs.get("scope1/constraints/cross-type-validation", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"跨类型校验 - {rule['id']}", passed, msg)
    return suite


def test_scope1_disclosure(specs: Dict):
    suite = TestSuite("Scope 1 披露要求")
    data = make_scope1_base_data()
    data["input"]["scope1_emission_sources"] = [make_stationary_source()]
    for rule in specs.get("scope1/reporting/disclosure-requirements", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"披露要求 - {rule['id']}", passed, msg)
    return suite


def test_scope1_prohibitions(specs: Dict):
    suite = TestSuite("Scope 1 禁止清单")
    data = make_scope1_base_data()
    data["input"]["scope1_emission_sources"] = [make_stationary_source()]
    for rule in specs.get("scope1/constraints/prohibitions", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"禁止清单 - {rule['id']}", passed, msg)
    return suite


def test_scope1_quality_criteria(specs: Dict):
    suite = TestSuite("Scope 1 质量标准")
    data = make_scope1_base_data()
    data["input"]["scope1_emission_sources"] = [make_stationary_source()]
    for rule in specs.get("scope1/constraints/quality-criteria", {}).get("rules", []):
        passed, msg = execute_rule(rule, data)
        if passed is not None:
            suite.assert_true(f"质量标准 - {rule['id']}", passed, msg)
    return suite


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 70)
    print("GHG Protocol Scope 2 Spec 全面测试")
    print("=" * 70)
    print()

    # 加载 spec
    spec_dir = Path(__file__).parent.parent / "specs"
    if not spec_dir.exists():
        print(f"❌ 找不到 spec 目录: {spec_dir}")
        sys.exit(1)

    print("📂 加载 spec 文件...")
    meta, specs = load_spec(spec_dir)
    print(f"   加载了 {len(specs)} 个 spec 文件")
    print()

    # 运行所有测试
    test_suites = [
        test_all_emission_source_types(specs),
        test_dual_reporting(specs),
        test_data_fallback_chains(specs),
        test_comply_or_explain(specs),
        test_location_based_method(specs),
        test_market_based_method(specs),
        test_prohibitions(specs),
        test_global_rules(specs, meta),
        test_emission_calculation(),
        test_edge_cases(specs),
        test_scope1_emission_categories(specs),
        test_scope1_stationary_combustion(specs),
        test_scope1_mobile_combustion(specs),
        test_scope1_process_emissions(specs),
        test_scope1_fugitive_emissions(specs),
        test_scope1_operational_boundary(specs),
        test_scope1_data_quality(specs),
        test_scope1_cross_type_validation(specs),
        test_scope1_disclosure(specs),
        test_scope1_prohibitions(specs),
        test_scope1_quality_criteria(specs),
    ]

    # 输出结果
    total_passed = 0
    total_failed = 0

    for suite in test_suites:
        print(f"\n{'─' * 70}")
        print(f"📋 {suite.name}")
        print(f"{'─' * 70}")

        for result in suite.results:
            status = "✅" if result.passed else "❌"
            print(f"   {status} {result.name}: {result.message}")

        print(f"\n   {suite.summary()}")
        total_passed += suite.passed
        total_failed += suite.failed

    # 总结
    print(f"\n{'=' * 70}")
    print(f"📊 测试总结")
    print(f"{'=' * 70}")
    print(f"   总测试数: {total_passed + total_failed}")
    print(f"   通过: {total_passed}")
    print(f"   失败: {total_failed}")
    print(f"   通过率: {total_passed / (total_passed + total_failed) * 100:.1f}%")
    print()

    if total_failed == 0:
        print("✅ 所有测试通过！Spec 验证完成。")
    else:
        print(f"⚠️  有 {total_failed} 个测试失败，请检查。")

    return total_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
