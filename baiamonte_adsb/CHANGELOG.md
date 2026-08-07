# Changelog

## 1.3.0

- Adds a cached live precipitation radar overlay from RainViewer with Italian radar coverage.
- Adds separate configuration switches for the operations dashboard and fullscreen TV display.
- Adds configurable radar opacity, live frame time, graceful fallback, and required weather attribution.
- Makes the overview map draggable and zoomable with wheel, touch, buttons, and automatic-view reset controls.

## 1.2.0

- Fixes live aircraft discovery by reading the feeder image's actual dump1090 JSON output.
- Adds a real OpenStreetMap basemap with geographically positioned aircraft in both interfaces.
- Adds visible Back controls to detail pages and the TV display.
- Adds automatic NMEA USB GPS detection for receiver, map, and feeder coordinates with a Home Assistant fallback.

## 1.1.0

- Ranks positioned aircraft by distance from the configured Baiamonte receiver location.
- Adds a compact `nearest_aircraft` top-10 feed for Home Assistant dashboards.
- Moves the default TV/kiosk host port to 8998 while retaining internal ingress port 8099.

## 1.0.4

- Makes Home Assistant resolve the TV display link using the configured host port.
- Clarifies that the editable TV port is the host-side value under Network while ingress remains on internal port 8099.

## 1.0.3

- Fixes app option loading so feeder credentials and receiver settings reach every service correctly.
- Prevents malformed environment records from stopping FlightRadar24 and FlightAware during startup.

## 1.0.2

- Adds a Baiamonte aircraft roster beside the TV radar map.
- Shows country flags, callsign, registration, aircraft type, altitude, speed, and track for recent contacts.

## 1.0.1

- Adds a fullscreen, map-only estate TV display at `/display`.
- Adds a minimal credential-free aircraft JSON feed at `/api/aircraft`.
- Publishes dashboard port 8099 for local-network TV access.

## 1.0.0

- Introduces the fully branded Tenuta Baiamonte airspace dashboard.
- Preserves multi-portal feeding for FlightRadar24, FlightAware, ADS-B Exchange, Plane Finder, OpenSky, adsb.fi, RadarBox, and ADSBHub.
- Adds aircraft positions, receiver health, coverage, portal state, and recent-contact views through Home Assistant ingress.
- Adds Baiamonte aviation iconography, Home Assistant translations, GitHub builds, and multi-architecture publishing.
