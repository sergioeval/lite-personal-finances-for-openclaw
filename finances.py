#!/usr/bin/env python3
"""Lite personal finances CLI.

Stores income and expenses in a local SQLite database.
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

DB_PATH = Path(__file__).with_name("finances.sqlite3")
VALID_TYPES = {"expense", "income"}
VALID_ACCOUNT_TYPES = {"debit", "credit"}


@dataclass(frozen=True)
class Account:
    id: int
    name: str
    type: str
    note: str


@dataclass(frozen=True)
class Transaction:
    id: int
    spent_at: str
    amount: float
    type: str
    category: str
    account_id: int
    account_name: str
    account_type: str
    note: str


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL CHECK(type IN ('debit', 'credit')),
                note TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spent_at TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount >= 0),
                type TEXT NOT NULL CHECK(type IN ('expense', 'income')),
                category TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE RESTRICT
            )
            """
        )
        conn.commit()


def ensure_default_account() -> int:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT id FROM accounts ORDER BY id ASC LIMIT 1").fetchone()
        if row:
            return int(row[0])
        cur = conn.execute(
            "INSERT INTO accounts (name, type, note) VALUES (?, ?, ?)",
            ("Default", "debit", "Auto-created default account"),
        )
        conn.commit()
        return int(cur.lastrowid)


def add_account(name: str, account_type: str, note: str) -> int:
    if account_type not in VALID_ACCOUNT_TYPES:
        raise ValueError(f"Invalid account type: {account_type}")
    init_db()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO accounts (name, type, note) VALUES (?, ?, ?)",
            (name, account_type, note),
        )
        conn.commit()
        return int(cur.lastrowid)


def fetch_accounts() -> list[Account]:
    init_db()
    with connect() as conn:
        rows = conn.execute("SELECT id, name, type, note FROM accounts ORDER BY id ASC").fetchall()
    return [Account(**dict(row)) for row in rows]


def add_transaction(kind: str, amount: float, category: str, account_id: int, note: str, spent_at: str | None = None) -> int:
    if kind not in VALID_TYPES:
        raise ValueError(f"Invalid transaction type: {kind}")
    init_db()
    spent_at = spent_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        account = conn.execute("SELECT id FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if account is None:
            raise ValueError(f"Account #{account_id} not found")
        cur = conn.execute(
            "INSERT INTO transactions (spent_at, amount, type, category, account_id, note) VALUES (?, ?, ?, ?, ?, ?)",
            (spent_at, amount, kind, category, account_id, note),
        )
        conn.commit()
        return int(cur.lastrowid)


def delete_transaction(transaction_id: int) -> bool:
    init_db()
    with connect() as conn:
        cur = conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        return cur.rowcount > 0


def fetch_transactions(limit: int | None = None) -> list[Transaction]:
    init_db()
    query = """
        SELECT t.id, t.spent_at, t.amount, t.type, t.category, t.account_id, a.name AS account_name, a.type AS account_type, t.note
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        ORDER BY t.spent_at DESC, t.id DESC
    """
    params: tuple[object, ...] = ()
    if limit is not None:
        query += " LIMIT ?"
        params = (limit,)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [Transaction(**dict(row)) for row in rows]


def build_filters(month: str | None, account_id: int | None, category: str | None):
    clauses = []
    params: list[object] = []
    if month:
        clauses.append("substr(t.spent_at, 1, 7) = ?")
        params.append(month)
    if account_id is not None:
        clauses.append("t.account_id = ?")
        params.append(account_id)
    if category:
        clauses.append("t.category = ?")
        params.append(category)
    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    return where_sql, params


def print_transactions(items: Iterable[Transaction]) -> None:
    rows = list(items)
    if not rows:
        print("No transactions recorded yet.")
        return

    print(f"{'ID':>4}  {'Spent at':<20}  {'Type':<8}  {'Amount':>10}  {'Account':<14}  {'Category':<16}  Note")
    print("-" * 115)
    for item in rows:
        print(
            f"{item.id:>4}  {item.spent_at[:19]:<20}  {item.type:<8}  {item.amount:>10.2f}  {item.account_name:<14}  {item.category:<16}  {item.note}"
        )


def print_accounts() -> None:
    rows = fetch_accounts()
    if not rows:
        print("No accounts recorded yet.")
        return
    print(f"{'ID':>4}  {'Type':<8}  {'Name':<20}  Note")
    print("-" * 60)
    for account in rows:
        print(f"{account.id:>4}  {account.type:<8}  {account.name:<20}  {account.note}")


def print_summary(month: str | None = None, account_id: int | None = None, category: str | None = None) -> None:
    init_db()
    where_sql, params = build_filters(month, account_id, category)
    with connect() as conn:
        totals = conn.execute(
            f"""
            SELECT
                COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) AS income_total,
                COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) AS expense_total
            FROM transactions t
            {where_sql}
            """,
            params,
        ).fetchone()

        by_type = conn.execute(
            f"""
            SELECT t.type, COALESCE(SUM(t.amount), 0) AS total
            FROM transactions t
            {where_sql}
            GROUP BY t.type
            ORDER BY t.type ASC
            """,
            params,
        ).fetchall()

        by_category = conn.execute(
            f"""
            SELECT t.type, t.category, COALESCE(SUM(t.amount), 0) AS total
            FROM transactions t
            {where_sql}
            GROUP BY t.type, t.category
            ORDER BY t.type ASC, total DESC, t.category ASC
            """,
            params,
        ).fetchall()

        by_account = conn.execute(
            f"""
            SELECT a.id, a.name, a.type AS account_type,
                   COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) AS income_total,
                   COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) AS expense_total
            FROM accounts a
            LEFT JOIN transactions t ON t.account_id = a.id
            {where_sql.replace('t.', 't.')}
            GROUP BY a.id, a.name, a.type
            ORDER BY a.id ASC
            """,
            params,
        ).fetchall()

    income_total = float(totals["income_total"])
    expense_total = float(totals["expense_total"])
    balance = income_total - expense_total

    header = "Summary"
    if month:
        header += f" for {month}"
    if account_id is not None:
        header += f" (account #{account_id})"
    if category:
        header += f" (category: {category})"
    print(header)
    print(f"Total income:  {income_total:.2f}")
    print(f"Total expense: {expense_total:.2f}")
    print(f"Net balance:   {balance:.2f}")

    if by_type:
        print("By type:")
        for row in by_type:
            print(f"  - {row['type']}: {row['total']:.2f}")

    if by_category:
        print("By category:")
        for row in by_category:
            print(f"  - {row['type']} / {row['category']}: {row['total']:.2f}")

    if by_account:
        print("By account:")
        for row in by_account:
            net = float(row["income_total"]) - float(row["expense_total"])
            print(
                f"  - #{row['id']} {row['name']} ({row['account_type']}): income {row['income_total']:.2f}, expense {row['expense_total']:.2f}, net {net:.2f}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lite personal finances tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    account_parser = subparsers.add_parser("account", help="Manage accounts")
    account_subparsers = account_parser.add_subparsers(dest="account_command", required=True)

    account_add = account_subparsers.add_parser("add", help="Add an account")
    account_add.add_argument("name", help="Account name")
    account_add.add_argument("type", choices=sorted(VALID_ACCOUNT_TYPES), help="Account type")
    account_add.add_argument("note", nargs="?", default="", help="Optional note")

    account_subparsers.add_parser("list", help="List accounts")

    add_parser = subparsers.add_parser("add", help="Add an expense")
    add_parser.add_argument("amount", type=float, help="Expense amount")
    add_parser.add_argument("category", help="Expense category")
    add_parser.add_argument("note", nargs="?", default="", help="Optional note")
    add_parser.add_argument("--account", type=int, default=None, help="Account ID")
    add_parser.add_argument("--spent-at", dest="spent_at", help="ISO timestamp, defaults to now in UTC")

    income_parser = subparsers.add_parser("income", help="Add an income")
    income_parser.add_argument("amount", type=float, help="Income amount")
    income_parser.add_argument("category", help="Income category")
    income_parser.add_argument("note", nargs="?", default="", help="Optional note")
    income_parser.add_argument("--account", type=int, default=None, help="Account ID")
    income_parser.add_argument("--spent-at", dest="spent_at", help="ISO timestamp, defaults to now in UTC")

    delete_parser = subparsers.add_parser("delete", help="Delete a transaction by ID")
    delete_parser.add_argument("id", type=int, help="Transaction ID")

    list_parser = subparsers.add_parser("list", help="List transactions")
    list_parser.add_argument("--limit", type=int, default=None, help="Limit number of rows")

    summary_parser = subparsers.add_parser("summary", help="Show income, expenses, and balance")
    summary_parser.add_argument("--month", help="Filter by month in YYYY-MM format")
    summary_parser.add_argument("--account", type=int, default=None, help="Filter by account ID")
    summary_parser.add_argument("--category", help="Filter by category")

    subparsers.add_parser("init", help="Initialize the database")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "init":
        init_db()
        default_account_id = ensure_default_account()
        print(f"Database ready at {DB_PATH}")
        print(f"Default account ready as #{default_account_id}")
        return

    if args.command == "account":
        if args.account_command == "add":
            row_id = add_account(args.name, args.type, args.note)
            print(f"Recorded account #{row_id}")
            return
        if args.account_command == "list":
            print_accounts()
            return

    if args.command == "add":
        account_id = args.account or ensure_default_account()
        row_id = add_transaction("expense", args.amount, args.category, account_id, args.note, args.spent_at)
        print(f"Recorded expense #{row_id}")
        return

    if args.command == "income":
        account_id = args.account or ensure_default_account()
        row_id = add_transaction("income", args.amount, args.category, account_id, args.note, args.spent_at)
        print(f"Recorded income #{row_id}")
        return

    if args.command == "delete":
        removed = delete_transaction(args.id)
        if removed:
            print(f"Deleted transaction #{args.id}")
        else:
            print(f"Transaction #{args.id} not found")
        return

    if args.command == "list":
        print_transactions(fetch_transactions(args.limit))
        return

    if args.command == "summary":
        print_summary(args.month, args.account, args.category)
        return


if __name__ == "__main__":
    main()
