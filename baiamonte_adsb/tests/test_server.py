import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path


SERVER = Path(__file__).parents[1] / "dashboard" / "server.py"
SPEC = importlib.util.spec_from_file_location("baiamonte_dashboard", SERVER)
dashboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard)


class DashboardTests(unittest.TestCase):
    def test_tv_layout_uses_fullscreen_map_and_nearest_aircraft_rail(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        html = (web / "display.html").read_text()
        script = (web / "display.js").read_text()
        self.assertIn('id="tv-shell"', html)
        self.assertIn('id="fleet"', html)
        self.assertIn("nearest_aircraft", script)

    def test_current_rainviewer_hash_path_is_valid(self):
        self.assertTrue(dashboard.valid_weather_tile_path("v2/radar/25dbbe425e29/256/7/67/48/2/1_1.png"))

    def test_weather_tile_path_rejects_traversal(self):
        self.assertFalse(dashboard.valid_weather_tile_path("v2/radar/../../options.json"))

    def test_feeder_aircraft_json_path_is_supported(self):
        self.assertIn(
            Path("/usr/lib/fr24/public_html/data/aircraft.json"),
            dashboard.AIRCRAFT_FILES,
        )

    def test_clean_aircraft_normalizes_dump1090_record(self):
        item = dashboard.clean_aircraft({"hex": "abc123", "flight": " ITA42 ", "r": "EI-EMN", "t": "B738", "alt_baro": 18500, "gs": 310.5})
        self.assertEqual(item["flight"], "ITA42")
        self.assertEqual(item["altitude"], 18500)
        self.assertEqual(item["speed"], 310.5)
        self.assertEqual(item["registration"], "EI-EMN")
        self.assertEqual(item["aircraft_type"], "B738")
        self.assertEqual(item["country_code"], "IE")
        self.assertEqual(item["carrier_country_code"], "IT")
        self.assertEqual(item["operator"], "ITA Airways")
        self.assertIsNone(item["distance_km"])

    def test_last_valid_aircraft_snapshot_survives_partial_decoder_write(self):
        old_files = dashboard.AIRCRAFT_FILES
        old_payload = dashboard.last_aircraft_payload
        old_source = dashboard.last_aircraft_source
        old_read_at = dashboard.last_aircraft_read_at
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aircraft.json"
            path.write_text(json.dumps({"messages": 7, "aircraft": [{"hex": "4ca8af", "flight": "RYR43ET"}]}))
            dashboard.AIRCRAFT_FILES = (path,)
            try:
                valid, source = dashboard.read_aircraft()
                path.write_text('{"messages": 8, "aircraft": [')
                cached, cached_source = dashboard.read_aircraft()
                self.assertEqual(valid, cached)
                self.assertEqual(source, cached_source)
                self.assertEqual(cached["aircraft"][0]["flight"], "RYR43ET")
            finally:
                dashboard.AIRCRAFT_FILES = old_files
                dashboard.last_aircraft_payload = old_payload
                dashboard.last_aircraft_source = old_source
                dashboard.last_aircraft_read_at = old_read_at

    def test_aircraft_distance_uses_receiver_position(self):
        item = dashboard.clean_aircraft(
            {"hex": "abc123", "lat": 37.75, "lon": 15.10},
            reference_lat=37.75,
            reference_lon=15.00,
        )
        self.assertAlmostEqual(item["distance_km"], 8.79, delta=0.1)

    def test_recent_usb_gps_fix_overrides_configured_location(self):
        old_file = dashboard.GPS_LOCATION_FILE
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gps.json"
            path.write_text(json.dumps({
                "lat": 37.8471,
                "lon": 14.9254,
                "alt": 959,
                "device": "/dev/ttyACM0",
                "timestamp": time.time(),
            }))
            dashboard.GPS_LOCATION_FILE = path
            os.environ["GPS_USE_USB"] = "true"
            try:
                location = dashboard.current_location()
                self.assertEqual(location["source"], "USB GPS")
                self.assertEqual(location["lat"], 37.8471)
                self.assertEqual(location["alt"], 959.0)
            finally:
                dashboard.GPS_LOCATION_FILE = old_file
                os.environ.pop("GPS_USE_USB", None)

    def test_weather_overlay_is_configurable_per_surface(self):
        os.environ["WEATHER_OVERLAY_DASHBOARD"] = "false"
        os.environ["WEATHER_OVERLAY_TV"] = "true"
        os.environ["WEATHER_OVERLAY_OPACITY"] = "150"
        try:
            self.assertFalse(dashboard.weather_config("dashboard")["enabled"])
            self.assertTrue(dashboard.weather_config("tv")["enabled"])
            self.assertEqual(dashboard.weather_config("tv")["opacity"], 1.0)
            self.assertEqual(dashboard.weather_config("tv")["provider"], "RainViewer")
        finally:
            os.environ.pop("WEATHER_OVERLAY_DASHBOARD", None)
            os.environ.pop("WEATHER_OVERLAY_TV", None)
            os.environ.pop("WEATHER_OVERLAY_OPACITY", None)

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
                self.assertIn("receiver_log", payload)
                self.assertIn("device", payload["receiver"])
                self.assertIn("gain", payload["receiver"])
            finally:
                dashboard.AIRCRAFT_FILES = old_files
                os.environ.pop("FR24FEED_FR24KEY", None)
                os.environ.pop("SERVICE_ENABLE_FR24FEED", None)

    def test_tv_feed_contains_aircraft_but_no_portal_configuration(self):
        old_files = dashboard.AIRCRAFT_FILES
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aircraft.json"
            path.write_text(json.dumps({"aircraft": [{"hex": "4ca8af", "flight": "RYR43ET", "lat": 37.9, "lon": 15.2}]}))
            dashboard.AIRCRAFT_FILES = (path,)
            os.environ["HTML_SITE_LAT"] = "37.8"
            os.environ["HTML_SITE_LON"] = "15.1"
            try:
                feed = dashboard.aircraft_feed()
                self.assertEqual(feed["aircraft"][0]["flight"], "RYR43ET")
                self.assertEqual(feed["nearest_aircraft"][0]["flight"], "RYR43ET")
                self.assertIn("weather", feed)
                self.assertNotIn("portals", feed)
                self.assertNotIn("receiver", feed)
            finally:
                dashboard.AIRCRAFT_FILES = old_files
                os.environ.pop("HTML_SITE_LAT", None)
                os.environ.pop("HTML_SITE_LON", None)


if __name__ == "__main__":
    unittest.main()
