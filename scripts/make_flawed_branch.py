"""Create a deliberately flawed pull-request branch for the review exercises (Labs 10 and 11).

    python scripts/make_flawed_branch.py

Creates branch `pr/flawed-lookup` from your CURRENT commit with one commit that contains three planted flaws:
  1. SQL built with an f-string (injection)
  2. a patient's phone number written to the log (personal data)
  3. an existing test silently skipped

Your working branch is left untouched. Review it with:   git diff HEAD...pr/flawed-lookup
(Use THREE dots. Two dots would also show everything you committed after the branch was created.)
"""
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
BRANCH = "pr/flawed-lookup"


def git(*a: str, check: bool = True) -> str:
    r = subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode:
        sys.exit(f"git {' '.join(a)} failed:\n{r.stderr}")
    return r.stdout.strip()


if git("status", "--porcelain"):
    sys.exit("Commit or stash your changes first (the flawed branch is created from your current commit).")
start = git("rev-parse", "--abbrev-ref", "HEAD")
detached = start == "HEAD"  # e.g. after `git switch --detach tags/lab-10-start`
if detached:
    start = git("rev-parse", "HEAD")
if git("branch", "--list", BRANCH):
    sys.exit(f"Branch {BRANCH} already exists. Delete it first:  git branch -D {BRANCH}")

LOOKUP = '''"""Look up a patient contact by phone number (used by the front desk)."""
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


def find_contact(db: Session, phone: str):
    log.info("looking up contact for %s", phone)
    return db.execute(text(f"select * from patient_contacts where phone = '{phone}'")).fetchall()
'''

git("switch", "-c", BRANCH)
try:
    (root / "backend" / "app" / "reminders" / "lookup.py").write_text(LOOKUP, encoding="utf-8")
    tests = root / "backend" / "tests" / "test_reminder_service.py"
    t = tests.read_text(encoding="utf-8")
    t2 = re.sub(
        r"(def test_SPEC001_AC2_does_not_text_an_opted_out_patient)",
        '@pytest.mark.skip(reason="flaky")\n\\1',
        t,
        count=1,
    )
    if "import pytest" not in t2:
        t2 = "import pytest\n" + t2
    tests.write_text(t2, encoding="utf-8")
    git("add", "backend/app/reminders/lookup.py", "backend/tests/test_reminder_service.py")
    git(
        "-c", "user.name=Lab Student", "-c", "user.email=student@example.test",
        "commit", "-q", "-m", "Add contact lookup for the front desk",
    )
finally:
    git("switch", "--detach", start) if detached else git("switch", start)

where = "your detached commit" if detached else f"'{start}'"
print(f"Created {BRANCH} with 1 commit (3 planted flaws). You are back on {where}.")
print(f"Review it:  git diff HEAD...{BRANCH}    (three dots: only what the flawed branch added)")
