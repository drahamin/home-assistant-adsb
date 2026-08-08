#!/usr/bin/env python3
"""Small, dependency-free status server for the Baiamonte ADS-B ingress UI."""

from __future__ import annotations

import json
import math
import mimetypes
import os
import re
import socket
import time
from collections import deque
from functools import lru_cache
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen


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
RECEIVER_LOG = deque(maxlen=80)
receiver_signature = None
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
AIRLINE_PREFIXES = {
    "AEE": ("Aegean Airlines", "GR"),
    "AFR": ("Air France", "FR"),
    "AUA": ("Austrian Airlines", "AT"),
    "BAW": ("British Airways", "GB"),
    "BEL": ("Brussels Airlines", "BE"),
    "DLH": ("Lufthansa", "DE"),
    "EIN": ("Aer Lingus", "IE"),
    "EJU": ("easyJet Europe", "AT"),
    "EZY": ("easyJet", "GB"),
    "FIN": ("Finnair", "FI"),
    "IBE": ("Iberia", "ES"),
    "ITA": ("ITA Airways", "IT"),
    "ITY": ("ITA Airways", "IT"),
    "KLM": ("KLM", "NL"),
    "LOT": ("LOT Polish Airlines", "PL"),
    "NAX": ("Norwegian", "NO"),
    "QTR": ("Qatar Airways", "QA"),
    "RYR": ("Ryanair", "IE"),
    "SAS": ("SAS", "SE"),
    "SWR": ("Swiss", "CH"),
    "TAP": ("TAP Air Portugal", "PT"),
    "THY": ("Turkish Airlines", "TR"),
    "TRA": ("Transavia", "NL"),
    "UAE": ("Emirates", "AE"),
    "VLG": ("Vueling", "ES"),
    "VOE": ("Volotea", "ES"),
    "WMT": ("Wizz Air Malta", "MT"),
    "WZZ": ("Wizz Air", "HU"),
}
AIRCRAFT_CACHE_SECONDS = 30
last_aircraft_payload: dict | None = None
last_aircraft_source: str | None = None
last_aircraft_read_at = 0.0


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
        "map_style": map_style(),
    }


def map_style() -> str:
    style = os.getenv("MAP_STYLE", "standard").strip().lower()
    return style if style in MAP_TILE_PROVIDERS else "standard"


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


MAP_TILE_PROVIDERS = {
    "standard": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "humanitarian": "https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
    "topographic": "https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
    "dark": "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
    "satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
}
WEATHER_TILE_PATTERN = re.compile(
    r"v2/radar/[A-Za-z0-9_-]+/256/\d+/\d+/\d+/\d+/[\d_]+\.png"
)


def valid_weather_tile_path(path: str) -> bool:
    return WEATHER_TILE_PATTERN.fullmatch(path) is not None


@lru_cache(maxsize=256)
def fetch_map_tile(style: str, zoom: int, x: int, y: int) -> tuple[bytes, str]:
    """Fetch and cache an OSM tile for TV browsers that block cross-origin images."""
    request = Request(
        MAP_TILE_PROVIDERS[style].format(z=zoom, x=x, y=y),
        headers={"User-Agent": "Tenuta-Baiamonte-ADS-B/1.4.2 (+https://github.com/drahamin/home-assistant-adsb)"},
    )
    with urlopen(request, timeout=10) as response:
        body = response.read()
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type = "image/png"
    elif body.startswith(b"\xff\xd8\xff"):
        content_type = "image/jpeg"
    else:
        raise ValueError("invalid map tile response")
    return body, content_type


weather_metadata_cache: dict[str, object] = {"body": None, "expires": 0.0}


def fetch_weather_metadata() -> bytes:
    body = weather_metadata_cache["body"]
    if isinstance(body, bytes) and time.time() < float(weather_metadata_cache["expires"]):
        return body
    request = Request(
        "https://api.rainviewer.com/public/weather-maps.json",
        headers={"User-Agent": "Tenuta-Baiamonte-ADS-B/1.4.2"},
    )
    with urlopen(request, timeout=10) as response:
        body = response.read()
    json.loads(body.decode("utf-8"))
    weather_metadata_cache.update({"body": body, "expires": time.time() + 300})
    return body


@lru_cache(maxsize=256)
def fetch_weather_tile(suffix: str) -> bytes:
    request = Request(
        f"https://tilecache.rainviewer.com/{suffix}",
        headers={"User-Agent": "Tenuta-Baiamonte-ADS-B/1.4.2"},
    )
    with urlopen(request, timeout=10) as response:
        body = response.read()
    if not body.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("invalid weather tile response")
    return body


def read_aircraft() -> tuple[dict, str | None]:
    global last_aircraft_payload, last_aircraft_source, last_aircraft_read_at
    for path in AIRCRAFT_FILES:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("aircraft", []), list):
                last_aircraft_payload = payload
                last_aircraft_source = str(path)
                last_aircraft_read_at = time.monotonic()
                return payload, last_aircraft_source
        except (OSError, json.JSONDecodeError):
            continue
    current_sources = {str(path) for path in AIRCRAFT_FILES}
    if (
        last_aircraft_payload is not None
        and last_aircraft_source in current_sources
        and time.monotonic() - last_aircraft_read_at <= AIRCRAFT_CACHE_SECONDS
    ):
        return last_aircraft_payload, last_aircraft_source
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
    flight = str(record.get("flight", "")).strip().upper() or "Unidentified"
    registration = str(record.get("r", record.get("registration", ""))).strip().upper()
    country_code = str(record.get("country_code", "")).strip().upper()
    if len(country_code) != 2:
        country_code = next((code for prefix, code in REGISTRATION_COUNTRIES if registration.startswith(prefix)), "")
    operator = str(record.get("ownOp", record.get("operator", ""))).strip()
    carrier_prefix = re.sub(r"[^A-Z]", "", flight)[:3]
    inferred_carrier, carrier_country_code = AIRLINE_PREFIXES.get(carrier_prefix, ("", ""))
    cleaned = {
        "hex": str(record.get("hex", "")).strip(),
        "flight": flight,
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
        "operator": operator or inferred_carrier,
        "carrier_country_code": carrier_country_code,
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
    global receiver_signature
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
    receiver_info = {
        "enabled": receiver,
        "ready": receiver and decoder_ready,
        "source_age": source_age,
        "messages": raw.get("messages", 0),
        "map_ready": tcp_ready(8080),
        "source": source,
        "device": os.getenv("RECEIVER_DEVICE_INDEX", "0"),
        "gain": os.getenv("RECEIVER_GAIN", "auto"),
        "ppm": os.getenv("RECEIVER_PPM", "0"),
        "bias_tee": enabled("RECEIVER_BIAS_TEE", False),
    }
    signature = (receiver_info["ready"], receiver_info["source"], location.get("source"))
    if signature != receiver_signature:
        state = "online" if receiver_info["ready"] else "starting" if receiver else "disabled"
        message = f"1090 MHz receiver {state} · {receiver_info['messages']} messages · location {location.get('source', 'unknown')}"
        RECEIVER_LOG.appendleft({"time": now, "message": message})
        receiver_signature = signature
    return {
        "generated_at": now,
        "site": os.getenv("HTML_SITE_NAME", "Tenuta Baiamonte Airspace"),
        "receiver": receiver_info,
        "receiver_log": list(RECEIVER_LOG),
        "location": location,
        "counts": {"aircraft": len(records), "positioned": positioned},
        "aircraft": records[:250],
        "portals": portals,
        "weather": weather_config("dashboard"),
        "map_style": map_style(),
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
        "map_style": map_style(),
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
        if path.rstrip("/") == "/api/weather-maps":
            try:
                body = fetch_weather_metadata()
            except (OSError, ValueError):
                self.send_error(HTTPStatus.BAD_GATEWAY, "Weather radar temporarily unavailable")
                return
            self.send_bytes(body, "application/json")
            return
        if path.startswith("/api/weather-tile/"):
            suffix = path.removeprefix("/api/weather-tile/")
            if not valid_weather_tile_path(suffix):
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid weather tile")
                return
            try:
                body = fetch_weather_tile(suffix)
            except (OSError, ValueError):
                self.send_error(HTTPStatus.BAD_GATEWAY, "Weather radar temporarily unavailable")
                return
            self.send_bytes(body, "image/png")
            return
        if path.startswith("/api/map-tile/"):
            try:
                _, _, _, style, zoom_text, x_text, y_file = path.split("/")
                zoom, x, y = int(zoom_text), int(x_text), int(y_file.removesuffix(".png"))
                limit = 2 ** zoom
                if style not in MAP_TILE_PROVIDERS or not (0 <= zoom <= 19 and 0 <= x < limit and 0 <= y < limit):
                    raise ValueError("tile outside supported range")
                body, content_type = fetch_map_tile(style, zoom, x, y)
            except (OSError, ValueError):
                self.send_error(HTTPStatus.BAD_GATEWAY, "Map tile temporarily unavailable")
                return
            self.send_bytes(body, content_type)
            return
        if path.rstrip("/").endswith("/api/status") or path == "/api/status":
            body = json.dumps(status_payload(), separators=(",", ":")).encode()
            self.send_bytes(body, "application/json")
            return
        if path.rstrip("/").endswith("/api/aircraft") or path == "/api/aircraft":
            body = json.dumps(aircraft_feed(), separators=(",", ":")).encode()
            self.send_bytes(body, "application/json")
            return
        relative = path.rsplit("/", 1)[-1] if path not in {"", "/"} else "index.html"
        if relative in {"display", "tv"}:
            relative = "display.html"
        if relative not in {"index.html", "app.css", "app.js", "map.js", "map-theme.css", "weather-theme.css", "interaction-theme.css", "detail-theme.css", "display.html", "display.css", "display-board.css", "display.js", "brand-icon.png"}:
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
