#!/usr/bin/env python3
"""Audit-log hook (docs/audit-log-schema.md). Fails open: always exits 0, never 2."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_LEN = 500
EVENTS = {"PreToolUse", "PostToolUse"}  # anything else (e.g. UserPromptSubmit) is not logged
# Keys that carry prompts or file contents: never logged, whatever their value.
CONTENT_KEYS = {"content", "old_string", "new_string", "new_source", "edits", "prompt"}
# Redact by value; group 1 (if present) is kept so the key name stays readable.
PATTERNS = [
    re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(
        r"(?i)\b((?:password|passwd|pwd|token|secret|api[_-]?key)[\"']?\s*[=:]\s*)"
        r"(?:\"[^\"]*\"|'[^']*'|[^\s&;\"']+)"
    ),
    re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}"
        r"|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}"
        r"|eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{5,})"
    ),
    re.compile(r"(?<![\w.])\+?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,5}(?![\w])"),
]


def redact(text: str) -> str:
    for pat in PATTERNS:
        text = pat.sub(lambda m: (m.group(1) if m.re.groups else "") + "[REDACTED]", text)
    return text[:MAX_LEN]  # truncate after redacting so a cut never leaves half a secret


def clean(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: "[omitted]" if k in CONTENT_KEYS else clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def main() -> None:
    event = json.load(sys.stdin)
    if event.get("hook_event_name") not in EVENTS:
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event.get("hook_event_name"),
        "session_id": event.get("session_id"),
        "tool": event.get("tool_name"),
        "input": clean(event.get("tool_input", {})),
        "cwd": clean(event.get("cwd")),
    }
    path = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()) / ".agents" / "audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
