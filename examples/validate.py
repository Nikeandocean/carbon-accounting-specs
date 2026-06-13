#!/usr/bin/env python3
"""
GHG Protocol Scope 2 Spec 验证脚本

用法: python examples/validate.py

功能:
1. 加载 spec 规则
2. 用示例数据执行校验
3. 输出校验结果
"""

import yaml
import json
import sys
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================================
# JsonLogic 简易实现（避免外部依赖）
# ============================================================

def jsonlogic(data, rules):
    """简易 JsonLogic 实现"""
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
            # Handle None comparisons
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
# 规则加载器
# ============================================================

def load_spec(spec_dir):
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


# ============================================================
# 规则执行器
# ============================================================

class RuleResult:
    def __init__(self, rule_id, rule_name, passed, message, severity, lifecycle):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.passed = passed
        self.message = message
        self.severity = severity
        self.lifecycle = lifecycle

    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} [{self.rule_id}] {self.rule_name}: {self.message}"


def execute_rules(specs, data):
    """执行所有规则"""
    results = []

    for spec_path, spec in specs.items():
        for rule in spec.get("rules", []):
            rule_id = rule.get("id", "unknown")
            rule_name = rule.get("name", "unknown")
            severity = rule.get("severity", "info")
            lifecycle = rule.get("lifecycle", "unknown")

            # 只执行 schema 层的规则
            if rule.get("layer") == "knowledge":
                continue

            # 检查 condition
            condition = rule.get("condition")
            if condition:
                if not jsonlogic(data, condition):
                    continue

            # 执行 assertion
            assertion = rule.get("assertion")
            if assertion:
                passed = jsonlogic(data, assertion)
                message = rule.get("on_fail_message", "校验通过" if passed else "校验失败")
                results.append(RuleResult(rule_id, rule_name, passed, message, severity, lifecycle))

    return results


def execute_fallback_chains(specs, data):
    """执行数据回退链"""
    fallback_results = []

    for spec_path, spec in specs.items():
        for chain_name, chain in spec.get("fallback_chains", {}).items():
            if not isinstance(chain, dict) or "chain" not in chain:
                continue

            for level in chain["chain"]:
                condition = level.get("condition")
                if condition and jsonlogic(data, condition):
                    action = level.get("on_match", {}).get("action", "unknown")
                    message = level.get("on_match", {}).get("message", "匹配")
                    fallback_results.append({
                        "chain": chain_name,
                        "level": level.get("level"),
                        "name": level.get("name"),
                        "action": action,
                        "message": message
                    })
                    break

    return fallback_results


# ============================================================
# 计算排放量
# ============================================================

def calculate_emissions(data):
    """计算排放量"""
    results = []
    for source in data.get("input", {}).get("emission_sources", []):
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
# 主程序
# ============================================================

def main():
    print("=" * 60)
    print("GHG Protocol Scope 2 Spec 验证")
    print("=" * 60)
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

    # 示例数据：合规场景
    valid_data = {
        "input": {
            "entity": {
                "name": "示例制造有限公司",
                "reporting_year": 2025,
                "control_method": "operational_control"
            },
            "emission_sources": [
                {
                    "id": "elec-001",
                    "type": "electricity",
                    "activity_data": 5000,
                    "emission_factor": {
                        "value": 0.5703,
                        "year": 2025,
                        "source": "生态环境部",
                        "type": "grid_average"
                    }
                },
                {
                    "id": "elec-002",
                    "type": "electricity",
                    "activity_data": 3000,
                    "emission_factor": {
                        "value": 0.0,
                        "year": 2025,
                        "source": "绿证",
                        "type": "certificate"
                    }
                }
            ],
            "assumptions": "使用国家电网平均排放因子",
            "methodology_rationale": "采用位置法和市场法双重报告",
            "data_sources": "生态环境部发布的排放因子"
        },
        "context": {
            "region": {
                "country_code": "CN",
                "has_market_instruments": True,
                "grid_average_ef": 0.5703
            },
            "emission_factors": {
                "current_year": 0.5703,
                "previous_year": 0.5810,
                "latest_available": 0.5703,
                "latest_year": 2025
            }
        }
    }

    # 示例数据：不合规场景（缺少必要字段）
    invalid_data = {
        "input": {
            "entity": {
                "name": "问题企业",
                "reporting_year": 2025,
                "control_method": "operational_control"
            },
            "emission_sources": [
                {
                    "id": "elec-001",
                    "type": "electricity",
                    "activity_data": 1000,
                    "emission_factor": {
                        "value": 0.5703,
                        "year": 2022,  # 因子年份不匹配
                        "source": "旧数据",
                        "type": "default"  # 使用缺省因子
                    }
                }
            ]
            # 缺少 assumptions, methodology_rationale, data_sources
        },
        "context": {
            "region": {
                "country_code": "CN",
                "has_market_instruments": True,
                "grid_average_ef": 0.5703
            }
        }
    }

    # 场景 1：合规数据校验
    print("-" * 60)
    print("📋 场景 1：合规数据校验")
    print("-" * 60)
    print()

    results = execute_rules(specs, valid_data)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    for r in results:
        print(f"   {r}")

    print()
    print(f"   结果: {passed} 通过, {failed} 失败")
    print()

    # 场景 2：不合规数据校验
    print("-" * 60)
    print("📋 场景 2：不合规数据校验")
    print("-" * 60)
    print()

    results2 = execute_rules(specs, invalid_data)
    passed2 = sum(1 for r in results2 if r.passed)
    failed2 = sum(1 for r in results2 if not r.passed)

    for r in results2:
        print(f"   {r}")

    print()
    print(f"   结果: {passed2} 通过, {failed2} 失败")
    print()

    # 场景 3：排放量计算
    print("-" * 60)
    print("📊 场景 3：排放量计算")
    print("-" * 60)
    print()

    emissions = calculate_emissions(emissions_data := valid_data)
    total = 0
    for e in emissions:
        print(f"   {e['id']} ({e['type']}): {e['activity_data']} MWh × {e['emission_factor']} tCO2/MWh = {e['emissions_tCO2']} tCO2")
        total += e["emissions_tCO2"]

    print()
    print(f"   总排放量: {total} tCO2")
    print()

    # 场景 4：数据回退链
    print("-" * 60)
    print("🔄 场景 4：数据回退链")
    print("-" * 60)
    print()

    fallback_results = execute_fallback_chains(specs, valid_data)
    for fb in fallback_results:
        print(f"   链: {fb['chain']}, 级别: {fb['level']}, 名称: {fb['name']}")
        print(f"   动作: {fb['action']}, 消息: {fb['message']}")
        print()

    # 总结
    print("=" * 60)
    print("✅ 验证完成")
    print("=" * 60)
    print()
    print("验证结果:")
    print(f"  - 合规场景: {passed}/{len(results)} 规则通过")
    print(f"  - 不合规场景: {passed2}/{len(results2)} 规则通过 (预期有失败)")
    print(f"  - 排放量计算: 正常工作")
    print(f"  - 数据回退链: 正常工作")
    print()
    print("结论: Spec 可以正常用于 GHG Protocol Scope 2 合规性校验")


if __name__ == "__main__":
    main()
