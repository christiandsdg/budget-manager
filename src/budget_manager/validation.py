"""Boundary checks: turn raw text (from the CLI or a CSV row) into a Transaction.

This is the single gate every transaction passes through. Rules:
  * Unambiguous clean-up is allowed: trimming whitespace, normalizing case
    ("EUR" for "eur"), padding 18.5 to 18.50.
  * Ambiguous input is never guessed at — it is rejected with a message that
    says which field is wrong and why (e.g. "Row 4: amount must be > 0.").
  * All problems in one record are reported together, so the user can fix a
    row in one pass instead of one error at a time.
"""

import re
from collections.abc import Mapping
from datetime import date
from decimal import Decimal

from budget_manager.models import CATEGORIES, CURRENCIES, FIELDS, Kind, Transaction

_ID_PATTERN = re.compile(r"T\d{3,}")
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUMBER_PATTERN = re.compile(r"-?\d+(\.\d+)?")


class ValidationError(ValueError):
    """Raised when raw input cannot become a valid Transaction.

    `problems` holds one plain-language message per invalid field; `row`
    (optional) locates the record in a file.
    """

    def __init__(self, problems: list[str], row: int | None = None) -> None:
        self.problems = problems
        self.row = row
        prefix = f"Row {row}: " if row is not None else ""
        super().__init__(prefix + "; ".join(problems) + ".")


# --- Field parsers -------------------------------------------------------
# Each takes the trimmed raw string and returns a clean value, or raises
# ValueError with a short message that names the field.


def parse_id(raw: str) -> str:
    value = raw.upper()
    if not _ID_PATTERN.fullmatch(value):
        raise ValueError(f"id must look like T001 (got '{raw}')")
    return value


def parse_date(raw: str) -> date:
    # Require exactly YYYY-MM-DD. date.fromisoformat alone would also accept
    # forms like "20260904", which we don't want in a file other tools read.
    if not _DATE_PATTERN.fullmatch(raw):
        raise ValueError(f"date must be in YYYY-MM-DD format (got '{raw}')")
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"date '{raw}' is not a real calendar date") from None


def parse_kind(raw: str) -> Kind:
    try:
        return Kind(raw.lower())
    except ValueError:
        allowed = " or ".join(f"'{k.value}'" for k in Kind)
        raise ValueError(f"kind must be {allowed} (got '{raw}')") from None


def parse_category(raw: str) -> str:
    value = raw.lower()
    if value not in CATEGORIES:
        allowed = ", ".join(sorted(CATEGORIES))
        raise ValueError(f"unknown category '{raw}' (allowed: {allowed})")
    return value


def parse_amount(raw: str) -> Decimal:
    if "," in raw:
        # "18,50" could be a decimal comma or a thousands separator — ambiguous.
        raise ValueError(f"amount must use '.' as the decimal separator (got '{raw}')")
    if not _NUMBER_PATTERN.fullmatch(raw):
        raise ValueError(f"amount must be a number like 18.50 (got '{raw}')")
    value = Decimal(raw)
    if value <= 0:
        raise ValueError("amount must be > 0")
    cents = value.quantize(Decimal("0.01"))
    if cents != value:
        # 18.505 would need rounding — refuse rather than silently change it.
        # (18.500 passes: trailing zeros don't change the value.)
        raise ValueError(f"amount must have at most 2 decimal places (got '{raw}')")
    return cents


def parse_currency(raw: str) -> str:
    value = raw.upper()
    if value not in CURRENCIES:
        raise ValueError(f"currency '{raw}' is not a valid ISO 4217 code")
    return value


_PARSERS = {
    "id": parse_id,
    "date": parse_date,
    "kind": parse_kind,
    "category": parse_category,
    "amount": parse_amount,
    "currency": parse_currency,
}


def parse_field(field: str, value: object) -> object:
    """Validate one field and return its clean value.

    Used for whole records (build_transaction) and for checking each answer
    the moment the user types it (cli). Raises ValueError with a message.
    """
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{field} is required")
    return _PARSERS[field](text)


# --- Record builder ------------------------------------------------------


def build_transaction(raw: Mapping[str, object], row: int | None = None) -> Transaction:
    """Validate a mapping of raw values and return a Transaction.

    Raises ValidationError listing every invalid or missing field.
    """
    clean: dict[str, object] = {}
    problems: list[str] = []

    for field in FIELDS:
        try:
            clean[field] = parse_field(field, raw.get(field))
        except ValueError as exc:
            problems.append(str(exc))

    if problems:
        raise ValidationError(problems, row)
    return Transaction(**clean)  # type: ignore[arg-type]
