"""Billing configuration. All amounts are integer cents."""

RATES: dict[str, int] = {
    "CONSULT": 5000,
    "XRAY": 12000,
    "LABPANEL": 3550,
    "VACCINE": 2799,
    "BANDAGE": 325,
}

# Items that carry no sales tax.
TAX_EXEMPT: frozenset[str] = frozenset({"VACCINE", "LABPANEL"})

TAX_PERCENT = 7
INSURANCE_COVERAGE_PERCENT = 80
