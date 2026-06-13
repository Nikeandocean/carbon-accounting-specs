# GHG Protocol Scope 2 Carbon Accounting Spec

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![YAML Validation](https://github.com/Nikeandocean/carbon-accounting-specs/actions/workflows/validate.yml/badge.svg)](https://github.com/Nikeandocean/carbon-accounting-specs/actions/workflows/validate.yml)
[![GitHub release](https://img.shields.io/github/v/release/Nikeandocean/carbon-accounting-specs)](https://github.com/Nikeandocean/carbon-accounting-specs/releases)
[![GitHub issues](https://img.shields.io/github/issues/Nikeandocean/carbon-accounting-specs)](https://github.com/Nikeandocean/carbon-accounting-specs/issues)

A machine-parseable YAML specification for GHG Protocol Scope 2 carbon accounting, designed to drive carbon accounting agents.

## 🎯 Overview

This specification implements the GHG Protocol Corporate Standard for Scope 2 (Indirect Emissions from Purchased Electricity, Steam, Heat, and Cooling). It provides:

- **Deterministic rules** (Layer 1) using JsonLogic and External Functions
- **Knowledge base** (Layer 2) with citations and interpretation guidance
- **Fallback chains** for data quality hierarchy
- **Cross-method validation** for dual reporting compliance

## 🏗️ Architecture

### Dual-Layer Design

```
Layer 1: Schema Config (Deterministic)
├── JsonLogic expressions for basic rules
├── External Functions for complex topology
└── Machine-executable without LLM

Layer 2: Knowledge Base (Semantic)
├── Citations from GHG Protocol
├── Interpretation guidance
└── Used by LLM when Schema layer is insufficient
```

### Dual-Engine Execution

| Engine | Scope | Percentage |
|--------|-------|------------|
| **JsonLogic** | Null checks, type validation, comparisons, set operations | 80% |
| **External Functions** | Organizational boundary, equity share, control methods | 20% |

## 📁 Structure

```
specs/
├── _meta.yaml              # Master configuration
├── principles/             # Core accounting principles
│   ├── organizational-boundary.yaml
│   ├── operational-boundary.yaml
│   ├── data-quality-hierarchy.yaml
│   └── emission-attribution.yaml
├── methods/                # Location-based and market-based methods
│   ├── location-based.yaml
│   ├── market-based.yaml
│   └── dual-reporting.yaml
├── reporting/              # Disclosure requirements
│   └── disclosure-requirements.yaml
└── constraints/            # Prohibitions and compliance rules
    └── prohibitions.yaml

schemas/
└── *.json                  # JSON Schema for external functions

docs/
├── README.md
├── LICENSE
├── methodology.md
├── schema-spec.md
└── agent-integration-guide.md

examples/
└── sample-usage.yaml
```

## 🚀 Quick Start

### For Agent Developers

1. Load `_meta.yaml` to get engine definitions and load order
2. Follow `load_order` to process files sequentially
3. Execute rules based on `lifecycle` stage
4. Use `fallback_chains` for emission factor selection
5. Run `cross_method_validation` in post-audit phase

### Python Example

```python
import yaml
from jsonlogic import jsonlogic

# Load spec
with open('specs/_meta.yaml', encoding='utf-8') as f:
    meta = yaml.safe_load(f)

# Load all files in order
specs = {}
for path in meta['load_order']:
    with open(f'specs/{path}.yaml', encoding='utf-8') as f:
        specs[path] = yaml.safe_load(f)

# Execute rules
for lifecycle in ['pre_calculation', 'runtime_inference', 'post_audit']:
    for spec in specs.values():
        for rule in spec.get('rules', []):
            if rule.get('lifecycle') == lifecycle:
                # Evaluate condition
                if rule.get('condition'):
                    if jsonlogic(rule['condition'], data):
                        # Evaluate assertion
                        if rule.get('assertion'):
                            result = jsonlogic(rule['assertion'], data)
                            # Handle on_fail
                            if not result:
                                handle_on_fail(rule, data)
```

## 📚 Documentation

- [Methodology](docs/methodology.md) - Dual-layer architecture and execution flow
- [Schema Specification](docs/schema-spec.md) - Input/output schema details
- [Agent Integration Guide](docs/agent-integration-guide.md) - Step-by-step integration instructions
- [Example Usage](examples/sample-usage.yaml) - Complete manufacturing company example

## 🔧 Rule Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Execution Flow                     │
├─────────────────────────────────────────────────────────────┤
│  1. Loading Phase                                           │
│     → Parse all rules, classify by lifecycle                │
│                                                             │
│  2. pre_calculation Phase                                   │
│     → Execute all lifecycle="pre_calculation" rules         │
│     → Validate input data completeness                      │
│     → Confirm organizational and operational boundaries     │
│                                                             │
│  3. runtime_inference Phase                                 │
│     → Execute calculations, trigger fallback_chains         │
│     → Execute lifecycle="runtime_inference" rules           │
│     → Dynamically select methods and factors                │
│                                                             │
│  4. post_audit Phase                                        │
│     → Execute all lifecycle="post_audit" rules              │
│     → Validate output completeness                          │
│     → Execute cross_method_validation                       │
│     → Generate audit log                                    │
│                                                             │
│  5. Output Phase                                            │
│     → Attach all source_ref and citation                    │
│     → Output all warnings and justifications                │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Fallback Chains

### Market-Based Chain
1. Contract/PPA → 2. REC → 3. Supplier → 4. Residual Mix → 5. Grid Average

### Location-Based Chain
1. Subnational → 2. National

### Time-Based Chain
1. Current Year → 2. Previous Year → 3. Latest Available

## 🛡️ Comply or Explain

Rules with `require_justification` action allow compliance through disclosure:

```yaml
justifications:
  "proh-006": "Global reason: 2026 official factors not yet published"
  "proh-006@emission_sources[1].id": "This site is in a remote area, only 2024 factors available"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [GHG Protocol](https://ghgprotocol.org/) for the emission accounting standards
- [JsonLogic](https://jsonlogic.com/) for the expression language
- [World Resources Institute (WRI)](https://www.wri.org/) and [WBCSD](https://www.wbcsd.org/) for the corporate standard

## 📞 Contact

- GitHub: [@Nikeandocean](https://github.com/Nikeandocean)
- Repository: [carbon-accounting-specs](https://github.com/Nikeandocean/carbon-accounting-specs)
