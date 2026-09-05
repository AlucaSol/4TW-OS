#!/usr/bin/python3
import base64
import importlib.util
from pathlib import Path
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("appliance", PROJECT / "rootfs-overlay/usr/local/lib/4tw/appliance.py")
appliance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(appliance)
ALLOW = ["https://4thewords.com/*", "https://*.4thewords.com/*"]


class Helpers(unittest.TestCase):
    def battery(self, **fields):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bat = root / "BAT0"
            bat.mkdir()
            for key, value in fields.items():
                (bat / key).write_text(str(value))
            return appliance.battery_text(root)

    def test_battery_capacity_only(self):
        self.assertEqual(self.battery(capacity=72), "Battery: 72%")

    def test_battery_missing(self):
        self.assertEqual(self.battery(), "Battery information unavailable")
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(appliance.battery_text(Path(folder)), "Battery information unavailable")

    def test_battery_energy_power(self):
        result = self.battery(capacity=60, status="Discharging", power_now=10_000_000, energy_now=25_000_000)
        self.assertIn("Power draw: 10.0 W", result)
        self.assertIn("Estimated remaining: ~2h 30m", result)

    def test_battery_charge_current(self):
        result = self.battery(status="Discharging", current_now=2_000_000, voltage_now=12_000_000, charge_now=3_000_000)
        self.assertIn("Power draw: 24.0 W", result)
        self.assertIn("Estimated remaining: ~1h 30m", result)

    def test_battery_charging_is_not_runtime(self):
        result = self.battery(capacity=80, status="Charging", power_now=10_000_000, energy_now=25_000_000)
        self.assertIn("Status: Charging", result)
        self.assertNotIn("remaining", result)

    def test_battery_no_invented_estimate(self):
        for fields in (
            dict(status="Discharging", capacity=80),
            dict(status="Discharging", power_now=0, energy_now=25_000_000),
            dict(status="Discharging", power_now="nan", energy_now="inf"),
            dict(status="Discharging", energy_now=25_000_000, current_now=2_000_000, voltage_now=12_000_000),
        ):
            self.assertNotIn("remaining", self.battery(**fields))

    def test_untrusted_status_not_displayed(self):
        self.assertEqual(self.battery(status="$(touch /tmp/unsafe)", capacity=50), "Battery: 50%")

    def test_backlight_steps_and_clamp(self):
        self.assertEqual(appliance.backlight_target(500, 1000, "up"), (600, 60))
        self.assertEqual(appliance.backlight_target(500, 1000, "down"), (400, 40))
        self.assertEqual(appliance.backlight_target(100, 1000, "down"), (100, 10))
        self.assertEqual(appliance.backlight_target(1000, 1000, "up"), (1000, 100))
        self.assertEqual(appliance.backlight_target(1000, 1000, "default"), (500, 50))
        with self.assertRaises(ValueError):
            appliance.backlight_target(100, 1000, ";sh")

    def test_backlight_writes_integer_and_handles_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertIsNone(appliance.set_backlight("up", root))
            dev = root / "generic-panel"
            dev.mkdir()
            (dev / "max_brightness").write_text("1000")
            (dev / "brightness").write_text("950")
            self.assertEqual(appliance.set_backlight("up", root), 100)
            self.assertEqual((dev / "brightness").read_text(), "1000")

    def test_allowed_and_denied_urls(self):
        for url in ("https://4thewords.com/", "https://www.4thewords.com/write", "https://api.4thewords.com/path?q=x"):
            self.assertTrue(appliance.permitted_url(url, ALLOW))
        for url in ("https://example.com/", "http://4thewords.com/", "https://4thewords.com.evil.example/",
                    "https://evil4thewords.com/", "https://4thewords.com@evil.example/", "https://u@4thewords.com/",
                    "https://4thewords.com:8443/", "file:///etc/passwd", "javascript:alert(1)",
                    "https://4thewords.com/\nanything", "https://4thewords.com:bad/", "https://[bad/"):
            self.assertFalse(appliance.permitted_url(url, ALLOW), url)

    def test_default_config_is_credential_free(self):
        self.assertEqual(appliance.parse_config((PROJECT / "config/4tw.cfg").read_text(), ALLOW),
                         ("https://4thewords.com/", b"", ""))

    def test_config_key_validation(self):
        for value in ("command=sh", "wifi_ssid_b64=\nwifi_ssid_b64=", "start_url=https://example.com/", "wifi_ssid_b64=%%", "no equals"):
            with self.assertRaises(ValueError):
                appliance.parse_config(value, ALLOW)

    def test_config_shell_text_is_just_data(self):
        ssid = b"$(touch /tmp/unsafe);wifi"
        psk = "pass;$(id)\\ word"
        config = "wifi_ssid_b64=" + base64.b64encode(ssid).decode() + "\nwifi_psk_b64=" + base64.b64encode(psk.encode()).decode()
        url, decoded_ssid, decoded_psk = appliance.parse_config(config, ALLOW)
        self.assertEqual(decoded_ssid, ssid)
        self.assertEqual(decoded_psk, psk)
        keyfile = appliance.nm_keyfile(decoded_ssid, decoded_psk)
        self.assertIn("psk=pass;$(id)\\\\\\sword", keyfile)
        self.assertNotIn("ssid=$(", keyfile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
