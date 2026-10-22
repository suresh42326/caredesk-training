"""Entry point: python -m legacy_billing.run legacy_billing/fixtures/visits.json"""
import json
import sys
from pathlib import Path

from legacy_billing.billing import InvoiceCalculator


def main() -> None:
    visits = json.loads(Path(sys.argv[1]).read_text())
    for vid, inv in sorted(InvoiceCalculator().compute_all(visits).items()):
        print(
            f"{vid} {inv.invoice_no} subtotal={inv.subtotal} tax={inv.tax} "
            f"total={inv.total} owes={inv.patient_owes}"
        )


if __name__ == "__main__":
    main()
