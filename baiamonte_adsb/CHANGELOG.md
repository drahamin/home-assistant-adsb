# Changelog

## 2.2.0

- Adds a reliable ADSBHub Client-mode raw upload to `data.adsbhub.org:5001`.
- Adds optional aggregated ADSBHub SBS input from port `5002` with a separate local relay that cannot be fed back into the estate decoder or other portals.
- Adds official ADSBHub dynamic-IP updates and automatic public IPv4/IPv6 detection.
- Adds protected Home Assistant configuration for the station key, public address, upload, download, and local inbound port.
- Adds a Baiamonte Watch Area panel with the copyable public address and independent outbound, inbound, and dynamic-IP status.

## 2.1.1

- Brightens the fullscreen `/tv` basemap without changing the Home Assistant dashboard theme or weather opacity.
- Narrows the TV aircraft rail and compacts its header, flags, rows, metadata, and footer while retaining all flight details.
- Preserves flexbox fallbacks for older Samsung/Tizen browsers alongside the compact grid layout.

## 2.1.0

- Adds automatic browser light/dark mode to the Home Assistant ADS-B dashboard.
- Aligns cards, forms, status badges, muted text, and map chrome with AIS and Vineyard Operations.
- Keeps the fullscreen TV display dark for distance viewing while retaining the brighter basemap.

## 2.0.0

- Adds a second-RTL-SDR, receive-only VHF airband receiver using RTLSDR-Airband and a private local Icecast stream.
- Adds a branded ingress VHF player, Catania channel scan list, radio health, same-device conflict warning, and optional AirNav VHF forwarding.
- Adds GPS-positioned Open-Meteo conditions, five-day weather, and eastern Sicily METAR reports.
- Adds a Catania airport board with free OpenSky observed movements and optional FlightAware AeroAPI schedules and gates.
- Adds on-demand, no-key ADSBDB aircraft and route enrichment to Live traffic cards.
- Keeps Home Assistant responsible for networking, updates, restart controls, and all secret storage.

## 1.5.1

- Brightens the fullscreen ADS-B basemap to the proven Rahamin TV profile while retaining the Baiamonte dark interface, altitude colors, labels, and weather overlay.

## 1.5.0

- Replaces triangular map markers with compact, track-oriented top-down aircraft silhouettes.
- Colors aircraft by altitude on both the Home Assistant and fullscreen TV maps.
- Adds an always-visible altitude color scale for ground, sub-10k, 10–20k, 20–30k, 30–40k, and 40k+ contacts.

## 1.4.2

- Keeps weather tiles geographically locked to the basemap during every pan, zoom, resize, and Home Assistant page return.
- Prevents a cached weather redraw from interrupting the map render and removing otherwise valid aircraft markers.
- Draws aircraft before starting weather work so radar availability can never control aircraft visibility.

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
