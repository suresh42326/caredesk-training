"""Lab 10 checker. Run from the repo root: python scripts/check_lab10.py [--skip-mutation]

Checks: the audit hook (exists, wired, redacts, fails open), the audit log is git-ignored, the tests pass, and
the mutation run on the reminder service leaves no surviving mutants.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
skip_mutation = "--skip-mutation" in sys.argv
problems: list[str] = []


def need(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


def run(cmd: list[str], cwd: Path = root, stdin: str | None = None, env: dict | None = None):
    return subprocess.run(
        cmd, cwd=cwd, input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env
    )


hook = root / ".claude" / "hooks" / "audit_log.py"
need(hook.exists(), ".claude/hooks/audit_log.py exists")

settings = root / ".claude" / "settings.json"
cfg = json.loads(settings.read_text(encoding="utf-8-sig")) if settings.exists() else {}
hooks = cfg.get("hooks", {})
audit_entries = [
    (event, h.get("command", ""))
    for event in ("PreToolUse", "PostToolUse")
    for entry in hooks.get(event, [])
    for h in entry.get("hooks", [])
    if "audit_log" in h.get("command", "")
]
need(bool(audit_entries), "an audit_log hook is wired in .claude/settings.json (PreToolUse or PostToolUse)")
need(
    all("$CLAUDE_PROJECT_DIR" in c for _, c in audit_entries) and bool(audit_entries),
    "the hook command uses $CLAUDE_PROJECT_DIR (works from any directory)",
)
need(
    any(entry.get("matcher") in ("*", "", None) or "Bash" in entry.get("matcher", "") for ev in ("PreToolUse", "PostToolUse")
        for entry in hooks.get(ev, []) if any("audit_log" in h.get("command", "") for h in entry.get("hooks", []))),
    "the audit hook covers more than one tool (matcher * or a list that includes Bash)",
)

gitignore = (root / ".gitignore").read_text(encoding="utf-8-sig") if (root / ".gitignore").exists() else ""
need("audit.jsonl" in gitignore, ".agents/audit.jsonl is git-ignored")

if hook.exists():
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, CLAUDE_PROJECT_DIR=tmp)
        event = {
            "hook_event_name": "PostToolUse", "session_id": "s-test", "tool_name": "Bash", "cwd": tmp,
            "tool_input": {"command": "curl -H 'Authorization: Bearer abcdef1234567890XYZ' -d phone=+91-90000-00001 http://x"},
        }
        r = run([sys.executable, str(hook)], stdin=json.dumps(event), env=env)
        need(r.returncode == 0, "hook exits 0 on a normal event")
        log = Path(tmp) / ".agents" / "audit.jsonl"
        text = log.read_text(encoding="utf-8") if log.exists() else ""
        need(bool(text.strip()), "hook writes one line to .agents/audit.jsonl")
        if text.strip():
            rec = json.loads(text.splitlines()[0])
            need(rec.get("tool") == "Bash" and rec.get("session_id") == "s-test", "the record has the tool and session id")
            need("abcdef1234567890XYZ" not in text, "bearer token is redacted by value")
            need("90000-00001" not in text and "9000000001" not in text, "phone number is redacted")
        r = run([sys.executable, str(hook)], stdin="this is not json", env=env)
        need(r.returncode == 0, "FAILS OPEN: garbage input still exits 0 (never blocks a tool)")
        blocked = Path(tmp) / "afile"
        blocked.write_text("x", encoding="utf-8")
        r = run([sys.executable, str(hook)], stdin=json.dumps(event), env=dict(os.environ, CLAUDE_PROJECT_DIR=str(blocked)))
        need(r.returncode == 0, "FAILS OPEN: an unwritable log location still exits 0")

r = run(["uv", "run", "pytest", "-q"], root / "backend")
need(r.returncode == 0, "backend tests pass")

if skip_mutation:
    print("SKIP  mutation run (--skip-mutation)")
else:
    r = run([sys.executable, "scripts/mutation.py", "--max-survivors", "0"])
    tail = [ln for ln in r.stdout.splitlines() if ln.startswith(("mutants:", "  SURVIVED"))]
    need(r.returncode == 0, "mutation testing leaves no surviving mutants on the reminder service")
    if r.returncode:
        for ln in tail:
            print("      " + ln)

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} CHECK(S) FAILED")
sys.exit(1 if problems else 0)
