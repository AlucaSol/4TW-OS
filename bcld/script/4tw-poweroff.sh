#!/bin/bash
set -eu

# Fixed-purpose privileged endpoint for the Openbox shutdown shortcut.
if [[ "$#" -ne 0 ]]; then
    exit 64
fi

/usr/bin/sync
exec /usr/bin/systemctl poweroff
