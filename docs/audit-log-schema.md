# Audit log schema (agent tool calls)

One JSON object per line in `.agents/audit.jsonl` (git-ignored). Written by a hook, never by the agent itself.

| Field | Meaning |
|---|---|
| `ts` | UTC timestamp, ISO 8601 |
| `event` | `PreToolUse` or `PostToolUse` |
| `session_id` | Claude Code session |
| `tool` | `Read`, `Edit`, `Write`, `Bash`, `mcp__server__tool`, ... |
| `input` | The tool input, **redacted** (secrets, tokens, phone numbers) and truncated to 500 characters per string |
| `cwd` | Working directory |

Rules for a useful audit log:
- Log **all** tools, including reads. A secret that was read is a secret that may leak.
- **Fail open**: a logging error must never block work. Always exit 0 from the logging hook.
- Redact by **value**, not only by key name: a token inside a shell command string is still a token.
- Keep the log out of the agent's reach (append-only location, shipped off the machine in CI) and state a retention period.
- Never log prompts or file contents by default.
