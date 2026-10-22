# caredesk-team plugin

Packages the CareDesk team's agent setup so any repo can install it.

| Component | What it does |
|---|---|
| `skills/fastapi-conventions` | FastAPI layering, errors, validation rules (loads when relevant) |
| `skills/new-endpoint` | `/caredesk-team:new-endpoint <resource> <action>` - test-first endpoint scaffold |
| `hooks/hooks.json` | PreToolUse hook that blocks shell reads of `.env`, `secrets/` and `seed/patients*` |

Validate: `claude plugin validate plugins/caredesk-team`
Try locally: `claude --plugin-dir plugins/caredesk-team`
