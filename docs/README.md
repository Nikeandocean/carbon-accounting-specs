# GHG Protocol Scope 2 Carbon Accounting Spec

A machine-parseable YAML specification for GHG Protocol Scope 2 carbon accounting, designed to drive carbon accounting agents.

## Overview

This specification implements the GHG Protocol Corporate Standard for Scope 2 (Indirect Emissions from Purchased Electricity, Steam, Heat, and Cooling). It provides:

- **Deterministic rules** (Layer 1) using JsonLogic and External Functions
- **Knowledge base** (Layer 2) with citations and interpretation guidance
- **Fallback chains** for data quality hierarchy
- **Cross-method validation** for dual reporting compliance

## Structure

```
specs/
├── _meta.yaml              # Master configuration
├── principles/             # Core accounting principles
├── methods/                # Location-based and market-based methods
├── reporting/              # Disclosure requirements
└── constraints/            # Prohibitions and compliance rules

schemas/
└── *.json                  # JSON Schema for external functions
```

## Quick Start

1. Load `_meta.yaml` to get engine definitions and load order
2. Follow `load_order` to process files sequentially
3. Execute rules based on `lifecycle` stage
4. Use `fallback_chains` for emission factor selection
5. Run `cross_method_validation` in post-audit phase

## Scope 1 Coverage

In addition to Scope 2, this repository now includes Scope 1 (direct emissions) rules:

| Module | Rules | Priority | Description |
|--------|-------|----------|-------------|
| Emission Categories | 4 | MUST/SHOULD | Source classification and identification |
| Stationary Combustion | 6 | MUST/SHOULD | Boilers, furnaces, generators |
| Mobile Combustion | 5 | MUST/SHOULD | Company fleet and vehicles |
| Process Emissions | 5 | MUST/SHOULD | Industrial process emissions |
| Fugitive Emissions | 5 | MUST/SHOULD | Refrigerant leaks, methane |
| Disclosure | 7 | MUST/SHOULD | Reporting requirements |
| Prohibitions | 6 | MUST | Double-counting, biogenic CO2 |
| Quality Criteria | 5 | MUST/SHOULD | Data quality requirements |

## For Agent Developers

See [Agent Integration Guide](agent-integration-guide.md) for detailed integration instructions.

## License

[MIT License](../LICENSE)
