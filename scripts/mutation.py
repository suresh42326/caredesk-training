"""Run mutation testing on the reminder service and fail if mutants survive.

    python scripts/mutation.py [--max-survivors 0] [--target app/reminders/service.py] [--tests tests/test_reminder_service.py]

Mutation testing changes the code on purpose (for example `<=` becomes `<`) and re-runs your tests. A test
suite that still passes has a gap: the "mutant survived". It is the best check for AI-written tests, which often
pass without asserting much. Uses pytest-gremlins (works on native Windows; mutmut does not). About 30 seconds.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent / "backend"
ap = argparse.ArgumentParser()
ap.add_argument("--max-survivors", type=int, default=0)
ap.add_argument("--target", default="app/reminders/service.py")
ap.add_argument("--tests", default="tests/test_reminder_service.py")
args = ap.parse_args()

report = backend / "coverage" / "gremlins" / "gremlins.json"
if report.exists():
    report.unlink()

cmd = [
    "uv", "run", "pytest", args.tests, "--gremlins", f"--gremlin-targets={args.target}",
    "--gremlin-operators=arithmetic,boolean,boundary,comparison,return_value",
    "--gremlin-parallel", "--gremlin-report=json", "-p", "no:cacheprovider", "-q",
]
print("running:", " ".join(cmd[2:]))
proc = subprocess.run(cmd, cwd=backend, capture_output=True, text=True, encoding="utf-8", errors="replace")
if not report.exists():
    print(proc.stdout[-1500:], proc.stderr[-1500:])
    sys.exit("mutation run produced no report (do the normal tests pass?)")

data = json.loads(report.read_text(encoding="utf-8"))
summary = data["summary"]
survivors = [r for r in data["results"] if r["status"] == "survived"]
print(f"\nmutants: {summary['total']}  killed: {summary['zapped']}  survived: {len(survivors)}  score: {summary['percentage']:.0f}%")
for r in survivors:
    rel = Path(r["file_path"]).name
    print(f"  SURVIVED {rel}:{r['line_number']}  {r['description']}  ({r['operator']})")
if len(survivors) > args.max_survivors:
    print(f"\nFAILED: {len(survivors)} surviving mutants (allowed {args.max_survivors}). Write a test that fails for each.")
    sys.exit(1)
print("\nMUTATION OK")
