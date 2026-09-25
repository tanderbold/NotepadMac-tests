#!/bin/bash
# Runs the suite inside a Tart macOS VM, so the app's windows, focus and
# alerts never reach the user's screen. The checks are the same: the same
# build of NotepadMac on the same macOS, driven by the same harness.
#
#   tools/vm.sh gui              boot with a window, for the one-time setup inside
#   tools/vm.sh push-setup       send vm-guest-setup.sh to the VM (nc -l 8000 > /tmp/s there)
#   tools/vm.sh setup            once, after vm-guest-setup.sh ran: the suite's Python packages
#   tools/vm.sh test [pytest…]   start the VM if needed, sync, run pytest there
#   tools/vm.sh sh 'command'     run a shell command in the VM over ssh (in ~/nm/<checkout folder>)
#   tools/vm.sh gui-sh 'command' sync, then run it inside the VM's GUI session (tests run this way)
#   tools/vm.sh pull [worker]    copy .work/<worker> (logs, snapshots, PDFs) to .work-vm/
#   tools/vm.sh stop
#
# The VM is Apple's own macOS (tart create --from-ipsw), reached over ssh with
# the key ~/.ssh/npp-e2e only. It shares no folder with the host: sources and
# the built app go in with rsync over that ssh, results come back the same way
# into .work-vm/ (a shared folder showed a rebuilt app bundle stale or empty).
# NPPMAC_E2E_WORKER is passed through, so several workers can share the VM;
# NPPMAC_VM_APP runs the tests against another worktree's build (see app_env).
set -euo pipefail
VM=${NPPMAC_VM:-npp-e2e}
GUEST_USER=${NPPMAC_VM_USER:-tester}
HERE=$(cd "$(dirname "$0")/.." && pwd)
NM=$(dirname "$HERE")
OUT="$HERE/.work-vm"
# Each checkout of the tests has its own copy in the VM (nm/<its folder name>), so a second checkout
# (another branch's tests) never replaces the files of a run in progress.
TD=nm/$(basename "$HERE")
RUN_OPTS=(--no-clipboard --no-audio)
SSH_OPTS=(-i ~/.ssh/npp-e2e -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=5
          -o HostKeyAlias="$VM" -o UserKnownHostsFile=~/.ssh/npp-e2e.known_hosts -o StrictHostKeyChecking=accept-new)

x() { ssh -n "${SSH_OPTS[@]}" "$GUEST_USER@$(tart ip "$VM")" "$1"; }

rs() { rsync -a --delete -e "ssh $(printf '%q ' "${SSH_OPTS[@]}")" "$@"; }

running() { tart list --format json | /usr/bin/python3 -c 'import json,sys
sys.exit(0 if any(m["Name"] == sys.argv[1] and m["State"] == "running" for m in json.load(sys.stdin)) else 1)' "$VM"; }

up() {
    mkdir -p "$OUT"
    if ! running; then
        # Detached from this script: no stdin, no stdout, not a job it waits on.
        nohup tart run "$VM" --no-graphics "${RUN_OPTS[@]}" </dev/null >"$OUT/tart-run.log" 2>&1 &
        disown
    fi
    for _ in $(seq 1 120); do
        x true 2>/dev/null && return 0
        sleep 1
    done
    echo "vm: $VM did not come up (see $OUT/tart-run.log)" >&2
    return 1
}

sync_in() {
    # Sources and the built app; not the object files, not the git history.
    local g="$GUEST_USER@$(tart ip "$VM")"
    x "mkdir -p ~/nm/npp ~/$TD"
    rs --exclude .git --exclude '/macos/build/*obj*' --exclude '/macos/build/*.dmg' \
       --exclude '/macos/build/uchardet-native' --exclude '/macos/build/*.a' "$NM/npp/" "$g:nm/npp/"
    rs --exclude .work --exclude .work-vm --exclude .venv --exclude __pycache__ \
       --exclude .pytest_cache "$HERE/" "$g:$TD/"
}

# A command run inside the VM user's GUI session (tools/vm-gui-run.sh, synced in with the tests).
gui_run() { x "~/$TD/tools/vm-gui-run.sh $(printf '%s' "$1" | base64)"; }

# NPPMAC_VM_APP=/path/to/NotepadMac.app (a build of another worktree, e.g. a fix
# branch): copied into the VM under the worker's name and given to the harness
# as NPPMAC_E2E_APP; without it the tests use npp/macos/build as synced.
app_env() {
    [ -n "${NPPMAC_VM_APP:-}" ] || return 0
    local w=${NPPMAC_E2E_WORKER:-main}
    x "mkdir -p ~/nm/apps/$w"
    rs "${NPPMAC_VM_APP%/}/" "$GUEST_USER@$(tart ip "$VM"):nm/apps/$w/NotepadMac.app/" >&2
    # The in-app suite builds the sample plugin from the SDK beside the build (<app>/../../plugin-sdk).
    local sdk; sdk="$(dirname "$(dirname "${NPPMAC_VM_APP%/}")")/plugin-sdk"
    [ -d "$sdk" ] && rs "$sdk/" "$GUEST_USER@$(tart ip "$VM"):nm/apps/plugin-sdk/" >&2
    printf 'export NPPMAC_E2E_APP=$HOME/nm/apps/%s/NotepadMac.app; ' "$w"
}

quote() { local out="" a; for a in "$@"; do out+=" $(printf '%q' "$a")"; done; printf '%s' "$out"; }

case "${1:-}" in
    gui)
        running && { echo "vm: $VM is already running (tools/vm.sh stop)" >&2; exit 1; }
        exec tart run "$VM" "${RUN_OPTS[@]}"
        ;;
    push-setup)
        # Before ssh works: vm-guest-setup.sh with the key inside, pushed to a
        # listener in the VM (the host's firewall refuses incoming connections,
        # so the host connects out). In the VM's Terminal:
        #   nc -l 8000 > /tmp/s      then      sudo bash /tmp/s
        ip=$(tart ip "$VM")
        { printf "NPP_E2E_KEY='%s'\n" "$(cat ~/.ssh/npp-e2e.pub)"; cat "$HERE/tools/vm-guest-setup.sh"; } |
            /usr/bin/python3 -c 'import socket, sys, time
data = sys.stdin.buffer.read()
for _ in range(900):
    try: s = socket.create_connection((sys.argv[1], 8000), timeout=2)
    except OSError: time.sleep(1); continue
    s.sendall(data); s.shutdown(socket.SHUT_WR); s.close(); print("sent"); sys.exit(0)
sys.exit("the VM never listened")' "$ip"
        ;;
    setup)
        up
        x "xcode-select -p >/dev/null && git --version && clang --version | head -1 && /usr/local/bin/python3.13 --version"
        x "test -x ~/nm/venv/bin/python || /usr/local/bin/python3.13 -m venv ~/nm/venv; \
           ~/nm/venv/bin/pip install -q$(quote $("$HERE/.venv/bin/pip" freeze))"
        ;;
    test)
        shift
        up
        # NPPMAC_VM_NOSYNC=1: another run just synced (parallel groups share one copy).
        [ -n "${NPPMAC_VM_NOSYNC:-}" ] || sync_in
        gui_run "$(app_env)COLUMNS=250 NPPMAC_E2E_ACTIVATE=1 NPPMAC_E2E_WORKER=$(printf '%q' "${NPPMAC_E2E_WORKER:-main}") ~/nm/venv/bin/python -m pytest$(quote "$@")"
        ;;
    sh)
        up
        x "cd ~/$TD && $2"
        ;;
    gui-sh)
        # The same inside the GUI session (the app's own suite, NPPMAC_TEST=1, runs this way).
        # With NPPMAC_VM_APP, $NPPMAC_E2E_APP there is that build.
        up
        sync_in
        gui_run "$(app_env)$2"
        ;;
    pull)
        up
        w=${2:-${NPPMAC_E2E_WORKER:-main}}
        rs --exclude '*.app' "$GUEST_USER@$(tart ip "$VM"):$TD/.work/$w/" "$OUT/$w/"
        echo "$OUT/$w"
        ;;
    stop)
        tart stop "$VM"
        ;;
    *)
        sed -n 2,18p "$0" | sed 's/^# \{0,1\}//'
        exit 2
        ;;
esac
