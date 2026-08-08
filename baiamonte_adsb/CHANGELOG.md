# Changelog

## 1.4.1

- Keeps the last valid decoder snapshot during brief `aircraft.json` replacement windows so aircraft no longer blink off the maps.
- Re-renders the overview map after Home Assistant page, visibility, and size changes.
- Preserves the last known receiver state during transient dashboard refresh failures and retries automatically.
- Adds separately labelled registration and carrier flags to Live traffic cards, with carrier inference for common Sicily traffic.

## 1.4.0

- Renames the fullscreen route from `/display` to `/tv`, while retaining `/display` as a compatibility alias.
- Adds friendly RTL-SDR device, gain, PPM correction, and bias-tee settings.
- Adds pinch-to-zoom and matching zoom/reset controls on dashboard and TV maps.
- Adds Samsung/Tizen flexbox layout fallbacks and older-browser-safe TV JavaScript.
- Adds receiver activity and radio-profile panels to the Watch Area page.
- Aligns page names with AIS: Overview, Live traffic, and Watch area.
- Adds compact country, airline/operator, registration, type, squawk, and distance aircraft cards.

## 1.3.2

- Accepts RainViewer's current alphanumeric radar-frame identifiers so precipitation tiles render on dashboards and TV displays.
- Redesigns the ADS-B TV display to match the AIS TV layout, with a large live map and a compact list of the ten nearest aircraft.

## 1.3.1

- Proxies and caches OpenStreetMap tiles through the app so TV and kiosk browsers reliably render the basemap.
- Proxies RainViewer metadata and precipitation tiles through the same local app for reliable TV weather overlays.
- Adds a settings selector for Standard, Humanitarian, Topographic, Dark, and Satellite base maps.

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
