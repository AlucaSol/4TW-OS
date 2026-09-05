"""Fixed-purpose kiosk helpers. No config values are evaluated as code."""
import base64
import binascii
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urlsplit

DEFAULT_URL = "https://4thewords.com/"
SYS_POWER = Path("/sys/class/power_supply")
SYS_BACKLIGHT = Path("/sys/class/backlight")


def number(path):
    try:
        value = float(path.read_text().strip())
        return value if math.isfinite(value) and value >= 0 else None
    except (OSError, ValueError):
        return None


def battery_text(root=SYS_POWER):
    sections = []
    for bat in sorted(root.glob("BAT*")):
        if number(bat / "present") == 0:
            continue
        lines = []
        capacity = number(bat / "capacity")
        if capacity is not None and capacity <= 100:
            lines.append(f"Battery: {capacity:.0f}%")
        try:
            status = (bat / "status").read_text().strip()
        except OSError:
            status = ""
        if status in {"Charging", "Discharging", "Full", "Not charging", "Unknown"}:
            lines.append(f"Status: {status}")
        power = number(bat / "power_now")
        current = number(bat / "current_now")
        voltage = number(bat / "voltage_now")
        if power is not None:
            watts = power / 1_000_000
        elif current is not None and voltage is not None and voltage > 0:
            watts = current * voltage / 1_000_000_000_000
        else:
            watts = None
        if watts is not None:
            lines.append(f"Power draw: {watts:.1f} W")
        # Runtime means time until empty, not time until fully charged.
        hours = None
        if status == "Discharging":
            energy = number(bat / "energy_now")
            charge = number(bat / "charge_now")
            # Use matched energy/power or charge/current units; do not use
            # instantaneous voltage to invent an energy conversion.
            if energy is not None and power is not None and power > 0:
                hours = energy / power
            elif charge is not None and current is not None and current > 0:
                hours = charge / current
            else:
                seconds = number(bat / "time_to_empty_now")
                if seconds is not None and 0 < seconds < 604800:
                    hours = seconds / 3600
        if hours is not None and math.isfinite(hours) and 0 <= hours < 168:
            minutes = round(hours * 60)
            lines.append(f"Estimated remaining: ~{minutes // 60}h {minutes % 60}m")
        if not lines:
            lines = ["Battery information unavailable"]
        if len(list(root.glob("BAT*"))) > 1:
            lines.insert(0, bat.name)
        sections.append("\n".join(lines))
    return "\n\n".join(sections) or "Battery information unavailable"


def notify(body):
    subprocess.run([
        "/usr/bin/notify-send", "--app-name=4TW-OS", "--expire-time=5000",
        "--hint=string:x-canonical-private-synchronous:4tw-status",
        "--", "4TW-OS", body,
    ], check=False, timeout=5)


def backlight_target(current, maximum, action):
    if action not in {"up", "down", "default"} or maximum < 1:
        raise ValueError("Invalid backlight request")
    maximum = int(maximum)
    percent = 50 if action == "default" else round(current * 100 / maximum) + (10 if action == "up" else -10)
    percent = min(100, max(10, percent))
    value = min(maximum, max(math.ceil(maximum / 10), round(maximum * percent / 100)))
    return value, round(value * 100 / maximum)


def set_backlight(action, root=SYS_BACKLIGHT):
    if action not in {"up", "down", "default"}:
        raise ValueError("Invalid backlight request")
    devices = []
    for device in root.glob("*"):
        maximum = number(device / "max_brightness")
        current = number(device / "brightness")
        if maximum is None or current is None or maximum < 1:
            continue
        try:
            kind = (device / "type").read_text().strip()
        except OSError:
            kind = ""
        devices.append(({"raw": 0, "platform": 1, "firmware": 2}.get(kind, 3), device, current, maximum))
    if not devices:
        return None
    _, device, current, maximum = sorted(devices)[0]
    value, percent = backlight_target(current, maximum, action)
    try:
        (device / "brightness").write_text(str(value))
    except OSError:
        return None
    return percent


def permitted_url(url, patterns):
    if not isinstance(url, str) or len(url) > 4096 or any(ord(c) < 33 or ord(c) == 127 for c in url):
        return False
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443):
            return False
        host = (parsed.hostname or "").lower()
    except ValueError:
        return False
    for pattern in patterns:
        match = re.fullmatch(r"https://(\*\.)?([a-z0-9]+(?:[.-][a-z0-9]+)*)/\*", pattern)
        if not match:
            raise ValueError("Unsupported allowlist pattern")
        wildcard, domain = match.groups()
        if host == domain or (wildcard and host.endswith("." + domain)):
            return True
    return False


def parse_config(text, patterns):
    if len(text.encode("utf-8")) > 16384:
        raise ValueError("Configuration too large")
    values = {}
    for line in text.lstrip("\ufeff").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or key not in {"wifi_ssid_b64", "wifi_psk_b64", "start_url"} or key in values:
            raise ValueError("Unsupported or duplicate configuration key")
        values[key] = value
    url = values.get("start_url") or DEFAULT_URL
    if not permitted_url(url, patterns):
        raise ValueError("Start URL is not allowed")
    try:
        ssid = base64.b64decode(values.get("wifi_ssid_b64", ""), validate=True)
        secret = base64.b64decode(values.get("wifi_psk_b64", ""), validate=True)
        psk = secret.decode("utf-8")
    except (ValueError, UnicodeError, binascii.Error) as error:
        raise ValueError("Invalid Base64 credentials") from error
    if ssid or psk:
        if not 1 <= len(ssid) <= 32:
            raise ValueError("Invalid SSID length")
        if not (8 <= len(secret) <= 63 or re.fullmatch(r"[0-9a-fA-F]{64}", psk)):
            raise ValueError("Invalid Wi-Fi password length")
        if any(ord(c) < 32 or ord(c) == 127 for c in psk):
            raise ValueError("Unsupported control character in Wi-Fi password")
    return url, ssid, psk


def nm_keyfile(ssid, psk):
    # NetworkManager/GLib keyfile escaping; SSID is an explicit byte array.
    escaped = psk.replace("\\", "\\\\").replace(" ", "\\s")
    return (
        "[connection]\nid=4tw-wifi\nuuid=2d5b597a-e4aa-4499-8b09-7ba9ec67508d\n"
        "type=wifi\nautoconnect=true\nautoconnect-retries=2\n\n"
        "[wifi]\nmode=infrastructure\nssid=" + ";".join(str(c) for c in ssid) + ";\n\n"
        "[wifi-security]\nkey-mgmt=wpa-psk\npsk=" + escaped + "\n\n"
        "[ipv4]\nmethod=auto\n\n[ipv6]\nmethod=auto\n"
    )


def configure_runtime():
    runtime = Path("/run/4tw")
    runtime.mkdir(mode=0o755, exist_ok=True)
    url, ssid, psk = DEFAULT_URL, b"", ""
    try:
        patterns = json.loads(Path("/etc/4tw/allowed-sites.json").read_text())
        with Path("/config/4tw.cfg").open(encoding="utf-8-sig") as handle:
            text = handle.read(16385)
        url, ssid, psk = parse_config(text, patterns)
    except (OSError, ValueError, UnicodeError):
        # Never print the input or a decoder exception containing credentials.
        print("4TW-OS: configuration unavailable or invalid; using safe defaults.", flush=True)
    (runtime / "start-url").write_text(url + "\n")
    (runtime / "start-url").chmod(0o644)
    if not ssid:
        print("4TW-OS: Wi-Fi credentials are not configured.", flush=True)
        return
    connections = Path("/run/NetworkManager/system-connections")
    connections.mkdir(mode=0o700, parents=True, exist_ok=True)
    connection = connections / "4tw-wifi.nmconnection"
    fd = os.open(connection, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(nm_keyfile(ssid, psk))
    try:
        for command in (
            ["radio", "wifi", "on"],
            ["connection", "load", str(connection)],
            ["--wait", "20", "connection", "up", "uuid", "2d5b597a-e4aa-4499-8b09-7ba9ec67508d"],
        ):
            result = subprocess.run(["/usr/bin/nmcli", *command], stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=25, check=False)
            if result.returncode:
                print("4TW-OS: Wi-Fi not connected yet; continuing kiosk startup.", flush=True)
                return
    except (OSError, subprocess.TimeoutExpired):
        print("4TW-OS: Wi-Fi attempt timed out; continuing kiosk startup.", flush=True)
