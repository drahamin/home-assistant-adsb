import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE = Path(__file__).parents[1] / "airband" / "usb_recovery.py"
SPEC = importlib.util.spec_from_file_location("baiamonte_usb_recovery", MODULE)
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


class USBRecoveryTests(unittest.TestCase):
    def test_serial_selection_distinguishes_identical_radio_models(self):
        with patch.object(recovery, "rtlsdr_serials", return_value=["BAIAMONTE-1090", "BAIAMONTE-VHF"]):
            self.assertEqual(recovery.selected_serial("BAIAMONTE-VHF", 0), "BAIAMONTE-VHF")

    def test_duplicate_factory_serial_is_rejected(self):
        with patch.object(recovery, "rtlsdr_serials", return_value=["00000001", "00000001"]):
            with self.assertRaisesRegex(OSError, "duplicated"):
                recovery.selected_serial("00000001", 1)

    def test_usb_bus_path_is_resolved_from_selected_serial(self):
        with tempfile.TemporaryDirectory() as temporary:
            device = Path(temporary) / "1-2"
            device.mkdir()
            (device / "serial").write_text("BAIAMONTE-VHF")
            (device / "busnum").write_text("1")
            (device / "devnum").write_text("7")
            self.assertEqual(recovery.usb_device_for_serial("BAIAMONTE-VHF", Path(temporary)), Path("/dev/bus/usb/001/007"))


if __name__ == "__main__":
    unittest.main()
