"""PreToolUse hook: keep a Delegated task inside its approved "Files in scope".

If `.agents/scope.json` exists (in the working directory or a parent), every Edit/Write/MultiEdit/NotebookEdit
must target a path matching one of its patterns. Otherwise the call is blocked (exit code 2) and the reason goes
back to Claude. With no scope file nothing is blocked (Pair mode).

    {"task": "T-001-02", "allowed": ["backend/app/reminders/provider.py", "backend/tests/test_sms_provider.py"]}

Patterns use fnmatch against the path relative to the repo root, with forward slashes ("*" also matches "/").
The progress file `.agents/progress/<task>.md` is always allowed. `.agents/scope.json` itself is never writable
by the agent: only a human widens scope.

Limit: this watches Claude's file-editing tools. A shell command that writes a file (for example `echo > x`)
is a different tool; pair this hook with permission rules and review.
"""
import fnmatch
import json
import os
import sys
from pathlib import Path


def find_scope(start: Path) -> Path | None:
    for folder in (start, *start.parents):
        candidate = folder / ".agents" / "scope.json"
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool_input = event.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not target:
        return 0
    cwd = Path(event.get("cwd") or os.getcwd())
    scope_file = find_scope(cwd)
    if scope_file is None:
        return 0

    repo_root = scope_file.parent.parent.resolve()
    try:
        scope = json.loads(scope_file.read_text(encoding="utf-8-sig"))
        allowed = list(scope.get("allowed", []))
    except (json.JSONDecodeError, OSError):
        print("Blocked: .agents/scope.json is unreadable, so no edit can be approved.", file=sys.stderr)
        return 2

    path = Path(target)
    path = (path if path.is_absolute() else cwd / path).resolve()
    try:
        rel = path.relative_to(repo_root).as_posix()
    except ValueError:
        print(f"Blocked: {path} is outside the repository for task {scope.get('task')}.", file=sys.stderr)
        return 2

    if rel == ".agents/scope.json":
        print("Blocked: only a human may change the task scope (.agents/scope.json).", file=sys.stderr)
        return 2
    patterns = allowed + [".agents/progress/*"]
    if any(fnmatch.fnmatch(rel, pat) for pat in patterns):
        return 0

    print(
        f"Blocked by task scope: {rel} is not in the approved Files in scope for {scope.get('task', 'this task')}. "
        f"Allowed: {', '.join(allowed)}. If the task needs more, stop and ask a human to widen the scope.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
