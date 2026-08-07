# Changelog

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
