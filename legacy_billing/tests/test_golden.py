"""Characterization tests: the migrated code must reproduce the recorded legacy output."""
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from legacy_billing.billing import InvoiceCalculator

ROOT = Path(__file__).resolve().parent.parent
VISITS = json.loads((ROOT / "fixtures" / "visits.json").read_text())
GOLDEN = json.loads((ROOT / "golden" / "invoices.json").read_text())


@pytest.fixture(scope="module")
def invoices():
    return InvoiceCalculator().compute_all(VISITS)


@pytest.mark.parametrize("visit_id", sorted(GOLDEN))
def test_matches_recorded_legacy_output(invoices, visit_id):
    actual = asdict(invoices[visit_id])
    actual.pop("visit_id")
    assert actual == GOLDEN[visit_id]


def test_invoice_numbers_are_sequential_per_calculator():
    calc = InvoiceCalculator()
    numbers = [calc.compute(v).invoice_no for v in VISITS]
    assert numbers == [f"INV-{i:05d}" for i in range(1, len(VISITS) + 1)]


def test_two_calculators_do_not_share_a_counter():
    # The legacy module used a global counter; the migrated code must not.
    assert InvoiceCalculator().compute(VISITS[0]).invoice_no == "INV-00001"
    assert InvoiceCalculator().compute(VISITS[0]).invoice_no == "INV-00001"


def test_truncation_not_rounding(invoices):
    # V003: subtotal 9697 * 5% = 484.85 -> legacy truncates to 484 (rounding would give 485).
    # Exercises the migrated code, so replacing `//` with round() makes this fail.
    assert invoices["V003"].discount == 484
