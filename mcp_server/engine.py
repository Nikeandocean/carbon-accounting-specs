"""
JsonLogic 规则执行引擎

从 examples/validate.py 提取并重构为可复用模块。
支持 condition + assertion 两阶段规则执行。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


# ============================================================
# JsonLogic 实现
# ============================================================

def jsonlogic(data: dict, rules: Any) -> Any:
    """JsonLogic 表达式求值"""
    if not isinstance(rules, dict):
        return rules

    for op, args in rules.items():
        if op == "var":
            return _get_var(data, args)
        elif op == "==":
            return jsonlogic(data, args[0]) == jsonlogic(data, args[1])
        elif op == "!=":
            l, r = jsonlogic(data, args[0]), jsonlogic(data, args[1])
            if l is None and r is None:
                return False
            if l is None or r is None:
                return True
            return l != r
        elif op == ">":
            l, r = jsonlogic(data, args[0]), jsonlogic(data, args[1])
            return l > r if l is not None and r is not None else False
        elif op == "<":
            l, r = jsonlogic(data, args[0]), jsonlogic(data, args[1])
            return l < r if l is not None and r is not None else False
        elif op == ">=":
            l, r = jsonlogic(data, args[0]), jsonlogic(data, args[1])
            return l >= r if l is not None and r is not None else False
        elif op == "<=":
            l, r = jsonlogic(data, args[0]), jsonlogic(data, args[1])
            return l <= r if l is not None and r is not None else False
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


def _get_var(data: dict, path: Any) -> Any:
    """按路径获取嵌套数据"""
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
# 规则执行结果
# ============================================================

@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    passed: bool
    message: str
    severity: str  # fatal / warning / info
    lifecycle: str  # pre_calculation / runtime_inference / post_audit
    citation: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "status": "pass" if self.passed else ("fatal" if self.severity == "fatal" else "warning"),
            "message": self.message,
            "severity": self.severity,
            "lifecycle": self.lifecycle,
            "citation": self.citation,
            "suggestion": self.suggestion,
        }


@dataclass
class AuditResult:
    """审查结果汇总"""
    domain: str  # "scope1" / "scope2" / "scope3" / "green_bond" / "green_credit"
    compliance: str  # "pass" / "warning" / "fatal"
    total_rules: int
    passed: int
    warnings: int
    fatal: int
    skipped: int
    results: list[RuleResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "compliance": self.compliance,
            "summary": {
                "total": self.total_rules,
                "passed": self.passed,
                "warnings": self.warnings,
                "fatal": self.fatal,
                "skipped": self.skipped,
            },
            "results": [r.to_dict() for r in self.results],
        }


# ============================================================
# 规则执行器
# ============================================================

def execute_rules(specs: dict[str, Any], data: dict, domain: str = "unknown") -> AuditResult:
    """执行所有规则并返回结构化结果"""
    results: list[RuleResult] = []

    for spec_path, spec in specs.items():
        for rule in spec.get("rules", []):
            rule_id = rule.get("id", "unknown")
            rule_name = rule.get("name", "unknown")
            severity = rule.get("severity", "info")
            lifecycle = rule.get("lifecycle", "unknown")

            # 跳过 knowledge 层规则
            if rule.get("layer") == "knowledge":
                continue

            # 检查 condition（前置条件）
            condition = rule.get("condition")
            if condition and not jsonlogic(data, condition):
                continue

            # 执行 assertion
            assertion = rule.get("assertion")
            if assertion:
                passed = bool(jsonlogic(data, assertion))
                message = rule.get(
                    "on_fail_message" if not passed else "on_pass_message",
                    "校验通过" if passed else "校验失败"
                )

                # 提取关联的 citation
                citation_id = rule.get("citation_ref", "")
                citation_text = ""
                if citation_id and spec.get("citations"):
                    for cit in spec["citations"]:
                        if cit.get("id") == citation_id:
                            citation_text = cit.get("text", "")
                            break

                results.append(RuleResult(
                    rule_id=rule_id,
                    rule_name=rule_name,
                    passed=passed,
                    message=message,
                    severity=severity,
                    lifecycle=lifecycle,
                    citation=citation_text,
                ))

    # 汇总
    passed_n = sum(1 for r in results if r.passed)
    fatal_n = sum(1 for r in results if not r.passed and r.severity == "fatal")
    warn_n = sum(1 for r in results if not r.passed and r.severity != "fatal")

    if fatal_n > 0:
        compliance = "fatal"
    elif warn_n > 0:
        compliance = "warning"
    else:
        compliance = "pass"

    return AuditResult(
        domain=domain,
        compliance=compliance,
        total_rules=len(results),
        passed=passed_n,
        warnings=warn_n,
        fatal=fatal_n,
        skipped=0,
        results=results,
    )
