# Baiamonte ADS-B

Baiamonte ADS-B is a fully branded Home Assistant app for receiving local 1090 MHz aircraft broadcasts and sharing them with multiple flight-tracking networks. It keeps the proven multi-portal feeder engine while adding a Tenuta Baiamonte operations dashboard, a live geographic aircraft map, automatic USB GPS location, Home Assistant ingress, and estate-wide visual identity.

## Supported networks

- FlightRadar24
- FlightAware
- ADS-B Exchange
- Plane Finder
- OpenSky Network
- adsb.fi
- RadarBox
- ADSBHub

Each network is optional. Enable only the services for which you have credentials and intend to share data.

## Installation

Add this repository to the Home Assistant App Store:

`https://github.com/drahamin/home-assistant-adsb`

Install **Baiamonte ADS-B**, connect a compatible RTL-SDR receiver, complete the app configuration, start the app, and enable **Show in sidebar**.

See [baiamonte_adsb/DOCS.md](baiamonte_adsb/DOCS.md) for configuration, portal keys, ports, and receiver guidance.

## Design

The interface follows the shared Baiamonte operations system used by Baiamonte LTE and Baiamonte AIS: volcanic black, warm ivory, estate gold, restrained typography, and operational status views. The aviation emblem is unique to ADS-B while remaining part of the same visual family.

## Estate TV display

Open `http://HOME_ASSISTANT_IP:8998/display` on a local TV browser for the fullscreen geographic estate aircraft map and its 10 closest positioned aircraft. You can change the host-side port under the app's **Network** section. A credential-free, distance-ranked JSON feed is available at `http://HOME_ASSISTANT_IP:8998/api/aircraft` for another dashboard to consume.

## Credits and licensing

The feeder runtime is based on Max Winterstein's Home Assistant wrapper and Thom-x's `docker-fr24feed-piaware-dump1090` image. Home Assistant sensor support originates from `adsb-hassio-sensors` by plo53. See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE).
