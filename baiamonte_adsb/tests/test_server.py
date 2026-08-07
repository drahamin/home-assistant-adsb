import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


SERVER = Path(__file__).parents[1] / "dashboard" / "server.py"
SPEC = importlib.util.spec_from_file_location("baiamonte_dashboard", SERVER)
dashboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard)


class DashboardTests(unittest.TestCase):
    def test_clean_aircraft_normalizes_dump1090_record(self):
        item = dashboard.clean_aircraft({"hex": "abc123", "flight": " ITA42 ", "alt_baro": 18500, "gs": 310.5})
        self.assertEqual(item["flight"], "ITA42")
        self.assertEqual(item["altitude"], 18500)
        self.assertEqual(item["speed"], 310.5)

    def test_status_never_exposes_credentials(self):
        old_files = dashboard.AIRCRAFT_FILES
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aircraft.json"
            path.write_text(json.dumps({"messages": 42, "aircraft": [{"hex": "abc123", "flight": "BAI1"}]}))
            dashboard.AIRCRAFT_FILES = (path,)
            os.environ["FR24FEED_FR24KEY"] = "super-secret"
            os.environ["SERVICE_ENABLE_FR24FEED"] = "true"
            try:
                payload = dashboard.status_payload()
                encoded = json.dumps(payload)
                self.assertNotIn("super-secret", encoded)
                portal = next(item for item in payload["portals"] if item["name"] == "FlightRadar24")
                self.assertTrue(portal["configured"])
                self.assertEqual(payload["counts"]["aircraft"], 1)
            finally:
                dashboard.AIRCRAFT_FILES = old_files
                os.environ.pop("FR24FEED_FR24KEY", None)
                os.environ.pop("SERVICE_ENABLE_FR24FEED", None)


if __name__ == "__main__":
    unittest.main()
