"""Lab 4 checker. Run from the repo root: python scripts/check_lab4.py"""
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
problems: list[str] = []


def need(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


settings_path = root / ".claude" / "settings.json"
need(settings_path.exists(), ".claude/settings.json exists")
settings = {}
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        need(False, f"settings.json is valid JSON ({e})")

deny = " ".join(settings.get("permissions", {}).get("deny", []))
for label, needle in [
    ("deny Read(./.env)", "Read(./.env)"),
    ("deny Read(./.env.*)", "Read(./.env.*)"),
    ("deny Read(./secrets/**)", "Read(./secrets/**)"),
    ("deny Read(./seed/patients*.csv)", "seed/patients"),
]:
    need(needle in deny, label)

pre = settings.get("hooks", {}).get("PreToolUse", [])
hook_cmds = [h.get("command", "") for entry in pre for h in entry.get("hooks", [])]
matchers = " ".join(entry.get("matcher", "") for entry in pre)
need(any("block_secret_reads" in c for c in hook_cmds), "a PreToolUse hook runs block_secret_reads")
need("Bash" in matchers, "hook matcher includes Bash")

hook = root / ".claude" / "hooks" / "block_secret_reads.py"
need(hook.exists(), ".claude/hooks/block_secret_reads.py exists")
if hook.exists():
    def run(cmd: str) -> int:
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
        return subprocess.run(
            [sys.executable, str(hook)], input=payload, text=True, capture_output=True, encoding="utf-8", errors="replace"
        ).returncode

    for cmd in ["cat .env", "type secrets\\sms_provider.key", "head seed/patients.csv",
                "grep -r KEY .env.local", "Get-Content .env"]:
        need(run(cmd) == 2, f"hook BLOCKS: {cmd}")
    for cmd in ["ls", "cat .env.example", "uv run pytest -q", "git status"]:
        need(run(cmd) == 0, f"hook allows: {cmd}")

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} CHECK(S) FAILED")
sys.exit(1 if problems else 0)
