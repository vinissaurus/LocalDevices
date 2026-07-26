import types
import unittest
from unittest import mock

import localdevices


class NormalizeDevicesTests(unittest.TestCase):
    def test_normalize_devices_sorts_and_maps_expected_fields(self) -> None:
        devices = localdevices.normalize_devices(
            {
                "192.168.1.30": {"gwId": "b-device", "version": 3.3, "productKey": "prod-b"},
                "192.168.1.20": {"id": "a-device", "name": "Kitchen Plug"},
            }
        )

        self.assertEqual(
            devices,
            [
                {
                    "ip": "192.168.1.20",
                    "device_id": "a-device",
                    "version": "",
                    "product_key": "",
                    "name": "Kitchen Plug",
                },
                {
                    "ip": "192.168.1.30",
                    "device_id": "b-device",
                    "version": "3.3",
                    "product_key": "prod-b",
                    "name": "",
                },
            ],
        )

    def test_normalize_devices_ignores_non_mapping_values(self) -> None:
        self.assertEqual(
            localdevices.normalize_devices({"192.168.1.10": "unexpected"}),
            [],
        )

    def test_normalize_devices_treats_none_values_as_empty_strings(self) -> None:
        self.assertEqual(
            localdevices.normalize_devices(
                {"192.168.1.15": {"gwId": "device-2", "version": None, "name": None}}
            ),
            [
                {
                    "ip": "192.168.1.15",
                    "device_id": "device-2",
                    "version": "",
                    "product_key": "",
                    "name": "",
                }
            ],
        )


class UiHelperTests(unittest.TestCase):
    def test_device_row_values_returns_treeview_tuple(self) -> None:
        self.assertEqual(
            localdevices.device_row_values(
                {
                    "ip": "192.168.1.50",
                    "device_id": "device-1",
                    "version": "3.5",
                    "product_key": "prod-key",
                    "name": "Lamp",
                }
            ),
            ("192.168.1.50", "device-1", "3.5", "prod-key", "Lamp"),
        )

    def test_build_status_message_handles_empty_and_populated_results(self) -> None:
        self.assertEqual(
            localdevices.build_status_message([]),
            "No Tuya devices were found on the local network.",
        )
        self.assertEqual(
            localdevices.build_status_message([{"ip": "192.168.1.50"}]),
            "Found 1 Tuya device(s) on the local network.",
        )


class DiscoverDevicesTests(unittest.TestCase):
    def test_discover_devices_uses_tinytuya_scan_and_normalizes_results(self) -> None:
        fake_tinytuya = types.SimpleNamespace(
            deviceScan=mock.Mock(
                return_value={"192.168.1.50": {"gwId": "device-1", "version": 3.5}}
            )
        )

        with mock.patch("localdevices.importlib.import_module", return_value=fake_tinytuya):
            devices = localdevices.discover_devices(timeout_seconds=5)

        fake_tinytuya.deviceScan.assert_called_once_with(maxretry=5, color=False, poll=False)
        self.assertEqual(
            devices,
            [
                {
                    "ip": "192.168.1.50",
                    "device_id": "device-1",
                    "version": "3.5",
                    "product_key": "",
                    "name": "",
                }
            ],
        )

    def test_discover_devices_reports_missing_dependency(self) -> None:
        with mock.patch(
            "localdevices.importlib.import_module",
            side_effect=ImportError("tinytuya is missing"),
        ):
            with self.assertRaises(localdevices.DiscoveryError) as context:
                localdevices.discover_devices()

        self.assertIn("TinyTuya is not installed", str(context.exception))

    def test_discover_devices_wraps_scan_failures(self) -> None:
        fake_tinytuya = types.SimpleNamespace(
            deviceScan=mock.Mock(side_effect=RuntimeError("socket failed"))
        )

        with mock.patch("localdevices.importlib.import_module", return_value=fake_tinytuya):
            with self.assertRaises(localdevices.DiscoveryError) as context:
                localdevices.discover_devices(timeout_seconds=2)

        self.assertIn("Unable to scan the local network for Tuya devices", str(context.exception))


if __name__ == "__main__":
    unittest.main()
