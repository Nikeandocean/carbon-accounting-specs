# Methodology

## Dual-Layer Architecture

### Layer 1: Schema Config (Deterministic)
- JsonLogic expressions for basic rules
- External Functions for complex topology
- Machine-executable without LLM

### Layer 2: Knowledge Base (Semantic)
- Citations from GHG Protocol
- Interpretation guidance for ambiguous cases
- Used by LLM when Schema layer is insufficient

## Dual-Engine Execution

### JsonLogic Engine
- Handles: null checks, type validation, comparisons, set operations
- 80% of all rules

### External Functions Engine
- Handles: organizational boundary, equity share, control methods
- 20% of rules requiring graph traversal

## Rule Lifecycle

1. **pre_calculation**: Input validation, boundary confirmation
2. **runtime_inference**: Method selection, factor selection
3. **post_audit**: Output validation, dual reporting check

## Fallback Chains

### Market-Based Chain
1. Contract/PPA → 2. REC → 3. Supplier → 4. Residual Mix → 5. Grid Average

### Location-Based Chain
1. Subnational → 2. National

### Time-Based Chain
1. Current Year → 2. Previous Year → 3. Latest Available

## Comply or Explain

Rules with `require_justification` action allow compliance through disclosure:
- Global justification: `input.justifications[rule_id]`
- Instance justification: `input.justifications["{rule_id}@{instance_path}"]`
