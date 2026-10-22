"""Map acceptance criteria to tests.

    python scripts/traceability.py [feature-folder]

Reads specs/<feature>/spec.md for ids like SPEC001/AC-3 and scans backend/tests for test functions whose
names contain the same id written as SPEC001_AC3. Exit code 1 if a criterion has no test, or a test names a
criterion that is not in the spec ("orphan tag").
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

root = Path(__file__).resolve().parent.parent
feature = sys.argv[1] if len(sys.argv) > 1 else "sms-reminders"
spec = (root / "specs" / feature / "spec.md").read_text(encoding="utf-8-sig")

criteria = sorted(set(re.findall(r"SPEC\d+/AC-\d+", spec)), key=lambda s: [int(n) for n in re.findall(r"\d+", s)])
spec_numbers = {re.match(r"SPEC(\d+)/", c).group(1) for c in criteria}
tests: dict[str, list[str]] = defaultdict(list)
for path in sorted((root / "backend" / "tests").glob("test_*.py")):
    for name in re.findall(r"^def (test_\w+)\(", path.read_text(encoding="utf-8-sig"), re.M):
        for spec_no, ac_no in re.findall(r"SPEC(\d+)_AC(\d+)", name):
            if spec_no not in spec_numbers:
                continue  # tests of other features are not orphans of this one
            tests[f"SPEC{spec_no}/AC-{ac_no}"].append(f"{path.name}::{name}")

uncovered = [c for c in criteria if c not in tests]
orphans = sorted(set(tests) - set(criteria))

print(f"{'Criterion':<16} Tests")
for c in criteria:
    print(f"{c:<16} {len(tests.get(c, []))}" + ("" if tests.get(c) else "   <-- NO TEST"))
if orphans:
    print("\nOrphan tags (test names a criterion that is not in the spec):", ", ".join(orphans))
print()
print("TRACEABILITY OK" if not (uncovered or orphans) else f"TRACEABILITY FAILED ({len(uncovered)} uncovered, {len(orphans)} orphan)")
sys.exit(1 if (uncovered or orphans) else 0)
