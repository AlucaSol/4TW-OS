# Build notes — 5 September 2026

The new implementation lives entirely in `ubuntu-sway/`. No BCLD source, previous BCLD artifact, internal disk, Windows EFI partition, BitLocker setting, or host firmware boot entry was changed.

## Environment and stages

Windows 11 PowerShell invoked the existing `Ubuntu-26.04` WSL2 distribution as root. Source was copied into `/home/jonbe/4tw-ubuntu-sway-build/` for native Linux ownership, filesystems and loop mounts. Exact Windows commands are in `../README.md`.

1. `packages`: debootstrap Ubuntu Resolute amd64, authenticated Ubuntu APT repositories, Mozilla's official repository with its published signing-key fingerprint verified. Service startup was suppressed inside the build chroot. Its temporary `/dev` contained only basic character devices, not host disk devices.
2. `configure`: installed the root-owned overlay, native Firefox policies and original logo; created the kiosk account and writable browser profile/metadata directories; generated initramfs; validated helpers, Sway and sudo; exercised the actual Firefox browser with a temporary test profile.
3. `image`: one complete 12 GiB raw GPT image assembled from the validated rootfs, using only loop-backed partitions in that new file. Ubuntu's signed shim, GRUB, MokManager and kernel were retained byte-for-byte. No `grub-install` or `efibootmgr` was run.
4. `verify`: inspect the final IMG read-only and test writes on a separate copy of its FAT configuration partition. VM testing uses a disposable QEMU disk snapshot and copied OVMF variable store, not a second complete image build.

Early validation caught two preparation issues before image assembly: a minimal `--no-install-recommends` installation required explicit initramfs/compression packages, and Firefox required a writable `.mozilla/firefox` metadata directory in addition to its explicit profile. Browser media codec libraries were also added after the initial headless test reported decoder errors. These were rootfs-stage corrections; no complete IMG was rebuilt to test them.

## Package versions

| Component | Installed version |
| --- | --- |
| Ubuntu | 26.04 LTS, amd64 |
| Firefox, Mozilla official APT | 155.0.1~build1 |
| Ubuntu generic kernel | 7.0.0-31.31 |
| shim-signed | 1.59+15.8-0ubuntu2 |
| grub-efi-amd64-signed | 1.215+2.14-2ubuntu1 |
| Sway | 1.11-3 |
| Mako | 1.10.0-1build1 |
| NetworkManager | 1.54.3-2ubuntu3 |
| PipeWire | 1.6.2-1ubuntu1.1 |

Full inventory and repository candidates are recorded in `artifacts/packages.tsv` and `artifacts/package-origins.txt`.

## Cache use

The initial seed contained 939 existing BCLD download-cache packages. The first main package install needed **310 MB of downloads out of 1,143 MB of package archives**, reusing approximately 833 MB. The base upgrade downloaded 549 kB out of 19.4 MB. Initramfs tools and zstd were then installed entirely from cache; the media-codec addition downloaded about 10 MB out of 28.9 MB. Index refreshes and genuinely new versions were downloaded normally. Logs retain the APT `Need to get` evidence, including `artifacts/prepare-packages-initial.log` on Windows.

QEMU/OVMF required approximately 24 MB of additional build-host-only downloads for the optional boot test. These packages and all package-download caches are excluded from the USB image. No additional Codex plugins were used.

## Output and persistence

The final deliverable is `artifacts/4TW-OS_RELEASE.img`, 12,884,901,888 bytes, with `4TW-OS_RELEASE.img.sha256`. The system filesystem has about 8.6 GiB free at creation. The initial configuration contains no Wi-Fi credentials or browser login. The original logo is copied without resizing or editing its pixels; Plymouth/Sway scale it proportionally at display time.

The complete IMG was assembled only once. Subsequent slow-VM testing identified a short CONFIG-device deadline; one targeted fstab edit increased 5 seconds to 30 seconds inside that existing IMG. No signed binaries, partitions or package contents were changed. Its checksum was regenerated and inspection repeated.

Artifact export uses Windows `Copy-Item` from the WSL UNC path. The initial sparse rsync transfers across WSL/NTFS were slow and redundantly started by diagnostic stages; those exact transfer processes were stopped, and rsync removed its incomplete temporary copies. The complete native IMG remained intact. The wrapper now exports only logs/checksums automatically, and README includes the explicit single IMG copy command.

This is a normal writable USB installation, not a RAM-root BCLD clone. Firefox login/profile state persists. Transient directories, logging and browser cache use RAM. There is no swap, automatic package-update timer, desktop workflow or normal administrative login.
