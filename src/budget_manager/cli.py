"""Command-line interaction: prompts in, text out. No business rules here.

Every decision (is this input valid? what is the next id? what is the balance?)
is delegated to services/validation; every file operation to storage. This
module only asks, shows, and coordinates load -> change -> save.
"""

import argparse
from pathlib import Path

from budget_manager import services, storage
from budget_manager.models import CATEGORIES, Kind, Transaction
from budget_manager.validation import ValidationError, parse_field

DEFAULT_FILE = Path("data/transactions.csv")

MENU = """
1) Add transaction
2) List transactions
3) Report
4) Quit"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive personal budget manager.")
    parser.add_argument(
        "--file", type=Path, default=DEFAULT_FILE, help=f"CSV file to use (default: {DEFAULT_FILE})"
    )
    path: Path = parser.parse_args(argv).file

    result = storage.load_transactions(path)
    if not result.ok:
        # Refuse to continue: saving would rewrite the file without the bad
        # rows, silently deleting data. The user fixes the file first.
        print(f"Cannot open {path} — fix these rows first:")
        for error in result.errors:
            print(f"  {error}")
        return 1

    transactions = result.transactions
    print(f"Loaded {len(transactions)} transaction(s) from {path}.")

    try:
        while True:
            print(MENU)
            choice = input("Choose 1-4: ").strip()
            if choice == "1":
                transactions = add_flow(transactions, path)
            elif choice == "2":
                show_list(transactions)
            elif choice == "3":
                show_report(transactions)
            elif choice == "4":
                return 0
            else:
                print(f"'{choice}' is not an option — enter 1, 2, 3 or 4.")
    except (EOFError, KeyboardInterrupt):
        print()  # Ctrl-D / Ctrl-C: exit cleanly; everything is already saved.
        return 0


PROMPTS = {
    "date": "Date (YYYY-MM-DD): ",
    "kind": f"Kind ({' / '.join(k.value for k in Kind)}): ",
    "category": f"Category ({', '.join(sorted(CATEGORIES))}): ",
    "amount": "Amount (e.g. 18.50): ",
    "currency": "Currency (ISO code, e.g. EUR): ",
}


def ask(field: str) -> str:
    """Prompt until the answer passes that field's validation rule."""
    while True:
        answer = input(PROMPTS[field])
        try:
            parse_field(field, answer)
            return answer
        except ValueError as problem:
            print(f"  ✗ {problem}. Try again.")


def add_flow(transactions: list[Transaction], path: Path) -> list[Transaction]:
    """Prompt for one transaction (each answer checked on entry); save immediately."""
    raw = {field: ask(field) for field in PROMPTS}
    try:
        updated = services.add_transaction(transactions, raw)
    except ValidationError as error:
        print("Not saved:")
        for problem in error.problems:
            print(f"  - {problem}")
        return transactions

    # Save right away so the file always matches what the user has been told.
    storage.save_transactions(path, updated)
    print(f"Saved {updated[-1].id}.")
    return updated


def show_list(transactions: list[Transaction]) -> None:
    if not transactions:
        print("No transactions yet.")
        return
    print(f"{'ID':<6}{'Date':<12}{'Kind':<9}{'Category':<15}{'Amount':>12}  Cur")
    for t in services.list_transactions(transactions):
        print(
            f"{t.id:<6}{t.date.isoformat():<12}{t.kind.value:<9}"
            f"{t.category:<15}{t.amount:>12,.2f}  {t.currency}"
        )


def show_report(transactions: list[Transaction]) -> None:
    summaries = services.summarize(transactions)
    if not summaries:
        print("No transactions yet.")
        return
    for s in summaries.values():
        print(f"\n{s.currency}  ({s.count} transaction(s))")
        print(f"  Income   {s.income:>12,.2f}")
        print(f"  Expenses {s.expenses:>12,.2f}")
        print(f"  Balance  {s.balance:>12,.2f}")
        for category, amount in sorted(s.expenses_by_category.items()):
            print(f"    {category:<15}{amount:>12,.2f}")


if __name__ == "__main__":
    raise SystemExit(main())
