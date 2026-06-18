---
name: pydantic
description: Create, refactor, or review Pydantic models for Python data contracts, validation, parsing, serialization, API schemas, configs, files, tool inputs/outputs, and external payloads.
---

# Pydantic Models

Use the repo's installed Pydantic version and existing style. For new v2 code, prefer `BaseModel`, `Field`, `ConfigDict`, `field_validator`, `model_validator`, `model_validate`, `model_dump`, and `TypeAdapter`.

## Workflow

1. Inspect existing models, naming, imports, config, and tests.
2. Model durable boundaries: APIs, config, files, DB records, tool I/O, and external services.
3. Prefer typed `BaseModel`s over loose `dict`, `Any`, untyped JSON, or scattered validation.
4. Put shape rules in types, `Field` constraints, validators, or computed fields.
5. Use `TypeAdapter` for validating standalone types or collections without creating wrapper models.
6. Keep models focused; avoid broad catch-all models unless the data is genuinely open-ended.
7. Add/update tests for coercion, rejection, defaults, aliases, serialization, and edge cases.

## Avoid

- Pydantic for trivial local variables.
- Heavy validation in hot loops without need.
- Manual parsing/validation that belongs in the model.
- Changing public payload shapes without checking callers.