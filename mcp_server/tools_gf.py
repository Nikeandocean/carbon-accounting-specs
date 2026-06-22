"""
绿色金融域 MCP Tools（域2）

注册绿色债券、绿色信贷、ISSB S2 合规性审查等工具。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp_server.engine import execute_rules, AuditResult
from mcp_server.loader import SpecLoader

logger = logging.getLogger(__name__)


# ============================================================
# 关键词映射：项目描述 → 绿色债券目录类别
# ============================================================

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    # 节能环保产业
    "C1.1": ["节能装备", "高效节能", "能效设备", "变频器", "节能电机", "余热锅炉"],
    "C1.2": ["环保装备", "除尘设备", "脱硫脱硝", "污水处理设备", "环保技术装备"],
    "C1.3": ["资源循环", "再生资源", "废品回收", "资源综合利用", "循环利用"],
    "C1.4": ["绿色交通装备", "新能源汽车零部件", "电动客车", "混合动力"],
    "C1.5": ["节能产品", "LED照明", "高效空调", "节能家电"],
    "C1.6": ["节能服务", "合同能源管理", "EMC", "能效诊断"],
    # 清洁生产产业
    "C2.1": ["有毒有害替代", "无毒替代", "低毒材料", "有害物质替代"],
    "C2.2": ["清洁生产", "清洁化改造", "超低排放", "绿色制造"],
    "C2.3": ["废弃物资源化", "废物利用", "工业固废", "资源化利用"],
    "C2.4": ["农业清洁", "有机农业", "生态农业", "绿色农业"],
    # 清洁能源产业
    "C3.1": ["太阳能", "光伏发电", "光伏组件", "分布式光伏", "集中式光伏"],
    "C3.2": ["风力发电", "风电", "风电机组", "海上风电", "陆上风电"],
    "C3.3": ["水力发电", "水电", "水电机组", "小水电", "抽水蓄能"],
    "C3.4": ["生物质能", "生物质发电", "沼气", "生物质燃料", "秸秆发电"],
    "C3.5": ["余热余压", "余热发电", "余压利用", "热电联产节能"],
    "C3.6": ["地热能", "地热发电", "地热供暖", "地源热泵"],
    "C3.7": ["海洋能", "潮汐能", "波浪能", "海洋发电"],
    "C3.8": ["氢能", "氢燃料电池", "绿氢", "氢能源", "电解水制氢"],
    # 生态环境产业
    "C4.1": ["自然保护", "自然保护区", "生态保护", "生物多样性保护"],
    "C4.2": ["生态修复", "矿山修复", "湿地修复", "土壤修复", "植被恢复"],
    "C4.3": ["国土整治", "土地整治", "矿山治理", "流域治理"],
    "C4.4": ["生物多样性", "种质资源", "濒危物种保护"],
    # 基础设施绿色升级
    "C5.1": ["绿色交通", "轨道交通", "地铁", "充电桩", "充换电", "新能源公交", "电动物流"],
    "C5.2": ["污水处理", "污水厂", "中水回用", "水环境治理"],
    "C5.3": ["垃圾处理", "垃圾焚烧", "垃圾发电", "固废处置", "资源化利用"],
    "C5.4": ["园林绿化", "城市绿化", "公园建设", "生态景观"],
    "C5.5": ["海绵城市", "雨水收集", "透水铺装", "雨水花园"],
    "C5.6": ["绿色建筑", "建筑节能", "被动房", "近零能耗建筑", "绿色改造"],
    # 绿色服务
    "C6.1": ["绿色咨询", "环境咨询", "碳咨询", "ESG咨询"],
    "C6.2": ["绿色认证", "碳认证", "环境认证", "绿色标识"],
    "C6.3": ["环境监测", "污染监测", "在线监测", "环境检测"],
    "C6.4": ["碳交易", "碳排放权", "碳配额", "CCER", "碳市场"],
    "C6.5": ["绿色技术推广", "环保技术", "清洁技术转让"],
}


# ============================================================
# 工具注册
# ============================================================

def register_gf_tools(mcp: Any, loader: SpecLoader) -> None:
    """注册绿色金融域 MCP 工具"""

    @mcp.tool()
    async def check_green_bond(
        project_name: str,
        industry_category: str,
        project_description: str,
        emissions_data: str = "{}",
        technology_type: str = "",
    ) -> str:
        """检查项目是否符合绿色债券支持项目目录要求。

        Args:
            project_name: 项目名称
            industry_category: 行业类别（如 C3.1、C5.2 等二级分类编码）
            project_description: 项目描述
            emissions_data: 排放数据 JSON 字符串
            technology_type: 技术类型
        """
        try:
            specs = loader.load_domain("green-finance/bond-eligibility")
            if not specs:
                specs = loader.load_domain("green-finance")

            emissions = json.loads(emissions_data) if emissions_data else {}

            data = {
                "project": {
                    "name": project_name,
                    "category_l2": industry_category,
                    "category_l2_prefix": industry_category.split(".")[0] if "." in industry_category else industry_category,
                    "description": project_description,
                    "technology_type": technology_type,
                    **emissions,
                },
            }

            result = execute_rules(specs, data, domain="green_bond")

            matched_categories = []
            missing_criteria = []
            for r in result.results:
                if r.passed:
                    matched_categories.append(r.rule_name)
                elif r.severity == "fatal":
                    missing_criteria.append(r.message)

            eligible = "yes"
            if result.compliance == "fatal":
                eligible = "no"
            elif result.compliance == "warning":
                eligible = "conditional"

            return json.dumps({
                "eligible": eligible,
                "matched_categories": matched_categories,
                "missing_criteria": missing_criteria,
                "total_rules": result.total_rules,
                "passed": result.passed,
                "warnings": result.warnings,
                "fatal": result.fatal,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("check_green_bond failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    async def check_green_credit(
        project_name: str,
        industry_code: str,
        loan_purpose: str,
        emissions_intensity: float = 0.0,
    ) -> str:
        """检查贷款项目是否属于绿色信贷范畴。

        Args:
            project_name: 项目名称
            industry_code: 行业代码
            loan_purpose: 贷款用途
            emissions_intensity: 排放强度（tCO2e/万元产值）
        """
        try:
            specs = loader.load_domain("green-finance/credit-classification")
            if not specs:
                specs = loader.load_domain("green-finance")

            data = {
                "input": {
                    "loan": {
                        "project_industry": industry_code,
                        "project_type": loan_purpose,
                        "emission_intensity": emissions_intensity if emissions_intensity > 0 else None,
                    },
                    "borrower": {
                        "name": project_name,
                    },
                },
                "context": {
                    "green_industry_catalog": [
                        "节能环保", "清洁生产", "清洁能源", "生态环境",
                        "基础设施绿色升级", "绿色服务",
                        "电力", "能源", "交通运输", "汽车制造",
                    ],
                    "restricted_industries": [
                        "钢铁（新增产能）", "水泥（新增产能）",
                        "电解铝（新增产能）", "平板玻璃（新增产能）",
                        "煤化工（新增产能）",
                    ],
                },
            }

            result = execute_rules(specs, data, domain="green_credit")

            classification = "green"
            reason_parts = []
            for r in result.results:
                if not r.passed and r.severity == "fatal":
                    classification = "ineligible"
                    reason_parts.append(r.message)
                elif not r.passed and r.severity == "warning":
                    if classification != "ineligible":
                        classification = "concern"
                    reason_parts.append(r.message)

            reason = "; ".join(reason_parts) if reason_parts else "符合绿色信贷条件"

            return json.dumps({
                "classification": classification,
                "reason": reason,
                "total_rules": result.total_rules,
                "passed": result.passed,
                "warnings": result.warnings,
                "fatal": result.fatal,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("check_green_credit failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    async def check_issb_s2(
        entity_name: str,
        scope1_emissions: float = 0.0,
        scope2_emissions: float = 0.0,
        scope3_emissions: float = 0.0,
        has_reduction_target: bool = False,
        carbon_credits_used: bool = False,
    ) -> str:
        """检查企业气候披露是否满足 ISSB S2 要求。

        Args:
            entity_name: 企业名称
            scope1_emissions: Scope 1 排放量（tCO2e）
            scope2_emissions: Scope 2 排放量（tCO2e）
            scope3_emissions: Scope 3 排放量（tCO2e），可选
            has_reduction_target: 是否已设定减排目标
            carbon_credits_used: 是否使用碳信用
        """
        try:
            specs = loader.load_domain("green-finance/issb-s2-disclosure")
            if not specs:
                specs = loader.load_domain("green-finance")

            data = {
                "input": {
                    "entity": {
                        "name": entity_name,
                        "reporting_year": 2025,
                        "has_reduction_target": has_reduction_target,
                        "uses_carbon_credits": carbon_credits_used,
                    },
                    "justifications": {},
                },
                "output": {
                    "governance": {
                        "climate_governance_body": None,
                        "management_role": None,
                    },
                    "strategy": {
                        "climate_risks_opportunities": None,
                        "transition_plan": None,
                        "financial_effects": None,
                    },
                    "risk_management": {
                        "risk_identification_process": None,
                        "overall_risk_integration": None,
                    },
                    "metrics": {
                        "ghg": {
                            "scope1_emissions_tco2e": scope1_emissions if scope1_emissions > 0 else None,
                            "scope2_location_based_tco2e": scope2_emissions if scope2_emissions > 0 else None,
                            "scope2_market_based_tco2e": scope2_emissions if scope2_emissions > 0 else None,
                            "scope3_emissions_tco2e": scope3_emissions if scope3_emissions > 0 else None,
                            "unit": "tCO2e",
                            "gwp_source": "IPCC_AR6",
                        },
                    },
                    "targets": {
                        "emission_reduction_targets": None,
                    },
                },
            }

            result = execute_rules(specs, data, domain="issb_s2")

            gaps = []
            for r in result.results:
                if not r.passed:
                    gaps.append({
                        "rule_id": r.rule_id,
                        "rule_name": r.rule_name,
                        "severity": r.severity,
                        "message": r.message,
                        "citation": r.citation,
                    })

            compliant = result.compliance == "pass"

            return json.dumps({
                "compliant": compliant,
                "gaps": gaps,
                "total_rules": result.total_rules,
                "passed": result.passed,
                "warnings": result.warnings,
                "fatal": result.fatal,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("check_issb_s2 failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    async def classify_project(
        project_description: str,
        industry: str = "",
    ) -> str:
        """根据项目描述自动匹配绿色债券目录类别。

        Args:
            project_description: 项目描述
            industry: 行业领域（可选，用于缩小匹配范围）
        """
        try:
            # 加载 bond-catalog 获取完整目录结构
            specs = loader.load_domain("green-finance/bond-catalog")
            catalog_spec = None
            for spec in specs.values():
                if "category_catalog" in spec:
                    catalog_spec = spec
                    break

            # 构建 category_id -> category_name 映射
            cat_map: dict[str, str] = {}
            if catalog_spec:
                for cat in catalog_spec.get("category_catalog", []):
                    for sub in cat.get("subcategories", []):
                        cat_map[sub["id"]] = f"{cat['name']} > {sub['name']}"

            # 关键词匹配
            desc_lower = project_description.lower()
            scores: dict[str, float] = {}

            for cat_id, keywords in _CATEGORY_KEYWORDS.items():
                match_count = 0
                for kw in keywords:
                    if kw.lower() in desc_lower:
                        match_count += 1
                if match_count > 0:
                    # 分数 = 匹配关键词数 / 该类别总关键词数，上限 1.0
                    scores[cat_id] = min(match_count / len(keywords) * 2, 1.0)

            # 按分数降序排列
            sorted_matches = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            matched_categories = []
            for cat_id, score in sorted_matches[:5]:  # 最多返回 5 个
                matched_categories.append({
                    "category_id": cat_id,
                    "category_name": cat_map.get(cat_id, cat_id),
                    "confidence": round(score, 2),
                })

            # 计算最高置信度
            top_confidence = matched_categories[0]["confidence"] if matched_categories else 0.0

            return json.dumps({
                "matched_categories": matched_categories,
                "confidence": top_confidence,
                "input_description": project_description,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("classify_project failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    async def get_gf_rule(rule_id: str) -> str:
        """查询绿色金融规则详情。

        Args:
            rule_id: 规则 ID（如 gbe-001、gf-cc-005、gf-s2-011 等）
        """
        try:
            rule = loader.get_rule(rule_id)
            if not rule:
                return json.dumps(
                    {"error": f"未找到规则: {rule_id}"},
                    ensure_ascii=False,
                )

            # 查找关联的 citation
            citation_text = ""
            citation_ref = rule.get("citation", "")
            if citation_ref:
                cit = loader.get_citation(citation_ref)
                if cit:
                    citation_text = cit.get("text", "")

            return json.dumps({
                "rule_id": rule.get("id"),
                "name": rule.get("name"),
                "type": rule.get("type"),
                "priority": rule.get("priority"),
                "severity": rule.get("severity"),
                "layer": rule.get("layer"),
                "lifecycle": rule.get("lifecycle"),
                "condition": rule.get("condition"),
                "assertion": rule.get("assertion"),
                "on_fail": rule.get("on_fail"),
                "on_fail_message": rule.get("on_fail_message"),
                "citation_ref": citation_ref,
                "citation_text": citation_text,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("get_gf_rule failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)
