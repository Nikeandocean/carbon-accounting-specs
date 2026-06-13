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

## For Agent Developers

See [Agent Integration Guide](agent-integration-guide.md) for detailed integration instructions.

## License

[MIT License](../LICENSE)
