"""
碳核算域 MCP Tools（域1：GHG Protocol Scope 1 & Scope 2）

提供合规审查、规则查询、失败解释等工具函数。
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .engine import execute_rules
from .loader import SpecLoader

_READ_ANN = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False,
)


def register_ghg_tools(mcp: FastMCP, loader: SpecLoader) -> None:
    """注册所有碳核算域 MCP 工具"""

    @mcp.tool(annotations=_READ_ANN)
    def audit_scope1(
        entity_name: str,
        reporting_year: int,
        emission_sources: str,
    ) -> str:
        """
        审查 Scope 1 直接排放数据合规性。

        根据 GHG Protocol Corporate Standard 对企业直接排放数据进行规则校验，
        包括排放源分类、活动数据完整性、排放因子合规性等。

        Args:
            entity_name: 企业名称
            reporting_year: 报告年度（如 2025）
            emission_sources: 排放源 JSON 数组字符串，每个元素包含：
                - id: 排放源唯一标识
                - type: 类型（stationary_combustion/mobile_combustion/process/fugitive）
                - fuel_type: 燃料类型（燃烧源必填）
                - activity_data: 活动数据数值
                - activity_unit: 单位（tonnes/litres/cubic_metres/GJ/kWh/km）
                - emission_factor: 排放因子对象（含 value, year, source）
                - gwp_source: GWP来源（IPCC_AR4/AR5/AR6）

        Returns:
            JSON 字符串，包含 compliance（pass/warning/fatal）、summary（统计）、results（逐条结果）
        """
        try:
            sources = json.loads(emission_sources)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"emission_sources JSON 解析失败: {e}"}, ensure_ascii=False)

        data = {
            "input": {
                "entity": {
                    "name": entity_name,
                    "reporting_year": reporting_year,
                },
                "scope1_emission_sources": sources,
            }
        }

        specs = loader.load_scope("scope1")
        # 同时加载 global_rules（_meta.yaml 中的全局规则）
        specs["_meta"] = {"rules": loader.meta.get("global_rules", [])}

        result = execute_rules(specs, data, domain="scope1")
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    @mcp.tool(annotations=_READ_ANN)
    def audit_scope2(
        entity_name: str,
        reporting_year: int,
        emission_sources: str,
        method: str = "dual",
    ) -> str:
        """
        审查 Scope 2 外购能源排放数据合规性。

        根据 GHG Protocol Scope 2 Guidance 对企业外购电力、蒸汽、热力、冷量
        进行规则校验，支持 location-based、market-based 和 dual 双重报告审查。

        Args:
            entity_name: 企业名称
            reporting_year: 报告年度（如 2025）
            emission_sources: 排放源 JSON 数组字符串，每个元素包含：
                - id: 排放源唯一标识
                - type: 类型（electricity/steam/heat/cooling）
                - activity_data: 活动数据（MWh）
                - emission_factor: 排放因子对象（含 value, year, source, type）
            method: 核算方法，可选值：
                - "location": 仅审查 location-based 方法
                - "market": 仅审查 market-based 方法
                - "dual": 审查双重报告（默认）

        Returns:
            JSON 字符串，包含 compliance（pass/warning/fatal）、summary（统计）、results（逐条结果）
        """
        try:
            sources = json.loads(emission_sources)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"emission_sources JSON 解析失败: {e}"}, ensure_ascii=False)

        valid_methods = ("location", "market", "dual")
        if method not in valid_methods:
            return json.dumps(
                {"error": f"method 必须为 {valid_methods} 之一，当前值: {method}"},
                ensure_ascii=False,
            )

        data = {
            "input": {
                "entity": {
                    "name": entity_name,
                    "reporting_year": reporting_year,
                    "accounting_method": method if method != "dual" else "dual_reporting",
                },
                "emission_sources": sources,
            }
        }

        # Scope 2 规范分布在顶层目录（principles/, methods/, constraints/ 等）
        # 加载所有规范并让 condition 条件自动过滤
        specs = dict(loader.specs)
        specs["_meta"] = {"rules": loader.meta.get("global_rules", [])}

        result = execute_rules(specs, data, domain="scope2")
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    @mcp.tool(annotations=_READ_ANN)
    def get_rule(rule_id: str) -> str:
        """
        查询规则详情和关联的标准引用。

        Args:
            rule_id: 规则 ID（如 rule-001, proh-001, global-001）

        Returns:
            JSON 字符串，包含规则的 id、name、severity、lifecycle、assertion、on_fail、citations 等详情
        """
        # 先从各 spec 文件中查找
        rule = loader.get_rule(rule_id)

        # 若未找到，检查 global_rules
        if rule is None:
            for gr in loader.meta.get("global_rules", []):
                if gr.get("id") == rule_id:
                    rule = gr
                    break

        if rule is None:
            return json.dumps({"error": f"未找到规则: {rule_id}"}, ensure_ascii=False)

        # 构造详情，包含关联的 citation 原文
        detail = {
            "id": rule.get("id"),
            "name": rule.get("name"),
            "priority": rule.get("priority"),
            "severity": rule.get("severity"),
            "layer": rule.get("layer"),
            "lifecycle": rule.get("lifecycle"),
            "on_fail": rule.get("on_fail"),
            "on_fail_message": rule.get("on_fail_message"),
            "condition": rule.get("condition"),
            "assertion": rule.get("assertion"),
            "citation_ref": rule.get("citation_ref") or rule.get("citation"),
        }

        # 附加 citation 原文
        cit_ref = detail["citation_ref"]
        if cit_ref and cit_ref.startswith("cit-"):
            cit = loader.get_citation(cit_ref)
            if cit:
                detail["citation_text"] = cit.get("text", "")
                detail["citation_spec"] = cit.get("spec", "")

        return json.dumps(detail, ensure_ascii=False, indent=2)

    @mcp.tool(annotations=_READ_ANN)
    def list_rules(scope: str | None = None, lifecycle: str | None = None) -> str:
        """
        列出适用的规则。

        Args:
            scope: 按 scope 过滤（如 "scope1", "scope2", "scope3"），不指定则返回全部
            lifecycle: 按生命周期阶段过滤（如 "pre_calculation", "runtime_inference", "post_audit"）

        Returns:
            JSON 字符串，包含规则列表（id、name、severity、lifecycle、spec 来源文件）
        """
        rules = loader.list_rules(scope=scope, lifecycle=lifecycle)

        # 同时包含 global_rules 中匹配的规则
        for gr in loader.meta.get("global_rules", []):
            if gr.get("layer") == "knowledge":
                continue
            if lifecycle and gr.get("lifecycle") != lifecycle:
                continue
            # scope 过滤：global_rules 有 scope 字段（如 "scope1_only"）
            if scope:
                gr_scope = gr.get("scope", "")
                if scope not in gr_scope and gr_scope:
                    continue
            rules.append({
                "id": gr.get("id"),
                "name": gr.get("name"),
                "severity": gr.get("severity"),
                "lifecycle": gr.get("lifecycle"),
                "spec": "_meta (global_rules)",
            })

        return json.dumps({"total": len(rules), "rules": rules}, ensure_ascii=False, indent=2)

    @mcp.tool(annotations=_READ_ANN)
    def explain_failure(rule_id: str, data: str) -> str:
        """
        解释规则失败原因并提供修复建议。

        对指定规则重新执行，若失败则返回详细的失败原因、引用原文和修复建议。

        Args:
            rule_id: 规则 ID（如 rule-001, proh-001, global-001）
            data: 待审查数据 JSON 字符串，结构与 audit_scope1/audit_scope2 的输入数据相同

        Returns:
            JSON 字符串，包含：
            - rule_id: 规则 ID
            - rule_name: 规则名称
            - passed: 是否通过
            - message: 失败/通过消息
            - citation_text: 引用的标准原文
            - suggestion: 修复建议
            - assertion: 规则断言表达式（供技术人员参考）
        """
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"data JSON 解析失败: {e}"}, ensure_ascii=False)

        # 查找规则
        rule = loader.get_rule(rule_id)
        found_in = "spec"
        if rule is None:
            for gr in loader.meta.get("global_rules", []):
                if gr.get("id") == rule_id:
                    rule = gr
                    found_in = "global_rules"
                    break

        if rule is None:
            return json.dumps({"error": f"未找到规则: {rule_id}"}, ensure_ascii=False)

        # 用单条规则构造 spec 来执行
        single_spec = {"rules": [rule]}
        if found_in == "global_rules":
            specs = {"_meta": single_spec}
        else:
            # 找到 rule 所在的 spec 文件
            specs = {}
            for path, spec in loader.specs.items():
                for r in spec.get("rules", []):
                    if r.get("id") == rule_id:
                        specs[path] = spec
                        break
                if specs:
                    break

        result = execute_rules(specs, parsed_data, domain="explain")

        # 提取执行结果
        rule_result = None
        for r in result.results:
            if r.rule_id == rule_id:
                rule_result = r
                break

        if rule_result is None:
            # 规则因 condition 不满足而被跳过
            return json.dumps({
                "rule_id": rule_id,
                "rule_name": rule.get("name", ""),
                "passed": None,
                "status": "skipped",
                "message": "规则因前置条件（condition）不满足而被跳过，未执行断言检查。",
                "condition": rule.get("condition"),
                "assertion": rule.get("assertion"),
            }, ensure_ascii=False, indent=2)

        # 构造修复建议
        suggestion = _build_suggestion(rule, rule_result)

        return json.dumps({
            "rule_id": rule_result.rule_id,
            "rule_name": rule_result.rule_name,
            "passed": rule_result.passed,
            "status": rule_result.to_dict()["status"],
            "message": rule_result.message,
            "severity": rule_result.severity,
            "lifecycle": rule_result.lifecycle,
            "assertion": rule.get("assertion"),
            "on_fail": rule.get("on_fail"),
            "citation_text": rule_result.citation or rule.get("citation"),
            "suggestion": suggestion,
        }, ensure_ascii=False, indent=2)


def _build_suggestion(rule: dict[str, Any], result: Any) -> str:
    """根据规则类型和失败原因生成修复建议"""
    rule_id = rule.get("id", "")
    on_fail = rule.get("on_fail", "")
    lifecycle = rule.get("lifecycle", "")

    parts: list[str] = []

    if on_fail == "require_justification":
        parts.append(
            f"此规则采用 Comply or Explain 模式。若确实无法满足，"
            f"请在输入数据的 justifications 字段中提供合规性解释，"
            f"key 为 \"{rule_id}\"。"
        )
    elif on_fail == "raise_fatal":
        parts.append("此规则为 fatal 级别，必须修复后重新提交审查。")
    elif on_fail == "raise_warning":
        parts.append("此规则为 warning 级别，建议修复以提高数据质量。")

    if lifecycle == "pre_calculation":
        parts.append("此规则在计算前校验，请检查输入数据的完整性和格式。")
    elif lifecycle == "post_audit":
        parts.append("此规则在计算后审计，请检查计算结果是否符合标准要求。")

    if result.citation:
        parts.append(f"参考标准原文: {result.citation[:200]}...")

    return " ".join(parts) if parts else "请根据规则断言检查输入数据。"
