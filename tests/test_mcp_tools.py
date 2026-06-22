"""
MCP 工具端到端测试

测试 GHG Protocol (域1) 和绿色金融 (域2) 的 MCP 工具。
使用 pytest 框架，直接调用 SpecLoader + execute_rules 验证工具逻辑。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server.engine import AuditResult, execute_rules
from mcp_server.loader import SpecLoader

# ============================================================
# Fixtures
# ============================================================

SPEC_DIR = Path(__file__).resolve().parent.parent / "specs"


@pytest.fixture(scope="module")
def loader() -> SpecLoader:
    """加载全部 spec 文件（module 级别共享）"""
    ldr = SpecLoader(SPEC_DIR)
    ldr.load_all()
    return ldr


# ============================================================
# 域1: GHG Protocol Scope 2 测试数据
# ============================================================

VALID_SCOPE2_SOURCES = [
    {
        "id": "elec-001",
        "type": "electricity",
        "activity_data": 5000,
        "emission_factor": {
            "value": 0.5703,
            "year": 2025,
            "source": "生态环境部",
            "type": "grid_average",
        },
    },
    {
        "id": "elec-002",
        "type": "electricity",
        "activity_data": 3000,
        "emission_factor": {
            "value": 0.0,
            "year": 2025,
            "source": "绿证",
            "type": "certificate",
        },
    },
]

INVALID_SCOPE2_SOURCES = [
    {
        "id": "elec-001",
        "type": "electricity",
        "activity_data": 1000,
        "emission_factor": {
            "value": 0.5703,
            "year": 2022,  # 因子年份不匹配
            "source": "旧数据",
            "type": "default",  # 使用缺省因子
        },
    },
]


def _build_scope2_data(sources: list, *, include_meta: bool = True) -> dict:
    """构造 audit_scope2 所需的完整输入数据"""
    data: dict = {
        "input": {
            "entity": {
                "name": "测试企业",
                "reporting_year": 2025,
                "accounting_method": "dual_reporting",
            },
            "emission_sources": sources,
            # 双重报告需要分别提供 location-based 和 market-based 输入
            "location_based_input": {
                "emission_sources": sources,
                "method": "location_based",
            },
            "market_based_input": {
                "emission_sources": sources,
                "method": "market_based",
            },
        },
    }
    if include_meta:
        data["input"]["assumptions"] = "使用国家电网平均排放因子"
        data["input"]["methodology_rationale"] = "采用位置法和市场法双重报告"
        data["input"]["data_sources"] = "生态环境部发布的排放因子"
        data["context"] = {
            "region": {
                "country_code": "CN",
                "has_market_instruments": True,
                "grid_average_ef": 0.5703,
            },
            "emission_factors": {
                "current_year": 0.5703,
                "previous_year": 0.5810,
                "latest_available": 0.5703,
                "latest_year": 2025,
            },
        }
    return data


def _audit_scope2(loader: SpecLoader, sources: list, **kwargs) -> AuditResult:
    """模拟 audit_scope2 工具调用"""
    data = _build_scope2_data(sources, **kwargs)
    specs = dict(loader.specs)
    specs["_meta"] = {"rules": loader.meta.get("global_rules", [])}
    return execute_rules(specs, data, domain="scope2")


# ============================================================
# 测试用例
# ============================================================


class TestAuditScope2:
    """audit_scope2 工具测试"""

    def test_audit_scope2_valid(self, loader: SpecLoader) -> None:
        """用合规数据测试 audit_scope2 —— Scope 2 核心规则不应有 fatal 错误"""
        result = _audit_scope2(loader, VALID_SCOPE2_SOURCES)

        assert isinstance(result, AuditResult)
        assert result.domain == "scope2"
        assert result.total_rules > 0

        # Scope 2 核心规则（rule-op-*, rule-lb-*, rule-mb-*, rule-dr-*, cert-*）不应 fatal
        # 注意：audit_scope2 加载全部 spec，跨域规则（s1-*, s3-*）可能因数据缺失而触发
        scope2_prefixes = ("rule-op", "rule-lb", "rule-mb", "rule-dr", "rule-cert", "cert-", "qc-")
        scope2_fatal = [
            r for r in result.results
            if not r.passed and r.severity == "fatal"
            and any(r.rule_id.startswith(p) for p in scope2_prefixes)
        ]
        assert len(scope2_fatal) == 0, (
            f"合规数据不应触发 Scope 2 核心规则 fatal，实际: {len(scope2_fatal)} 条\n"
            + "\n".join(f"  [{r.rule_id}] {r.message}" for r in scope2_fatal)
        )

    def test_audit_scope2_invalid(self, loader: SpecLoader) -> None:
        """用不合规数据测试 audit_scope2 —— 应检测到问题"""
        result = _audit_scope2(loader, INVALID_SCOPE2_SOURCES, include_meta=False)

        assert isinstance(result, AuditResult)
        # 不合规数据应触发至少一条失败
        failed = [r for r in result.results if not r.passed]
        assert len(failed) > 0, "不合规数据应至少触发一条规则失败"


class TestGetRule:
    """get_rule 工具测试"""

    def test_get_rule_known(self, loader: SpecLoader) -> None:
        """查询已知规则 —— 应返回完整详情"""
        # global-001 是 _meta.yaml 中的全局规则
        rule = None
        for gr in loader.meta.get("global_rules", []):
            if gr.get("id") == "global-001":
                rule = gr
                break

        assert rule is not None, "global-001 应存在于 global_rules 中"
        assert rule["name"] == "完整性原则"
        assert rule["severity"] == "fatal"

    def test_get_rule_from_spec(self, loader: SpecLoader) -> None:
        """从 spec 文件中查询规则"""
        # 遍历所有 spec 查找第一个有 assertion 的规则
        found = False
        for spec in loader.specs.values():
            for rule in spec.get("rules", []):
                if rule.get("assertion") and rule.get("layer") != "knowledge":
                    assert rule["id"] is not None
                    assert rule["name"] is not None
                    found = True
                    break
            if found:
                break

        assert found, "应至少存在一条 schema 层规则"

    def test_get_rule_not_found(self, loader: SpecLoader) -> None:
        """查询不存在的规则 —— 应返回 None"""
        rule = loader.get_rule("nonexistent-rule-999")
        assert rule is None


class TestListRules:
    """list_rules 工具测试"""

    def test_list_rules_all(self, loader: SpecLoader) -> None:
        """列出全部规则 —— 应有非零条目"""
        rules = loader.list_rules()
        assert len(rules) > 0, "应至少有一条规则"

    def test_list_rules_by_scope(self, loader: SpecLoader) -> None:
        """按 scope 过滤规则"""
        scope1_rules = loader.list_rules(scope="scope1")
        scope2_rules = loader.list_rules(scope="scope2")

        # scope1 和 scope2 的规则应各自独立存在
        assert len(scope1_rules) > 0, "scope1 应有规则"
        assert len(scope2_rules) > 0, "scope2 应有规则"

        # scope1 规则不应出现在 scope2 列表中
        scope1_ids = {r["id"] for r in scope1_rules}
        scope2_ids = {r["id"] for r in scope2_rules}
        # 允许 global 规则同时出现在两个列表中，但 spec 级别的不应重叠
        spec_scope1 = {r["id"] for r in scope1_rules if not r["spec"].startswith("_meta")}
        spec_scope2 = {r["id"] for r in scope2_rules if not r["spec"].startswith("_meta")}
        assert spec_scope1.isdisjoint(spec_scope2), (
            f"scope1 和 scope2 的 spec 规则不应重叠: {spec_scope1 & spec_scope2}"
        )

    def test_list_rules_by_lifecycle(self, loader: SpecLoader) -> None:
        """按 lifecycle 过滤规则"""
        pre_rules = loader.list_rules(lifecycle="pre_calculation")
        post_rules = loader.list_rules(lifecycle="post_audit")

        assert len(pre_rules) > 0, "pre_calculation 阶段应有规则"
        assert len(post_rules) > 0, "post_audit 阶段应有规则"

        # 每条规则的 lifecycle 应匹配过滤条件
        for r in pre_rules:
            assert r["lifecycle"] == "pre_calculation"
        for r in post_rules:
            assert r["lifecycle"] == "post_audit"


class TestCheckGreenBond:
    """check_green_bond 工具测试"""

    def test_green_bond_eligible(self, loader: SpecLoader) -> None:
        """符合条件的绿色债券项目 —— 应返回 eligible"""
        specs = loader.load_domain("green-finance/bond-eligibility")
        if not specs:
            specs = loader.load_domain("green-finance")

        if not specs:
            pytest.skip("未找到绿色金融 spec 文件")

        data = {
            "project": {
                "name": "分布式光伏发电项目",
                "category_l2": "C3.1",
                "category_l2_prefix": "C3",
                "description": "屋顶分布式光伏发电系统，装机容量10MW",
                "technology_type": "光伏发电",
            },
        }

        result = execute_rules(specs, data, domain="green_bond")
        assert isinstance(result, AuditResult)
        assert result.domain == "green_bond"

    def test_green_bond_ineligible(self, loader: SpecLoader) -> None:
        """不符合条件的项目 —— 应返回问题"""
        specs = loader.load_domain("green-finance/bond-eligibility")
        if not specs:
            specs = loader.load_domain("green-finance")

        if not specs:
            pytest.skip("未找到绿色金融 spec 文件")

        data = {
            "project": {
                "name": "传统燃煤发电项目",
                "category_l2": "X1.1",  # 不存在的类别
                "category_l2_prefix": "X1",
                "description": "新建燃煤发电厂",
                "technology_type": "燃煤发电",
            },
        }

        result = execute_rules(specs, data, domain="green_bond")
        assert isinstance(result, AuditResult)
        # 无效类别应触发至少一条失败
        failed = [r for r in result.results if not r.passed]
        assert len(failed) > 0, "无效项目应触发规则失败"


class TestCheckGreenCredit:
    """check_green_credit 工具测试"""

    def test_green_credit_eligible(self, loader: SpecLoader) -> None:
        """绿色信贷分类 —— 合格项目"""
        specs = loader.load_domain("green-finance/credit-classification")
        if not specs:
            specs = loader.load_domain("green-finance")

        if not specs:
            pytest.skip("未找到绿色金融 spec 文件")

        data = {
            "input": {
                "loan": {
                    "project_industry": "清洁能源",
                    "project_type": "光伏发电项目建设贷款",
                    "emission_intensity": 0.05,
                },
                "borrower": {"name": "绿色能源有限公司"},
            },
            "context": {
                "green_industry_catalog": [
                    "节能环保", "清洁生产", "清洁能源", "生态环境",
                    "基础设施绿色升级", "绿色服务",
                ],
                "restricted_industries": [
                    "钢铁（新增产能）", "水泥（新增产能）",
                ],
            },
        }

        result = execute_rules(specs, data, domain="green_credit")
        assert isinstance(result, AuditResult)
        assert result.domain == "green_credit"

    def test_green_credit_restricted(self, loader: SpecLoader) -> None:
        """绿色信贷分类 —— 限制类项目"""
        specs = loader.load_domain("green-finance/credit-classification")
        if not specs:
            specs = loader.load_domain("green-finance")

        if not specs:
            pytest.skip("未找到绿色金融 spec 文件")

        data = {
            "input": {
                "loan": {
                    "project_industry": "钢铁",
                    "project_type": "新建高炉产能扩张",
                    "emission_intensity": 5.2,
                },
                "borrower": {"name": "传统钢铁有限公司"},
            },
            "context": {
                "green_industry_catalog": [
                    "节能环保", "清洁生产", "清洁能源", "生态环境",
                    "基础设施绿色升级", "绿色服务",
                ],
                "restricted_industries": [
                    "钢铁（新增产能）", "水泥（新增产能）",
                ],
            },
        }

        result = execute_rules(specs, data, domain="green_credit")
        assert isinstance(result, AuditResult)


class TestExplainFailure:
    """explain_failure 工具测试"""

    def test_explain_failure_known_rule(self, loader: SpecLoader) -> None:
        """解释已知规则的失败原因"""
        # 使用 global-003（透明度原则），用缺少 meta 字段的数据触发失败
        rule = None
        for gr in loader.meta.get("global_rules", []):
            if gr.get("id") == "global-003":
                rule = gr
                break

        if rule is None:
            pytest.skip("global-003 规则不存在")

        # 构造缺少 transparency 字段的数据
        data = {
            "input": {
                "entity": {"name": "测试企业", "reporting_year": 2025},
                "emission_sources": [],
                # 故意不提供 assumptions, methodology_rationale, data_sources
            }
        }

        single_spec = {"_meta": {"rules": [rule]}}
        result = execute_rules(single_spec, data, domain="explain")

        assert isinstance(result, AuditResult)
        # 应触发 global-003 失败
        failed = [r for r in result.results if r.rule_id == "global-003" and not r.passed]
        assert len(failed) > 0, "缺少 transparency 字段应触发 global-003 失败"

    def test_explain_failure_with_citation(self, loader: SpecLoader) -> None:
        """规则失败时应包含 citation 信息"""
        # 查找一条有 citation_ref 或 citation 字段的规则
        target_rule = None
        for spec in loader.specs.values():
            for rule in spec.get("rules", []):
                cit_ref = rule.get("citation_ref") or rule.get("citation", "")
                if cit_ref and rule.get("assertion"):
                    target_rule = rule
                    break
            if target_rule:
                break

        if target_rule is None:
            pytest.skip("未找到带 citation 的规则")

        # 验证 citation 可以被解析
        cit_ref = target_rule.get("citation_ref") or target_rule.get("citation", "")
        if cit_ref.startswith("cit-"):
            cit = loader.get_citation(cit_ref)
            assert cit is not None, f"citation {cit_ref} 应可被解析"
            assert cit["text"], f"citation {cit_ref} 应有原文"
        else:
            # citation 可能是直接文本引用，验证非空即可
            assert cit_ref, "citation 字段不应为空"

    def test_explain_failure_skipped_condition(self, loader: SpecLoader) -> None:
        """当 condition 不满足时，规则应被跳过"""
        # global-001 的 condition 是 emission_sources != null
        # 传入 emission_sources 为 null 时应被跳过
        rule = None
        for gr in loader.meta.get("global_rules", []):
            if gr.get("id") == "global-001":
                rule = gr
                break

        if rule is None:
            pytest.skip("global-001 规则不存在")

        data = {
            "input": {
                "entity": {"name": "测试企业", "reporting_year": 2025},
                # emission_sources 缺失 → condition 不满足 → 规则跳过
            }
        }

        single_spec = {"_meta": {"rules": [rule]}}
        result = execute_rules(single_spec, data, domain="explain")

        # 当 condition 不满足时，规则不执行，结果为空
        triggered = [r for r in result.results if r.rule_id == "global-001"]
        assert len(triggered) == 0, "condition 不满足时 global-001 应被跳过"
