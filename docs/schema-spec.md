# Schema Specification

## Input Schema

### Context
- `region.country_code`: ISO 3166-1 alpha-2
- `region.subnational_code`: ISO 3166-2 (optional)
- `region.has_market_instruments`: boolean
- `region.grid_average_ef`: number (tCO2/MWh)
- `region.residual_mix_ef`: number (tCO2/MWh)
- `emission_factors.current_year`: number
- `emission_factors.previous_year`: number
- `emission_factors.latest_available`: number
- `emission_factors.latest_year`: integer

### Input
- `entity.name`: string
- `entity.reporting_year`: integer
- `entity.control_method`: enum
- `emission_sources[]`: array of emission sources
- `justifications`: object with rule_id keys

## Output Schema

- `total_scope2_emissions`: number
- `location_based_emissions`: number (if dual reporting)
- `market_based_emissions`: number (if dual reporting)
- `methodology`: string
- `emission_factor_source`: string
- `reporting_period`: string
- `data_quality_assessment`: object (optional)

## JsonLogic Expressions

Standard JsonLogic operators:
- `{"var": "path"}`: Variable access
- `{"==": [a, b]}`: Equality
- `{"!=": [a, b]}`: Inequality
- `{"and": [...]}`: Logical AND
- `{"or": [...]}`: Logical OR
- `{"all": [array, condition]}`: All elements match
- `{"none": [array, condition]}`: No elements match
