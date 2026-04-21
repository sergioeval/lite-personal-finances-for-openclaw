# Lite Personal Finances

A small Python CLI for tracking income and expenses in a local SQLite database.

## Features

- add expenses from the command line
- add income from the command line
- delete transactions by ID
- manage accounts
- store data locally in SQLite
- list recorded transactions
- show income, expense, balance, category, month, and account summaries

## Usage

Initialize the database:

```bash
python3 finances.py init
```

Add an account:

```bash
python3 finances.py account add Main debit "primary checking"
```

List accounts:

```bash
python3 finances.py account list
```

Add an expense:

```bash
python3 finances.py add 120.50 groceries "supermarket run" --account 1
```

Add income:

```bash
python3 finances.py income 1500 salary "monthly payment" --account 1
```

Delete a transaction:

```bash
python3 finances.py delete 3
```

List transactions:

```bash
python3 finances.py list
```

Limit the list:

```bash
python3 finances.py list --limit 5
```

Show a summary:

```bash
python3 finances.py summary
python3 finances.py summary --month 2026-02
python3 finances.py summary --account 1
python3 finances.py summary --category groceries
python3 finances.py summary --month 2026-02 --category groceries
```

## Data file

The SQLite database is created locally as:

```text
finances.sqlite3
```

It is ignored by git and should not be committed.
