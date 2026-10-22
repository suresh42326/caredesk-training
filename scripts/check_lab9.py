"""Lab 9 checker. Run from the repo root: python scripts/check_lab9.py [feature-folder]

Checks the end state of an orchestrated delivery: the roster, the scope gate, the implementation, the
traceability, the progress files and the commit trailers.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
feature = sys.argv[1] if len(sys.argv) > 1 else "sms-reminders"
problems: list[str] = []


def need(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


def run(cmd: list[str], cwd: Path = root) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def frontmatter(path: Path) -> dict[str, str]:
    m = re.match(r"^---\r?\n(.*?)\r?\n---", path.read_text(encoding="utf-8-sig"), re.S)
    out: dict[str, str] = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
    return out


# 1. Roster
for name in ("test-author", "implementer", "reviewer"):
    p = root / ".claude" / "agents" / f"{name}.md"
    need(p.exists(), f".claude/agents/{name}.md exists")
    if p.exists():
        fm = frontmatter(p)
        need(fm.get("name") == name, f"{name}: name matches file")
        need(len(fm.get("description", "")) >= 100, f"{name}: description says when to use it")
        need("tools" in fm, f"{name}: tools are restricted")
reviewer = root / ".claude" / "agents" / "reviewer.md"
if reviewer.exists():
    tools = frontmatter(reviewer).get("tools", "")
    need(not re.search(r"\b(Edit|Write|MultiEdit)\b", tools), "reviewer is read-only (no Edit/Write)")
    need("uv run" not in tools, "reviewer cannot run the code under review")

# 2. Scope gate wired
settings = root / ".claude" / "settings.json"
need(settings.exists() and "scope_guard" in settings.read_text(encoding="utf-8-sig"), "scope_guard hook is wired in settings.json")
need((root / ".claude" / "hooks" / "scope_guard.py").exists(), "scope_guard.py exists")

# 3. Implementation present
for f in (
    "backend/app/reminders/provider.py",
    "backend/app/reminders/service.py",
    "backend/app/routes/reminders.py",
):
    need((root / f).exists(), f"{f} exists")
revs = list((root / "backend" / "migrations").glob("0002_*.py"))
need(bool(revs), "a generated migration revision 0002 exists")
if revs:
    need("reminders" in revs[0].read_text(encoding="utf-8-sig"), "revision 0002 creates the reminders table")

# 4. Tests, lint, traceability
r = run(["uv", "run", "pytest", "-q"], root / "backend")
need(r.returncode == 0, "backend tests pass")
r = run(["uv", "run", "ruff", "check", "."], root / "backend")
need(r.returncode == 0, "ruff check passes")
r = run([sys.executable, "scripts/traceability.py", feature])
need(r.returncode == 0, "traceability: every acceptance criterion has a test (and no orphan tags)")

# 5. Progress files
progress = [p for p in (root / ".agents" / "progress").glob("T-*.md")]
need(len(progress) >= 2, f"at least 2 progress files in .agents/progress ({len(progress)} found)")
for p in progress:
    t = p.read_text(encoding="utf-8-sig")
    need(all(h in t for h in ("Done", "Pending", "Decisions")), f"{p.name} has Done / Pending / Decisions")

# 6. Commit trailers
if shutil.which("git"):
    log = run(["git", "log", "--format=%H%x1f%B%x1e"]).stdout
    agent_commits = [c for c in log.split("\x1e") if "Agent-Mode:" in c]
    need(len(agent_commits) >= 2, f"at least 2 agent commits with trailers ({len(agent_commits)} found)")
    for c in agent_commits:
        sha = c.split("\x1f")[0].strip()[:8]
        missing = [t for t in ("Agent-Model", "Agent-Mode", "Agent-Session", "Agent-Operator") if f"{t}:" not in c]
        need(not missing, f"commit {sha} has all four Agent-* trailers" + (f" (missing {missing})" if missing else ""))
        need("Co-Authored-By" not in c, f"commit {sha} uses trailers, not a co-author line")

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} CHECK(S) FAILED")
sys.exit(1 if problems else 0)
