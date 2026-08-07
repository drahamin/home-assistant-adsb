# Baiamonte ADS-B setup

## What this app does

Baiamonte ADS-B reads 1090 MHz aircraft broadcasts from a compatible USB RTL-SDR receiver, decodes them with dump1090, displays aircraft in a Tenuta Baiamonte dashboard, publishes Home Assistant feeder sensors, and optionally shares the same local feed with supported tracking networks.

## Hardware

1. Connect a compatible RTL-SDR USB receiver to the Home Assistant host.
2. Attach a 1090 MHz antenna. For reliable results, use a short, good-quality USB extension and place the antenna safely with a clear view of the sky.
3. Install and start the app. Home Assistant grants the container USB access through the app manifest.

## First start

The default configuration enables dump1090, FlightAware, FlightRadar24, and the receiver's original web map. Add portal credentials before expecting those external feeds to report as ready.

The receiver location defaults to the Home Assistant home latitude, longitude, and elevation. These values are resolved at startup and are not sent anywhere except to feeder services you explicitly enable.

## Portal credentials

| Network | Enable option | Credential option |
| --- | --- | --- |
| FlightAware | `SERVICE_ENABLE_PIAWARE` | `PIAWARE_FEEDER_DASH_ID` |
| FlightRadar24 | `SERVICE_ENABLE_FR24FEED` | `FR24FEED_FR24KEY` |
| ADS-B Exchange | `SERVICE_ENABLE_ADSBEXCHANGE` | `ADSBEXCHANGE_UUID` |
| Plane Finder | `SERVICE_ENABLE_PLANEFINDER` | `PLANEFINDER_SHARECODE` |
| OpenSky | `SERVICE_ENABLE_OPENSKY` | `OPENSKY_USERNAME` and related OpenSky fields |
| adsb.fi | `SERVICE_ENABLE_ADSBFI` | `ADSBFI_UUID` |
| RadarBox | `SERVICE_ENABLE_RADARBOX` | `RADARBOX_SHARING_KEY` |
| ADSBHub | `SERVICE_ENABLE_ADSBHUB` | `ADSBHUB_CKEY` |

Obtain credentials directly from each portal. The dashboard deliberately shows only whether a credential exists; it never returns secret values to the browser.

## Interfaces

- Home Assistant ingress on internal port `8099`: branded Baiamonte operations dashboard.
- Optional port `8080`: original receiver map supplied by the feeder image.
- Optional port `8754`: FlightRadar24 feeder status.
- Optional port `30053`: Plane Finder feeder status.

Assign an external host port in the app's Network section only when direct access is necessary. Home Assistant ingress requires no external port.

## Data ports

Ports `30001` through `30005` retain standard dump1090 raw, Beast, and BaseStation inputs/outputs. Leave them unpublished unless another trusted receiver or local service needs them.

## Home Assistant sensors

The bundled `adsb-hassio-sensors` service publishes feeder health and counters to Home Assistant for supported portals. Entity names are created by that upstream component and vary by enabled service.

## Privacy and safe operation

- Portal credentials remain in Home Assistant app configuration.
- No credentials are included in the branded dashboard status response.
- Aircraft data is informational and must not be used for aviation safety, navigation, or traffic separation.
- Sharing aircraft data is optional. Review each portal's terms before enabling it.

## Troubleshooting

- **Receiver stays on Starting:** confirm the USB stick is visible to Home Assistant, stop any other app using the SDR, and review the app log.
- **Aircraft appear without positions:** some Mode-S contacts do not provide a locally decoded position; more messages or a suitable receiver location may be required.
- **Portal says Needs key:** add the matching portal credential and restart the app.
- **Port conflict:** leave optional external ports disabled unless you explicitly need them. The sidebar dashboard works through ingress on its own internal port.
