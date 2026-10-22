#!/usr/bin/env bash
# CareDesk Day-1 preflight. Run from the repo root. Exits non-zero if anything required is missing.
fail=0
check() {
  if command -v "$1" >/dev/null 2>&1; then echo "OK   $1: $($1 --version 2>&1 | head -1)"
  else echo "FAIL $1 not found"; fail=1; fi
}
check claude; check git; check uv; check node
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "FAIL ANTHROPIC_API_KEY is set: it overrides your seat login and bills the API. Run: unset ANTHROPIC_API_KEY"
  fail=1
else
  echo "OK   ANTHROPIC_API_KEY not set"
fi
if [ ! -f .env ]; then cp .env.example .env && echo "OK   created .env from .env.example"; fi
if (cd backend && uv run --python 3.12 --group dev pytest -q >/dev/null 2>&1); then
  echo "OK   backend tests pass"
else
  echo "FAIL backend tests"; fail=1
fi
# Day 2: optional PostgreSQL reachability check (only when PGHOST is set in .env)
if [ -f .env ] && grep -q "^PGHOST=" .env; then
  if (cd backend && uv run python -c "from app.db import engine; engine.connect().close()" >/dev/null 2>&1); then echo "OK   PostgreSQL reachable"; else echo "FAIL PostgreSQL not reachable (check .env values and network/firewall)"; fail=1; fi
fi
if [ $fail -eq 0 ]; then echo "PREFLIGHT PASSED"; else echo "PREFLIGHT FAILED"; fi
exit $fail
