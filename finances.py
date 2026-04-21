#!/usr/bin/env python3
"""Lite personal finances CLI.

Stores expenses in a local SQLite database.
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

DB_PATH = Path(__file__).with_name("finances.sqlite3")


@dataclass(frozen=True)
class Expense:
    id: int
    spent_at: str
    amount: float
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
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spent_at TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.commit()


def add_expense(amount: float, category: str, note: str, spent_at: str | None = None) -> int:
    init_db()
    spent_at = spent_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (spent_at, amount, category, note) VALUES (?, ?, ?, ?)",
            (spent_at, amount, category, note),
        )
        conn.commit()
        return int(cur.lastrowid)


def fetch_expenses(limit: int | None = None) -> list[Expense]:
    init_db()
    query = "SELECT id, spent_at, amount, category, note FROM expenses ORDER BY spent_at DESC, id DESC"
    params: tuple[object, ...] = ()
    if limit is not None:
        query += " LIMIT ?"
        params = (limit,)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [Expense(**dict(row)) for row in rows]


def print_expenses(expenses: Iterable[Expense]) -> None:
    rows = list(expenses)
    if not rows:
        print("No expenses recorded yet.")
        return

    print(f"{'ID':>4}  {'Spent at':<20}  {'Amount':>10}  {'Category':<16}  Note")
    print("-" * 80)
    for item in rows:
        print(
            f"{item.id:>4}  {item.spent_at[:19]:<20}  {item.amount:>10.2f}  {item.category:<16}  {item.note}"
        )


def print_summary() -> None:
    init_db()
    with connect() as conn:
        total = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses").fetchone()[0]
        by_category = conn.execute(
            "SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses GROUP BY category ORDER BY total DESC, category ASC"
        ).fetchall()

    print(f"Total spent: {total:.2f}")
    if by_category:
        print("By category:")
        for row in by_category:
            print(f"  - {row['category']}: {row['total']:.2f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lite personal finances tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add an expense")
    add_parser.add_argument("amount", type=float, help="Expense amount")
    add_parser.add_argument("category", help="Expense category")
    add_parser.add_argument("note", nargs="?", default="", help="Optional note")
    add_parser.add_argument("--spent-at", dest="spent_at", help="ISO timestamp, defaults to now in UTC")

    list_parser = subparsers.add_parser("list", help="List expenses")
    list_parser.add_argument("--limit", type=int, default=None, help="Limit number of rows")

    subparsers.add_parser("summary", help="Show totals")
    subparsers.add_parser("init", help="Initialize the database")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "init":
        init_db()
        print(f"Database ready at {DB_PATH}")
        return

    if args.command == "add":
        row_id = add_expense(args.amount, args.category, args.note, args.spent_at)
        print(f"Recorded expense #{row_id}")
        return

    if args.command == "list":
        print_expenses(fetch_expenses(args.limit))
        return

    if args.command == "summary":
        print_summary()
        return


if __name__ == "__main__":
    main()
