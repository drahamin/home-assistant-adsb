import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


SERVER = Path(__file__).parents[1] / "dashboard" / "server.py"
SPEC = importlib.util.spec_from_file_location("baiamonte_dashboard", SERVER)
dashboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard)


class DashboardTests(unittest.TestCase):
    def test_dashboard_follows_browser_color_scheme(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        html = (web / "index.html").read_text()
        theme = (web / "theme.css").read_text()
        self.assertIn('id="automatic-theme"', html)
        self.assertIn('id="forced-dark-theme"', html)
        self.assertIn('src="theme-control.js?v=230"', html)
        self.assertIn('media="(prefers-color-scheme: dark)"', html)
        self.assertIn("@media(prefers-color-scheme:dark)", theme)
        self.assertIn("color-scheme:light dark", theme)
        self.assertIn("color-scheme:dark", (web / "forced-dark.css").read_text())
        self.assertIn("applyDashboardTheme", (web / "theme-control.js").read_text())

    def test_dashboard_theme_setting_supports_auto_light_and_dark(self):
        for theme in ("auto", "light", "dark"):
            os.environ["DASHBOARD_THEME"] = theme
            self.assertEqual(dashboard.dashboard_theme(), theme)
        os.environ["DASHBOARD_THEME"] = "invalid"
        self.assertEqual(dashboard.dashboard_theme(), "auto")
        os.environ.pop("DASHBOARD_THEME", None)

    def test_baiamonte_touch_icons_and_web_manifest_are_available(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        dashboard_html = (web / "index.html").read_text()
        tv_html = (web / "display.html").read_text()
        manifest = json.loads((web / "site.webmanifest").read_text())
        for html in (dashboard_html, tv_html):
            self.assertIn('rel="apple-touch-icon"', html)
            self.assertIn('rel="manifest"', html)
            self.assertIn('favicon-32.png', html)
        self.assertEqual(manifest["short_name"], "Baiamonte ADS-B")
        self.assertEqual({item["sizes"] for item in manifest["icons"]}, {"192x192", "512x512"})
        for filename in ("favicon-16.png", "favicon-32.png", "apple-touch-icon.png", "app-icon-192.png", "app-icon-512.png"):
            self.assertTrue((web / filename).is_file())

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

    def test_adsbhub_targets_are_labeled_on_dashboard_and_tv(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        dashboard_html = (web / "index.html").read_text()
        tv_html = (web / "display.html").read_text()
        dashboard_script = (web / "app.js").read_text()
        tv_script = (web / "display.js").read_text()
        health_script = (web / "adsbhub-health.js").read_text()
        self.assertIn('href="adsbhub-targets.css?v=231"', dashboard_html)
        self.assertIn('href="adsbhub-targets.css?v=231"', tv_html)
        self.assertIn("adsbhub-target", dashboard_script)
        self.assertIn("adsbhub-target", tv_script)
        self.assertIn("displayed_target_count", health_script)

    def test_tv_refresh_pauses_when_hidden_and_cannot_overlap(self):
        script = (Path(__file__).parents[1] / "dashboard" / "web" / "display.js").read_text()
        self.assertIn("if(refreshRunning){refreshQueued=true;return}", script)
        self.assertIn("if(!document.hidden)refresh()", script)
        self.assertIn("visibilitychange", script)
        self.assertIn("api/aircraft?include_miami=1", script)

    def test_overview_and_tv_have_sicily_miami_map_focus(self):
        web = Path(__file__).parents[1] / "dashboard" / "web"
        focus = (web / "site-focus.js").read_text()
        for html_name in ("index.html", "display.html"):
            html = (web / html_name).read_text()
            self.assertIn("site-focus.js?v=252", html)
            self.assertIn("site-focus.css?v=251", html)
        self.assertIn("data-site=\"sicily\"", focus)
        self.assertIn("data-site=\"miami\"", focus)
        self.assertIn("Rahamin ADS-B · Miami", focus)
        self.assertIn("resetMapView", focus)
        self.assertIn("resetView", (web / "map.js").read_text())

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
        self.assertEqual(item["source"], "Local receiver")
        self.assertIsNone(item["distance_km"])

    def test_adsbhub_targets_are_merged_for_display_but_local_targets_win(self):
        old_files = dashboard.AIRCRAFT_FILES
        old_status = dashboard.ADSBHUB_STATUS_FILE
        with tempfile.TemporaryDirectory() as tmp:
            aircraft_file = Path(tmp) / "aircraft.json"
            status_file = Path(tmp) / "adsbhub.json"
            aircraft_file.write_text(json.dumps({"aircraft": [{"hex": "abc123", "flight": "LOCAL1"}]}))
            status_file.write_text(json.dumps({"inbound_targets": [
                {"hex": "abc123", "flight": "DUPLICATE", "lat": 37.8, "lon": 14.9, "source": "ADSBHub"},
                {"hex": "def456", "flight": "HUB2", "lat": 37.9, "lon": 15.1, "source": "ADSBHub"},
            ]}))
            dashboard.AIRCRAFT_FILES = (aircraft_file,)
            dashboard.ADSBHUB_STATUS_FILE = status_file
            os.environ["ADSBHUB_INBOUND_ENABLED"] = "true"
            os.environ["ADSBHUB_DISPLAY_TARGETS"] = "true"
            try:
                payload = dashboard.status_payload()
                by_hex = {item["hex"]: item for item in payload["aircraft"]}
                self.assertEqual(set(by_hex), {"abc123", "def456"})
                self.assertEqual(by_hex["abc123"]["source"], "Local + ADSBHub")
                self.assertEqual(by_hex["abc123"]["lat"], 37.8)
                self.assertEqual(by_hex["def456"]["source"], "ADSBHub")
                self.assertEqual(payload["counts"]["local"], 1)
                self.assertEqual(payload["counts"]["adsbhub"], 2)
                self.assertEqual(payload["adsbhub"]["displayed_target_count"], 2)
                self.assertEqual(payload["adsbhub"]["positioned_target_count"], 2)
                self.assertNotIn("inbound_targets", payload["adsbhub"])
            finally:
                dashboard.AIRCRAFT_FILES = old_files
                dashboard.ADSBHUB_STATUS_FILE = old_status
                os.environ.pop("ADSBHUB_INBOUND_ENABLED", None)
                os.environ.pop("ADSBHUB_DISPLAY_TARGETS", None)

    def test_adsbhub_map_targets_are_limited_to_sicily_radius(self):
        old_files = dashboard.AIRCRAFT_FILES
        old_status = dashboard.ADSBHUB_STATUS_FILE
        with tempfile.TemporaryDirectory() as tmp:
            aircraft_file = Path(tmp) / "aircraft.json"
            status_file = Path(tmp) / "adsbhub.json"
            aircraft_file.write_text(json.dumps({"aircraft": []}))
            status_file.write_text(json.dumps({"inbound_targets": [
                {"hex": "near01", "lat": 37.9, "lon": 15.0, "source": "ADSBHub"},
                {"hex": "far001", "lat": 25.8, "lon": -80.2, "source": "ADSBHub"},
            ]}))
            dashboard.AIRCRAFT_FILES = (aircraft_file,)
            dashboard.ADSBHUB_STATUS_FILE = status_file
            os.environ["ADSBHUB_INBOUND_ENABLED"] = "true"
            os.environ["ADSBHUB_DISPLAY_TARGETS"] = "true"
            os.environ["ADSBHUB_DISPLAY_RADIUS_KM"] = "500"
            os.environ["HTML_SITE_LAT"] = "37.847"
            os.environ["HTML_SITE_LON"] = "14.925"
            try:
                payload = dashboard.status_payload()
                self.assertEqual([item["hex"] for item in payload["aircraft"]], ["near01"])
                self.assertEqual(payload["counts"]["adsbhub"], 2)
                self.assertEqual(payload["adsbhub"]["display_radius_km"], 500)
            finally:
                dashboard.AIRCRAFT_FILES = old_files
                dashboard.ADSBHUB_STATUS_FILE = old_status
                os.environ.pop("ADSBHUB_INBOUND_ENABLED", None)
                os.environ.pop("ADSBHUB_DISPLAY_TARGETS", None)
                os.environ.pop("ADSBHUB_DISPLAY_RADIUS_KM", None)
                os.environ.pop("HTML_SITE_LAT", None)
                os.environ.pop("HTML_SITE_LON", None)

    def test_miami_proxy_accepts_only_receiver_local_aircraft(self):
        response = {
            "generated_at": time.time(),
            "site": "Rahamin ADS-B · Miami Airspace",
            "aircraft": [
                {"hex": "a00001", "flight": "MIA1", "data_source": "Local receiver"},
                {"hex": "a00003", "flight": "MIA2", "data_source": "Local receiver + ADSBHub"},
                {"hex": "a00002", "flight": "HUB1", "data_source": "ADSBHub"},
            ],
        }
        dashboard.MIAMI_PROXY_CACHE.update({"attempted_at": 0.0, "received_at": 0.0, "aircraft": [], "error": ""})
        os.environ["MIAMI_PROXY_ENABLED"] = "true"
        os.environ["MIAMI_PROXY_URL"] = "http://miami.test/api/aircraft"
        mock_response = MagicMock()
        mock_response.__enter__.return_value.read.return_value = json.dumps(response).encode()
        with patch.object(dashboard, "urlopen", return_value=mock_response):
            proxy = dashboard.miami_proxy_status()
        try:
            self.assertTrue(proxy["online"])
            self.assertEqual([item["hex"] for item in proxy["aircraft"]], ["a00001", "a00003"])
            self.assertEqual(proxy["aircraft"][0]["source"], "Rahamin Miami proxy")
        finally:
            os.environ.pop("MIAMI_PROXY_ENABLED", None)
            os.environ.pop("MIAMI_PROXY_URL", None)

    def test_miami_proxy_is_display_only_and_deduplicated_before_adsbhub(self):
        old_files = dashboard.AIRCRAFT_FILES
        with tempfile.TemporaryDirectory() as tmp:
            aircraft_file = Path(tmp) / "aircraft.json"
            aircraft_file.write_text(json.dumps({"aircraft": [{"hex": "abc123", "flight": "SICILY"}]}))
            dashboard.AIRCRAFT_FILES = (aircraft_file,)
            miami = {
                "enabled": True, "configured": True, "online": True,
                "aircraft": [
                    {"hex": "abc123", "flight": "MIAMI-DUP", "source": "Rahamin Miami proxy"},
                    {"hex": "def456", "flight": "MIAMI", "source": "Rahamin Miami proxy"},
                ],
                "target_count": 2, "displayed_target_count": 0,
                "deduplicated_target_count": 0, "last_success": time.time(),
                "source_age": 0, "error": "",
            }
            hub = {"inbound_targets": [{"hex": "def456", "flight": "HUB-DUP", "lat": 25.86, "lon": -80.19, "source": "ADSBHub"}]}
            try:
                with patch.object(dashboard, "miami_proxy_status", return_value=miami), patch.object(dashboard, "adsbhub_status", return_value=hub):
                    payload = dashboard.status_payload()
                by_hex = {item["hex"]: item for item in payload["aircraft"]}
                self.assertEqual(set(by_hex), {"abc123", "def456"})
                self.assertEqual(by_hex["abc123"]["source"], "Local receiver")
                self.assertEqual(by_hex["def456"]["source"], "Rahamin Miami proxy")
                self.assertEqual(by_hex["def456"]["lat"], 25.86)
                self.assertEqual(payload["counts"]["miami"], 2)
                self.assertEqual(payload["miami_proxy"]["deduplicated_target_count"], 1)
                self.assertEqual(payload["miami_proxy"]["adsbhub_enriched_target_count"], 1)
            finally:
                dashboard.AIRCRAFT_FILES = old_files

    def test_miami_proxy_targets_are_reserved_when_adsbhub_fills_display_limit(self):
        old_files = dashboard.AIRCRAFT_FILES
        old_status = dashboard.ADSBHUB_STATUS_FILE
        with tempfile.TemporaryDirectory() as tmp:
            aircraft_file = Path(tmp) / "aircraft.json"
            status_file = Path(tmp) / "adsbhub.json"
            aircraft_file.write_text(json.dumps({"aircraft": []}))
            status_file.write_text(json.dumps({"inbound_targets": [
                {"hex": f"h{index:05d}", "lat": 37.8 + (index % 10) / 100, "lon": 14.9, "source": "ADSBHub"}
                for index in range(150)
            ]}))
            dashboard.AIRCRAFT_FILES = (aircraft_file,)
            dashboard.ADSBHUB_STATUS_FILE = status_file
            os.environ["ADSBHUB_INBOUND_ENABLED"] = "true"
            os.environ["ADSBHUB_DISPLAY_TARGETS"] = "true"
            os.environ["ADSBHUB_DISPLAY_LIMIT"] = "100"
            os.environ["HTML_SITE_LAT"] = "37.847"
            os.environ["HTML_SITE_LON"] = "14.925"
            miami = {
                "enabled": True, "configured": True, "online": True,
                "aircraft": [{"hex": "miami1", "flight": "MIA1", "lat": 25.86, "lon": -80.19, "source": "Rahamin Miami proxy"}],
                "target_count": 1, "displayed_target_count": 0, "deduplicated_target_count": 0,
                "last_success": time.time(), "source_age": 0, "error": "",
            }
            try:
                with patch.object(dashboard, "miami_proxy_status", return_value=miami):
                    payload = dashboard.status_payload()
                self.assertEqual(len(payload["aircraft"]), 100)
                self.assertIn("miami1", {item["hex"] for item in payload["aircraft"]})
                self.assertEqual(payload["miami_proxy"]["displayed_target_count"], 1)
                self.assertEqual(payload["miami_proxy"]["display_truncated"], 0)
            finally:
                dashboard.AIRCRAFT_FILES = old_files
                dashboard.ADSBHUB_STATUS_FILE = old_status
                for key in ("ADSBHUB_INBOUND_ENABLED", "ADSBHUB_DISPLAY_TARGETS", "ADSBHUB_DISPLAY_LIMIT", "HTML_SITE_LAT", "HTML_SITE_LON"):
                    os.environ.pop(key, None)

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
        self.assertIn('src="adsbhub-health.js?v=233"', html)
        self.assertIn("Both flowing", (web / "adsbhub-health.js").read_text())
        self.assertIn("Only needed for automatic public-IP updates", (web / "adsbhub-health.js").read_text())

    def test_adsbhub_portal_is_ready_without_optional_dynamic_ip_key(self):
        os.environ["SERVICE_ENABLE_ADSBHUB"] = "true"
        os.environ.pop("ADSBHUB_CKEY", None)
        try:
            payload = dashboard.status_payload()
            hub = next(item for item in payload["portals"] if item["name"] == "ADSBHub")
            self.assertTrue(hub["enabled"])
            self.assertTrue(hub["configured"])
            self.assertTrue(payload["adsbhub"]["inbound_enabled"])
        finally:
            os.environ.pop("SERVICE_ENABLE_ADSBHUB", None)

    def test_adsbhub_status_distinguishes_connected_from_data_flowing(self):
        old_file = dashboard.ADSBHUB_STATUS_FILE
        with tempfile.TemporaryDirectory() as tmp:
            status_file = Path(tmp) / "adsbhub.json"
            status_file.write_text(json.dumps({
                "outbound_connected": True,
                "inbound_connected": True,
                "outbound_bytes": 2048,
                "inbound_bytes": 4096,
            }))
            dashboard.ADSBHUB_STATUS_FILE = status_file
            os.environ["SERVICE_ENABLE_ADSBHUB"] = "true"
            os.environ["ADSBHUB_INBOUND_ENABLED"] = "true"
            try:
                status = dashboard.adsbhub_status()
                self.assertTrue(status["outbound_active"])
                self.assertTrue(status["inbound_active"])
            finally:
                dashboard.ADSBHUB_STATUS_FILE = old_file
                os.environ.pop("SERVICE_ENABLE_ADSBHUB", None)
                os.environ.pop("ADSBHUB_INBOUND_ENABLED", None)

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
            with patch.object(dashboard, "urlopen", return_value=Response()) as urlopen:
                result = dashboard.adsbhub_public_ip_check()
            self.assertEqual(result["detected_public_ipv4"], "203.0.113.9")
            self.assertEqual(urlopen.call_args.args[0].full_url, "https://www.adsbhub.org/getmyip.php")
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

    def test_airband_status_detects_matching_radio_serials(self):
        os.environ.update({
            "AIRBAND_ENABLED": "true",
            "RECEIVER_DEVICE_SERIAL": "DUPLICATE",
            "VHF_DEVICE_SERIAL": "DUPLICATE",
        })
        try:
            with patch.object(dashboard, "tcp_ready", return_value=False):
                status = dashboard.airband_status()
            self.assertTrue(status["device_conflict"])
            self.assertEqual(status["device"], "Serial DUPLICATE")
        finally:
            os.environ.pop("AIRBAND_ENABLED", None)
            os.environ.pop("RECEIVER_DEVICE_SERIAL", None)
            os.environ.pop("VHF_DEVICE_SERIAL", None)

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
