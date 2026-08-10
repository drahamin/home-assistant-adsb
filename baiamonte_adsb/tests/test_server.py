import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


SERVER = Path(__file__).parents[1] / "dashboard" / "server.py"
SPEC = importlib.util.spec_from_file_location("baiamonte_dashboard", SERVER)
dashboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard)


class DashboardTests(unittest.TestCase):
    def test_dashboard_follows_browser_color_scheme(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        html = (web / "index.html").read_text()
        theme = (web / "theme.css").read_text()
        self.assertIn('href="theme.css?v=210"', html)
        self.assertIn('media="(prefers-color-scheme: dark)"', html)
        self.assertIn("@media(prefers-color-scheme:dark)", theme)
        self.assertIn("color-scheme:light dark", theme)

    def test_tv_layout_uses_fullscreen_map_and_nearest_aircraft_rail(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        html = (web / "display.html").read_text()
        script = (web / "display.js").read_text()
        self.assertIn('id="tv-shell"', html)
        self.assertIn('id="fleet"', html)
        self.assertIn("nearest_aircraft", script)

    def test_tv_map_is_bright_and_aircraft_rows_are_compact(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        html = (web / "display.html").read_text()
        styles = (web / "display.css").read_text()
        self.assertIn('href="display.css?v=211"', html)
        self.assertIn("brightness(1.16)", styles)
        self.assertIn("flex:0 0 360px", styles)
        self.assertIn("padding:8px 5px", styles)
        self.assertIn("grid-template-columns:minmax(0,1fr) clamp(300px,23vw,390px)", styles)

    def test_dashboard_and_tv_use_shared_altitude_aircraft_icons(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        map_script = (web / "map.js").read_text()
        dashboard_script = (web / "app.js").read_text()
        tv_script = (web / "display.js").read_text()
        self.assertIn("AIRCRAFT_ICON", map_script)
        self.assertIn("ALTITUDE_BANDS", map_script)
        self.assertIn("altitude-legend", map_script)
        self.assertIn("BaiamonteAircraftVisual.apply", dashboard_script)
        self.assertIn("BaiamonteAircraftVisual.apply", tv_script)
        self.assertNotIn("<span>▲</span>", dashboard_script)
        self.assertNotIn(">▲</i>", tv_script)

    def test_dashboard_has_ingress_vhf_player_and_back_navigation(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        html = (web / "index.html").read_text()
        script = (web / "app.js").read_text()
        self.assertIn('id="airband"', html)
        self.assertIn('src="api/airband-stream"', html)
        self.assertIn('data-go="overview"', html)
        self.assertIn("renderAirband(data.airband)", script)

    def test_dashboard_includes_sicily_weather_airport_and_enrichment_views(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        html = (web / "index.html").read_text()
        operations = (web / "operations.js").read_text()
        self.assertIn('id="weather"', html)
        self.assertIn('id="airport"', html)
        self.assertIn("LICC", html)
        self.assertIn("api/aircraft-detail", operations)

    def test_supplemental_weather_uses_sicily_aviation_stations(self):
        forecast = {"current": {"temperature_2m": 22}, "daily": {"time": ["2026-08-09"]}}
        metars = [{"icaoId": "LICC", "fltCat": "VFR", "wspd": 8}]
        with patch.object(dashboard, "fetch_json", side_effect=[forecast, metars]) as fetch:
            weather = dashboard.supplemental_weather({"lat": 37.847, "lon": 14.925})
        self.assertEqual(weather["current"]["temperature_2m"], 22)
        self.assertEqual(weather["aviation"][0]["station"], "LICC")
        self.assertIn("LICC,LICR,LICZ,LICB", fetch.call_args_list[1].args[1])

    def test_opensky_airport_board_returns_observed_catania_movements(self):
        observed = [{"icao24": "4ca8af", "callsign": "RYR43ET", "estDepartureAirport": "LIRF", "estArrivalAirport": "LICC", "firstSeen": 10, "lastSeen": 20}]
        with patch.object(dashboard, "fetch_json", return_value=observed):
            board = dashboard.airport_board("LICC")
        self.assertEqual(board["airport"], "LICC")
        self.assertEqual(board["arrivals"][0]["ident"], "RYR43ET")
        self.assertFalse(board["live_status"])

    def test_current_rainviewer_hash_path_is_valid(self):
        self.assertTrue(dashboard.valid_weather_tile_path("v2/radar/25dbbe425e29/256/7/67/48/2/1_1.png"))

    def test_cached_weather_frame_remains_promise_compatible(self):
        script = (Path(__file__).parents[1] / "dashboard" / "web" / "map.js").read_text()
        self.assertIn("return Promise.resolve(weatherMetadata)", script)

    def test_weather_render_cannot_preempt_aircraft_markers(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        dashboard_script = (web / "app.js").read_text()
        tv_script = (web / "display.js").read_text()
        self.assertLess(dashboard_script.index("map.appendChild(node)});weatherMap.render"), dashboard_script.index("$('#radar-map').addEventListener"))
        self.assertLess(tv_script.index("positioned.forEach(item=>addAircraftMarker"), tv_script.index("weatherMap.render(view,data.weather)"))

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
            os.environ["AIRBAND_SOURCE_PASSWORD"] = "audio-source-secret"
            os.environ["AIRNAV_VHF_PASSWORD"] = "airnav-secret"
            os.environ["ADSBHUB_CKEY"] = "adsbhub-secret"
            os.environ["SERVICE_ENABLE_ADSBHUB"] = "true"
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
                self.assertIn("airband", payload)
                self.assertNotIn("audio-source-secret", encoded)
                self.assertNotIn("airnav-secret", encoded)
                self.assertNotIn("adsbhub-secret", encoded)
                self.assertIn("adsbhub", payload)
                self.assertTrue(payload["adsbhub"]["configured"])
            finally:
                dashboard.AIRCRAFT_FILES = old_files
                os.environ.pop("FR24FEED_FR24KEY", None)
                os.environ.pop("SERVICE_ENABLE_FR24FEED", None)
                os.environ.pop("AIRBAND_SOURCE_PASSWORD", None)
                os.environ.pop("AIRNAV_VHF_PASSWORD", None)
                os.environ.pop("ADSBHUB_CKEY", None)
                os.environ.pop("SERVICE_ENABLE_ADSBHUB", None)

    def test_adsbhub_panel_shows_public_address_and_separate_routes(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        html = (web / "index.html").read_text()
        script = (web / "operations.js").read_text()
        self.assertIn('id="adsbhub-public-ip"', html)
        self.assertIn('id="check-adsbhub-ip"', html)
        self.assertIn("OUTBOUND RAW", html)
        self.assertIn("INBOUND SBS", html)
        self.assertIn("renderADSBHub", script)
        self.assertIn("api/adsbhub-public-ip", script)

    def test_adsbhub_public_ip_check_reports_manual_mismatch_without_credentials(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return b"203.0.113.9"

        os.environ["ADSBHUB_PUBLIC_IP_MODE"] = "manual"
        os.environ["ADSBHUB_PUBLIC_HOST"] = "198.51.100.44"
        os.environ["ADSBHUB_CKEY"] = "never-return-this"
        try:
            with patch.object(dashboard, "urlopen", return_value=Response()):
                result = dashboard.adsbhub_public_ip_check()
            self.assertEqual(result["detected_public_ipv4"], "203.0.113.9")
            self.assertFalse(result["matches"])
            self.assertNotIn("never-return-this", json.dumps(result))
        finally:
            os.environ.pop("ADSBHUB_PUBLIC_IP_MODE", None)
            os.environ.pop("ADSBHUB_PUBLIC_HOST", None)
            os.environ.pop("ADSBHUB_CKEY", None)

    def test_airband_status_warns_when_both_roles_use_one_radio(self):
        os.environ.update({"AIRBAND_ENABLED": "true", "RECEIVER_DEVICE_INDEX": "1", "VHF_DEVICE": "1"})
        try:
            status = dashboard.airband_status()
            self.assertTrue(status["enabled"])
            self.assertTrue(status["device_conflict"])
            self.assertEqual(status["channels"], [])
        finally:
            os.environ.pop("AIRBAND_ENABLED", None)
            os.environ.pop("RECEIVER_DEVICE_INDEX", None)
            os.environ.pop("VHF_DEVICE", None)

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
