"""Persistence: read and write transactions as CSV.

Two boundary rules live here:
  * Reading: every row goes through validation.build_transaction, so a file is
    held to exactly the same rules as keyboard input. Problems are reported per
    row ("Row 4: ...") using the line number a user sees in a text editor.
  * Writing: saves are atomic — data goes to a temporary file first, which then
    replaces the real file in one step. A crash mid-save leaves the previous
    complete file, never a half-written one.

Storage reports problems; it does not decide what to do about them. The caller
(the CLI) chooses whether a file with bad rows is usable.
"""

import csv
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from budget_manager.models import FIELDS, Transaction
from budget_manager.validation import ValidationError, build_transaction


@dataclass
class LoadResult:
    """Outcome of reading a file: the valid transactions plus every problem found."""

    transactions: list[Transaction] = field(default_factory=list)
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_transactions(path: Path) -> LoadResult:
    """Read a CSV file into transactions.

    A missing or empty file is a valid empty budget (first run). Rows that fail
    validation are collected in `errors` and left out of `transactions`.
    """
    result = LoadResult()
    if not path.exists():
        return result

    # utf-8-sig also accepts files saved by Excel, which start with a hidden BOM.
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:  # completely empty file
            return result

        header_problems = _check_header(reader.fieldnames)
        if header_problems:
            # Without the right columns no row can be read reliably.
            result.errors.append(ValidationError(header_problems, row=1))
            return result
        # Use the cleaned-up names (" Amount" -> "amount") as the row keys.
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]

        first_seen: dict[str, int] = {}  # id -> row where it first appeared
        for row in reader:
            line = reader.line_num
            if None in row:  # DictReader puts surplus values under the key None
                result.errors.append(
                    ValidationError([f"has more values than the {len(FIELDS)} columns"], line)
                )
                continue
            try:
                transaction = build_transaction(row, row=line)
            except ValidationError as exc:
                result.errors.append(exc)
                continue
            if transaction.id in first_seen:
                result.errors.append(
                    ValidationError(
                        [f"duplicate id '{transaction.id}' (first used on row {first_seen[transaction.id]})"],
                        line,
                    )
                )
                continue
            first_seen[transaction.id] = line
            result.transactions.append(transaction)

    return result


def save_transactions(path: Path, transactions: list[Transaction]) -> None:
    """Write all transactions to `path`, replacing its contents atomically.

    Order is preserved as given, so the last row is always the most recent addition.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # The temp file must be in the same folder for os.replace to be atomic.
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(t.to_row() for t in transactions)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _check_header(fieldnames: list[str]) -> list[str]:
    """Return problems with the header row (empty list if it is fine)."""
    names = [name.strip().lower() for name in fieldnames]
    problems = []
    missing = [f for f in FIELDS if f not in names]
    unknown = [n for n in names if n not in FIELDS]
    if missing:
        problems.append("missing column(s): " + ", ".join(missing))
    if unknown:
        # An unknown column is often a typo ("ammount"); reject rather than ignore.
        problems.append("unknown column(s): " + ", ".join(unknown))
    return problems
