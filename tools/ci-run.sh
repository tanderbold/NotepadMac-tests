#!/bin/bash
# Every area in turn, each its own pytest run, on the machine this runs on - a CI runner or a
# spare Mac, never one someone is working at: the app takes the focus (NPPMAC_E2E_ACTIVATE).
#   NPPMAC_E2E_APP=/path/to/NotepadMac.app tools/ci-run.sh [area ...]
# Writes .work-ci/<area>.log and .xml (JUnit) and .work-ci/summary.md; exits 1 if an area failed.
cd "$(dirname "$0")/.."
: "${NPPMAC_E2E_APP:?set NPPMAC_E2E_APP to the NotepadMac.app to test}"
export NPPMAC_E2E_ACTIVATE=1
PY=${PYTHON:-python3}
out=.work-ci
mkdir -p "$out"
areas=("$@")
if [ ${#areas[@]} -eq 0 ]; then
    for f in tests/test_*.py; do a=$(basename "$f" .py); a=${a#test_}; [ "$a" = smoke ] || areas+=("$a"); done
fi
status=0
{ echo "| Area | Result |"; echo "|---|---|"; } > "$out/summary.md"
for a in "${areas[@]}"; do
    NPPMAC_E2E_WORKER=ci-$a "$PY" -m pytest "tests/test_$a.py" -q -p no:cacheprovider -rfEX --tb=short \
        -o timeout=300 --junitxml="$out/$a.xml" > "$out/$a.log" 2>&1
    rc=$?
    line=$(grep -E '^[0-9]+ (passed|failed|error)|(passed|failed|error).* in [0-9.]+s' "$out/$a.log" | tail -1)
    echo "$a: ${line:-no summary} (rc=$rc)"
    echo "| $a | ${line:-no summary} |" >> "$out/summary.md"
    [ $rc -eq 0 ] || status=1
    rm -rf ".work/ci-$a/NotepadMacE2E.app"
done
exit $status
