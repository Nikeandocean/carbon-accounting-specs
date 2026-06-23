"""
Spec-Driven 审计工作流测试

演示完整的 spec-driven 审计流程：
1. describe_spec - 了解 spec 要求
2. get_data_requirements - 获取数据收集清单
3. analyze_gaps - 差距分析
4. validate_data - 数据验证
5. get_remediation - 修复指导
6. generate_report - 生成报告
"""

import asyncio
import json
import sys
import io
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.loader import SpecLoader
from mcp_server.tools_spec import register_spec_tools


async def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    # 初始化 loader
    spec_dir = Path(__file__).parent.parent / "specs"
    loader = SpecLoader(spec_dir)
    loader.load_all()

    print("=" * 60)
    print("Spec-Driven 审计工作流测试")
    print("=" * 60)

    # ============================================================
    # Step 1: describe_spec - 了解 spec 要求
    # ============================================================
    print("\n[Step 1] describe_spec - 了解 spec 要求")
    print("-" * 40)

    specs = loader.load_domain('issb-s2-disclosure')
    all_rules = []
    all_citations = []
    for path, spec in specs.items():
        rules = spec.get('rules', [])
        citations = spec.get('citations', [])
        schema_rules = [r for r in rules if r.get('layer') != 'knowledge']
        all_rules.extend(schema_rules)
        all_citations.extend(citations)

    print(f"Spec: issb-s2-disclosure")
    print(f"  规则数: {len(all_rules)}")
    print(f"  引用数: {len(all_citations)}")

    # 按支柱统计
    pillar_counts = {}
    for rule in all_rules:
        name = rule.get('name', '')
        if '治理' in name:
            pillar = 'governance'
        elif '战略' in name:
            pillar = 'strategy'
        elif '风险' in name:
            pillar = 'risk_management'
        elif '排放' in name or 'Scope' in name:
            pillar = 'metrics'
        elif '目标' in name:
            pillar = 'targets'
        else:
            pillar = 'other'
        pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1

    print(f"\n  支柱分布:")
    for pillar, count in pillar_counts.items():
        print(f"    {pillar}: {count}")

    # ============================================================
    # Step 2: get_data_requirements - 获取数据收集清单
    # ============================================================
    print("\n[Step 2] get_data_requirements - 获取数据收集清单")
    print("-" * 40)

    from mcp_server.tools_spec import _extract_var_paths

    required_fields = []
    optional_fields = []

    for rule in all_rules:
        assertion = rule.get('assertion', {})
        fields = _extract_var_paths(assertion)
        severity = rule.get('severity', 'info')

        for field_path in fields:
            field_info = {
                'path': field_path,
                'rule_id': rule.get('id'),
                'severity': severity,
            }
            if severity == 'fatal':
                required_fields.append(field_info)
            else:
                optional_fields.append(field_info)

    # 去重
    required_paths = set(f['path'] for f in required_fields)
    optional_paths = set(f['path'] for f in optional_fields)

    print(f"必填字段数: {len(required_paths)}")
    print(f"选填字段数: {len(optional_paths)}")

    print(f"\n必填字段示例:")
    for path in list(required_paths)[:10]:
        print(f"  - {path}")

    # ============================================================
    # Step 3: 模拟数据收集
    # ============================================================
    print("\n[Step 3] 模拟数据收集")
    print("-" * 40)

    # 模拟一个部分完成的数据
    sample_data = {
        "input": {
            "entity": {
                "name": "示例企业",
                "reporting_year": 2025,
                "is_financial_institution": False,
            },
            "justifications": {},
        },
        "output": {
            "governance": {
                "climate_governance_body": "董事会ESG委员会",
                "management_role": "CEO直接负责",
                "climate_linked_remuneration_pct": 15,
            },
            "strategy": {
                "climate_risks_opportunities": ["转型风险：碳税增加", "物理风险：极端天气"],
                "transition_plan": "2030年碳中和路径",
                "financial_effects": "预计增加成本5%",
            },
            "risk_management": {
                "risk_identification_process": "年度气候风险评估",
                "overall_risk_integration": "纳入企业风险管理框架",
            },
            "metrics": {
                "ghg": {
                    "scope1_emissions_tco2e": 10000,
                    "scope2_location_based_tco2e": 5000,
                    "scope2_market_based_tco2e": 3000,
                    "scope3_emissions_tco2e": 50000,
                    "unit": "tCO2e",
                    "gwp_source": "IPCC_AR6",
                },
            },
            "targets": {
                "emission_reduction_targets": {
                    "metric": "tCO2e",
                    "base_year": 2020,
                    "target_year": 2030,
                    "scope_coverage": "Scope 1+2",
                    "gases_covered": "CO2, CH4, N2O",
                    "target_type": "absolute",
                    "gross_or_net": "net",
                },
            },
        },
    }

    print("模拟数据已准备")
    print(f"  实体: {sample_data['input']['entity']['name']}")
    print(f"  Scope 1: {sample_data['output']['metrics']['ghg']['scope1_emissions_tco2e']} tCO2e")
    print(f"  Scope 2 (location): {sample_data['output']['metrics']['ghg']['scope2_location_based_tco2e']} tCO2e")

    # ============================================================
    # Step 4: analyze_gaps - 差距分析
    # ============================================================
    print("\n[Step 4] analyze_gaps - 差距分析")
    print("-" * 40)

    from mcp_server.engine import execute_rules

    result = execute_rules(specs, sample_data, domain="issb-s2-disclosure")

    satisfied = [r for r in result.results if r.passed]
    missing_fatal = [r for r in result.results if not r.passed and r.severity == 'fatal']
    missing_warning = [r for r in result.results if not r.passed and r.severity == 'warning']

    print(f"覆盖率: {len(satisfied)}/{len(result.results)} ({len(satisfied)/len(result.results)*100:.1f}%)")
    print(f"  通过: {len(satisfied)}")
    print(f"  缺失 (fatal): {len(missing_fatal)}")
    print(f"  缺失 (warning): {len(missing_warning)}")

    if missing_fatal:
        print(f"\n严重缺失:")
        for r in missing_fatal[:5]:
            print(f"  - {r.rule_id}: {r.rule_name}")
            print(f"    {r.message[:80]}...")

    # ============================================================
    # Step 5: get_remediation - 修复指导
    # ============================================================
    print("\n[Step 5] get_remediation - 修复指导")
    print("-" * 40)

    if missing_fatal:
        sample_rule_id = missing_fatal[0].rule_id
        rule = loader.get_rule(sample_rule_id)
        if rule:
            print(f"规则: {sample_rule_id}")
            print(f"  名称: {rule.get('name')}")
            print(f"  要求: {rule.get('on_fail_message', '')[:100]}...")

            # 获取 citation
            citation_id = rule.get('citation', '')
            if citation_id:
                cit = loader.get_citation(citation_id)
                if cit:
                    print(f"  标准引用: {cit.get('text', '')[:100]}...")

    # ============================================================
    # Step 6: generate_report - 生成报告
    # ============================================================
    print("\n[Step 6] generate_report - 生成报告")
    print("-" * 40)

    print(f"合规状态: {result.compliance}")
    print(f"总结:")
    print(f"  检查规则: {result.total_rules}")
    print(f"  通过: {result.passed}")
    print(f"  警告: {result.warnings}")
    print(f"  严重失败: {result.fatal}")

    # 按支柱统计
    pillar_results = {}
    for r in result.results:
        name = r.rule_name
        if '治理' in name:
            pillar = 'governance'
        elif '战略' in name:
            pillar = 'strategy'
        elif '风险' in name:
            pillar = 'risk_management'
        elif '排放' in name or 'Scope' in name:
            pillar = 'metrics'
        elif '目标' in name:
            pillar = 'targets'
        else:
            pillar = 'other'

        if pillar not in pillar_results:
            pillar_results[pillar] = {'passed': 0, 'failed': 0}
        if r.passed:
            pillar_results[pillar]['passed'] += 1
        else:
            pillar_results[pillar]['failed'] += 1

    print(f"\n支柱评估:")
    for pillar, stats in pillar_results.items():
        total = stats['passed'] + stats['failed']
        coverage = stats['passed'] / total * 100 if total > 0 else 0
        status = "✓" if stats['failed'] == 0 else "✗"
        print(f"  {status} {pillar}: {stats['passed']}/{total} ({coverage:.1f}%)")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
