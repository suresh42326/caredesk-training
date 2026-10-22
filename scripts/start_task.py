"""Start an approved Delegated task: worktree + branch + scope file + progress file.

    python scripts/start_task.py T-001-02 [feature-folder]
    python scripts/start_task.py T-001-02 --dry-run

What it does, for the task block in specs/<feature>/tasks.md:
  1. refuses to run unless the task's Approval block is signed (nothing executes until tasks.md is approved);
  2. creates a git worktree under .claude/worktrees/<task-id>/ on the task's branch, based on YOUR CURRENT
     COMMIT (not the default branch, which `claude --worktree` would use);
  3. writes .agents/scope.json from the task's "Files in scope" (the scope_guard hook enforces it);
  4. writes .agents/progress/<task-id>.md from the template, and copies .env if present.

Then:  cd .claude/worktrees/<task-id>  and start Claude there.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser()
ap.add_argument("task")
ap.add_argument("feature", nargs="?", default="sms-reminders")
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

tasks_md = (root / "specs" / args.feature / "tasks.md").read_text(encoding="utf-8-sig")
blocks = re.split(r"^##\s+(?=T-\d+-\d+)", tasks_md, flags=re.M)[1:]
block = next((b for b in blocks if b.startswith(args.task)), None)
if block is None:
    sys.exit(f"Task {args.task} not found in specs/{args.feature}/tasks.md")

title = block.splitlines()[0].split(":", 1)[-1].strip()
branch_m = re.search(r"Branch:?\*{0,2}\s*`?(agent/[A-Za-z0-9._/-]+)`?", block)
scope_m = re.search(r"Files in scope:?\*{0,2}\s*(.+)", block)
appr_m = re.search(r"Approval:?\*{0,2}\s*(.+)", block)
if not (branch_m and scope_m and appr_m):
    sys.exit("Task block needs Branch, Files in scope and Approval lines.")
signed = re.search(r"[A-Za-z]{3,}", re.sub(r"(Tech lead|Date)", "", appr_m.group(1)))
if not signed:
    sys.exit(f"{args.task} is NOT approved: sign the Approval block in tasks.md first. Nothing executes before that.")

branch = branch_m.group(1)
allowed = [
    re.sub(r"\s*\(.*?\)", "", part).strip().strip("`")
    for part in scope_m.group(1).split(",")
    if part.strip()
]
worktree = root / ".claude" / "worktrees" / args.task

print(f"Task      : {args.task} - {title}")
print(f"Branch    : {branch}  (from your current commit)")
print(f"Worktree  : {worktree}")
print("In scope  :")
for a in allowed:
    print(f"   {a}")
if args.dry_run:
    print("\nDry run: nothing created.")
    sys.exit(0)

subprocess.run(["git", "worktree", "add", "-b", branch, str(worktree), "HEAD"], cwd=root, check=True)
(worktree / ".agents" / "progress").mkdir(parents=True, exist_ok=True)
(worktree / ".agents" / "scope.json").write_text(
    json.dumps({"task": args.task, "allowed": allowed}, indent=2) + "\n", encoding="utf-8"
)
progress = worktree / ".agents" / "progress" / f"{args.task}.md"
progress.write_text(
    f"# {args.task} progress\n**Objective:** {title}\n**Status:** in progress\n\n## Done\n- (nothing yet)\n\n"
    "## Pending\n- (see tasks.md)\n\n## Decisions\n- \n\n## Blockers / questions for a human\n- \n",
    encoding="utf-8",
)
if (root / ".env").exists():
    shutil.copy(root / ".env", worktree / ".env")
print(f"\nReady. Next:  cd {worktree.relative_to(root).as_posix()}  then start claude there.")
