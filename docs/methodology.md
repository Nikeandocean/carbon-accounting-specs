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

## Scope 1 Calculation

### Emission Categories
- **Stationary Combustion**: Fuel × Emission Factor (CO2 + CH4×GWP + N2O×GWP)
- **Mobile Combustion**: Distance × Vehicle EF OR Fuel Volume × Fuel EF
- **Process Emissions**: Production Output × Process EF
- **Fugitive Emissions**: Leak Rate × GWP

### Biogenic CO2
CO2 from combustion of biomass is reported outside Scopes 1-3. CH4 and N2O from biomass combustion are reported in Scope 1.

### CHP Allocation
Emissions from CHP facilities are allocated between heat (Scope 1) and electricity (Scope 2) using energy, exergy, or constant allocation methods.
