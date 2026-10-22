"""Lab 5 checker. Run from the repo root: python scripts/check_lab5.py"""
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
server = root / "mcp_servers" / "clinic_rules" / "server.py"
smoke = root / "mcp_servers" / "clinic_rules" / "smoke.py"
problems: list[str] = []


def need(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


need(server.exists(), "mcp_servers/clinic_rules/server.py exists")
need((root / "mcp_servers" / "clinic_rules" / "policies").is_dir(), "policies/ folder exists")

mcp_json = root / ".mcp.json"
need(mcp_json.exists(), ".mcp.json exists (project scope, committed)")
if mcp_json.exists():
    try:
        cfg = json.loads(mcp_json.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        cfg = {}
        need(False, f".mcp.json is valid JSON ({e})")
    servers = cfg.get("mcpServers", {})
    need("clinic-rules" in servers, "clinic-rules is registered")
    raw = mcp_json.read_text(encoding="utf-8-sig")
    need(not re.search(r"MCP_PGPASSWORD\"\s*:\s*\"(?!\$\{)", raw), "no literal password in .mcp.json (uses ${VAR})")

if server.exists():
    src = server.read_text(encoding="utf-8-sig")
    tree = ast.parse(src)
    prints = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print"]
    need(not prints, "server never calls print() (stdout carries the MCP protocol)")
    tools = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and any("tool" in ast.unparse(d) for d in n.decorator_list)
    ]
    need(len(tools) >= 2, "at least two tools are defined")
    for t in tools:
        doc = ast.get_docstring(t) or ""
        need(len(doc) >= 120, f"tool {t.name}: description is substantive ({len(doc)} chars, need >= 120)")
    need("read_only" in src or "SELECT" in src.upper(), "database access is read-only (SELECT only)")
    need(not re.search(r"execute\(\s*f[\"']", src), "SQL is parameterised (no f-string SQL)")
    need("ToolError" in src, "failures are raised as ToolError (structured, not a crash)")

if smoke.exists():
    r = subprocess.run(
        ["uv", "run", "--python", "3.12", "--script", str(smoke)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=root
    )
    out = r.stdout
    need(r.returncode == 0, "smoke test exits 0")
    need("lookup_appointment_rules" in out, "smoke test lists the lookup tool")
    need("list_upcoming_appointments" in out, "smoke test lists the appointments tool")
    need("[cancellation]" in out, "smoke test tool call returned the cancellation policy")

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} CHECK(S) FAILED")
sys.exit(1 if problems else 0)
