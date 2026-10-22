"""Invoice calculator (migrated from Python 2.7).

Behaviour is intentionally identical to the legacy code, including truncating integer
division. The recorded legacy output in golden/invoices.json is the specification.
"""
from dataclasses import dataclass
from typing import Any

from legacy_billing import config, rates


@dataclass(frozen=True)
class Invoice:
    invoice_no: str
    visit_id: str
    subtotal: int
    discount: int
    tax: int
    total: int
    patient_owes: int
    avg_line: int


class InvoiceCalculator:
    """Holds the invoice counter that used to be a module-level global."""

    def __init__(self) -> None:
        self._counter = 0

    def _next_invoice_no(self) -> str:
        self._counter += 1
        return f"INV-{self._counter:05d}"

    def compute(self, visit: dict[str, Any]) -> Invoice:
        subtotal = 0
        exempt_subtotal = 0
        for item in visit["items"]:
            cents = rates.rate_for(item["code"]) * item["qty"]
            subtotal += cents
            if rates.is_exempt(item["code"]):
                exempt_subtotal += cents

        # `//` reproduces Python 2 `/` on non-negative ints (truncation).
        pct = visit.get("discount_pct", 0)
        discount = subtotal * pct // 100
        exempt_discount = exempt_subtotal * pct // 100

        taxable = (subtotal - discount) - (exempt_subtotal - exempt_discount)
        tax = taxable * config.TAX_PERCENT // 100
        total = subtotal - discount + tax

        owes = total
        if visit.get("insured"):
            owes = total * (100 - config.INSURANCE_COVERAGE_PERCENT) // 100

        return Invoice(
            invoice_no=self._next_invoice_no(),
            visit_id=visit["visit_id"],
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total=total,
            patient_owes=owes,
            avg_line=subtotal // len(visit["items"]),
        )

    def compute_all(self, visits: list[dict[str, Any]]) -> dict[str, Invoice]:
        return {v["visit_id"]: self.compute(v) for v in visits}
