"""Lab 4a checker. Run from the repo root: python scripts/check_lab4a.py

Checks the code changes for the SQLite -> PostgreSQL migration. If your .env has PGHOST set, it also
connects and confirms the appointments table exists in YOUR database.
"""
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
backend = root / "backend"
problems: list[str] = []


def need(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


pyproject = (backend / "pyproject.toml").read_text(encoding="utf-8-sig")
need("psycopg" in pyproject, "psycopg (PostgreSQL driver) is a dependency")
need("alembic" in pyproject, "alembic is a dependency")

versions = [p for p in (backend / "migrations").glob("*.py") if p.name != "__init__.py"]
need(len(versions) >= 1, "an Alembic revision exists in backend/migrations")
text = " ".join(v.read_text(encoding="utf-8-sig") for v in versions)
need("appointments" in text, "a revision creates the appointments table")

main_py = (backend / "app" / "main.py").read_text(encoding="utf-8-sig")
need("create_all" not in main_py, "main.py no longer calls create_all (Alembic owns the schema)")

db_py = (backend / "app" / "db.py").read_text(encoding="utf-8-sig")
need("URL.create" in db_py or "postgresql" in db_py, "db.py can build a PostgreSQL URL")
need("sslmode" in db_py, "db.py sets sslmode for PostgreSQL")

env_example = (root / ".env.example").read_text(encoding="utf-8-sig")
need("PGHOST" in env_example, ".env.example documents the PG* variables")
active = [ln for ln in env_example.splitlines() if ln.strip().startswith("DATABASE_URL=")]
need(not active, ".env.example does not set DATABASE_URL (it would override PG*)")

r = subprocess.run(["uv", "run", "pytest", "-q"], cwd=backend, capture_output=True, text=True, encoding="utf-8", errors="replace")
need(r.returncode == 0, "backend tests still pass (tests use in-memory SQLite)")

try:
    from dotenv import dotenv_values

    values = {**dotenv_values(root / ".env"), **os.environ}
except Exception:
    values = dict(os.environ)
if values.get("PGHOST"):
    code = (
        "from sqlalchemy import inspect; from app.db import engine; "
        "print('appointments' in inspect(engine).get_table_names())"
    )
    r = subprocess.run(["uv", "run", "python", "-c", code], cwd=backend, capture_output=True, text=True, encoding="utf-8", errors="replace")
    need(r.stdout.strip().endswith("True"), "connected to PostgreSQL and the appointments table exists")
else:
    print("SKIP  PGHOST not set: skipping the live database check")

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} CHECK(S) FAILED")
sys.exit(1 if problems else 0)
