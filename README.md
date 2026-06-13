# GHG Protocol Scope 2 — Machine-Readable Compliance Spec for AI Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/v/release/Nikeandocean/carbon-accounting-specs)](https://github.com/Nikeandocean/carbon-accounting-specs/releases)

> 把 GHG Protocol 的 Scope 2 规则转化为 AI 可消费的结构化数据。
> 每条规则可追溯，每步计算可审计。

[中文文档](docs/README_CN.md) | [English](#what-is-this)

---

## What is this?

一套开源的 YAML 规则文件，定义了 GHG Protocol Scope 2 的所有合规要求。
任何 AI agent 或碳核算软件都可以直接加载这套规则，自动校验核算结果。

**这不是碳计算器。** 它不含排放因子数据库，不替代 GHG Protocol 标准本身。
它是**合规矩阵**——告诉你"算完之后要满足哪些条件才算合规"。

## 它能做什么？

✅ 校验核算数据是否完整
✅ 自动选择最优排放因子（含数据回退链）
✅ 检测 Scope 1/2 边界重叠
✅ 强制双重报告合规
✅ 每条判定追溯到 GHG Protocol 原文

## 规则覆盖范围

| 模块 | 规则数 | 优先级 | 说明 |
|------|--------|--------|------|
| 组织边界 | 3 | MUST | 控制权法、股权比例法 |
| 运营边界 | 3 | MUST | 排放源识别、类型校验 |
| 位置法 | 3 | MUST/SHOULD | 电网平均因子计算 |
| 市场法 | 3 | MUST/SHOULD | 合同工具优先 |
| 双重报告 | 2 | MUST | 触发条件、输出校验 |
| 披露要求 | 3 | MUST/SHOULD | 必须披露字段 |
| 禁止清单 | 6 | MUST/SHOULD | 双重计算、时效性等 |

## 快速开始

```python
import yaml
from jsonlogic import jsonlogic

# 1. 加载 spec
with open('specs/_meta.yaml', encoding='utf-8') as f:
    meta = yaml.safe_load(f)

# 2. 按 load_order 加载所有规则
specs = {}
for path in meta['load_order']:
    with open(f'specs/{path}.yaml', encoding='utf-8') as f:
        specs[path] = yaml.safe_load(f)

# 3. 准备你的核算数据
data = {
    "input": {
        "entity": {"name": "示例企业", "reporting_year": 2025, "control_method": "operational_control"},
        "emission_sources": [
            {"id": "elec-001", "type": "electricity", "activity_data": 1000,
             "emission_factor": {"value": 0.5703, "year": 2024, "source": "生态环境部", "type": "grid_average"}}
        ]
    },
    "context": {
        "region": {"country_code": "CN", "has_market_instruments": true, "grid_average_ef": 0.5703}
    }
}

# 4. 执行规则校验
for spec in specs.values():
    for rule in spec.get('rules', []):
        if rule.get('lifecycle') == 'pre_calculation':
            if rule.get('condition'):
                if jsonlogic(rule['condition'], data):
                    if rule.get('assertion'):
                        result = jsonlogic(rule['assertion'], data)
                        if not result:
                            print(f"❌ 规则 {rule['id']} 失败: {rule.get('on_fail_message')}")

print("✅ 所有前置规则校验通过")
```

## 数据回退链

当高优先级数据不可用时，系统自动降级：

**市场法：** 合同/PPA → 绿证 → 供应商因子 → 残余组合 → 电网平均
**位置法：** 区域电网 → 国家电网
**时间：** 当年 → 前一年 → 最近可用

## 参与贡献

我们欢迎以下贡献：

- 🌍 添加你所在国家/地区的排放因子数据
- 📝 改进规则的中文翻译
- 🐛 报告规则逻辑错误
- 💡 提出 Scope 1/3 的规则建议

请查看 [贡献指南](CONTRIBUTING.md) 了解详情。

## 路线图

- [x] Scope 2（当前版本）
- [ ] Scope 1（直接排放）
- [ ] Scope 3（价值链排放）
- [ ] 行业细分规则（电力、钢铁、化工等）
- [ ] 特定合规要求（EU CBAM、中国碳市场等）

## 致谢

- [GHG Protocol](https://ghgprotocol.org/) — 排放核算标准
- [World Resources Institute (WRI)](https://www.wri.org/) — 标准制定机构
- [WBCSD](https://www.wbcsd.org/) — 标准制定机构

## 许可证

MIT License - 详见 [LICENSE](LICENSE)
