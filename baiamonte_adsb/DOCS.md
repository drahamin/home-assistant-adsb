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

## USB GPS location

The app automatically looks for an attached NMEA USB GPS on `/dev/ttyACM*`, `/dev/ttyUSB*`, and `/dev/serial/by-id/*`. A recent GPS fix becomes the receiver location used by dump1090, the Baiamonte maps, distance ranking, and feeder services. If no valid fix arrives during the configured startup wait, the app uses the Home Assistant location.

Keep **Use attached USB GPS** enabled and leave **USB GPS device** set to `auto` for normal use. If the host has several serial devices, select the GPS explicitly, for example `/dev/ttyACM0`. Most receivers use 9600 baud.

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
- Local network `http://HOME_ASSISTANT_IP:8998/display`: fullscreen geographic TV map with the 10 closest positioned aircraft.
- Local network `http://HOME_ASSISTANT_IP:8998/api/aircraft`: distance-ranked JSON feed containing receiver position, counts, and current aircraft.
- Optional port `8080`: original receiver map supplied by the feeder image.
- Optional port `8754`: FlightRadar24 feeder status.
- Optional port `30053`: Plane Finder feeder status.

Internal port `8099` is published as host port `8998` by default for the estate TV display. To use another port, open the app's **Network** section, change the host-side value beside **TV display host port**, save, and restart the app. The container and Home Assistant ingress continue to use internal port `8099`; this is expected.

The TV feed contains aircraft observations only and never includes portal keys, feeder IDs, UUIDs, or sharecodes. Home Assistant ingress remains available for authenticated operators.

The geographic background uses OpenStreetMap tiles and therefore requires network access from the browser displaying the dashboard. Aircraft data remains local to the app.

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
- **USB GPS is waiting:** confirm the device appears as `/dev/ttyACM*` or `/dev/ttyUSB*`, then set the exact path and baud rate in the app configuration if automatic detection cannot distinguish it from another serial device.
- **Aircraft appear without positions:** some Mode-S contacts do not provide a locally decoded position; more messages or a suitable receiver location may be required.
- **Portal says Needs key:** add the matching portal credential and restart the app.
- **TV port does not appear to change:** only edit the host-side value under **Network**. Internal port `8099` is fixed for Home Assistant ingress. Save the network setting, then restart the app.
- **Port conflict:** leave optional external ports disabled unless you explicitly need them. The sidebar dashboard works through ingress on its own internal port.
