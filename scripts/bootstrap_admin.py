"""
Bootstrap or reset an admin user with a hashed password.

Usage:
    python scripts/bootstrap_admin.py --username admin --email admin@example.com
    # password read from $ADMIN_BOOTSTRAP_PASSWORD or prompt

Requires the same Postgres env vars as the backend.
"""
import argparse
import getpass
import os
import sys

import psycopg2
from werkzeug.security import generate_password_hash


def db():
    if os.getenv("DATABASE_URL"):
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    pwd = os.getenv("POSTGRES_PASSWORD")
    if not pwd:
        sys.exit("POSTGRES_PASSWORD or DATABASE_URL must be set")
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=pwd,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--role", default="admin", choices=["admin", "user"])
    args = ap.parse_args()

    password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD")
    if not password:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm:  ")
        if password != confirm:
            sys.exit("Passwords do not match")

    if len(password) < 12:
        sys.exit("Password must be at least 12 characters")

    pwd_hash = generate_password_hash(password)

    conn = db()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username)
                DO UPDATE SET password_hash = EXCLUDED.password_hash,
                              email = EXCLUDED.email,
                              role = EXCLUDED.role,
                              failed_attempts = 0,
                              locked_until = NULL
                """,
                (args.username, args.email, pwd_hash, args.role),
            )
    conn.close()
    print(f"User '{args.username}' ({args.role}) ready.")


if __name__ == "__main__":
    main()
