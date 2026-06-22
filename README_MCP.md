# Spec-Driven Review MCP Server

GHG Protocol + 绿色金融双域合规审查 MCP 服务器。

## 简介

Spec-Driven Review 是一个基于 MCP (Model Context Protocol) 的合规审查服务器。它将 GHG Protocol 碳核算标准和绿色金融政策编码为机器可执行的 YAML 规范，提供自动化合规审查能力。

**双域架构：**

- **域1 — 碳核算**：基于 GHG Protocol Corporate Standard、Scope 2 Guidance (2015)、Scope 3 Standard，对企业排放数据进行规则校验
- **域2 — 绿色金融**：基于绿色债券支持项目目录、绿色信贷分类指引、ISSB S2 气候披露要求，对金融项目进行资格审查

## 安装

```bash
# 克隆仓库
git clone <repo-url>
cd rules_for_spec_driven_agent

# 安装（开发模式）
pip install -e .

# 安装开发依赖（含测试）
pip install -e ".[dev]"
```

## 在 Claude Desktop 中配置

编辑 Claude Desktop 配置文件（`claude_desktop_config.json`），添加 MCP Server：

```json
{
  "mcpServers": {
    "spec-review": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/rules_for_spec_driven_agent"
    }
  }
}
```

Windows 用户请使用完整路径：

```json
{
  "mcpServers": {
    "spec-review": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "D:\\Users\\TaoYan\\rules_for_spec_driven_agent"
    }
  }
}
```

## 可用工具

### 域1：碳核算

| 工具 | 说明 |
|------|------|
| `audit_scope1` | 审查 Scope 1 直接排放数据合规性 |
| `audit_scope2` | 审查 Scope 2 外购能源排放数据合规性（支持 location/market/dual） |
| `get_rule` | 查询规则详情和关联的 GHG Protocol 标准引用 |
| `list_rules` | 列出适用的规则（可按 scope、lifecycle 过滤） |
| `explain_failure` | 解释规则失败原因并提供修复建议 |

### 域2：绿色金融

| 工具 | 说明 |
|------|------|
| `check_green_bond` | 检查项目是否符合绿色债券支持项目目录要求 |
| `check_green_credit` | 检查贷款项目是否属于绿色信贷范畴 |
| `check_issb_s2` | 检查企业气候披露是否满足 ISSB S2 要求 |
| `classify_project` | 根据项目描述自动匹配绿色债券目录类别 |
| `get_gf_rule` | 查询绿色金融规则详情 |

## Demo 场景示例

### 场景 1：Scope 2 合规审查

```
用户：帮我审查这家企业的外购电力数据是否合规

Claude 调用 audit_scope2：
{
  "entity_name": "示例制造有限公司",
  "reporting_year": 2025,
  "emission_sources": "[{\"id\":\"elec-001\",\"type\":\"electricity\",\"activity_data\":5000,\"emission_factor\":{\"value\":0.5703,\"year\":2025,\"source\":\"生态环境部\",\"type\":\"grid_average\"}}]",
  "method": "dual"
}
```

### 场景 2：绿色债券资格检查

```
用户：我们有一个光伏发电项目，想发行绿色债券，帮我查一下是否符合目录要求

Claude 调用 check_green_bond：
{
  "project_name": "屋顶分布式光伏发电项目",
  "industry_category": "C3.1",
  "project_description": "装机容量10MW的屋顶分布式光伏发电系统",
  "technology_type": "光伏发电"
}
```

### 场景 3：规则失败解释

```
用户：为什么我的数据审查不通过？帮我解释一下

Claude 先调用 audit_scope2 获取失败列表，
再对每条失败规则调用 explain_failure 获取详细原因和修复建议
```

## 运行测试

```bash
# 运行全部测试
pytest

# 运行指定测试文件
pytest tests/test_mcp_tools.py -v

# 查看测试覆盖率
pytest --cov=mcp_server --cov-report=term-missing
```

## 规范验证

```bash
# 验证 YAML 语法
find specs -name "*.yaml" -exec python -c "import yaml; yaml.safe_load(open('{}', encoding='utf-8'))" \;

# 验证 JSON Schema
find schemas -name "*.json" -exec python -c "import json; json.load(open('{}'))" \;

# 运行综合验证脚本
python examples/validate.py
```

## 项目结构

```
rules_for_spec_driven_agent/
├── specs/                      # YAML 规范文件
│   ├── _meta.yaml              # 主配置（规则引擎、加载顺序、全局规则）
│   ├── principles/             # Scope 2 原则
│   ├── methods/                # Scope 2 核算方法
│   ├── constraints/            # Scope 2 约束条件
│   ├── scope1/                 # Scope 1 直接排放
│   ├── scope3/                 # Scope 3 价值链排放
│   └── green-finance/          # 绿色金融规范
├── schemas/                    # JSON Schema（外部函数输入输出）
├── mcp_server/                 # MCP Server 实现
│   ├── server.py               # 服务器入口
│   ├── engine.py               # JsonLogic 规则执行引擎
│   ├── loader.py               # YAML 规范加载器
│   ├── tools_ghg.py            # 域1：碳核算工具
│   ├── tools_gf.py             # 域2：绿色金融工具
│   └── bridge.py               # 跨域桥接
├── tests/                      # 测试
│   └── test_mcp_tools.py       # MCP 工具端到端测试
├── examples/                   # 示例脚本
├── pyproject.toml              # 项目配置
└── README_MCP.md               # 本文档
```

## 规则引擎架构

采用双层设计：

- **Layer 1 (Schema)**：确定性规则，使用 JsonLogic 表达式，约 80% 的规则可机器执行
- **Layer 2 (Knowledge)**：引用原文、解释指导和语义上下文，供 LLM Agent 在 Schema 层不足时使用

规则执行分三个阶段：

1. `pre_calculation` — 输入校验、边界确认
2. `runtime_inference` — 动态方法/因子选择
3. `post_audit` — 输出校验、审计日志生成
