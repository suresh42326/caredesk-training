"""Lab 12 (capstone) checker. Run from the repo root: python scripts/check_lab12.py [--skip-mutation]

Checks the whole chain for the cancel-appointment feature: spec/design/tasks, implementation, a PostgreSQL-safe
migration, traceability, tests, mutation testing, progress files, commit trailers, the CI gate, the audit hook,
and the written report.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
feature = "cancel-appointment"
skip_mutation = "--skip-mutation" in sys.argv
problems: list[str] = []


def need(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


def run(cmd: list[str], cwd: Path = root):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


# 1. Spec, design, tasks
r = run([sys.executable, "scripts/check_lab7.py", feature])
need(r.returncode == 0, "spec, design and tasks pass the Lab 7 checker (check_lab7.py cancel-appointment)")

# 2. Implementation and migration
for f in ("backend/app/cancellation.py", "backend/app/routes/cancellation.py"):
    need((root / f).exists(), f"{f} exists")
revs = sorted((root / "backend" / "migrations").glob("0003_*.py"))
need(bool(revs), "a generated migration revision 0003 exists")
if revs:
    text = revs[0].read_text(encoding="utf-8-sig")
    need("cancelled_late" in text, "revision 0003 adds the cancelled_late column")
    need("server_default" in text, "cancelled_late has a server default (existing rows stay valid)")
    need("sa.text('0')" not in text and 'sa.text("0")' not in text,
         "the boolean default is NOT the SQLite rendering text('0') (PostgreSQL rejects it): regenerate against PostgreSQL")

# 3. Tests, lint, traceability
r = run(["uv", "run", "pytest", "-q"], root / "backend")
need(r.returncode == 0, "backend tests pass")
r = run(["uv", "run", "ruff", "check", "."], root / "backend")
need(r.returncode == 0, "ruff check passes")
r = run([sys.executable, "scripts/traceability.py", feature])
need(r.returncode == 0, "traceability: every SPEC002 criterion has a test")
names = " ".join(p.read_text(encoding="utf-8-sig") for p in (root / "backend" / "tests").glob("test_cancellation*.py"))
need("test_SPEC002_AC4" in names and re.search(r"\(\s*24\s*,\s*False\s*\)", names) is not None,
     "a test covers the exact 24-hour boundary (late versus not late)")

# 4. Mutation testing
if skip_mutation:
    print("SKIP  mutation runs (--skip-mutation)")
else:
    r = run([sys.executable, "scripts/mutation.py", "--target", "app/cancellation.py",
             "--tests", "tests/test_cancellation.py", "--max-survivors", "0"])
    need(r.returncode == 0, "mutation testing on cancellation.py leaves no surviving mutants")
    r = run([sys.executable, "scripts/mutation.py", "--max-survivors", "0"])
    need(r.returncode == 0, "mutation testing on the reminder service still leaves no surviving mutants")

# 5. Delegated-work evidence
progress = list((root / ".agents" / "progress").glob("T-002-*.md"))
need(len(progress) >= 2, f"at least 2 progress files for the capstone tasks ({len(progress)} found)")
log = run(["git", "log", "--format=%H%x1f%B%x1e"]).stdout
agent = [c for c in log.split("\x1e") if "Agent-Mode:" in c and "T-002" in c]
need(len(agent) >= 2, f"at least 2 capstone commits with Agent-* trailers ({len(agent)} found)")
for c in agent:
    sha = c.split("\x1f")[0].strip()[:8]
    missing = [t for t in ("Agent-Model", "Agent-Mode", "Agent-Session", "Agent-Operator") if f"{t}:" not in c]
    need(not missing, f"commit {sha} has all four trailers" + (f" (missing {missing})" if missing else ""))

# 6. Gates from earlier labs are still in place
r = run([sys.executable, "scripts/check_lab11.py"])
need(r.returncode == 0, "the CI workflows and the review gate still pass check_lab11.py")
r = run([sys.executable, "scripts/check_lab10.py", "--skip-mutation"])
need(r.returncode == 0, "the audit hook still passes check_lab10.py")
audit = root / ".agents" / "audit.jsonl"
if audit.exists():
    raw = audit.read_text(encoding="utf-8", errors="replace")
    need(len(raw.splitlines()) >= 5, "the audit log has entries from your sessions")
    need("sk-ant-" not in raw and not re.search(r"Bearer\s+[A-Za-z0-9._-]{16,}", raw), "the audit log contains no raw secrets")
else:
    print("SKIP  .agents/audit.jsonl not found (it is git-ignored; it exists on your machine after real sessions)")

# 7. The report
report = root / "docs" / "capstone-report.md"
need(report.exists(), "docs/capstone-report.md exists")
if report.exists():
    t = report.read_text(encoding="utf-8-sig")
    for h in ("Result", "Gates", "Findings caught", "Cost and time", "What I would change"):
        need(re.search(rf"^##\s+{h}", t, re.M) is not None, f"report has a '{h}' section")
    need(re.search(r"\$\s?\d|\d\s?(dollar|USD)", t, re.I) is not None, "report states a cost figure")
    need(len(re.findall(r"^\s*(?:\d+\.|-)\s+\S", t, re.M)) >= 8, "report lists concrete evidence (at least 8 list items)")

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} CHECK(S) FAILED")
sys.exit(1 if problems else 0)
