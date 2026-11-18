"""Transaction schema: the data contract every other module depends on.

This module only *describes* what a transaction is. It does not read user
input, touch files, or decide whether raw data is acceptable — turning raw
input into a Transaction is the job of validation.py.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Kind(StrEnum):
    """Direction of money flow. StrEnum members compare equal to their string value."""

    EXPENSE = "expense"
    INCOME = "income"


# Controlled vocabulary for categories. Anything outside this set is rejected
# at the boundary (validation.py) rather than silently mapped to "other".
CATEGORIES: frozenset[str] = frozenset(
    {
        "food",
        "housing",
        "transport",
        "utilities",
        "health",
        "entertainment",
        "salary",
        "other",
    }
)

# Active ISO 4217 currency codes (circulating national currencies only; fund
# codes, precious metals and test codes such as XAU or XTS are excluded).
# Snapshot as of 2026 — e.g. XCG replaced ANG (2025) and BGN left when
# Bulgaria adopted the euro (2026). Update this set if ISO changes the list.
CURRENCIES: frozenset[str] = frozenset(
    """
    AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BHD BIF BMD BND BOB BRL
    BSD BTN BWP BYN BZD CAD CDF CHF CLP CNY COP CRC CUP CVE CZK DJF DKK DOP
    DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG
    HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD
    KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK
    MXN MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR
    RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP
    SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VED VES VND
    VUV WST XAF XCD XCG XOF XPF YER ZAR ZMW ZWG
    """.split()
)

# Column order used everywhere a transaction is flattened (CSV header, display).
FIELDS: tuple[str, ...] = ("id", "date", "kind", "category", "amount", "currency")


@dataclass(frozen=True)
class Transaction:
    """One validated budget record.

    frozen=True: once created, a transaction cannot be changed by accident.
    Every field is always present — no optional fields that sometimes vanish.
    """

    id: str  # "T001", "T002", ... assigned by the service layer
    date: date  # stored as a real date; ISO string only at the file boundary
    kind: Kind
    category: str  # one of CATEGORIES
    amount: Decimal  # > 0, at most 2 decimal places (Decimal = exact money math)
    currency: str  # one of CURRENCIES, upper-case

    @property
    def signed_amount(self) -> Decimal:
        """Amount with sign applied: income positive, expense negative."""
        return self.amount if self.kind is Kind.INCOME else -self.amount

    def to_row(self) -> dict[str, str]:
        """Flatten to plain strings (for CSV writing), in FIELDS order."""
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "kind": self.kind.value,
            "category": self.category,
            "amount": f"{self.amount:.2f}",
            "currency": self.currency,
        }
