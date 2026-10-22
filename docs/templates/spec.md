# SPEC-<nnn>: <feature name>

Status: Draft | Grilled | Approved  
Owner: <name>  
Risk tier: Low | Medium | High (see docs/agent-operating-model.md)

## Problem and outcome
<Two sentences: who has what problem, and what changes for them.>  
**Success measure:** <metric, baseline, target>

## User stories
- US-1: As a <role>, I want <capability>, so that <benefit>.

## Acceptance criteria (EARS, one behaviour each)

Patterns: `The <system> shall <response>.` (always) - `When <trigger>, the <system> shall <response>.` -
`While <state>, the <system> shall <response>.` - `If <unwanted condition>, then the <system> shall <response>.` -
`Where <option is enabled>, the <system> shall <response>.`

| ID | Criterion | Test layer |
|---|---|---|
| SPEC<nnn>/AC-1 | When <trigger>, the system shall <response>. | unit |
| SPEC<nnn>/AC-2 | If <unwanted condition>, then the system shall <response>. | integration |

Every criterion is testable and maps to at least one automated test whose name contains the AC id
(for example `test_SPEC001_AC1_...`).

## Out of scope
- <item>

## Open questions (filled by grilling)

| # | Question | Owner | Resolved answer |
|---|---|---|---|

A spec is **Approved** only when every open question has a resolved answer.

## Approval
Product owner: ________  Tech lead: ________  Date: ________
