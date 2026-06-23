"""
Spec-Driven 审计 MCP Tools

实现完整的 spec-driven 审计流程：
1. describe_spec - 描述 spec 结构和要求
2. get_data_requirements - 获取数据收集要求
3. analyze_gaps - 差距分析
4. validate_data - 数据验证
5. get_remediation - 修复指导
6. generate_report - 生成合规报告
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from .engine import execute_rules, jsonlogic, AuditResult
from .loader import SpecLoader

logger = logging.getLogger(__name__)


def register_spec_tools(mcp: FastMCP, loader: SpecLoader) -> None:
    """注册 spec-driven 审计工具"""

    @mcp.tool()
    async def describe_spec(spec_id: str = "") -> str:
        """
        描述 spec 的结构、覆盖范围和要求概览。

        这是 spec-driven 审计的起点：agent 调用此工具了解 spec 需要什么数据，
        然后引导用户逐步提供。

        Args:
            spec_id: spec 文件标识（如 "issb-s2-disclosure", "scope1", "green-finance"）。
                     空字符串表示返回所有 spec 的概览。

        Returns:
            JSON 字符串，包含：
            - domain: 领域名称
            - scope: 覆盖范围描述
            - pillars: 按支柱/类别分组的规则统计
            - severity_breakdown: 按严重级别统计
            - lifecycle_breakdown: 按生命周期阶段统计
            - citations_count: 引用数量
        """
        try:
            if spec_id:
                specs = loader.load_domain(spec_id)
                if not specs:
                    return json.dumps(
                        {"error": f"未找到 spec: {spec_id}"},
                        ensure_ascii=False,
                    )
            else:
                specs = loader.specs

            # 收集所有规则和引用
            all_rules = []
            all_citations = []
            spec_summaries = []

            for path, spec in specs.items():
                rules = spec.get("rules", [])
                citations = spec.get("citations", [])
                meta = spec.get("meta", {})

                # 过滤 knowledge 层规则
                schema_rules = [r for r in rules if r.get("layer") != "knowledge"]

                # 按支柱分组
                pillar_counts = {}
                for rule in schema_rules:
                    name = rule.get("name", "")
                    # 尝试从规则名称或 ID 推断支柱
                    rule_id = rule.get("id", "")
                    if "governance" in name.lower() or "治理" in name:
                        pillar = "governance"
                    elif "strategy" in name.lower() or "战略" in name:
                        pillar = "strategy"
                    elif "risk" in name.lower() or "风险" in name:
                        pillar = "risk_management"
                    elif "metric" in name.lower() or "指标" in name or "排放" in name:
                        pillar = "metrics"
                    elif "target" in name.lower() or "目标" in name:
                        pillar = "targets"
                    elif "scenario" in name.lower() or "情景" in name:
                        pillar = "scenario_analysis"
                    elif "scope2" in name.lower() or "合同" in name:
                        pillar = "scope2"
                    elif "scope3" in name.lower() or "融资" in name:
                        pillar = "scope3"
                    elif "appendix" in name.lower() or "附录" in name:
                        pillar = "appendix"
                    else:
                        pillar = "other"
                    pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1

                spec_summaries.append({
                    "spec_id": path,
                    "title": meta.get("source", path),
                    "version": meta.get("version", "unknown"),
                    "rules_count": len(schema_rules),
                    "citations_count": len(citations),
                    "pillars": pillar_counts,
                })

                all_rules.extend(schema_rules)
                all_citations.extend(citations)

            # 统计严重级别
            severity_counts = {}
            for rule in all_rules:
                sev = rule.get("severity", "info")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            # 统计生命周期
            lifecycle_counts = {}
            for rule in all_rules:
                lc = rule.get("lifecycle", "unknown")
                lifecycle_counts[lc] = lifecycle_counts.get(lc, 0) + 1

            # 统计 on_fail 类型
            on_fail_counts = {}
            for rule in all_rules:
                of = rule.get("on_fail", "unknown")
                on_fail_counts[of] = on_fail_counts.get(of, 0) + 1

            return json.dumps({
                "spec_id": spec_id or "all",
                "specs": spec_summaries,
                "totals": {
                    "rules": len(all_rules),
                    "citations": len(all_citations),
                },
                "severity_breakdown": severity_counts,
                "lifecycle_breakdown": lifecycle_counts,
                "on_fail_breakdown": on_fail_counts,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("describe_spec failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    async def get_data_requirements(spec_id: str) -> str:
        """
        获取 spec 要求的输入数据结构。

        分析 spec 中所有规则的 condition 和 assertion，
        提取出需要用户提供哪些数据字段。

        Args:
            spec_id: spec 文件标识（如 "issb-s2-disclosure", "scope1"）

        Returns:
            JSON 字符串，包含：
            - required_fields: 必填字段列表（severity=fatal 的规则要求的字段）
            - optional_fields: 选填字段列表（severity=warning 的规则要求的字段）
            - conditional_fields: 条件字段（依赖其他条件的字段）
            - input_schema: 建议的输入数据结构
        """
        try:
            specs = loader.load_domain(spec_id)
            if not specs:
                return json.dumps(
                    {"error": f"未找到 spec: {spec_id}"},
                    ensure_ascii=False,
                )

            required_fields = []
            optional_fields = []
            conditional_fields = []

            for path, spec in specs.items():
                for rule in spec.get("rules", []):
                    if rule.get("layer") == "knowledge":
                        continue

                    rule_id = rule.get("id", "")
                    severity = rule.get("severity", "info")
                    assertion = rule.get("assertion", {})
                    condition = rule.get("condition", {})

                    # 从 assertion 中提取 var 路径
                    fields = _extract_var_paths(assertion)

                    # 判断是否有条件
                    has_condition = bool(condition) and condition != {}

                    for field_path in fields:
                        field_info = {
                            "path": field_path,
                            "rule_id": rule_id,
                            "rule_name": rule.get("name", ""),
                            "severity": severity,
                            "lifecycle": rule.get("lifecycle", ""),
                        }

                        if has_condition:
                            condition_paths = _extract_var_paths(condition)
                            field_info["condition"] = {
                                "expression": condition,
                                "depends_on": condition_paths,
                            }
                            conditional_fields.append(field_info)
                        elif severity == "fatal":
                            required_fields.append(field_info)
                        else:
                            optional_fields.append(field_info)

            # 去重
            required_fields = _deduplicate_fields(required_fields)
            optional_fields = _deduplicate_fields(optional_fields)
            conditional_fields = _deduplicate_fields(conditional_fields)

            # 构建建议的输入 schema
            input_schema = _build_input_schema(
                required_fields + optional_fields + conditional_fields
            )

            return json.dumps({
                "spec_id": spec_id,
                "required_fields": required_fields,
                "optional_fields": optional_fields,
                "conditional_fields": conditional_fields,
                "summary": {
                    "required_count": len(required_fields),
                    "optional_count": len(optional_fields),
                    "conditional_count": len(conditional_fields),
                },
                "input_schema": input_schema,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("get_data_requirements failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    async def analyze_gaps(spec_id: str, data: str) -> str:
        """
        分析已有数据与 spec 要求之间的差距。

        输入已有数据，返回哪些要求已满足、哪些缺失、优先级如何。

        Args:
            spec_id: spec 文件标识（如 "issb-s2-disclosure"）
            data: 已有数据 JSON 字符串，结构与 spec 要求的输入一致

        Returns:
            JSON 字符串，包含：
            - coverage: 覆盖率（0-1）
            - satisfied: 已满足的规则列表
            - missing_fatal: 缺失的 fatal 级别要求
            - missing_warning: 缺失的 warning 级别要求
            - recommendations: 数据收集建议（按优先级排序）
        """
        try:
            specs = loader.load_domain(spec_id)
            if not specs:
                return json.dumps(
                    {"error": f"未找到 spec: {spec_id}"},
                    ensure_ascii=False,
                )

            parsed_data = json.loads(data)

            # 执行规则
            result = execute_rules(specs, parsed_data, domain=spec_id)

            # 分析结果
            satisfied = []
            missing_fatal = []
            missing_warning = []
            skipped = []

            for r in result.results:
                if r.passed:
                    satisfied.append({
                        "rule_id": r.rule_id,
                        "rule_name": r.rule_name,
                    })
                elif r.severity == "fatal":
                    missing_fatal.append({
                        "rule_id": r.rule_id,
                        "rule_name": r.rule_name,
                        "message": r.message,
                        "citation": r.citation,
                    })
                elif r.severity == "warning":
                    missing_warning.append({
                        "rule_id": r.rule_id,
                        "rule_name": r.rule_name,
                        "message": r.message,
                        "citation": r.citation,
                    })

            # 计算覆盖率
            total = len(result.results)
            coverage = len(satisfied) / total if total > 0 else 0

            # 生成建议
            recommendations = _generate_recommendations(
                missing_fatal, missing_warning
            )

            return json.dumps({
                "spec_id": spec_id,
                "coverage": round(coverage, 2),
                "summary": {
                    "total_rules": total,
                    "satisfied": len(satisfied),
                    "missing_fatal": len(missing_fatal),
                    "missing_warning": len(missing_warning),
                    "skipped": len(skipped),
                },
                "satisfied": satisfied,
                "missing_fatal": missing_fatal,
                "missing_warning": missing_warning,
                "recommendations": recommendations,
            }, ensure_ascii=False, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps(
                {"error": f"data JSON 解析失败: {e}"},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.exception("analyze_gaps failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    async def validate_data(spec_id: str, data: str) -> str:
        """
        执行完整的 spec 规则验证。

        这是 spec-driven 审计的核心：用 spec 中定义的规则验证数据。

        Args:
            spec_id: spec 文件标识（如 "issb-s2-disclosure", "scope1"）
            data: 待验证数据 JSON 字符串

        Returns:
            JSON 字符串，包含完整的审计结果：
            - compliance: 合规状态（pass/warning/fatal）
            - summary: 统计摘要
            - results: 逐条规则的执行结果
            - pillar_assessment: 按支柱的评估
        """
        try:
            specs = loader.load_domain(spec_id)
            if not specs:
                return json.dumps(
                    {"error": f"未找到 spec: {spec_id}"},
                    ensure_ascii=False,
                )

            parsed_data = json.loads(data)

            # 执行规则
            result = execute_rules(specs, parsed_data, domain=spec_id)

            # 按支柱分组评估
            pillar_assessment = {}
            for r in result.results:
                # 从规则名称推断支柱
                pillar = _infer_pillar(r.rule_name, r.rule_id)
                if pillar not in pillar_assessment:
                    pillar_assessment[pillar] = {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                        "rules": [],
                    }
                pillar_assessment[pillar]["total"] += 1
                if r.passed:
                    pillar_assessment[pillar]["passed"] += 1
                else:
                    pillar_assessment[pillar]["failed"] += 1
                pillar_assessment[pillar]["rules"].append(r.to_dict())

            # 计算每个支柱的状态
            for pillar, assessment in pillar_assessment.items():
                if assessment["failed"] > 0:
                    # 检查是否有 fatal 失败
                    has_fatal = any(
                        not r.passed and r.severity == "fatal"
                        for r in result.results
                        if _infer_pillar(r.rule_name, r.rule_id) == pillar
                    )
                    assessment["status"] = "fatal" if has_fatal else "warning"
                else:
                    assessment["status"] = "pass"

            return json.dumps({
                "domain": result.domain,
                "compliance": result.compliance,
                "summary": {
                    "total": result.total_rules,
                    "passed": result.passed,
                    "warnings": result.warnings,
                    "fatal": result.fatal,
                    "skipped": result.skipped,
                },
                "pillar_assessment": pillar_assessment,
                "results": [r.to_dict() for r in result.results],
            }, ensure_ascii=False, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps(
                {"error": f"data JSON 解析失败: {e}"},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.exception("validate_data failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    async def get_remediation(spec_id: str, rule_id: str) -> str:
        """
        获取规则失败的修复指导。

        返回规则的详细解释、关联的 citation 原文、修复步骤和示例数据。

        Args:
            spec_id: spec 文件标识
            rule_id: 规则 ID（如 "gf-s2-001"）

        Returns:
            JSON 字符串，包含：
            - rule: 规则详情
            - citation: 关联的标准引用原文
            - explanation: 规则要求的通俗解释
            - remediation_steps: 修复步骤
            - example_data: 示例数据
        """
        try:
            # 查找规则
            rule = loader.get_rule(rule_id)
            if not rule:
                return json.dumps(
                    {"error": f"未找到规则: {rule_id}"},
                    ensure_ascii=False,
                )

            # 获取关联的 citation
            citation_id = rule.get("citation", "") or rule.get("citation_ref", "")
            citation = None
            if citation_id:
                citation = loader.get_citation(citation_id)

            # 生成修复指导
            explanation = _generate_explanation(rule)
            remediation_steps = _generate_remediation_steps(rule)
            example_data = _generate_example_data(rule)

            return json.dumps({
                "rule": {
                    "id": rule.get("id"),
                    "name": rule.get("name"),
                    "priority": rule.get("priority"),
                    "severity": rule.get("severity"),
                    "lifecycle": rule.get("lifecycle"),
                    "on_fail": rule.get("on_fail"),
                    "on_fail_message": rule.get("on_fail_message"),
                    "condition": rule.get("condition"),
                    "assertion": rule.get("assertion"),
                },
                "citation": {
                    "id": citation_id,
                    "text": citation.get("text", "") if citation else "",
                    "section": citation.get("section", "") if citation else "",
                },
                "explanation": explanation,
                "remediation_steps": remediation_steps,
                "example_data": example_data,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("get_remediation failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    async def generate_report(
        spec_id: str,
        data: str,
        entity_name: str = "未命名实体",
        report_format: str = "json",
    ) -> str:
        """
        生成完整的合规审计报告。

        执行所有规则并生成结构化的合规报告，包含执行摘要、
        各支柱评估、详细发现和修复建议。

        Args:
            spec_id: spec 文件标识
            data: 待审计数据 JSON 字符串
            entity_name: 实体名称
            report_format: 报告格式（"json" 或 "markdown"）

        Returns:
            合规审计报告（JSON 或 Markdown 格式）
        """
        try:
            specs = loader.load_domain(spec_id)
            if not specs:
                return json.dumps(
                    {"error": f"未找到 spec: {spec_id}"},
                    ensure_ascii=False,
                )

            parsed_data = json.loads(data)

            # 执行规则
            result = execute_rules(specs, parsed_data, domain=spec_id)

            # 按支柱分组
            pillar_results = {}
            for r in result.results:
                pillar = _infer_pillar(r.rule_name, r.rule_id)
                if pillar not in pillar_results:
                    pillar_results[pillar] = []
                pillar_results[pillar].append(r)

            # 构建报告
            report = {
                "report_metadata": {
                    "spec_id": spec_id,
                    "entity_name": entity_name,
                    "generated_at": datetime.now().isoformat(),
                    "spec_version": _get_spec_version(specs),
                },
                "executive_summary": {
                    "compliance_status": result.compliance,
                    "total_rules_checked": result.total_rules,
                    "passed": result.passed,
                    "warnings": result.warnings,
                    "critical_failures": result.fatal,
                    "coverage": round(result.passed / result.total_rules * 100, 1) if result.total_rules > 0 else 0,
                },
                "pillar_assessments": {},
                "critical_findings": [],
                "warnings": [],
                "remediation_plan": [],
            }

            # 各支柱评估
            for pillar, rules in pillar_results.items():
                passed = sum(1 for r in rules if r.passed)
                failed = sum(1 for r in rules if not r.passed)
                has_fatal = any(
                    not r.passed and r.severity == "fatal" for r in rules
                )

                report["pillar_assessments"][pillar] = {
                    "status": "fatal" if has_fatal else ("warning" if failed > 0 else "pass"),
                    "total": len(rules),
                    "passed": passed,
                    "failed": failed,
                    "coverage": round(passed / len(rules) * 100, 1) if rules else 0,
                }

                # 收集失败项
                for r in rules:
                    if not r.passed:
                        finding = {
                            "rule_id": r.rule_id,
                            "rule_name": r.rule_name,
                            "severity": r.severity,
                            "message": r.message,
                            "citation": r.citation,
                            "pillar": pillar,
                        }
                        if r.severity == "fatal":
                            report["critical_findings"].append(finding)
                        else:
                            report["warnings"].append(finding)

                        # 生成修复建议
                        remediation = _generate_remediation_steps(
                            loader.get_rule(r.rule_id) or {}
                        )
                        report["remediation_plan"].append({
                            "rule_id": r.rule_id,
                            "priority": "high" if r.severity == "fatal" else "medium",
                            "steps": remediation,
                        })

            # 按优先级排序修复计划
            report["remediation_plan"].sort(
                key=lambda x: 0 if x["priority"] == "high" else 1
            )

            if report_format == "markdown":
                return _format_report_markdown(report)
            else:
                return json.dumps(report, ensure_ascii=False, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps(
                {"error": f"data JSON 解析失败: {e}"},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.exception("generate_report failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================
# 辅助函数
# ============================================================

def _extract_var_paths(expr: Any) -> list[str]:
    """从 JsonLogic 表达式中提取所有 var 路径"""
    paths = []
    if isinstance(expr, dict):
        for op, args in expr.items():
            if op == "var" and isinstance(args, str):
                paths.append(args)
            elif isinstance(args, list):
                for arg in args:
                    paths.extend(_extract_var_paths(arg))
            elif isinstance(args, dict):
                paths.extend(_extract_var_paths(args))
    elif isinstance(expr, list):
        for item in expr:
            paths.extend(_extract_var_paths(item))
    return paths


def _deduplicate_fields(fields: list[dict]) -> list[dict]:
    """按 path 去重，保留 severity 最高的"""
    seen = {}
    for f in fields:
        path = f["path"]
        if path not in seen:
            seen[path] = f
        elif f["severity"] == "fatal" and seen[path]["severity"] != "fatal":
            seen[path] = f
    return list(seen.values())


def _build_input_schema(fields: list[dict]) -> dict:
    """从字段列表构建建议的输入 schema"""
    schema = {}
    for f in fields:
        parts = f["path"].split(".")
        current = schema
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = {
            "required": f["severity"] == "fatal",
            "rule": f["rule_id"],
        }
    return schema


def _generate_recommendations(
    missing_fatal: list[dict],
    missing_warning: list[dict],
) -> list[dict]:
    """生成数据收集建议"""
    recommendations = []

    # 按支柱分组
    pillar_groups = {}
    for item in missing_fatal + missing_warning:
        pillar = _infer_pillar(item["rule_name"], item["rule_id"])
        if pillar not in pillar_groups:
            pillar_groups[pillar] = {"fatal": [], "warning": []}
        if item in missing_fatal:
            pillar_groups[pillar]["fatal"].append(item)
        else:
            pillar_groups[pillar]["warning"].append(item)

    # 生成建议
    priority_order = [
        ("governance", "治理"),
        ("strategy", "战略"),
        ("risk_management", "风险管理"),
        ("metrics", "指标"),
        ("targets", "目标"),
        ("scenario_analysis", "情景分析"),
    ]

    for pillar, label in priority_order:
        if pillar in pillar_groups:
            group = pillar_groups[pillar]
            if group["fatal"]:
                recommendations.append({
                    "priority": "high",
                    "pillar": pillar,
                    "label": label,
                    "message": f"首先收集{label}相关信息（{len(group['fatal'])} 项必填）",
                    "rules": [r["rule_id"] for r in group["fatal"]],
                })
            if group["warning"]:
                recommendations.append({
                    "priority": "medium",
                    "pillar": pillar,
                    "label": label,
                    "message": f"然后补充{label}信息（{len(group['warning'])} 项建议）",
                    "rules": [r["rule_id"] for r in group["warning"]],
                })

    return recommendations


def _infer_pillar(rule_name: str, rule_id: str) -> str:
    """从规则名称或 ID 推断支柱"""
    name_lower = rule_name.lower()
    id_lower = rule_id.lower()

    if "治理" in name_lower or "governance" in name_lower:
        return "governance"
    elif "战略" in name_lower or "strategy" in name_lower:
        return "strategy"
    elif "风险" in name_lower or "risk" in name_lower:
        return "risk_management"
    elif "排放" in name_lower or "ghg" in name_lower or "scope" in name_lower:
        return "metrics"
    elif "目标" in name_lower or "target" in name_lower:
        return "targets"
    elif "情景" in name_lower or "scenario" in name_lower:
        return "scenario_analysis"
    elif "融资" in name_lower or "financed" in name_lower:
        return "financed_emissions"
    elif "附录" in name_lower or "appendix" in name_lower:
        return "appendix"
    else:
        return "other"


def _get_spec_version(specs: dict) -> str:
    """获取 spec 版本"""
    for spec in specs.values():
        meta = spec.get("meta", {})
        if meta.get("version"):
            return meta["version"]
    return "unknown"


def _generate_explanation(rule: dict) -> str:
    """生成规则的通俗解释"""
    name = rule.get("name", "")
    on_fail_message = rule.get("on_fail_message", "")
    severity = rule.get("severity", "")

    parts = []
    parts.append(f"规则「{name}」要求：")
    if on_fail_message:
        parts.append(on_fail_message)

    if severity == "fatal":
        parts.append("这是强制性要求，必须满足。")
    elif severity == "warning":
        parts.append("这是建议性要求，强烈建议满足。")

    return " ".join(parts)


def _generate_remediation_steps(rule: dict) -> list[str]:
    """生成修复步骤"""
    steps = []
    on_fail = rule.get("on_fail", "")
    lifecycle = rule.get("lifecycle", "")
    name = rule.get("name", "")

    if on_fail == "require_justification":
        steps.append("如果确实无法满足此要求，请在输入数据的 justifications 字段提供解释")
        steps.append(f"key 为 \"{rule.get('id', '')}\"")

    if lifecycle == "pre_calculation":
        steps.append("检查输入数据的完整性和格式")
    elif lifecycle == "post_audit":
        steps.append("检查计算结果是否符合标准要求")

    if "披露" in name:
        steps.append("在报告中添加相关披露内容")
    elif "检查" in name or "验证" in name:
        steps.append("确保数据符合规范要求")

    return steps if steps else ["请根据规则断言检查输入数据"]


def _generate_example_data(rule: dict) -> dict:
    """生成示例数据"""
    assertion = rule.get("assertion", {})
    paths = _extract_var_paths(assertion)

    example = {}
    for path in paths:
        parts = path.split(".")
        current = example
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = "<示例值>"

    return example


def _format_report_markdown(report: dict) -> str:
    """将报告格式化为 Markdown"""
    lines = []
    meta = report["report_metadata"]
    summary = report["executive_summary"]

    lines.append(f"# 合规审计报告")
    lines.append(f"")
    lines.append(f"**实体**: {meta['entity_name']}")
    lines.append(f"**规范**: {meta['spec_id']}")
    lines.append(f"**版本**: {meta['spec_version']}")
    lines.append(f"**日期**: {meta['generated_at']}")
    lines.append(f"")
    lines.append(f"## 执行摘要")
    lines.append(f"")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 合规状态 | {summary['compliance_status']} |")
    lines.append(f"| 检查规则数 | {summary['total_rules_checked']} |")
    lines.append(f"| 通过 | {summary['passed']} |")
    lines.append(f"| 警告 | {summary['warnings']} |")
    lines.append(f"| 严重失败 | {summary['critical_failures']} |")
    lines.append(f"| 覆盖率 | {summary['coverage']}% |")
    lines.append(f"")

    lines.append(f"## 支柱评估")
    lines.append(f"")
    lines.append(f"| 支柱 | 状态 | 通过/总数 | 覆盖率 |")
    lines.append(f"|------|------|----------|--------|")
    for pillar, assessment in report["pillar_assessments"].items():
        lines.append(
            f"| {pillar} | {assessment['status']} | "
            f"{assessment['passed']}/{assessment['total']} | "
            f"{assessment['coverage']}% |"
        )
    lines.append(f"")

    if report["critical_findings"]:
        lines.append(f"## 严重问题")
        lines.append(f"")
        for finding in report["critical_findings"]:
            lines.append(f"### {finding['rule_id']}: {finding['rule_name']}")
            lines.append(f"")
            lines.append(f"- **严重级别**: {finding['severity']}")
            lines.append(f"- **消息**: {finding['message']}")
            if finding["citation"]:
                lines.append(f"- **标准引用**: {finding['citation'][:200]}...")
            lines.append(f"")

    if report["warnings"]:
        lines.append(f"## 警告")
        lines.append(f"")
        for warning in report["warnings"]:
            lines.append(f"- **{warning['rule_id']}**: {warning['message']}")
        lines.append(f"")

    if report["remediation_plan"]:
        lines.append(f"## 修复计划")
        lines.append(f"")
        for i, item in enumerate(report["remediation_plan"], 1):
            lines.append(f"{i}. **{item['rule_id']}** ({item['priority']})")
            for step in item["steps"]:
                lines.append(f"   - {step}")
        lines.append(f"")

    return "\n".join(lines)
