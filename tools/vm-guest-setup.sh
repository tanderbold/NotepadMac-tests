#!/bin/bash
# Run once inside the VM, from the user's Terminal there: `nc -l 8000 > /tmp/s`
# while the host runs `tools/vm.sh push-setup`, then `sudo bash /tmp/s`
# (after turning on System Settings > General > Sharing > Remote Login).
# Everything here changes the VM only.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo" >&2; exit 1; }
U=${SUDO_USER:?run with sudo from the user account}
H=$(dscl . -read "/Users/$U" NFSHomeDirectory | awk '{print $2}')
# The host's public key: given in NPP_E2E_KEY (tools/vm.sh serve-setup puts it
# there), else read from the shares, automounted in /Volumes/My Shared Files
# or mounted by hand at ~/shared or ~/s.
KEY=${NPP_E2E_KEY:-}
if [ -z "$KEY" ]; then
    for SHARE in "/Volumes/My Shared Files" "$H/shared" "$H/s"; do
        [ -f "$SHARE/out/npp-e2e.pub" ] && KEY=$(cat "$SHARE/out/npp-e2e.pub") && break
    done
fi
[ -n "$KEY" ] || { echo "no host key: the shared folders are not mounted" >&2; exit 1; }
PY=3.13.3

# ssh: the host's key only, no passwords.
install -d -m 700 -o "$U" -g staff "$H/.ssh"
echo "$KEY" >> "$H/.ssh/authorized_keys"
chown "$U":staff "$H/.ssh/authorized_keys"; chmod 600 "$H/.ssh/authorized_keys"
printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
    > /etc/ssh/sshd_config.d/100-npp-e2e.conf

# Apple's Command Line Tools (git, clang), unattended.
if ! xcode-select -p >/dev/null 2>&1; then
    touch /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
    label=$(softwareupdate -l 2>/dev/null | sed -n 's/^\* Label: \(Command Line Tools.*\)$/\1/p' | tail -1)
    softwareupdate -i "$label" --verbose
    rm -f /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
fi

# Python from python.org, installed only if the package is signed by the PSF.
if [ ! -x /usr/local/bin/python3.13 ]; then
    pkg=/tmp/python-$PY.pkg
    curl -fsSL -o "$pkg" "https://www.python.org/ftp/python/$PY/python-$PY-macos11.pkg"
    pkgutil --check-signature "$pkg" | grep -q "Developer ID Installer: Python Software Foundation" \
        || { echo "python package signature not as expected" >&2; exit 1; }
    installer -pkg "$pkg" -target /
    rm -f "$pkg"
fi

# Keep the GUI session awake: no system or display sleep, no screen saver.
pmset -a sleep 0 displaysleep 0 disksleep 0
sudo -u "$U" defaults -currentHost write com.apple.screensaver idleTime 0

launchctl kickstart -k system/com.openssh.sshd 2>/dev/null || true
echo "done: ssh is key-only for $U; the host can take it from here"
