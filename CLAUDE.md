# CareDesk

@AGENTS.md
@docs/org-rules.md

## Claude-specific
- Prefer small, reviewable diffs. Show the plan before multi-file changes.
- Run `cd backend && uv run pytest -q` after every code change and fix failures before reporting done.

## Where the detail lives (loaded only when needed)
- Backend code conventions: the `fastapi-conventions` skill (Claude loads it when the task is about backend code).
- Test conventions: `.claude/rules/python-tests.md` (loads when you read test files).
- Migration rules: `.claude/rules/migrations.md` (loads when you read migration files).
- New endpoints: run `/new-endpoint <resource> <action>`.
- Clinic policy questions: use the `clinic-rules` MCP server, not guesses.
