"""TRAINER TOOL: create one database + one app role + one read-only role per participant.

Run once before Day 2. It needs the ADMIN login, which is read from environment variables only and
is never written anywhere:

    PGHOST, PGADMINUSER, PGADMINPASSWORD  (and optionally PGPORT, PGSSLMODE; default sslmode=require)

Per alias `ana` it creates:
    role      ana        LOGIN, owns database caredesk_ana         (used by the app and Alembic)
    role      ana_ro     LOGIN, SELECT only, read-only by default  (used by the MCP lab)
    database  caredesk_ana

Safe by default: without --execute it only prints what it would do. Passwords are generated
randomly and written to a git-ignored CSV (--out). Existing roles keep their passwords unless
--reset-passwords is given. --drop removes everything created for the aliases (needs --yes).

    uv run --with "psycopg[binary]" python tools/provision_participant_dbs.py --alias ana ravi
    uv run --with "psycopg[binary]" python tools/provision_participant_dbs.py --aliases-file names.txt --execute
"""
import argparse
import csv
import os
import re
import secrets
import sys
from pathlib import Path

import psycopg
from psycopg import sql

ALIAS_RE = re.compile(r"^[a-z][a-z0-9_]{1,20}$")


def admin_conn(dbname: str) -> psycopg.Connection:
    missing = [k for k in ("PGHOST", "PGADMINUSER", "PGADMINPASSWORD") if not os.environ.get(k)]
    if missing:
        sys.exit(f"Set these environment variables first: {', '.join(missing)}")
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ.get("PGPORT", "5432")),
        user=os.environ["PGADMINUSER"],
        password=os.environ["PGADMINPASSWORD"],
        dbname=dbname,
        sslmode=os.environ.get("PGSSLMODE", "require"),
        connect_timeout=15,
        autocommit=True,
    )


def role_exists(cur, name: str) -> bool:
    cur.execute("select 1 from pg_roles where rolname = %s", (name,))
    return cur.fetchone() is not None


def db_exists(cur, name: str) -> bool:
    cur.execute("select 1 from pg_database where datname = %s", (name,))
    return cur.fetchone() is not None


def provision(alias: str, reset: bool, execute: bool, writer) -> None:
    owner, ro, db = alias, f"{alias}_ro", f"caredesk_{alias}"
    pw_owner, pw_ro = secrets.token_urlsafe(14), secrets.token_urlsafe(14)
    print(f"{alias}: role {owner}, role {ro}, database {db}")
    if not execute:
        return
    with admin_conn("postgres") as conn:
        cur = conn.cursor()
        created = {}
        for role, pw in ((owner, pw_owner), (ro, pw_ro)):
            if not role_exists(cur, role):
                cur.execute(sql.SQL("create role {} login password {}").format(sql.Identifier(role), sql.Literal(pw)))
                created[role] = pw
            elif reset:
                cur.execute(sql.SQL("alter role {} password {}").format(sql.Identifier(role), sql.Literal(pw)))
                created[role] = pw
        # Azure's admin is not a superuser: it must be a member of a role to make it own a database.
        cur.execute(sql.SQL("grant {} to current_user").format(sql.Identifier(owner)))
        if not db_exists(cur, db):
            cur.execute(sql.SQL("create database {} owner {}").format(sql.Identifier(db), sql.Identifier(owner)))
        cur.execute(sql.SQL("revoke connect on database {} from public").format(sql.Identifier(db)))
        cur.execute(sql.SQL("grant connect on database {} to {}").format(sql.Identifier(db), sql.Identifier(ro)))
        cur.execute(sql.SQL("alter role {} set default_transaction_read_only = on").format(sql.Identifier(ro)))
        cur.execute(sql.SQL("alter role {} set statement_timeout = '5s'").format(sql.Identifier(ro)))
    # Azure: the owner of a new database is NOT automatically allowed to create objects in the public
    # schema ("permission denied for schema public"). Grant it from inside the new database.
    with admin_conn(db) as dbconn:
        dbconn.execute(sql.SQL("grant all on schema public to {}").format(sql.Identifier(owner)))
    # Read-only role gets SELECT on tables the owner creates later (Alembic runs as the owner).
    # Executed as the owner, so no extra membership is needed.
    owner_pw = created.get(owner)
    if owner_pw:
        with psycopg.connect(
            host=os.environ["PGHOST"], port=int(os.environ.get("PGPORT", "5432")), user=owner,
            password=owner_pw, dbname=db, sslmode=os.environ.get("PGSSLMODE", "require"),
            connect_timeout=15, autocommit=True,
        ) as oc:
            c = oc.cursor()
            c.execute(sql.SQL("grant usage on schema public to {}").format(sql.Identifier(ro)))
            c.execute(sql.SQL("alter default privileges in schema public grant select on tables to {}").format(sql.Identifier(ro)))
    for role, pw in created.items():
        writer.writerow([alias, role, db, pw])


def drop(alias: str) -> None:
    owner, ro, db = alias, f"{alias}_ro", f"caredesk_{alias}"
    with admin_conn("postgres") as conn:
        cur = conn.cursor()
        cur.execute(sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(db)))
        for role in (ro, owner):
            cur.execute(sql.SQL("drop role if exists {}").format(sql.Identifier(role)))
    print(f"dropped {alias}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alias", nargs="*", default=[], help="participant aliases")
    ap.add_argument("--aliases-file", help="text file, one alias per line")
    ap.add_argument("--execute", action="store_true", help="actually create things (default: dry run)")
    ap.add_argument("--reset-passwords", action="store_true")
    ap.add_argument("--drop", action="store_true", help="remove databases and roles for the aliases")
    ap.add_argument("--yes", action="store_true", help="confirm --drop")
    ap.add_argument("--out", default="provisioned_credentials.csv")
    a = ap.parse_args()

    aliases = list(a.alias)
    if a.aliases_file:
        aliases += [x.strip() for x in Path(a.aliases_file).read_text().splitlines() if x.strip()]
    bad = [x for x in aliases if not ALIAS_RE.match(x)]
    if bad or not aliases:
        sys.exit(f"Invalid or missing aliases (lowercase letters/digits/_, 2-21 chars): {bad or 'none given'}")

    if a.drop:
        if not (a.yes and a.execute):
            sys.exit("--drop needs --execute --yes")
        for x in aliases:
            drop(x)
        return

    out = Path(a.out)
    new_file = a.execute and not out.exists()
    with (out.open("a", newline="") if a.execute else open(os.devnull, "w")) as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["alias", "role", "database", "password"])
        for x in aliases:
            provision(x, a.reset_passwords, a.execute, w)
    print("\nDRY RUN: nothing was created. Add --execute." if not a.execute else f"\nCredentials appended to {out} (git-ignored). Distribute individually.")


if __name__ == "__main__":
    main()
