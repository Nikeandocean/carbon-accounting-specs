# Spec-Driven Review MCP Server — Dual-Domain MVP Plan

## 核心定位

**碳核算 + 绿色金融，两个问题域，一个 MCP Server。**

- **域1（碳核算）**：GHG Protocol Scope 1/2/3 — "企业怎么算碳排放"（已有 356 条规则）
- **域2（绿色金融）**：绿色债券目录 + 绿色信贷 + ISSB — "这笔贷款/债券是否符合绿色金融标准"（新增规则）
- **串联**：碳核算审查结果 → 输入绿色金融资格判定 → 一个 Agent 调用完成全流程

## 架构

```
┌─────────────────────────────────────────────────────────┐
│              任何 MCP-compatible Agent                    │
│     Claude Desktop / Cursor / 自研 Agent                 │
│                                                          │
│  "这家钢铁企业的余热发电项目能发绿色债券吗？"              │
│                     │                                    │
│                     ▼                                    │
│              MCP Client                                  │
└─────────────┬───────────────────────────────────────────┘
              │ MCP Protocol (stdio)
              ▼
┌─────────────────────────────────────────────────────────┐
│          spec-driven-review MCP Server                   │
│                                                          │
│  ┌─────────────────────┐  ┌──────────────────────────┐  │
│  │  域1: 碳核算审查     │  │  域2: 绿色金融合规       │  │
│  │                     │  │                          │  │
│  │  Tools:             │  │  Tools:                  │  │
│  │  ├ audit_scope1     │  │  ├ check_green_bond      │  │
│  │  ├ audit_scope2     │  │  ├ check_green_credit    │  │
│  │  ├ audit_scope3     │  │  ├ check_issb_s2         │  │
│  │  ├ get_rule         │  │  ├ get_gf_rule           │  │
│  │  └ explain_failure  │  │  └ classify_project      │  │
│  │                     │  │                          │  │
│  │  Specs: 42 YAML     │  │  Specs: 新增 YAML        │  │
│  │  Rules: 356 条      │  │  Rules: 新增 80-100 条   │  │
│  │  Citations: 413 条  │  │  Citations: 新增 30+ 条  │  │
│  └─────────────────────┘  └──────────────────────────┘  │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │  共享层                                              ││
│  │  ├ JsonLogic Engine (统一规则执行)                    ││
│  │  ├ YAML Loader (统一规范加载)                         ││
│  │  └ Citation Index (统一引用索引)                      ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## 域1: 碳核算审查（已有，直接复用）

| Tool | 功能 | 规则来源 |
|------|------|----------|
| `audit_scope1` | 直接排放合规审查 | specs/scope1/*.yaml |
| `audit_scope2` | 外购能源合规审查 | specs/methods/*.yaml, specs/constraints/*.yaml |
| `audit_scope3` | 供应链排放合规审查 | specs/scope3/*.yaml |
| `get_rule` | 查询规则详情+引用 | 全部 42 个 YAML |
| `explain_failure` | 解释失败原因+修复建议 | 规则 + citations |

**状态：356 条规则已就绪，需封装为 MCP Tool 接口。**

## 域2: 绿色金融合规（新增）

### 需要新增的 YAML 规范

| 文件 | 内容 | 预估规则数 | 来源标准 |
|------|------|-----------|----------|
| `specs/green-finance/bond-catalog.yaml` | 绿色债券目录结构（6大类） | 15-20 | 《绿色债券支持项目目录(2021)》 |
| `specs/green-finance/bond-eligibility.yaml` | 债券准入条件（排放阈值、技术标准） | 25-30 | 同上 + 绿色债券发行指引 |
| `specs/green-finance/credit-classification.yaml` | 绿色信贷分类标准 | 15-20 | 《绿色信贷统计制度》 |
| `specs/green-finance/issb-s2-disclosure.yaml` | ISSB S2 气候披露要求 | 20-25 | IFRS S2 气候相关披露 |
| `specs/green-finance/cross-domain-bridge.yaml` | 碳数据→金融资格映射 | 10-15 | 跨域桥接规则 |

### MCP Tools

| Tool | 输入 | 输出 |
|------|------|------|
| `check_green_bond` | 项目数据(行业/排放/技术) | 绿色债券资格判定 + 匹配目录条目 |
| `check_green_credit` | 贷款项目数据 | 绿色信贷分类(正常/关注/不合格) |
| `check_issb_s2` | 企业气候数据 | ISSB S2 披露合规检查 |
| `classify_project` | 项目描述 | 自动匹配绿色债券目录类别 |
| `get_gf_rule` | rule_id | 绿色金融规则详情 + 政策原文引用 |

### 串联场景（核心 Demo）

```
用户: "这家钢铁企业的100MW余热发电项目能发绿色债券吗？"

Agent 自动执行:
  Step 1 → audit_scope1(project_data)     # 碳数据合规吗？
  Step 2 → check_green_bond(project_data)  # 符合绿色债券目录吗？
  Step 3 → 综合回答

输出:
  "碳核算审查：通过（12/12条规则通过）
   绿色债券资格：有条件通过
   - 匹配目录：清洁能源-余热余压利用（1.3.4）
   - 待补充：需提供第三方减排量核查报告
   - 引用：《绿色债券支持项目目录》第1类第3项第4条"
```

## 工作量估算

| 阶段 | 任务 | 人周 |
|------|------|------|
| **Phase 1: MCP 骨架** | Server 入口 + YAML Loader + JsonLogic 引擎封装 | 1.5 |
| **Phase 2: 域1 Tools** | audit_scope1/2/3 + get_rule + explain_failure | 2 |
| **Phase 3: 域2 YAML** | 研读绿色债券目录 + 编写 5 个 YAML 规范文件 | 2 |
| **Phase 4: 域2 Tools** | check_green_bond + check_green_credit + classify_project | 1.5 |
| **Phase 5: 串联+测试** | 跨域场景 + 端到端测试 | 1 |
| **Phase 6: 文档+Demo** | 技术文档 + PPT + 演示排练 | 1 |
| **合计** | | **~9 人周** |

10 周 deadline，9 人周工作量，1 周 buffer。

## 需要新增的代码

| 模块 | 文件 | 行数 |
|------|------|------|
| MCP Server 入口 | `mcp_server/server.py` | ~200 |
| 碳核算 Tools | `mcp_server/tools_ghg.py` | ~300 |
| 绿色金融 Tools | `mcp_server/tools_gf.py` | ~250 |
| 规则引擎 | `mcp_server/engine.py` | ~200 |
| 跨域桥接 | `mcp_server/bridge.py` | ~150 |
| 输入 Schema | `mcp_server/schemas.py` | ~150 |
| 测试 | `tests/test_mcp.py` | ~200 |
| 绿色金融 YAML | `specs/green-finance/*.yaml` | ~500 (YAML) |
| 配置 | `pyproject.toml` | ~30 |
| **合计** | | **~2000 行** |

## 关键依赖

```
# pyproject.toml
[project]
dependencies = [
    "mcp>=1.0.0",        # MCP Python SDK
    "pyyaml>=6.0",
    "jsonschema>=4.0",
]
```

无需 LLM、无需数据库、无需前端框架。
