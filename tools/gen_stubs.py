"""Writes tests/test_<area>.py stubs for plan cases that have no test yet.

A stub skips with "not implemented". Existing tests (matched by the case id in
the function name) are left alone, so this can be rerun after the plan grows.
"""
import re
from collections import defaultdict
from planlib import ROOT, all_cases, test_name

cases, errors = all_cases()
if errors:
    raise SystemExit("\n".join(errors))
by_area = defaultdict(list)
for c in cases:
    by_area[c["area"]].append(c)
made = 0
for area, cs in by_area.items():
    path = ROOT / "tests" / f"test_{area.lower()}.py"
    existing = path.read_text() if path.exists() else ""
    have = set(re.findall(r"def test_([a-z0-9]+_\d{3})_", existing))
    new = []
    for c in cs:
        key = f"{c['area'].lower()}_{c['num']}"
        if key in have:
            continue
        doc = (f'    """{c["id"]}: {c["title"]}\n\n'
               f'    Covers: {c.get("covers", "-")}\n    Channel: {c.get("channel", "")}\n'
               f'    Steps: {c.get("steps", "")}\n    Expect: {c.get("expect", "")}\n    """')
        doc = doc.replace("\\", "\\\\")
        new.append(f"\n\n@pytest.mark.case(\"{c['id']}\")\ndef {test_name(c)}(app):\n{doc}\n    pytest.skip(\"not implemented\")\n")
        made += 1
    if not new:
        continue
    header = existing or (f'"""{area}: end-to-end tests (plan: plan/{area}.md)."""\nimport pytest\n\n'
                          f'from harness.sci import *  # noqa: F401,F403\n')
    path.write_text(header.rstrip("\n") + "\n" + "".join(new))
print(f"{made} stubs written")
