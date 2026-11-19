"""Budget logic: add, list, summarize.

Pure functions only: they take a list of transactions and return new values.
Nothing here prompts the user, prints, or touches files — so every rule can be
tested directly with plain lists, and the CLI and storage layers stay thin.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from budget_manager.models import Kind, Transaction
from budget_manager.validation import build_transaction


# --- Adding ----------------------------------------------------------------


def next_id(transactions: Iterable[Transaction]) -> str:
    """Return the next free id: one above the highest existing number.

    Based on the highest number (not the count), so ids are never reused
    even if a transaction in the middle was removed.
    """
    highest = max((int(t.id[1:]) for t in transactions), default=0)
    return f"T{highest + 1:03d}"


def add_transaction(
    transactions: list[Transaction], raw: Mapping[str, object]
) -> list[Transaction]:
    """Validate raw input, assign an id, and return a NEW list including it.

    The user never chooses the id: any 'id' in `raw` is overwritten.
    Raises ValidationError if the input is invalid; `transactions` is untouched.
    """
    record = {**raw, "id": next_id(transactions)}
    return [*transactions, build_transaction(record)]


# --- Listing ---------------------------------------------------------------


def list_transactions(transactions: Iterable[Transaction]) -> list[Transaction]:
    """All transactions in chronological order (ties broken by id)."""
    return sorted(transactions, key=lambda t: (t.date, t.id))


# --- Reporting -------------------------------------------------------------


@dataclass
class CurrencySummary:
    """Totals for one currency. Amounts are never mixed across currencies."""

    currency: str
    income: Decimal = Decimal("0.00")
    expenses: Decimal = Decimal("0.00")
    expenses_by_category: dict[str, Decimal] = field(default_factory=dict)
    count: int = 0

    @property
    def balance(self) -> Decimal:
        return self.income - self.expenses


def summarize(transactions: Iterable[Transaction]) -> dict[str, CurrencySummary]:
    """Income, expenses, balance and expense breakdown — one summary per currency.

    Currencies are reported separately because there is no exchange-rate data;
    adding EUR and USD together would produce a meaningless number.
    """
    summaries: dict[str, CurrencySummary] = {}
    for t in transactions:
        s = summaries.setdefault(t.currency, CurrencySummary(t.currency))
        s.count += 1
        if t.kind is Kind.INCOME:
            s.income += t.amount
        else:
            s.expenses += t.amount
            s.expenses_by_category[t.category] = (
                s.expenses_by_category.get(t.category, Decimal("0.00")) + t.amount
            )
    return dict(sorted(summaries.items()))
