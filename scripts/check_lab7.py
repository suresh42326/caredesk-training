"""Lab 7 checker. Run from the repo root: python scripts/check_lab7.py [feature-folder]

Validates the spec -> design -> tasks artifacts in specs/<feature>/ (default: sms-reminders).
"""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
feature = sys.argv[1] if len(sys.argv) > 1 else "sms-reminders"
folder = root / "specs" / feature
problems: list[str] = []


def need(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


def read(name: str) -> str:
    p = folder / name
    return p.read_text(encoding="utf-8-sig") if p.exists() else ""


def section(text: str, heading: str) -> str:
    m = re.search(rf"^##+\s+{heading}.*?$(.*?)(?=^##+\s|\Z)", text, re.S | re.M | re.I)
    return m.group(1) if m else ""


EARS = re.compile(r"\b(when|while|if|where)\b.+\bshall\b|^the .+ shall\b|\bshall\b", re.I)
# Unfilled template placeholders look like <feature name> or <nnn>. A plain "<" in prose (for example "<=") is fine.
PLACEHOLDER = re.compile(r"<[A-Za-z][^<>\n]{0,40}>")

# ---- spec.md
spec = read("spec.md")
need(bool(spec), f"specs/{feature}/spec.md exists")
if spec:
    need(bool(re.search(r"Status:\s*(Grilled|Approved)", spec)), "spec Status is Grilled or Approved")
    acs = re.findall(r"^\|\s*(SPEC\d+/AC-\d+)\s*\|\s*(.+?)\s*\|", spec, re.M)
    ids = [a for a, _ in acs]
    need(len(ids) >= 6, f"at least 6 acceptance criteria ({len(ids)} found)")
    need(len(set(ids)) == len(ids), "acceptance-criteria ids are unique")
    bad = [a for a, c in acs if not EARS.search(c)]
    need(not bad, "every criterion uses an EARS form with 'shall'" + (f" (fix: {bad})" if bad else ""))
    unwanted = [c for _, c in acs if re.match(r"\s*if\b.+\bthen\b", c, re.I)]
    need(len(unwanted) >= 2, "at least 2 'If ..., then ...' (unwanted-behaviour) criteria")
    oq = section(spec, "Open questions")
    rows = [r for r in oq.splitlines() if r.startswith("|") and not re.match(r"^\|[\s\-|]*$", r) and "Question" not in r]
    resolved = [r for r in rows if len([c for c in r.strip("|").split("|") if c.strip()]) >= 4]
    need(len(resolved) >= 5, f"at least 5 resolved open questions from grilling ({len(resolved)} found)")
    need(len(rows) == len(resolved), "no open question is left unresolved")
    need(len(section(spec, "Out of scope").strip()) > 10, "Out of scope is not empty")
    need(not PLACEHOLDER.search(re.sub(r"<!--.*?-->", "", spec, flags=re.S)), "no template placeholders such as <feature name> left in spec.md")
else:
    ids = []

# ---- design.md
design = read("design.md")
need(bool(design), f"specs/{feature}/design.md exists")
if design:
    for h in ("Data model", "Threat-model", "Test plan", "Rollout"):
        need(bool(section(design, h)), f"design has a '{h}' section")
    need("migration" in design.lower(), "design discusses the migration")
    need(bool(section(design, "Contracts") or section(design, "Interfaces")), "design fixes the contracts between tasks (a 'Contracts' or 'Interfaces' section)")
    missing = [i for i in ids if i not in design]
    need(not missing, "design test plan covers every acceptance criterion" + (f" (missing {missing})" if missing else ""))
    need(not PLACEHOLDER.search(design), "no template placeholders such as <feature name> left in design.md")

# ---- tasks.md
tasks = read("tasks.md")
need(bool(tasks), f"specs/{feature}/tasks.md exists")
if tasks:
    blocks = re.split(r"^##\s+(?=T-\d+-\d+)", tasks, flags=re.M)[1:]
    need(len(blocks) >= 3, f"at least 3 tasks ({len(blocks)} found)")
    covered: set[str] = set()
    for b in blocks:
        tid = re.match(r"(T-\d+-\d+)", b).group(1)
        for label in ("ACs covered", "Mode", "Risk", "Branch", "Budget", "Files in scope", "Done criteria", "Escalate", "Approval"):
            need(label.lower() in b.lower(), f"{tid} has '{label}'")
        need(bool(re.search(r"agent/T-\d+-\d+-[a-z0-9-]+", b)), f"{tid} branch follows agent/<task-id>-<slug>")
        need(bool(re.search(r"Risk:?\*{0,2}\s*(Low|Medium|High)", b, re.I)), f"{tid} has a valid risk tier")
        scope = re.search(r"Files in scope:?\*{0,2}\s*(.+)", b)
        need(bool(scope) and len(scope.group(1).strip()) > 3, f"{tid} lists files in scope")
        appr = re.search(r"Approval:?\*{0,2}\s*(.+)", b)
        signed = bool(appr) and bool(re.search(r"[A-Za-z]{3,}", re.sub(r"(Tech lead|Date)", "", appr.group(1))))
        need(signed, f"{tid} approval block is signed (a name, not blanks)")
        covered |= set(re.findall(r"SPEC\d+/AC-\d+", b))
    miss = [i for i in ids if i not in covered]
    need(not miss, "every acceptance criterion is covered by a task" + (f" (missing {miss})" if miss else ""))
    need(bool(re.search(r"Risk:?\*{0,2}\s*High", tasks, re.I)), "at least one High-risk task (a database migration is High)")
    need(not PLACEHOLDER.search(tasks), "no template placeholders such as <feature name> left in tasks.md")

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} CHECK(S) FAILED")
sys.exit(1 if problems else 0)
