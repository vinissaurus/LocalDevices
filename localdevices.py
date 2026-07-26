from __future__ import annotations

import importlib
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk
    from tkinter import ttk


DEFAULT_SCAN_TIMEOUT_SECONDS = 18


class DiscoveryError(RuntimeError):
    """Raised when Tuya device discovery cannot be completed."""


def stringify_field(value: object | None) -> str:
    return "" if value in (None, "") else str(value)


def discover_devices(timeout_seconds: int = DEFAULT_SCAN_TIMEOUT_SECONDS) -> list[dict[str, str]]:
    try:
        tinytuya = importlib.import_module("tinytuya")
    except ImportError as exc:
        raise DiscoveryError(
            "TinyTuya is not installed. Run `python -m pip install -r requirements.txt` first."
        ) from exc

    try:
        devices = tinytuya.deviceScan(
            maxretry=timeout_seconds,
            color=False,
            poll=False,
        )
    except Exception as exc:  # pragma: no cover - library/network failures are surfaced to the UI.
        raise DiscoveryError(f"Unable to scan the local network for Tuya devices: {exc}") from exc

    return normalize_devices(devices)


def normalize_devices(raw_devices: dict[str, dict[str, object]] | None) -> list[dict[str, str]]:
    if not raw_devices:
        return []

    devices: list[dict[str, str]] = []
    for fallback_ip, payload in raw_devices.items():
        if not isinstance(payload, dict):
            continue

        devices.append(
            {
                "ip": stringify_field(payload.get("ip") or fallback_ip),
                "device_id": stringify_field(payload.get("gwId") or payload.get("id")),
                "version": stringify_field(payload.get("version")),
                "product_key": stringify_field(payload.get("productKey")),
                "name": stringify_field(payload.get("name")),
            }
        )

    return sorted(devices, key=lambda device: (device["ip"], device["device_id"]))


def device_row_values(device: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        device["ip"],
        device["device_id"],
        device["version"],
        device["product_key"],
        device["name"],
    )


def build_status_message(devices: list[dict[str, str]]) -> str:
    if devices:
        return f"Found {len(devices)} Tuya device(s) on the local network."
    return "No Tuya devices were found on the local network."


def build_app() -> "tk.Tk":
    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
    except ImportError as exc:
        raise SystemExit(
            "Tkinter is not available in this Python installation. Install a Python build with Tk support and try again."
        ) from exc

    class TuyaDiscoveryApp(tk.Tk):
        def __init__(self) -> None:
            super().__init__()
            self.title("LocalDevices")
            self.geometry("860x420")
            self.minsize(720, 320)

            self.scan_button = ttk.Button(self, text="Scan local network", command=self.start_scan)
            self.scan_button.pack(padx=16, pady=(16, 8), anchor="w")

            self.status_var = tk.StringVar(value="Ready to scan for Tuya devices.")
            ttk.Label(self, textvariable=self.status_var).pack(padx=16, pady=(0, 12), anchor="w")

            columns = ("ip", "device_id", "version", "product_key", "name")
            self.tree = ttk.Treeview(self, columns=columns, show="headings")
            self.tree.heading("ip", text="IP address")
            self.tree.heading("device_id", text="Device ID")
            self.tree.heading("version", text="Version")
            self.tree.heading("product_key", text="Product key")
            self.tree.heading("name", text="Name")
            self.tree.column("ip", width=130, anchor="w")
            self.tree.column("device_id", width=220, anchor="w")
            self.tree.column("version", width=80, anchor="center")
            self.tree.column("product_key", width=180, anchor="w")
            self.tree.column("name", width=180, anchor="w")
            self.tree.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        def start_scan(self) -> None:
            self.scan_button.state(["disabled"])
            self.status_var.set("Scanning the local network for Tuya devices...")
            self.clear_results()
            threading.Thread(target=self._scan_in_background, daemon=True).start()

        def _scan_in_background(self) -> None:
            try:
                devices = discover_devices()
            except DiscoveryError as exc:
                self.after(0, lambda: self._scan_failed(str(exc)))
                return

            self.after(0, lambda: self._scan_succeeded(devices))

        def _scan_failed(self, message: str) -> None:
            self.scan_button.state(["!disabled"])
            self.status_var.set("Scan failed.")
            messagebox.showerror("LocalDevices", message)

        def _scan_succeeded(self, devices: list[dict[str, str]]) -> None:
            self.scan_button.state(["!disabled"])

            for device in devices:
                self.tree.insert(
                    "",
                    "end",
                    values=device_row_values(device),
                )

            self.status_var.set(build_status_message(devices))

        def clear_results(self) -> None:
            for item in self.tree.get_children():
                self.tree.delete(item)

    return TuyaDiscoveryApp()


def main() -> None:
    app = build_app()
    app.mainloop()


if __name__ == "__main__":
    main()
