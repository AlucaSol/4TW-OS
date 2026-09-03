# How to build the 4TW-OS IMG from Windows 11

You do **not** need to open an Ubuntu window. Run every command below in
Windows PowerShell. `wsl.exe` starts and controls the Ubuntu WSL2 environment
automatically.

No new packages, Docker images, Codex plugins, or other software are needed.
The prepared Linux build tree and package cache already exist.

## Locations

Windows project and finished files:

```text
C:\Users\jonbe\Documents\AI projects\4TW-OS\bcld
C:\Users\jonbe\Documents\AI projects\4TW-OS\bcld\artifacts
```

Prepared Linux build tree and cache:

```text
/home/jonbe/bcld-4thewords-build
/home/jonbe/bcld-4thewords-build/.build-cache/apt/archives
```

The current customised source has already been copied into the Linux build
tree. Do not run the builders directly from the Windows `C:` drive; BCLD needs
Linux permissions, links, mounts, and line endings.

## 1. Open PowerShell

Open **Windows PowerShell** or a PowerShell tab in Windows Terminal. The build
itself does not normally require "Run as administrator".

Check that the prepared WSL2 environment exists:

```powershell
wsl.exe -l -v
```

It should list `Ubuntu-26.04` with version `2`. Its state can be `Stopped`;
the next command starts it automatically.

## 2. Check the existing cache

```powershell
wsl.exe -d Ubuntu-26.04 -u root -- bash -lc "find /home/jonbe/bcld-4thewords-build/.build-cache/apt/archives -maxdepth 1 -type f -name '*.deb' | wc -l"
```

The current cache contains about 930 packages. A different number later is not
necessarily an error.

## 3. Build the Release ISO

Copy and run this as one PowerShell command:

```powershell
wsl.exe -d Ubuntu-26.04 -u root -- bash -lc "set -o pipefail; cd /home/jonbe/bcld-4thewords-build; export BCLD_MODEL=release; export BCLD_USE_CACHE=1; ./ISO-builder.sh 2>&1 | tee /home/jonbe/ISO-builder-4thewords-latest.log"
```

Check that it succeeded:

```powershell
if ($LASTEXITCODE -ne 0) { throw "ISO build failed with exit code $LASTEXITCODE" }
```

The builder refreshes repository indexes, but cached package files are reused.
Lines such as `Need to get 0 B/...` confirm cache hits.

## 4. Build the writable USB IMG

```powershell
wsl.exe -d Ubuntu-26.04 -u root -- bash -lc "set -o pipefail; cd /home/jonbe/bcld-4thewords-build; export BCLD_MODEL=release; ./IMG-builder.sh 2>&1 | tee /home/jonbe/IMG-builder-4thewords-latest.log"
```

Check that it succeeded:

```powershell
if ($LASTEXITCODE -ne 0) { throw "IMG build failed with exit code $LASTEXITCODE" }
```

The Linux artifacts are now in:

```text
/home/jonbe/bcld-4thewords-build/artifacts
```

## 5. Copy the IMG and ISO back to Windows

Run this PowerShell block:

```powershell
$WindowsArtifacts = 'C:\Users\jonbe\Documents\AI projects\4TW-OS\bcld\artifacts'
New-Item -ItemType Directory -Force -Path $WindowsArtifacts | Out-Null

$ImageName = (wsl.exe -d Ubuntu-26.04 -u root -- bash -lc "cd /home/jonbe/bcld-4thewords-build/artifacts; ls -1t *_RELEASE.img | head -n 1").Trim()
if ([string]::IsNullOrWhiteSpace($ImageName)) { throw 'No Release IMG was found' }

wsl.exe -d Ubuntu-26.04 -u root -- cp "/home/jonbe/bcld-4thewords-build/artifacts/$ImageName" "/mnt/c/Users/jonbe/Documents/AI projects/4TW-OS/bcld/artifacts/$ImageName"
if ($LASTEXITCODE -ne 0) { throw "IMG copy failed with exit code $LASTEXITCODE" }

wsl.exe -d Ubuntu-26.04 -u root -- cp /home/jonbe/bcld-4thewords-build/artifacts/bcld.iso "/mnt/c/Users/jonbe/Documents/AI projects/4TW-OS/bcld/artifacts/bcld.iso"
if ($LASTEXITCODE -ne 0) { throw "ISO copy failed with exit code $LASTEXITCODE" }
```

## 6. Create and verify SHA-256 checksums

Continue in the same PowerShell window:

```powershell
$ImagePath = Join-Path $WindowsArtifacts $ImageName
$IsoPath = Join-Path $WindowsArtifacts 'bcld.iso'

$ImageHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ImagePath).Hash.ToLowerInvariant()
$IsoHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $IsoPath).Hash.ToLowerInvariant()

"$ImageHash  $ImageName" | Set-Content -LiteralPath "$ImagePath.sha256" -Encoding ascii -NoNewline
"$IsoHash  bcld.iso" | Set-Content -LiteralPath "$IsoPath.sha256" -Encoding ascii -NoNewline

Get-Item -LiteralPath $ImagePath, $IsoPath
Get-Content -LiteralPath "$ImagePath.sha256", "$IsoPath.sha256"
```

The `.img` is the file to write to the USB. Do not write only `bcld.iso`.

## 7. Optional: stop WSL2

After the build and copies have finished:

```powershell
wsl.exe --shutdown
```

## Important notes

- Building the ISO removes older files from the **Linux** `artifacts` folder.
  Files already copied to the Windows artifacts folder are retained.
- The package cache is retained and is not included inside the finished IMG.
- Wi-Fi credentials must be added afterward to `bcld.cfg` on the USB's writable
  `BCLD-USB` partition. Never add them to the source tree.
- If you edit source files in the Windows project later, those edits must be
  copied to the matching path under `/home/jonbe/bcld-4thewords-build` before
  rebuilding. Copy only the changed source files; do not copy `artifacts`,
  `.build-cache`, `chroot`, or other generated build directories.
