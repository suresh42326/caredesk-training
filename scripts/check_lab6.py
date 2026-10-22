"""Lab 6 checker. Run from the repo root: python scripts/check_lab6.py"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
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


# 1. Slim CLAUDE.md
claude_md = root / "CLAUDE.md"
need(claude_md.exists(), "CLAUDE.md exists")
if claude_md.exists():
    text = claude_md.read_text(encoding="utf-8-sig")
    lines = len(text.splitlines())
    need(lines <= 40, f"CLAUDE.md is lean ({lines} lines, limit 40)")
    need("@AGENTS.md" in text, "CLAUDE.md still imports @AGENTS.md")
    need("fastapi-conventions" in text, "CLAUDE.md points to the fastapi-conventions skill")

# 2. Path-scoped rules
for name in ("python-tests.md", "migrations.md"):
    p = root / ".claude" / "rules" / name
    need(p.exists() and "paths:" in p.read_text(encoding="utf-8-sig"), f".claude/rules/{name} has paths: frontmatter")

# 3. Skills
fc = root / ".claude" / "skills" / "fastapi-conventions"
need((fc / "SKILL.md").exists(), "fastapi-conventions/SKILL.md exists")
need((fc / "reference.md").exists(), "fastapi-conventions/reference.md exists (progressive disclosure)")
if (fc / "SKILL.md").exists():
    fm = frontmatter(fc / "SKILL.md")
    need(len(fm.get("description", "")) >= 80, "fastapi-conventions has a descriptive description (>= 80 chars)")
    need(len((fc / "SKILL.md").read_text(encoding="utf-8-sig").splitlines()) <= 60, "SKILL.md body is short (<= 60 lines)")

ne = root / ".claude" / "skills" / "new-endpoint" / "SKILL.md"
need(ne.exists(), "new-endpoint/SKILL.md exists")
if ne.exists():
    fm = frontmatter(ne)
    need(fm.get("disable-model-invocation", "").lower() == "true", "new-endpoint is user-invoked only (disable-model-invocation)")
    need("allowed-tools" in fm, "new-endpoint restricts tools with allowed-tools")
    need("argument-hint" in fm, "new-endpoint declares an argument-hint")
    need("$ARGUMENTS" in ne.read_text(encoding="utf-8-sig"), "new-endpoint uses $ARGUMENTS")

# 4. Plugin
plugin = root / "plugins" / "caredesk-team"
pj = plugin / ".claude-plugin" / "plugin.json"
need(pj.exists(), "plugin.json exists")
if pj.exists():
    need(json.loads(pj.read_text(encoding="utf-8-sig")).get("name") == "caredesk-team", "plugin name is caredesk-team")
need((plugin / "skills" / "new-endpoint" / "SKILL.md").exists(), "plugin contains the new-endpoint skill")
need((plugin / "skills" / "fastapi-conventions" / "SKILL.md").exists(), "plugin contains the fastapi-conventions skill")
need((plugin / "hooks" / "hooks.json").exists(), "plugin contains hooks/hooks.json")

if shutil.which("claude"):
    r = subprocess.run(["claude", "plugin", "validate", str(plugin)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    need(r.returncode == 0, "claude plugin validate passes")
else:
    print("SKIP  claude not on PATH: skipping plugin validation")

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} CHECK(S) FAILED")
sys.exit(1 if problems else 0)
