#!/bin/bash
set -eu

# Harmless fixed-purpose proof that Openbox receives the global shortcut.
if [[ "$#" -ne 0 ]]; then
    exit 64
fi

exec /usr/bin/xmessage \
    -center \
    -timeout 5 \
    -buttons '' \
    -title '4TW-OS Hotkey Test' \
    '4TW hotkey OK' >/dev/null 2>&1
