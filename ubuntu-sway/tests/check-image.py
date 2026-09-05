#!/usr/bin/python3
import json
from pathlib import Path
import re
import sys

root, project = map(Path, sys.argv[1:])
def check(ok, message):
    if not ok:
        raise SystemExit("FAIL: " + message)
    print("PASS: " + message)
fstab = (root / "etc/fstab").read_text()
entries = [line.split() for line in fstab.splitlines() if line.strip() and not line.startswith("#")]
check(len(entries) == 5 and not any(e[2] == "swap" for e in entries), "only USB partitions and two tmpfs mounts; no swap or internal disk mounts")
check(all(e[0].startswith("UUID=") for e in entries[:3]), "all USB partitions mounted by exact UUID")
check({e[1] for e in entries if e[2] == "tmpfs"} == {"/tmp", "/var/tmp"}, "temporary directories use RAM")
check("x-systemd.device-timeout=30s" in fstab, "CONFIG discovery allows 30 seconds without an Ethernet wait")
grub = (root / "boot/grub/grub.cfg").read_text()
check(grub.count("menuentry ") == 1 and "password_pbkdf2 locked " in grub, "one boot entry, GRUB command/edit access password-locked")
check(entries[0][0] in grub and "quiet splash" in grub, "GRUB boots the exact USB root UUID with Plymouth")
for line in grub.splitlines():
    if line.strip().startswith("linux ") or line.strip().startswith("initrd "):
        check((root / line.split()[1].lstrip("/")).is_file(), "GRUB kernel/initramfs target exists")
check(not list((root / "var/cache/apt/archives").glob("*.deb")), "package-download cache excluded from final IMG")
check(not (root / ".build-cache").exists() and not (root / "usr/sbin/policy-rc.d").exists(), "no build cache or service-start blocker shipped")
check(not list((root / "home/kiosk/.mozilla/4tw").iterdir()), "shipped Firefox profile is empty and contains no test session/login")
check(not (root / "home/kiosk/.mozilla/4tw-build-smoke").exists(), "temporary browser test profile removed")
for path in (root / "var/lib/NetworkManager/system-connections", root / "etc/NetworkManager/system-connections"):
    check(not path.exists() or not list(path.iterdir()), "no persistent Wi-Fi credentials in " + str(path.relative_to(root)))
check((root / "etc/machine-id").stat().st_size == 0, "machine ID initialized separately on first boot")
for folder in (root / "usr/local", root / "etc/4tw", root / "etc/firefox"):
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix not in {".pyc"}:
            data = path.read_text(errors="replace")
            check("--marionette" not in data and "--remote-debugging-port" not in data and "MOZ_DISABLE_CONTENT_SANDBOX" not in data,
                  "no browser test/debug flags in " + str(path.relative_to(root)))
