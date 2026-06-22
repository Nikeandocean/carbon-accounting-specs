"""
Spec-Driven Review MCP Server

碳核算 + 绿色金融双域合规审查 MCP 服务器入口。
基于 GHG Protocol 标准对企业排放数据进行自动化合规审查。
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .loader import SpecLoader
from .tools_ghg import register_ghg_tools
from .tools_gf import register_gf_tools
from .bridge import register_bridge_tools

# 初始化规范加载器（相对于项目根目录的 specs/ 目录）
_spec_dir = Path(__file__).resolve().parent.parent / "specs"
loader = SpecLoader(_spec_dir)
loader.load_all()

# 创建 MCP Server 实例
mcp = FastMCP(
    name="spec-driven-review",
    instructions=(
        "碳核算 + 绿色金融双域合规审查 MCP 服务器。\n\n"
        "域1 — 碳核算审查（GHG Protocol）：\n"
        "- audit_scope1: 审查 Scope 1 直接排放数据合规性\n"
        "- audit_scope2: 审查 Scope 2 外购能源排放数据合规性\n"
        "- audit_scope3: 审查 Scope 3 供应链排放数据合规性\n"
        "- get_rule: 查询规则详情和关联的 GHG Protocol 标准引用\n"
        "- list_rules: 列出适用的规则\n"
        "- explain_failure: 解释规则失败原因并提供修复建议\n\n"
        "域2 — 绿色金融合规：\n"
        "- check_green_bond: 检查项目是否符合绿色债券支持项目目录\n"
        "- check_green_credit: 检查贷款项目是否属于绿色信贷范畴\n"
        "- check_issb_s2: 检查 ISSB S2 气候披露合规性\n"
        "- classify_project: 自动匹配绿色债券目录类别\n"
        "- get_gf_rule: 查询绿色金融规则详情\n\n"
        "跨域审查：\n"
        "- full_green_finance_audit: 一站式绿色金融合规审查\n"
        "  （碳数据审查 → 绿色债券资格 → 绿色信贷分类 → 综合判定）"
    ),
)

# 注册工具 — 域1: 碳核算 + 域2: 绿色金融 + 跨域桥接
register_ghg_tools(mcp, loader)
register_gf_tools(mcp, loader)
register_bridge_tools(mcp, loader)


def main() -> None:
    """以 stdio 模式启动 MCP Server"""
    mcp.run()


if __name__ == "__main__":
    main()
