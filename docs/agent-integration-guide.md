# Agent Integration Guide

## Loading the Spec

```python
import yaml

# Load meta file
with open('specs/_meta.yaml', encoding='utf-8') as f:
    meta = yaml.safe_load(f)

# Get load order
load_order = meta['load_order']

# Load files in order
specs = {}
for path in load_order:
    with open(f'specs/{path}.yaml', encoding='utf-8') as f:
        specs[path] = yaml.safe_load(f)
```

## Executing Rules

### Lifecycle-Based Execution

```python
# Group rules by lifecycle
rules_by_lifecycle = {
    'pre_calculation': [],
    'runtime_inference': [],
    'post_audit': []
}

for spec in specs.values():
    for rule in spec.get('rules', []):
        lifecycle = rule.get('lifecycle', 'runtime_inference')
        rules_by_lifecycle[lifecycle].append(rule)

# Execute in order
for lifecycle in ['pre_calculation', 'runtime_inference', 'post_audit']:
    for rule in rules_by_lifecycle[lifecycle]:
        execute_rule(rule, context, input_data)
```

### JsonLogic Evaluation

```python
from jsonlogic import jsonlogic

def evaluate_condition(rule, data):
    condition = rule.get('condition')
    if condition is None:
        return True
    return jsonlogic(condition, data)

def evaluate_assertion(rule, data):
    assertion = rule.get('assertion')
    if assertion is None:
        return True
    return jsonlogic(assertion, data)
```

### Handling on_fail Actions

```python
def handle_on_fail(rule, result, input_data):
    on_fail = rule.get('on_fail')

    if on_fail == 'raise_fatal':
        raise ComplianceError(rule['on_fail_message'])

    elif on_fail == 'raise_warning':
        log_warning(rule['on_fail_message'])

    elif on_fail == 'require_justification':
        rule_id = rule['id']
        justification = get_justification(rule_id, input_data)
        if justification:
            log_warning(f"{rule['on_fail_message']} (justified: {justification})")
        else:
            raise ComplianceError(rule['on_fail_message'])

    elif on_fail == 'mark_unavailable':
        set_state(rule.get('set_state'))
        log_fatal(rule['on_fail_message'])
```

## Fallback Chain Execution

```python
def execute_fallback_chain(chain, context, input_data):
    for level in chain['chain']:
        condition = level['condition']
        if jsonlogic(condition, {'context': context, 'input': input_data}):
            # on_match
            action = level['on_match']['action']
            if action == 'use_value':
                return get_value(level['data_type'])
            elif action == 'use_value_with_warning':
                log_warning(level['on_match']['message'])
                return get_value(level['data_type'])
        else:
            # on_null
            action = level['on_null']['action']
            if action == 'proceed_to_next':
                continue
            elif action == 'raise_fatal':
                raise ComplianceError(level['on_null']['message'])
            elif action == 'mark_unavailable':
                set_state(level['on_null'].get('set_state'))
                return None

    raise ComplianceError("All fallback levels exhausted")
```

## External Function Calls

```python
def call_external_function(function_id, params, schemas):
    # Load input schema
    input_schema = load_schema(schemas[function_id]['input_schema'])

    # Validate params
    validate(params, input_schema)

    # Call function (implement based on your runtime)
    result = runtime.call(function_id, params)

    # Validate output
    output_schema = load_schema(schemas[function_id]['output_schema'])
    validate(result, output_schema)

    return result
```
