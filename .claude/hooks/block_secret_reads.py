"""PreToolUse hook: stop shell commands from reading secret or PII files.

Why: `permissions.deny` Read(...) rules cover Claude's file tools and the file commands it recognises
in Bash (cat, head, sed, redirects). They do NOT cover indirect reads such as `grep -r` that does not
name the file, or a script that opens it. This hook inspects every Bash/PowerShell command first.

Claude Code sends JSON on stdin. Exit code 2 blocks the call and sends stderr back to Claude.
Any other exit code lets the call through.

Limits: this is a speed bump, not a security boundary. A determined command can be obfuscated.
Combine it with deny rules, least-privilege credentials and (where available) the sandbox.
"""
import json
import re
import sys

# Paths that must never be read through the shell. `.env.example` is allowed.
SENSITIVE = [
    r"(^|[\s/\\\"'=])\.env(?!\.example)(\.[\w-]+)?($|[\s/\\\"';|&>)])",
    r"(^|[\s/\\\"'=])secrets[/\\]",
    r"seed[/\\]patients",
]
PATTERNS = [re.compile(p, re.IGNORECASE) for p in SENSITIVE]


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # not our payload; do not block
    command = (event.get("tool_input") or {}).get("command", "")
    for pattern in PATTERNS:
        if pattern.search(command):
            print(
                "Blocked by project policy: this command would read a secret or PII file "
                "(.env, secrets/, seed/patients*). Ask the user for the specific value you need "
                "instead of reading the file.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
