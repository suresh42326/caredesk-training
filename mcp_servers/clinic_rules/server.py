# /// script
# requires-python = ">=3.10"
# dependencies = ["fastmcp>=4,<5", "psycopg[binary]>=3.2", "python-dotenv>=1.0"]
# ///
"""CareDesk clinic-rules MCP server (read-only).

Exposes:
  tool      lookup_appointment_rules(topic)        clinic policy text
  tool      list_upcoming_appointments(patient_id) rows from the database, via a SELECT-only role
  resource  clinic://policies/{name}               one policy document
  resource  clinic://policies                      index of policy names
  prompt    explain_policy(topic)                  reusable instruction template

RULE FOR STDIO SERVERS: never print to stdout. stdout carries the protocol. Log to stderr.
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("clinic-rules")

HERE = Path(__file__).resolve().parent
POLICY_DIR = Path(os.environ.get("POLICY_DIR") or HERE / "policies").resolve()
_DOTENV = dotenv_values(HERE.parents[1] / ".env")  # repo-root .env (git-ignored); real env wins

mcp = FastMCP(
    "clinic-rules",
    instructions="Read-only access to CareDesk clinic policies and a patient's upcoming appointments.",
)


def _setting(name: str) -> str | None:
    """Environment first, then the repo .env. Empty strings count as unset."""
    return os.environ.get(name) or _DOTENV.get(name) or None


def _policies() -> dict[str, Path]:
    return {p.stem: p for p in sorted(POLICY_DIR.glob("*.md"))}


@mcp.tool
def lookup_appointment_rules(topic: str) -> str:
    """Look up the clinic's written appointment policies (cancellation, rescheduling, late arrival,
    no-shows, telehealth). Use this whenever a question is about what the CLINIC ALLOWS or CHARGES;
    do not guess policy from the code. Returns the matching policy documents, or a clear
    'no rules found' message. Read-only. Does not look at any patient's actual appointments."""
    t = topic.lower().strip()
    hits = [
        f"[{name}]\n{p.read_text(encoding='utf-8').strip()}"
        for name, p in _policies().items()
        if t in name.lower() or t in p.read_text(encoding="utf-8").lower()
    ]
    return "\n\n".join(hits) or f"No rules found for '{topic}'. Available: {', '.join(_policies())}."


@mcp.tool
def list_upcoming_appointments(patient_id: int, limit: int = 10) -> dict:
    """List ONE patient's upcoming appointments (soonest first) from the CareDesk database.
    Use this for questions about a specific patient's schedule, not for clinic policy.
    Read-only: connects with a SELECT-only database role. An empty list means the patient has no
    upcoming appointments; it is not an error."""
    if not 1 <= limit <= 50:
        raise ToolError("limit must be between 1 and 50")
    host, user, password = _setting("MCP_PGHOST"), _setting("MCP_PGUSER"), _setting("MCP_PGPASSWORD")
    database = _setting("MCP_PGDATABASE")
    if not (host and user and password and database):
        raise ToolError(
            "Database access is not configured for this server. Set MCP_PGHOST, MCP_PGDATABASE, "
            "MCP_PGUSER and MCP_PGPASSWORD (read-only role) and restart. Not retryable until fixed."
        )
    try:
        with psycopg.connect(
            host=host,
            port=int(_setting("MCP_PGPORT") or 5432),
            user=user,
            password=password,
            dbname=database,
            sslmode=_setting("MCP_PGSSLMODE") or "require",
            connect_timeout=10,
            options="-c default_transaction_read_only=on",
        ) as conn:
            rows = conn.execute(
                "select id, starts_at, duration_min, reason from appointments "
                "where patient_id = %s and starts_at >= %s order by starts_at limit %s",
                (patient_id, datetime.now(), limit),
            ).fetchall()
    except psycopg.OperationalError as e:
        log.error("database connection failed: %s", e)
        raise ToolError("Could not connect to the database (network, credentials or firewall). Retryable.") from e
    except psycopg.Error as e:
        log.error("query failed: %s", e)
        raise ToolError(f"Query failed: {type(e).__name__}. Not retryable.") from e
    return {
        "patient_id": patient_id,
        "count": len(rows),
        "appointments": [
            {"id": r[0], "starts_at": r[1].isoformat(), "duration_min": r[2], "reason": r[3]} for r in rows
        ],
    }


@mcp.resource("clinic://policies/{name}", mime_type="text/markdown")
def policy(name: str) -> str:
    """Read one policy document by name (no extension)."""
    files = _policies()
    if name not in files:
        raise ValueError(f"unknown policy {name!r}; available: {sorted(files)}")
    return files[name].read_text(encoding="utf-8")


@mcp.resource("clinic://policies", name="policy-index", mime_type="text/plain")
def policy_index() -> str:
    """List the available policy names."""
    return "\n".join(_policies())


@mcp.prompt
def explain_policy(topic: str) -> str:
    """Explain a clinic policy to a patient in plain language."""
    return (
        f"Use lookup_appointment_rules for '{topic}'. Explain the policy to a patient in plain "
        "language, cite the policy name, and say what they should do next."
    )


if __name__ == "__main__":
    mcp.run()  # stdio
