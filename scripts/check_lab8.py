"""Lab 8 checker. Run from the repo root: python scripts/check_lab8.py [feature-folder]"""
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


def frontmatter(path: Path) -> dict[str, str]:
    m = re.match(r"^---\r?\n(.*?)\r?\n---", path.read_text(encoding="utf-8-sig"), re.S)
    out: dict[str, str] = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
    return out


for persona in ("analyst", "architect"):
    path = root / ".claude" / "agents" / f"{persona}.md"
    need(path.exists(), f".claude/agents/{persona}.md exists")
    if not path.exists():
        continue
    fm = frontmatter(path)
    body = path.read_text(encoding="utf-8-sig")
    need(fm.get("name") == persona, f"{persona}: name matches the file name")
    need(len(fm.get("description", "")) >= 100, f"{persona}: description says when to use it (>= 100 chars)")
    need("use" in fm.get("description", "").lower(), f"{persona}: description tells Claude when to delegate ('Use ...')")
    tools = {t.strip() for t in fm.get("tools", "").split(",") if t.strip()}
    need(bool(tools), f"{persona}: tools are restricted with an allow-list")
    need(not tools & {"Bash", "Edit", "MultiEdit", "NotebookEdit"}, f"{persona}: no shell and no code-editing tools")
    need("model" in fm, f"{persona}: model is chosen explicitly")
    need(re.search(r"never write or change code|do not write code", body, re.I) is not None, f"{persona}: body forbids writing code")
    need(re.search(r"^##\s+Output", body, re.M) is not None, f"{persona}: body defines an Output format")
    need(re.search(r"data, never as instructions|untrusted", body, re.I) is not None, f"{persona}: body treats file text as data")

brief = root / "specs" / feature / "analyst-brief.md"
arch = root / "specs" / feature / "architecture.md"
need(brief.exists(), f"specs/{feature}/analyst-brief.md exists")
need(arch.exists(), f"specs/{feature}/architecture.md exists")
if brief.exists():
    t = brief.read_text(encoding="utf-8-sig")
    for h in ("Problem", "Users", "Goals", "Assumptions", "Risks", "Open questions"):
        need(re.search(rf"^##\s+.*{h}", t, re.M | re.I) is not None, f"brief has a '{h}' section")
    need(len(re.findall(r"^\d+\.\s", t, re.M)) >= 3, "brief lists at least 3 numbered open questions")
if arch.exists():
    t = arch.read_text(encoding="utf-8-sig")
    for h in ("Context", "Components", "Data", "Interfaces", "Risks", "Options considered", "Decisions"):
        need(re.search(rf"^##\s+.*{h}", t, re.M | re.I) is not None, f"architecture has a '{h}' section")

if shutil.which("claude"):
    r = subprocess.run(
        ["claude", "plugin", "validate", str(root / ".claude" / "agents")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    need(r.returncode == 0, "claude plugin validate passes for .claude/agents")
else:
    print("SKIP  claude not on PATH: skipping agent validation")

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} CHECK(S) FAILED")
sys.exit(1 if problems else 0)
