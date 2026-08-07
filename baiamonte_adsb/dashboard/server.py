#!/usr/bin/env python3
"""Small, dependency-free status server for the Baiamonte ADS-B ingress UI."""

from __future__ import annotations

import json
import math
import mimetypes
import os
import socket
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


WEB_ROOT = Path(__file__).resolve().parent / "web"
AIRCRAFT_FILES = (
    Path(os.getenv("BAIAMONTE_AIRCRAFT_JSON", "/usr/lib/fr24/public_html/data/aircraft.json")),
    Path("/usr/lib/fr24/public_html/data/aircraft.json"),
    Path("/run/dump1090-fa/aircraft.json"),
    Path("/var/run/dump1090-fa/aircraft.json"),
    Path("/run/dump1090-mutability/aircraft.json"),
    Path("/var/run/dump1090-mutability/aircraft.json"),
    Path("/run/readsb/aircraft.json"),
)
GPS_LOCATION_FILE = Path(os.getenv("BAIAMONTE_GPS_JSON", "/run/baiamonte/gps.json"))
PORTALS = (
    ("FlightAware", "SERVICE_ENABLE_PIAWARE", "PIAWARE_FEEDER_DASH_ID"),
    ("FlightRadar24", "SERVICE_ENABLE_FR24FEED", "FR24FEED_FR24KEY"),
    ("ADS-B Exchange", "SERVICE_ENABLE_ADSBEXCHANGE", "ADSBEXCHANGE_UUID"),
    ("Plane Finder", "SERVICE_ENABLE_PLANEFINDER", "PLANEFINDER_SHARECODE"),
    ("OpenSky", "SERVICE_ENABLE_OPENSKY", "OPENSKY_USERNAME"),
    ("adsb.fi", "SERVICE_ENABLE_ADSBFI", "ADSBFI_UUID"),
    ("RadarBox", "SERVICE_ENABLE_RADARBOX", "RADARBOX_SHARING_KEY"),
    ("ADSBHub", "SERVICE_ENABLE_ADSBHUB", "ADSBHUB_CKEY"),
)
REGISTRATION_COUNTRIES = (
    ("EI-", "IE"), ("9H-", "MT"), ("D-", "DE"), ("I-", "IT"), ("G-", "GB"),
    ("F-", "FR"), ("N", "US"), ("C-", "CA"), ("PH-", "NL"), ("EC-", "ES"),
    ("HB-", "CH"), ("OE-", "AT"), ("SE-", "SE"), ("LN-", "NO"), ("OY-", "DK"),
    ("OH-", "FI"), ("SP-", "PL"), ("CS-", "PT"), ("OO-", "BE"), ("SX-", "GR"),
    ("TC-", "TR"), ("A6-", "AE"), ("A7-", "QA"), ("HZ-", "SA"), ("JA", "JP"),
    ("HL", "KR"), ("B-", "CN"), ("VT-", "IN"), ("VH-", "AU"), ("ZK-", "NZ"),
)


def enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def number(name: str) -> float | None:
    try:
        return float(os.getenv(name, ""))
    except (TypeError, ValueError):
        return None


def weather_config(surface: str) -> dict:
    """Return public, credential-free weather overlay settings for one UI."""
    variable = "WEATHER_OVERLAY_TV" if surface == "tv" else "WEATHER_OVERLAY_DASHBOARD"
    try:
        opacity = max(10, min(100, int(os.getenv("WEATHER_OVERLAY_OPACITY", "55")))) / 100
    except ValueError:
        opacity = 0.55
    return {
        "enabled": enabled(variable, default=surface == "dashboard"),
        "provider": "RainViewer",
        "layer": "precipitation radar",
        "opacity": opacity,
    }


def current_location() -> dict:
    """Prefer a recent USB GPS fix, then fall back to configured coordinates."""
    if enabled("GPS_USE_USB", True):
        try:
            fix = json.loads(GPS_LOCATION_FILE.read_text(encoding="utf-8"))
            latitude = float(fix["lat"])
            longitude = float(fix["lon"])
            timestamp = float(fix.get("timestamp", 0))
            if -90 <= latitude <= 90 and -180 <= longitude <= 180 and time.time() - timestamp < 180:
                altitude = fix.get("alt")
                return {
                    "lat": latitude,
                    "lon": longitude,
                    "alt": float(altitude) if altitude is not None else number("HTML_SITE_ALT"),
                    "source": "USB GPS",
                    "device": str(fix.get("device", "")),
                    "fix_age": max(0, round(time.time() - timestamp, 1)),
                }
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            pass
    return {
        "lat": number("HTML_SITE_LAT"),
        "lon": number("HTML_SITE_LON"),
        "alt": number("HTML_SITE_ALT"),
        "source": "Home Assistant",
        "device": "",
        "fix_age": None,
    }


def tcp_ready(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.15):
            return True
    except OSError:
        return False


def read_aircraft() -> tuple[dict, str | None]:
    for path in AIRCRAFT_FILES:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload, str(path)
        except (OSError, json.JSONDecodeError):
            continue
    return {"aircraft": [], "now": time.time(), "messages": 0}, None


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance between two WGS84 positions."""
    radius_km = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    a = min(1.0, max(0.0, a))
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def clean_aircraft(record: dict, reference_lat: float | None = None, reference_lon: float | None = None) -> dict:
    altitude = record.get("alt_baro", record.get("altitude"))
    if altitude == "ground":
        altitude = 0
    registration = str(record.get("r", record.get("registration", ""))).strip().upper()
    country_code = str(record.get("country_code", "")).strip().upper()
    if len(country_code) != 2:
        country_code = next((code for prefix, code in REGISTRATION_COUNTRIES if registration.startswith(prefix)), "")
    cleaned = {
        "hex": str(record.get("hex", "")).strip(),
        "flight": str(record.get("flight", "")).strip() or "Unidentified",
        "lat": record.get("lat"),
        "lon": record.get("lon"),
        "altitude": altitude,
        "speed": record.get("gs", record.get("speed")),
        "track": record.get("track"),
        "seen": record.get("seen"),
        "messages": record.get("messages", 0),
        "category": record.get("category", ""),
        "registration": registration,
        "aircraft_type": str(record.get("t", record.get("type", ""))).strip().upper(),
        "operator": str(record.get("ownOp", record.get("operator", ""))).strip(),
        "squawk": str(record.get("squawk", "")).strip(),
        "country_code": country_code,
    }
    latitude, longitude = cleaned["lat"], cleaned["lon"]
    if all(isinstance(value, (int, float)) for value in (latitude, longitude, reference_lat, reference_lon)):
        cleaned["distance_km"] = round(distance_km(reference_lat, reference_lon, latitude, longitude), 2)
    else:
        cleaned["distance_km"] = None
    return cleaned


def status_payload() -> dict:
    raw, source = read_aircraft()
    location = current_location()
    site_lat = location["lat"]
    site_lon = location["lon"]
    records = [clean_aircraft(item, site_lat, site_lon) for item in raw.get("aircraft", []) if isinstance(item, dict)]
    records.sort(key=lambda item: (
        item["distance_km"] is None,
        item["distance_km"] if item["distance_km"] is not None else math.inf,
        item["seen"] is None,
        item["seen"] if item["seen"] is not None else math.inf,
    ))
    positioned = sum(item["lat"] is not None and item["lon"] is not None for item in records)
    portals = []
    for label, flag, credential in PORTALS:
        is_enabled = enabled(flag, default=flag in {"SERVICE_ENABLE_PIAWARE", "SERVICE_ENABLE_FR24FEED"})
        portals.append({
            "name": label,
            "enabled": is_enabled,
            "configured": bool(os.getenv(credential, "").strip()) if is_enabled else False,
        })
    receiver = enabled("SERVICE_ENABLE_DUMP1090", True)
    decoder_ready = tcp_ready(30005) or source is not None
    now = time.time()
    source_age = None
    if source:
        try:
            source_age = max(0, round(now - Path(source).stat().st_mtime, 1))
        except OSError:
            pass
    return {
        "generated_at": now,
        "site": os.getenv("HTML_SITE_NAME", "Tenuta Baiamonte Airspace"),
        "receiver": {
            "enabled": receiver,
            "ready": receiver and decoder_ready,
            "source_age": source_age,
            "messages": raw.get("messages", 0),
            "map_ready": tcp_ready(8080),
        },
        "location": location,
        "counts": {"aircraft": len(records), "positioned": positioned},
        "aircraft": records[:250],
        "portals": portals,
        "weather": weather_config("dashboard"),
    }


def aircraft_feed() -> dict:
    """Return the deliberately small, credential-free feed used by wall displays."""
    status = status_payload()
    nearest = [item for item in status["aircraft"] if item.get("distance_km") is not None][:10]
    return {
        "generated_at": status["generated_at"],
        "site": status["site"],
        "receiver_online": status["receiver"]["ready"],
        "location": status["location"],
        "counts": status["counts"],
        "aircraft": status["aircraft"],
        "nearest_aircraft": nearest,
        "weather": weather_config("tv"),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "BaiamonteADS-B/1.0"

    def send_bytes(self, body: bytes, content_type: str, status: int = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        dynamic = content_type == "application/json" or content_type.startswith("text/html") or "javascript" in content_type
        self.send_header("Cache-Control", "no-store" if dynamic else "public, max-age=300")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        path = unquote(urlsplit(self.path).path)
        if path.rstrip("/").endswith("/api/status") or path == "/api/status":
            body = json.dumps(status_payload(), separators=(",", ":")).encode()
            self.send_bytes(body, "application/json")
            return
        if path.rstrip("/").endswith("/api/aircraft") or path == "/api/aircraft":
            body = json.dumps(aircraft_feed(), separators=(",", ":")).encode()
            self.send_bytes(body, "application/json")
            return
        relative = path.rsplit("/", 1)[-1] if path not in {"", "/"} else "index.html"
        if relative == "display":
            relative = "display.html"
        if relative not in {"index.html", "app.css", "app.js", "map.js", "map-theme.css", "weather-theme.css", "interaction-theme.css", "display.html", "display.css", "display-board.css", "display.js", "brand-icon.png"}:
            relative = "index.html"
        target = WEB_ROOT / relative
        try:
            body = target.read_bytes()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"
        self.send_bytes(body, content_type)

    def log_message(self, template: str, *args: object) -> None:
        if os.getenv("BAIAMONTE_DASHBOARD_LOG", "").lower() in {"1", "true"}:
            super().log_message(template, *args)


if __name__ == "__main__":
    port = int(os.getenv("BAIAMONTE_DASHBOARD_PORT", "8099"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Baiamonte ADS-B dashboard listening on {port}", flush=True)
    server.serve_forever()
