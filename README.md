# Lite Personal Finances

A small Python CLI for tracking income and expenses in a local SQLite database.

## Features

- add expenses from the command line
- add income from the command line
- delete transactions by ID
- store data locally in SQLite
- list recorded transactions
- show income, expense, and net balance summaries

## Usage

Initialize the database:

```bash
python3 finances.py init
```

Add an expense:

```bash
python3 finances.py add 120.50 groceries "supermarket run"
```

Add income:

```bash
python3 finances.py income 1500 salary "monthly payment"
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
```

## Data file

The SQLite database is created locally as:

```text
finances.sqlite3
```

It is ignored by git and should not be committed.
