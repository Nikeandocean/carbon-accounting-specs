"""
跨域桥接：串联碳核算审查和绿色金融判定

将 Scope 1/2 碳核算结果映射到绿色信贷、绿色债券、ISSB 合规性评估。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.types import ToolAnnotations
from mcp_server.engine import execute_rules, AuditResult
from mcp_server.loader import SpecLoader

logger = logging.getLogger(__name__)

_READ_ANN = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False,
)


# ============================================================
# 内部辅助函数
# ============================================================

def _run_scope1_audit(loader: SpecLoader, project_data: dict) -> AuditResult:
    """执行 Scope 1 碳核算审查"""
    specs = loader.load_scope("scope1")
    if not specs:
        # 回退：加载所有包含 scope1 的 spec
        specs = {k: v for k, v in loader.specs.items() if "scope1" in k}
    data = {
        "input": {
            "entity": project_data.get("entity", {}),
            "scope1_emission_sources": project_data.get("scope1_emission_sources", []),
            "emission_sources": project_data.get("emission_sources", []),
            "justifications": project_data.get("justifications", {}),
            "assumptions": project_data.get("assumptions"),
            "methodology_rationale": project_data.get("methodology_rationale"),
            "data_sources": project_data.get("data_sources"),
        },
        "output": {},
        "context": project_data.get("context", {}),
    }
    return execute_rules(specs, data, domain="scope1")


def _run_scope2_audit(loader: SpecLoader, project_data: dict) -> AuditResult:
    """执行 Scope 2 碳核算审查"""
    specs = loader.load_scope("scope2")
    if not specs:
        specs = {k: v for k, v in loader.specs.items() if "scope2" in k or k.startswith("principles/") or k.startswith("methods/") or k.startswith("constraints/") or k.startswith("reporting/")}
    data = {
        "input": {
            "entity": project_data.get("entity", {}),
            "emission_sources": project_data.get("emission_sources", []),
            "justifications": project_data.get("justifications", {}),
            "assumptions": project_data.get("assumptions"),
            "methodology_rationale": project_data.get("methodology_rationale"),
            "data_sources": project_data.get("data_sources"),
            "accounting_method": project_data.get("accounting_method"),
        },
        "output": {},
        "context": project_data.get("context", {}),
    }
    return execute_rules(specs, data, domain="scope2")


def _run_green_bond_check(loader: SpecLoader, project_data: dict, carbon_result: dict) -> AuditResult:
    """基于碳核算结果执行绿色债券资格检查"""
    specs = loader.load_domain("green-finance/bond-eligibility")
    if not specs:
        specs = {k: v for k, v in loader.specs.items() if "bond-eligibility" in k}

    scope1_total = carbon_result.get("scope1_total_tco2e", 0)
    scope2_total = carbon_result.get("scope2_total_tco2e", 0)

    data = {
        "project": {
            "name": project_data.get("entity", {}).get("name", ""),
            "category_l1": project_data.get("project_category_l1", ""),
            "category_l2": project_data.get("project_category_l2", ""),
            "category_l2_prefix": project_data.get("project_category_l2", "").split(".")[0] if project_data.get("project_category_l2") else "",
            "description": project_data.get("project_description", ""),
        },
        "input": {
            "entity": {
                "scope1_emission_intensity": scope1_total,
                "scope2_emission_intensity": scope2_total,
            },
            "evaluation": {
                "purpose": "green_bond",
            },
            "justifications": project_data.get("justifications", {}),
        },
        "context": {
            "industry_benchmark": project_data.get("context", {}).get("industry_benchmark", {}),
        },
    }
    return execute_rules(specs, data, domain="green_bond")


def _run_green_credit_check(loader: SpecLoader, project_data: dict, carbon_result: dict) -> AuditResult:
    """基于碳核算结果执行绿色信贷分类检查"""
    specs = loader.load_domain("green-finance/credit-classification")
    if not specs:
        specs = {k: v for k, v in loader.specs.items() if "credit-classification" in k}

    data = {
        "input": {
            "loan": {
                "project_industry": project_data.get("industry", ""),
                "project_type": project_data.get("project_type", ""),
                "emission_intensity": carbon_result.get("emission_intensity", None),
            },
            "borrower": {
                "name": project_data.get("entity", {}).get("name", ""),
            },
            "evaluation": {
                "purpose": "green_credit",
            },
            "justifications": project_data.get("justifications", {}),
        },
        "context": {
            "green_industry_catalog": [
                "节能环保", "清洁生产", "清洁能源", "生态环境",
                "基础设施绿色升级", "绿色服务",
            ],
            "restricted_industries": [
                "钢铁（新增产能）", "水泥（新增产能）",
                "电解铝（新增产能）", "平板玻璃（新增产能）",
                "煤化工（新增产能）",
            ],
            "industry_benchmark_emission_intensity": project_data.get("context", {}).get(
                "industry_benchmark_emission_intensity", None
            ),
        },
    }
    return execute_rules(specs, data, domain="green_credit")


def _determine_overall(carbon_audit: AuditResult, green_bond: AuditResult, green_credit: AuditResult) -> str:
    """综合判定：pass / conditional / fail"""
    # 碳核算有 fatal → fail
    if carbon_audit.compliance == "fatal":
        return "fail"
    # 绿色债券有 fatal → fail
    if green_bond.compliance == "fatal":
        return "fail"
    # 绿色信贷有 fatal → fail
    if green_credit.compliance == "fatal":
        return "fail"
    # 有 warning → conditional
    if any(r == "warning" for r in [carbon_audit.compliance, green_bond.compliance, green_credit.compliance]):
        return "conditional"
    return "pass"


# ============================================================
# 跨域审查主函数
# ============================================================

def cross_domain_audit(loader: SpecLoader, project_data: dict) -> dict:
    """
    跨域桥接审查：串联碳核算和绿色金融判定。

    Args:
        loader: 已加载所有 spec 的 SpecLoader 实例
        project_data: 项目数据，包含：
            - entity: {name, reporting_year, ...}
            - scope1_emission_sources: Scope 1 排放源列表
            - emission_sources: Scope 2 排放源列表
            - project_category_l2: 绿色债券目录二级分类（如 C3.1）
            - project_description: 项目描述
            - industry: 行业
            - context: 上下文数据

    Returns:
        综合审查结果字典
    """
    # Step 1: 碳核算审查
    scope1_result = _run_scope1_audit(loader, project_data)
    scope2_result = _run_scope2_audit(loader, project_data)

    # 汇总碳核算结果
    carbon_audit = {
        "scope1": scope1_result.to_dict(),
        "scope2": scope2_result.to_dict(),
        "overall_compliance": "pass",
    }
    if scope1_result.compliance == "fatal" or scope2_result.compliance == "fatal":
        carbon_audit["overall_compliance"] = "fatal"
    elif scope1_result.compliance == "warning" or scope2_result.compliance == "warning":
        carbon_audit["overall_compliance"] = "warning"

    # 从审查结果中提取排放汇总（供下游使用）
    scope1_total = 0.0
    scope2_total = 0.0
    # 尝试从 project_data 中直接获取汇总数据
    if "scope1_total_tco2e" in project_data:
        scope1_total = project_data["scope1_total_tco2e"]
    if "scope2_total_tco2e" in project_data:
        scope2_total = project_data["scope2_total_tco2e"]

    carbon_summary = {
        "scope1_total_tco2e": scope1_total,
        "scope2_total_tco2e": scope2_total,
        "emission_intensity": project_data.get("emission_intensity"),
    }

    # Step 2: 绿色债券资格检查
    green_bond_result = _run_green_bond_check(loader, project_data, carbon_summary)

    # Step 3: 绿色信贷分类检查
    green_credit_result = _run_green_credit_check(loader, project_data, carbon_summary)

    # Step 4: 综合判定
    overall = _determine_overall(scope1_result, green_bond_result, green_credit_result)

    return {
        "carbon_audit": carbon_audit,
        "green_bond": green_bond_result.to_dict(),
        "green_credit": green_credit_result.to_dict(),
        "overall": overall,
    }


# ============================================================
# MCP Tool 注册
# ============================================================

def register_bridge_tools(mcp: Any, loader: SpecLoader) -> None:
    """注册跨域桥接 MCP 工具"""

    @mcp.tool(annotations=_READ_ANN)
    async def full_green_finance_audit(project_data: str) -> str:
        """一站式绿色金融合规审查（碳数据 + 金融资格）。

        串联 Scope 1/2 碳核算审查 → 绿色债券资格检查 → 绿色信贷分类 → 综合报告。

        Args:
            project_data: JSON 字符串，包含项目信息和排放数据。结构示例：
                {
                    "entity": {"name": "企业名称", "reporting_year": 2025},
                    "scope1_emission_sources": [...],
                    "emission_sources": [...],
                    "project_category_l2": "C3.1",
                    "project_description": "100MW光伏发电项目",
                    "industry": "清洁能源",
                    "context": {"industry_benchmark": {...}}
                }
        """
        try:
            data = json.loads(project_data)
            result = cross_domain_audit(loader, data)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"JSON 解析失败: {e}"}, ensure_ascii=False)
        except Exception as e:
            logger.exception("full_green_finance_audit failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)
