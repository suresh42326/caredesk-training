"""Lab 11 checker. Run from the repo root: python scripts/check_lab11.py

Static checks of the three workflows (security properties, not just "does it exist"), the offline self-test of
the review gate, and actionlint if it is installed.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
wf = root / ".github" / "workflows"
problems: list[str] = []


def need(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


def jobs_of(text: str) -> dict[str, str]:
    """Rough split of the `jobs:` section into {job name: its text}."""
    m = re.search(r"^jobs:\s*$", text, re.M)
    if not m:
        return {}
    body = text[m.end():]
    parts = re.split(r"^  ([A-Za-z0-9_-]+):\s*$", body, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def top_level_env(text: str) -> str:
    return "".join(m.group(1) for m in re.finditer(r"^env:\s*\n((?:[ \t]+.*\n|\n)*)", text, re.M))


def without_comments(text: str) -> str:
    return re.sub(r"(?m)^\s*#.*$", "", text)


files = {}
for name in ("claude-review.yml", "ai-gate.yml", "scheduled-report.yml"):
    p = wf / name
    need(p.exists(), f".github/workflows/{name} exists")
    if p.exists():
        files[name] = p.read_text(encoding="utf-8-sig")

for name, text in files.items():
    need("pull_request_target" not in without_comments(text), f"{name}: does not use pull_request_target (it runs with base-repo secrets)")
    need(bool(re.search(r"^permissions:", text, re.M)), f"{name}: sets top-level permissions (least privilege)")
    need("sk-ant-" not in text, f"{name}: no literal API key")
    key_lines = [ln for ln in text.splitlines() if "ANTHROPIC_API_KEY" in ln and ":" in ln and not ln.strip().startswith("#")]
    need(all("secrets.ANTHROPIC_API_KEY" in ln for ln in key_lines), f"{name}: the API key only comes from secrets")
    need("ANTHROPIC_API_KEY" not in top_level_env(text), f"{name}: the API key is not in workflow-wide env (scope it to one step)")
    for uses in re.findall(r"^\s*-?\s*uses:\s*(\S+)", text, re.M):
        if not uses.startswith(("actions/", "github/", "./")):
            need(bool(re.search(r"@[0-9a-f]{40}$", uses)), f"{name}: third-party action {uses.split('@')[0]} is pinned to a commit SHA")

if "claude-review.yml" in files:
    t = files["claude-review.yml"]
    need("anthropics/claude-code-action@" in t, "claude-review: uses anthropics/claude-code-action")
    need("--max-turns" in t, "claude-review: caps the agent with --max-turns")
    need("head.repo.full_name == github.repository" in t, "claude-review: skips pull requests from forks (no secrets there)")
    need("contents: write" not in t, "claude-review: no contents: write (a reviewer should not push)")
    need("pull-requests: write" in t, "claude-review: can post review comments (pull-requests: write)")

if "ai-gate.yml" in files:
    t = files["ai-gate.yml"]
    need("scripts/ci_review.py" in t, "ai-gate: runs scripts/ci_review.py")
    need("head.repo.full_name != github.repository" in t and "exit 1" in t,
         "ai-gate: FAILS CLOSED for fork pull requests (a skipped required check counts as passing)")
    need(not re.search(r"^  gate:\s*\n(?:    #.*\n)*    if:", t, re.M), "ai-gate: the job itself is never skipped by a job-level if")
    need("timeout-minutes" in t, "ai-gate: has a timeout")
    need(bool(re.search(r"claude-code@\$\{?CLAUDE_CODE_VERSION|claude-code@\d", t)), "ai-gate: pins the Claude Code version")

if "scheduled-report.yml" in files:
    t = files["scheduled-report.yml"]
    need("schedule:" in t and "workflow_dispatch" in t, "scheduled-report: runs on a schedule and can be started by hand")
    need("contents: write" not in t, "scheduled-report: no contents: write")
    for job, body in jobs_of(t).items():
        if "claude-code-action" in body:
            writes = re.findall(r"^\s+([a-z-]+): write", body, re.M)
            need(set(writes) <= {"id-token"}, f"scheduled-report: the job that runs Claude ({job}) has no write permission except id-token ({writes})")
            need("--max-turns" in body, f"scheduled-report: {job} caps turns")
            need("--disallowedTools" in body or "--allowedTools" in body, f"scheduled-report: {job} restricts tools")
    stripped = re.sub(r'--disallowedTools "[^"]*"', "", t)
    need("gh pr create" not in stripped, "scheduled-report: never opens a pull request")
    need("gh issue create" in t, "scheduled-report: reports through an issue (report-only)")

r = subprocess.run(
    [sys.executable, "scripts/ci_review.py", "--self-test"],
    cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
)
need(r.returncode == 0, "ci_review.py self-test passes (the gate fails closed on a broken reviewer)")

if shutil.which("actionlint"):
    r = subprocess.run(["actionlint"], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    need(r.returncode == 0, "actionlint passes" + ("" if r.returncode == 0 else ": " + r.stdout[:300]))
else:
    print("SKIP  actionlint not installed (pip install actionlint-py)")

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} CHECK(S) FAILED")
sys.exit(1 if problems else 0)
