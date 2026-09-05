4TW-OS USB configuration

Edit 4tw.cfg on THIS FAT32 partition using Windows Notepad.
Do not change the key names. Do not add quotes around values.

wifi_ssid_b64 and wifi_psk_b64 are UTF-8 Base64 text, NOT encryption.
Anyone with this USB can decode them. Keep credentials out of source control.
Both may be left empty, but then Wi-Fi will not connect.

Only HTTPS start URLs permitted by the built-in allowlist are accepted.
The default is https://4thewords.com/
An invalid configuration fails safely to the default URL without Wi-Fi.

Use Ctrl+Alt+Delete for clean shutdown before unplugging.
If Windows offers to format another partition on this USB, CANCEL.
Never format the Linux system or EFI partition.
