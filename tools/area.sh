#!/bin/bash
# One area (or -k selection) in the VM with untruncated summary lines, against NPPMAC_VM_APP if set.
# tools/area.sh <worker> tests/test_x.py [pytest args...]
cd "$(dirname "$0")/.."
export NPPMAC_VM_APP=${NPPMAC_VM_APP:-$(cd .. && pwd)/npp/macos/build/NotepadMac.app}
w=$1; shift
NPPMAC_E2E_WORKER=$w tools/vm.sh test "$@" -q -p no:cacheprovider -rfEX --tb=short -o timeout=120
