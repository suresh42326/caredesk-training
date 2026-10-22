# Design: SPEC-<nnn> <feature name>

Spec: specs/<feature>/spec.md (must be Approved before this is written)

## What changes (architecture delta)
<Components added or changed. Keep to the delta, not the whole system.>

## Data model and migration
<Tables/columns added. Migration plan: expand first, contract later. Note: migrations are GENERATED, never hand-edited.>

## API and breaking changes
<Endpoints added or changed. State "no breaking changes" explicitly if true.>

## Threat-model delta
<New data, new trust boundaries, new ways to abuse it. What is logged. What must never appear in messages or logs.>

## Test plan
| AC | Test layer | Test name pattern |
|---|---|---|

## Rollout and rollback
<Feature flag or kill switch. What happens to in-flight work on rollback.>

## Decisions (ADR candidates)
<Hard-to-reverse choices and the options rejected. Link an ADR if one is written.>
