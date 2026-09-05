#!/usr/bin/python3
"""Checks usable both before assembly and against the mounted final image."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys

root, project = map(Path, sys.argv[1:])
def read(path):
    return (root / path.lstrip("/")).read_text()
def check(condition, message):
    if not condition:
        raise SystemExit("FAIL: " + message)
    print("PASS: " + message)

check('VERSION_ID="26.04"' in read("/usr/lib/os-release"), "Ubuntu 26.04 base")
check("MODEL=Release" in read("/etc/4tw-release"), "4TW-OS Release model")
policy = json.loads(read("/etc/firefox/policies/policies.json"))["policies"]
allow = json.loads(read("/etc/4tw/allowed-sites.json"))
check(policy["WebsiteFilter"] == {"Block": ["<all_urls>"], "Exceptions": allow}, "native WebsiteFilter blocks all other sites")
check(allow == json.loads((project / "config/allowed-sites.json").read_text()), "installed allowlist matches explicit source")
for key in ("DisableDeveloperTools", "BlockAboutConfig", "BlockAboutProfiles", "BlockAboutAddons", "DisablePrivateBrowsing"):
    check(policy.get(key) is True, key)
check(policy["DisableSecurityBypass"] == {"InvalidCertificate": True, "SafeBrowsing": True}, "TLS/certificate bypass prohibited")
check(policy["Preferences"]["browser.cache.disk.enable"]["Value"] is False, "Firefox disk cache disabled; profile remains persistent")
# Policy recognition is checked against Services.policies in the actual running
# Firefox by browser-smoke.py, not inferred from source or an archive schema.

sway = read("/etc/4tw/sway.conf")
active = [line.strip() for line in sway.splitlines() if line.strip() and not line.lstrip().startswith("#")]
check(not any(re.match(r"(include|bar|bindcode|mode|workspace)\b", line) for line in active), "Sway has no desktop includes, bar, workspace UI or hidden key modes")
expected = {
    "bindsym --inhibited --no-repeat Ctrl+Mod1+b exec /usr/local/bin/4tw-battery",
    "bindsym --inhibited Ctrl+Mod1+Left exec /usr/local/bin/4tw-brightness down",
    "bindsym --inhibited Ctrl+Mod1+Right exec /usr/local/bin/4tw-brightness up",
    "bindsym --inhibited --no-repeat Ctrl+Mod1+Delete exec /usr/bin/sudo -n /usr/local/sbin/4tw-poweroff",
    "exec /usr/local/libexec/4tw-browser",
}
check({line for line in active if " exec " in line or line.startswith("exec ")} == expected,
      "only four fixed global controls and one startup command are executable in Sway")
browser = read("/usr/local/libexec/4tw-browser")
tree = ast.parse(browser)
launches = [node for node in ast.walk(tree) if isinstance(node, ast.List) and node.elts and isinstance(node.elts[0], ast.Constant) and node.elts[0].value == "/usr/bin/firefox"]
check(len(launches) == 1 and len(launches[0].elts) == 6, "exactly one Firefox invocation with one positional start URL")
check('"--kiosk"' in browser and '"--profile"' in browser and 'LOCK_NB' in browser, "kiosk mode, persistent profile, single-instance launcher lock")
check('"Homepage"' not in json.dumps(policy), "no redundant homepage launch policy")
check("/usr/bin/sudo -n /usr/local/sbin/4tw-poweroff" in read("/usr/local/libexec/4tw-session") and '"/usr/local/sbin/4tw-poweroff"' in browser,
      "browser/compositor exit requests poweroff, never falls into a shell")
sudoers = read("/etc/sudoers.d/4tw-kiosk")
check('NOPASSWD: /usr/local/sbin/4tw-poweroff "", /usr/local/sbin/4tw-backlight up, /usr/local/sbin/4tw-backlight down' in sudoers,
      "passwordless privileges limited to exact shutdown and brightness commands")
for path in ("usr/local/bin/4tw-battery", "usr/local/bin/4tw-brightness", "usr/local/sbin/4tw-backlight", "usr/local/sbin/4tw-poweroff", "usr/local/sbin/4tw-configure", "usr/local/lib/4tw/appliance.py", "etc/sudoers.d/4tw-kiosk"):
    stat = (root / path).stat()
    check(stat.st_uid == 0 and not stat.st_mode & 0o022, path + " is root-owned and not user-writable")
check("unmanaged-devices=type:ethernet" in read("/etc/NetworkManager/conf.d/4tw.conf"), "wired interfaces are unmanaged")
check((root / "etc/systemd/system/NetworkManager-wait-online.service").is_symlink(), "NetworkManager wait-online disabled")
check("TimeoutStartSec=35" in read("/etc/systemd/system/4tw-configure.service"), "Wi-Fi startup has a bounded timeout")
check("source " not in read("/usr/local/sbin/4tw-configure") and "shell=True" not in read("/usr/local/lib/4tw/appliance.py"), "config parser never sources shell code")
check("layer=overlay" in read("/etc/4tw/mako.conf") and "default-timeout=5000" in read("/etc/4tw/mako.conf"), "notification sits above fullscreen and automatically expires")
check((root / "usr/share/plymouth/themes/4tw/4TW-OS.png").read_bytes() == (project / "assets/4TW-OS.png").read_bytes(), "Plymouth logo is byte-identical to existing asset")
check("Math.Min" in read("/usr/share/plymouth/themes/4tw/4tw.script"), "Plymouth preserves image aspect ratio")
check("Storage=volatile" in read("/etc/systemd/journald.conf.d/4tw.conf"), "logs kept in RAM")
check("HandlePowerKey=poweroff" in read("/etc/systemd/logind.conf.d/4tw.conf"), "physical power button requests clean poweroff")
passwd = {line.split(":")[0]: line.split(":") for line in read("/etc/passwd").splitlines()}
check(passwd["kiosk"][-1] == "/usr/local/libexec/4tw-session", "kiosk login program is not a normal shell")
installed = set(subprocess.check_output(["chroot", str(root), "dpkg-query", "-W", "-f=${Package}\n"], text=True).splitlines())
for package in ("openssh-server", "dropbear", "xterm", "foot", "gnome-terminal", "konsole", "nautilus", "thunar", "dolphin", "swaybar", "wofi", "rofi", "gdm3", "sddm", "lightdm", "snapd"):
    check(package not in installed, package + " is not installed")
check(not any(p.startswith("nvidia-driver-") for p in installed), "no proprietary high-power NVIDIA driver setup")
print("Root filesystem checks passed.")
