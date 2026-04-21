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


@dataclass(frozen=True)
class Transaction:
    id: int
    spent_at: str
    amount: float
    type: str
    category: str
    note: str


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spent_at TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount >= 0),
                type TEXT NOT NULL CHECK(type IN ('expense', 'income')),
                category TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.commit()


def add_transaction(kind: str, amount: float, category: str, note: str, spent_at: str | None = None) -> int:
    if kind not in VALID_TYPES:
        raise ValueError(f"Invalid transaction type: {kind}")
    init_db()
    spent_at = spent_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO transactions (spent_at, amount, type, category, note) VALUES (?, ?, ?, ?, ?)",
            (spent_at, amount, kind, category, note),
        )
        conn.commit()
        return int(cur.lastrowid)


def fetch_transactions(limit: int | None = None) -> list[Transaction]:
    init_db()
    query = "SELECT id, spent_at, amount, type, category, note FROM transactions ORDER BY spent_at DESC, id DESC"
    params: tuple[object, ...] = ()
    if limit is not None:
        query += " LIMIT ?"
        params = (limit,)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [Transaction(**dict(row)) for row in rows]


def print_transactions(items: Iterable[Transaction]) -> None:
    rows = list(items)
    if not rows:
        print("No transactions recorded yet.")
        return

    print(f"{'ID':>4}  {'Spent at':<20}  {'Type':<8}  {'Amount':>10}  {'Category':<16}  Note")
    print("-" * 95)
    for item in rows:
        print(
            f"{item.id:>4}  {item.spent_at[:19]:<20}  {item.type:<8}  {item.amount:>10.2f}  {item.category:<16}  {item.note}"
        )


def print_summary() -> None:
    init_db()
    with connect() as conn:
        totals = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income_total,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expense_total
            FROM transactions
            """
        ).fetchone()
        by_type = conn.execute(
            "SELECT type, COALESCE(SUM(amount), 0) AS total FROM transactions GROUP BY type ORDER BY type ASC"
        ).fetchall()
        by_category = conn.execute(
            "SELECT type, category, COALESCE(SUM(amount), 0) AS total FROM transactions GROUP BY type, category ORDER BY type ASC, total DESC, category ASC"
        ).fetchall()

    income_total = float(totals["income_total"])
    expense_total = float(totals["expense_total"])
    balance = income_total - expense_total

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lite personal finances tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add an expense")
    add_parser.add_argument("amount", type=float, help="Expense amount")
    add_parser.add_argument("category", help="Expense category")
    add_parser.add_argument("note", nargs="?", default="", help="Optional note")
    add_parser.add_argument("--spent-at", dest="spent_at", help="ISO timestamp, defaults to now in UTC")

    income_parser = subparsers.add_parser("income", help="Add an income")
    income_parser.add_argument("amount", type=float, help="Income amount")
    income_parser.add_argument("category", help="Income category")
    income_parser.add_argument("note", nargs="?", default="", help="Optional note")
    income_parser.add_argument("--spent-at", dest="spent_at", help="ISO timestamp, defaults to now in UTC")

    list_parser = subparsers.add_parser("list", help="List transactions")
    list_parser.add_argument("--limit", type=int, default=None, help="Limit number of rows")

    subparsers.add_parser("summary", help="Show income, expenses, and balance")
    subparsers.add_parser("init", help="Initialize the database")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "init":
        init_db()
        print(f"Database ready at {DB_PATH}")
        return

    if args.command == "add":
        row_id = add_transaction("expense", args.amount, args.category, args.note, args.spent_at)
        print(f"Recorded expense #{row_id}")
        return

    if args.command == "income":
        row_id = add_transaction("income", args.amount, args.category, args.note, args.spent_at)
        print(f"Recorded income #{row_id}")
        return

    if args.command == "list":
        print_transactions(fetch_transactions(args.limit))
        return

    if args.command == "summary":
        print_summary()
        return


if __name__ == "__main__":
    main()
