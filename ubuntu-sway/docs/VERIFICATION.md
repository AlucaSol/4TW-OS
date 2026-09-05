# Release verification

The final deliverable is `ubuntu-sway/artifacts/4TW-OS_RELEASE.img` (12,884,901,888 bytes). Use its adjacent `.sha256` file for the definitive final checksum. This report distinguishes automated/VM checks from Acer hardware testing.

Final SHA-256:

```text
5e77ff864c84f6042a3ab0b6179c99eb61534422d7e59f5fa1d4ce2d1dba3587
```

## Actual IMG inspection

The image was attached as a **read-only loop device**, not flashed to a drive. `artifacts/verify-img.log` records these checks:

| Check | Result |
| --- | --- |
| GPT, primary/backup tables | Valid; 3 partitions |
| Partition 1 | 256 MiB FAT32, EFI System Partition, `4TW-EFI` |
| Partition 2 | 11,774 MiB ext4, `4TW-ROOT`, about 8.6 GiB free |
| Partition 3 | Approximately 257 MiB FAT32, `4TW-CONFIG` |
| Filesystem checks | ext4 and both FAT filesystems pass read-only fsck |
| CONFIG writable | A byte-for-byte copy of partition 3 accepts file creation; final IMG remains unmodified by this test |
| Model/base | `/etc/4tw-release`: `MODEL=Release`; Ubuntu 26.04 amd64 |
| Removable boot path | `EFI/BOOT/BOOTX64.EFI`, accompanying signed GRUB and MokManager |
| Shim | Microsoft Windows UEFI Driver Publisher / Microsoft UEFI CA 2011 signature listed |
| GRUB and kernel | Canonical Secure Boot Signing (2022 v1) signatures listed |
| Boot binary integrity | EFI copies byte-match packaged files; dpkg verification of signed shim/GRUB/kernel packages passes |
| Kernel/initramfs | Correct files exist and GRUB selects the image's exact root UUID |
| Boot editing/console | GRUB password-locked; single unrestricted auto-boot entry |
| Logo | Installed PNG byte-matches the original BCLD asset and is present inside initramfs |
| Firefox launch | One fixed invocation, `--kiosk`, one positional URL, persistent profile, launcher lock |
| Website policy | Native WebsiteFilter blocks all URLs except the explicit HTTPS 4thewords allowlist |
| Kiosk controls | Only the four fixed global helper commands and one startup command are executable in Sway config |
| Privilege scope | Exact no-argument poweroff helper and exact brightness up/down commands only |
| Services/applications | No SSH server, terminal emulator, file manager, desktop environment, display manager, Snap daemon or application launcher installed |
| Wi-Fi | NetworkManager, Ethernet unmanaged, no wait-online service, bounded direct Wi-Fi attempt |
| Credentials/test data | No Wi-Fi credentials, populated runtime Firefox profile, test profile or automation flags in the image |
| Flash writes | RAM transient directories/logs/cache; no USB swap; normal profile persistence |
| Build cache | No package archives or external build-cache directory in the image |

`sgdisk` notes that the final partition ends at the last GPT-usable sector rather than a 2048-sector boundary. This is not a filesystem error; no partition encryption tool is used. `sbverify` notes ordinary PE section gaps in packaged shim/MokManager; their signed bytes are unchanged.

## Pre-image runtime tests

`tests/test_helpers.py`: **13 tests passed**, covering capacity-only/missing batteries, power/current conversions, measured-rate runtime estimates, invalid fields, brightness steps/clamps, integer sysfs writes, URL validation, Base64 validation, duplicate/unknown keys and shell-like text treated only as data.

Sway's own configuration validator passed. `visudo` passed. Running `sudo -l` as the kiosk account allowed only the intended fixed commands and rejected shell access, general `systemctl`, brightness default-setting and extra poweroff arguments.

The actual installed Firefox was exercised using a temporary profile and build-only Marionette flags:

- Every configured enterprise policy was accepted and active.
- Exactly one initial tab loaded `https://4thewords.com/`, with title “4thewords - Fight Monsters by Writing | Gamified Writing App”.
- A clicked test link to `https://example.com/4tw-link-test` reached Firefox's `blockedByPolicy` error, not the external page.
- Direct navigation to `https://example.org/4tw-direct-test` was likewise blocked.
- TLS bypass was not enabled (`acceptInsecureCerts=false`).
- The temporary profile/metadata and debugging flags were removed/excluded afterwards.

See `artifacts/browser-smoke.json` and `firefox-smoke.log`. Headless Firefox does not provide a meaningful physical fullscreen check; fullscreen was checked separately in the VM. WSL headless tests reported host user-namespace/framebuffer limitations; no sandbox-disable flags were added to the image.

## Isolated VM checks

QEMU 10.2.1 used Ubuntu OVMF's **Microsoft-key Secure Boot template**, SMM enabled, the removable USB boot path, and a disposable disk snapshot. No host/internal disk was exposed. No guest Wi-Fi adapter was emulated, so the booted Firefox correctly showed its connection-error page for **4thewords.com**, with no address bar, tabs, taskbar or desktop UI.

Observed on the actual image:

- Ubuntu EFI chain reached the correctly centred Plymouth logo and then fullscreen Firefox.
- Ctrl+Alt+B displayed “Battery information unavailable” above Firefox, appropriate for a VM without a battery; it then disappeared automatically.
- Ctrl+Alt+Right displayed “Brightness control unavailable”, appropriate for a VM without a laptop backlight.
- Alt+F4 did not close Firefox or expose a shell/desktop.
- Ctrl+Alt+Delete powered the VM completely off.
- QEMU's emulated physical power-button event also powered the VM completely off.

Screenshots include `vm-first-boot.png`, `vm-kiosk.png`, `vm-battery-4s.png`, `vm-battery-7s.png`, `vm-brightness-4s.png` and `vm-after-alt-f4.png`. Under software CPU emulation the helpers needed several seconds to start; early screenshots preceded the notification. A separate headless Sway/Mako test confirmed that the notification list became populated and then empty after timeout (`test-notifications.log`). No notification-code change was needed.

The slow VM exposed an overly short 5-second CONFIG-device discovery deadline. This was corrected to **30 seconds in the existing IMG's fstab and future builder output**, without downloading packages, reassembling partitions, or creating a second complete IMG. The previous fstab is retained in `artifacts/fstab-before-timeout-fix.txt`; the final one is in `fstab-final.txt`. The correction concerns USB-device discovery, not Ethernet waiting. Image inspection and checksum generation are repeated after that targeted edit.

The corrected image passed the repeated read-only inspection, booted into fullscreen Firefox again (`vm-final-kiosk.png`), and its Windows copy independently matched the final SHA-256 above. The VM had no network adapter; this does not verify real Wi-Fi association. BCLD remained unchanged in the final Git diff.

## Still requires the physical Acer

These are **not claimed as hardware-verified**:

- Firmware Secure Boot acceptance under the Acer's actual trusted/revoked-key state and F12 boot menu.
- Configuration partition mounting and real Wi-Fi association, including that network's security mode.
- Full 4thewords rendering, login, writing/save/sync, audio, and any supporting-domain requirements.
- Clicked external-link blocking in the actual logged-in workflow.
- Real battery percentage/status/power/runtime values.
- Actual panel brightness, default 50%, 10–100% limits, both brightness directions.
- Physical keyboard shortcut operation, clean Ctrl+Alt+Delete shutdown and the laptop power button.
- Integrated/discrete GPU selection, runtime power state and battery life.

After flashing, fill in only the USB's `4tw.cfg`, boot with Secure Boot enabled, complete these checks, and always use clean shutdown before unplugging. The USB is unencrypted and must not be treated as protection against physical tampering.
