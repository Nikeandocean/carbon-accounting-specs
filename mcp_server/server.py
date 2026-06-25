"""
Spec-Driven Review MCP Server

碳核算 + 绿色金融双域合规审查 MCP 服务器入口。
基于 GHG Protocol 标准对企业排放数据进行自动化合规审查。

环境变量：
  SPEC_DIR       — spec 文件目录路径（默认：项目根目录下的 specs/）
  SPEC_REMOTE    — 远程 spec 目录 URL（R2/S3），启动时下载到本地
  MCP_TRANSPORT  — 传输协议：stdio（默认）或 streamable-http
  MCP_HOST       — HTTP 模式监听地址（默认 0.0.0.0）
  MCP_PORT       — HTTP 模式监听端口（默认 8000）
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

from mcp.server.fastmcp import FastMCP

from .loader import SpecLoader
from .tools_ghg import register_ghg_tools
from .tools_gf import register_gf_tools
from .tools_spec import register_spec_tools
from .tools_search import register_search_tools
from .bridge import register_bridge_tools


def _resolve_spec_dir() -> Path:
    """解析 spec 目录路径，支持本地路径和远程 URL。"""
    remote_url = os.environ.get("SPEC_REMOTE")
    if remote_url:
        # 从远程下载 spec zip 包
        tmp_dir = Path(tempfile.mkdtemp(prefix="specs_"))
        zip_path = tmp_dir / "specs.zip"
        print(f"[spec-driven-review] Downloading specs from {remote_url} ...")

        from urllib.request import Request
        req = Request(remote_url, headers={"User-Agent": "spec-driven-review/0.1.0"})

        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if proxy:
            from urllib.request import ProxyHandler, build_opener
            opener = build_opener(ProxyHandler({"https": proxy, "http": proxy}))
            with opener.open(req) as resp, open(zip_path, "wb") as f:
                f.write(resp.read())
        else:
            with urlopen(req) as resp, open(zip_path, "wb") as f:
                f.write(resp.read())

        with ZipFile(zip_path) as zf:
            zf.extractall(tmp_dir)
        zip_path.unlink()
        # 查找解压后的 specs 目录
        candidates = list(tmp_dir.rglob("_meta.yaml"))
        if candidates:
            return candidates[0].parent
        return tmp_dir

    local_dir = os.environ.get("SPEC_DIR")
    if local_dir:
        return Path(local_dir)

    return Path(__file__).resolve().parent.parent / "specs"


# 初始化规范加载器
_spec_dir = _resolve_spec_dir()
loader = SpecLoader(_spec_dir)
loader.load_all()

# 创建 MCP Server 实例
mcp = FastMCP(
    name="spec-driven-review",
    instructions=(
        "碳核算 + 绿色金融双域合规审查 MCP 服务器。\n\n"
        "Spec-Driven 审计工具（核心）：\n"
        "- describe_spec: 描述 spec 结构和要求概览\n"
        "- get_data_requirements: 获取数据收集要求\n"
        "- analyze_gaps: 分析已有数据与 spec 要求的差距\n"
        "- validate_data: 执行完整的 spec 规则验证\n"
        "- get_remediation: 获取规则失败的修复指导\n"
        "- generate_report: 生成完整的合规审计报告\n\n"
        "Phase 4 — 多 Spec 联动（跨域审计）：\n"
        "- describe_multi_spec: 描述多个 spec 的联合概览\n"
        "- validate_multi_spec: 用多个 spec 联合验证数据\n"
        "- generate_cross_domain_report: 生成跨域合规审计报告\n\n"
        "Phase 5 — 语义搜索：\n"
        "- search_citations: 用自然语言搜索标准引用原文\n"
        "- search_rules: 用自然语言搜索规则\n"
        "- search_all: 综合搜索（citations + rules）\n\n"
        "Phase 6 — 动态 Spec 更新：\n"
        "- reload_specs: 重新加载所有 spec 文件\n"
        "- get_spec_versions: 获取所有 spec 版本信息\n"
        "- compare_spec_rules: 获取 spec 规则快照\n"
        "- diff_spec_snapshots: 对比两个快照的差异\n\n"
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

# 注册工具 — Spec-Driven 审计 + 域1: 碳核算 + 域2: 绿色金融 + 跨域桥接 + 语义搜索
register_spec_tools(mcp, loader)
register_ghg_tools(mcp, loader)
register_gf_tools(mcp, loader)
register_bridge_tools(mcp, loader)
register_search_tools(mcp, loader)


def main() -> None:
    """启动 MCP Server，支持 stdio 和 streamable-http 两种传输模式。"""
    import sys

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    print(f"[spec-driven-review] Starting with transport={transport}", flush=True)

    if transport == "streamable-http":
        from mcp.server.fastmcp.server import TransportSecuritySettings

        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8000"))
        print(f"[spec-driven-review] HTTP server on {host}:{port}", flush=True)
        mcp.settings.host = host
        mcp.settings.port = port
        # Disable DNS rebinding protection for reverse proxy (Fly.io, Cloudflare, etc.)
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )
        try:
            mcp.run(transport="streamable-http")
        except Exception as e:
            print(f"[spec-driven-review] FATAL: {e}", file=sys.stderr, flush=True)
            raise
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
