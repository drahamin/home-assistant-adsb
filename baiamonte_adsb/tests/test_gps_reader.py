import importlib.util
import unittest
from pathlib import Path


GPS_READER = Path(__file__).parents[1] / "gps" / "gps_reader.py"
SPEC = importlib.util.spec_from_file_location("baiamonte_gps", GPS_READER)
gps = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gps)


class GPSReaderTests(unittest.TestCase):
    def test_parses_valid_gga_position_and_altitude(self):
        fix = gps.parse_sentence(
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        )
        self.assertAlmostEqual(fix["lat"], 48.1173, places=4)
        self.assertAlmostEqual(fix["lon"], 11.5167, places=4)
        self.assertEqual(fix["alt"], 545.4)
        self.assertEqual(fix["satellites"], 8)

    def test_rejects_sentence_with_bad_checksum(self):
        self.assertIsNone(
            gps.parse_sentence(
                "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*00"
            )
        )


if __name__ == "__main__":
    unittest.main()
