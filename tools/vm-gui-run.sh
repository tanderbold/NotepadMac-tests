#!/bin/zsh
# Inside the VM: runs a command (base64 in $1) as a launchd job of the user's
# GUI session and streams its output; exits with the command's exit code.
# tools/vm.sh calls it over ssh. A process started straight from ssh can open
# windows but never becomes the active application, so key windows, focus and
# what the app does "when it comes to the front" would differ from the host.
set -e
tests=${0:A:h:h}   # the checkout of the tests this script came with
# One run at a time in the GUI session: every copy of the app makes itself the active application
# (NPPMAC_E2E_ACTIVATE), so two runs side by side take the focus from each other and key windows,
# key equivalents and activation-time checks fail at random. A run waits here for the one before.
lock=~/nm/gui-run.lock
while ! mkdir "$lock" 2>/dev/null; do
    holder=$(cat "$lock/pid" 2>/dev/null || true)
    if [[ -n "$holder" ]] && ! kill -0 "$holder" 2>/dev/null; then rm -rf "$lock"; continue; fi   # left by a dead run
    sleep 2
done
echo $$ > "$lock/pid"
trap 'rm -rf "$lock"' EXIT
id="org.npp-e2e.run.$(uuidgen)"   # unique: two runs sharing a folder mixed their output
d=~/nm/runs/$id
mkdir -p "$d"
print -r -- "$1" | base64 -D > "$d/run.sh"
: > "$d/out"
cat > "$d/job.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
<key>Label</key><string>$id</string>
<key>ProgramArguments</key><array>
<string>/bin/zsh</string><string>-c</string>
<string>cd '$tests'; /bin/zsh '$d/run.sh' &gt; '$d/out' 2&gt;&amp;1; echo \$? &gt; '$d/rc'</string>
</array>
<key>RunAtLoad</key><true/>
</dict></plist>
EOF
launchctl bootstrap "gui/$(id -u)" "$d/job.plist"
tail -n +1 -f "$d/out" & t=$!
while [[ ! -f "$d/rc" ]]; do sleep 1; done
sleep 1
kill $t 2>/dev/null || true
launchctl bootout "gui/$(id -u)/$id" 2>/dev/null || true
rc=$(<"$d/rc")
rm -rf "$d"
exit $rc
