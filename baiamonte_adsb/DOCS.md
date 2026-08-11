# Baiamonte ADS-B setup

## What this app does

Baiamonte ADS-B reads 1090 MHz aircraft broadcasts from a compatible USB RTL-SDR receiver, decodes them with dump1090, displays aircraft in a Tenuta Baiamonte dashboard, publishes Home Assistant feeder sensors, and optionally shares the same local feed with supported tracking networks.

## Hardware

1. Connect a compatible RTL-SDR USB receiver to the Home Assistant host. Connect a second receiver if you want VHF aviation audio.
2. Attach a 1090 MHz antenna. For reliable results, use a short, good-quality USB extension and place the antenna safely with a clear view of the sky.
3. Install and start the app. Home Assistant grants the container USB access through the app manifest.

## First start

The default configuration enables dump1090, FlightAware, FlightRadar24, and the receiver's original web map. Add portal credentials before expecting those external feeds to report as ready.

The receiver location defaults to the Home Assistant home latitude, longitude, and elevation. These values are resolved at startup and are not sent anywhere except to feeder services you explicitly enable.

The receiver settings expose the RTL-SDR device index or serial, gain, oscillator correction in PPM, and optional bias tee. Leave gain on `auto`, PPM on `0`, and bias tee off unless the antenna hardware requires different values.

When two identical RTL-SDR sticks are installed, give each stick a unique serial with `rtl_eeprom`, then enter those values under **ADS-B radio serial** and **VHF radio serial**. Serial selection overrides the legacy indexes and prevents USB discovery order from swapping the 1090 MHz and VHF receivers after a reboot. Factory-default duplicate serials are not stable identifiers and should be changed before enabling both roles.

The optional VHF recovery control resets and re-enumerates only the selected VHF USB stick after RTLSDR-Airband exits unexpectedly. It tries twice by default, then uses slower restart-only recovery to avoid a reset loop. For a manual recovery, enable **Reset VHF USB radio on start**, restart the add-on once, and turn the option back off. USB reset support depends on the host exposing the receiver through the add-on's USB access; hubs without per-port switching perform a logical USB reset rather than removing electrical power.

## VHF airband audio

Enable **VHF airband receiver** to use a second RTL-SDR for receive-only civil aviation audio. The default ADS-B device is `0` and the default VHF device is `1`. Keep these different: a single tuner cannot decode 1090 MHz ADS-B and scan 118–137 MHz voice channels simultaneously. The dashboard reports a device conflict when both roles match.

The default scan list contains published Catania Tower, Approach, Ground, and ATIS frequencies. Aviation frequencies change; confirm the current Italian AIP before operational use. Gain, squelch, PPM correction, frequencies, and channel labels are configurable. Audio is played through Home Assistant ingress, so port `8000` does not need to be exposed.

Optional AirNav VHF forwarding uses the Icecast server, port, username, password, and mount supplied by AirNav. Sharing is disabled by default. Local and AirNav passwords never appear in dashboard responses.

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
| ADSBHub | `SERVICE_ENABLE_ADSBHUB` | Dynamic-IP key is optional |

Obtain credentials directly from each portal. The dashboard deliberately shows only whether a credential exists; it never returns secret values to the browser.

## ADSBHub in and out

1. In the app configuration, enable **Send aircraft to ADSBHub**.
2. The station's dynamic IP update key is optional and is used only when automatic public-IP updates are wanted. This is a protected password field; do not place the key in GitHub or screenshots.
3. For a fixed address, select **manual** and enter it. For a changing address, select **auto**, enable public-IP updates, and add the optional key.
4. Restart the app, open **Watch area**, and copy the displayed public address.
5. In the ADSBHub station profile select **Client**, choose **Raw**, and use the displayed address for **Station Host (IP)**. The app sends local raw data to `data.adsbhub.org:5001`.

When ADSBHub sharing is enabled, the app automatically uses two-way mode: it connects to `data.adsbhub.org:5002`, relays that SBS stream on the separate local port `5002`, and—when **Show ADSBHub targets** is enabled—parses it into display-only dashboard and TV targets. Select **ADSBHub outbound only** only when downloads are intentionally unwanted. Imported targets are labeled **ADSBHub** and are never imported into dump1090 or sent to another portal, preventing a data-sharing loop. Publish host port `5002` under **Network** only if another trusted device needs to read it.

The Watch Area reports outbound, inbound, and dynamic-IP state independently. ADSBHub grants aggregated access based on the station's configured public address and requires the station to be actively sharing data.

Both ADSBHub TCP sessions remain open during quiet traffic periods and use operating-system TCP keepalive to recover from a failed network path. **Both connected** means the raw upload and the optional aggregated download are simultaneously established. Each route shows its own error and byte count when troubleshooting.

## Rahamin Miami private receiver proxy

Enable **Show Rahamin Miami receiver traffic** and enter the Miami appliance's private `/api/aircraft` address in **Rahamin Miami aircraft feed**. Keep that address in Home Assistant configuration rather than committing it to GitHub. Only records explicitly marked **Local receiver** by the Miami appliance are accepted. Miami's ADSBHub and other network-fed targets are rejected before merging, and matching ICAO addresses are shown once. This connection is display-only: its targets never enter dump1090, ADSBHub outbound, or another feeder.

Version 2.5.1 adds **Sicily** and **Miami** buttons directly on the overview and TV maps. Each view is centered and scaled independently so the transatlantic distance cannot push aircraft off-screen. The TV map explicitly requests the configured Miami display feed; no proxied record is connected to an outbound feeder. When a selected site has no positioned aircraft, the map temporarily shows the other active site instead of presenting a blank map.

Inbound ADSBHub aircraft are filtered for display using **ADSBHub Sicily display radius** (500 km by default). The separate ADSBHub TCP relay remains complete and unchanged, but only nearby targets are placed into the Sicily dashboard/TV aircraft collection.

Use **ADSBHub public IP detection → auto** for a changing external address. Choose `manual` and enter the fixed address only when required. **Check public IP now** in Watch Area asks ADSBHub's own address service what it currently sees and warns when that differs from the manual value.

## Interfaces

- Home Assistant ingress on internal port `8099`: branded Baiamonte operations dashboard.
- Local network `http://HOME_ASSISTANT_IP:8998/tv`: fullscreen geographic TV map with the 10 closest positioned aircraft. `/display` remains an alias for existing dashboards.
- Local network `http://HOME_ASSISTANT_IP:8998/api/aircraft`: distance-ranked JSON feed containing receiver position, counts, and current aircraft.
- Optional port `8080`: original receiver map supplied by the feeder image.
- Optional port `8754`: FlightRadar24 feeder status.
- Optional port `30053`: Plane Finder feeder status.
- Optional port `8000`: direct local VHF Icecast audio; leave unpublished when using the ingress player.
- Optional port `5002`: separate ADSBHub aggregated SBS output for trusted local consumers.

Internal port `8099` is published as host port `8998` by default for the estate TV display. To use another port, open the app's **Network** section, change the host-side value beside **TV display host port**, save, and restart the app. The container and Home Assistant ingress continue to use internal port `8099`; this is expected.

The TV feed contains aircraft observations only and never includes portal keys, feeder IDs, UUIDs, or sharecodes. Home Assistant ingress remains available for authenticated operators.

The geographic background uses OpenStreetMap tiles and therefore requires network access from the browser displaying the dashboard. Aircraft data remains local to the app.

## Live weather radar

The geographic maps can display the latest precipitation radar from RainViewer. RainViewer combines Italian Civil Protection and regional radar sources and covers Sicily. The app caches the current radar frame and respects the provider's current public API limits.

The Overview and TV maps can be dragged to move around Sicily and zoomed with a pinch gesture, mouse wheel, or `+` and `−` controls. Select **Reset** to return to the automatic view that fits the receiver and current aircraft. Both maps use the same controls.

- **Live rain radar on dashboard** controls the map inside Home Assistant and is enabled by default.
- **Live rain radar on TV** controls the fullscreen display independently and is disabled by default.
- **Weather overlay opacity** controls how strongly the radar appears over the Baiamonte basemap.

Map and RainViewer requests are proxied through the app so restricted TV browsers do not need direct cross-origin tile access. The TV layout includes a flexbox fallback for Samsung/Tizen models whose browser predates CSS Grid. If the weather service is temporarily unavailable, aircraft and the base map continue working normally. Weather radar is informational and must not be used for aviation safety decisions.

The dashboard also includes **VHF airband**, **Weather**, and **Airport board** pages. Weather uses Open-Meteo for GPS-positioned conditions and AviationWeather.gov for nearby Sicily METAR reports. Airport Board defaults to Catania Fontanarossa (`LICC`) and uses free observed OpenSky movements; an optional FlightAware AeroAPI key adds schedules, gates, and enhanced live status. Live traffic can request no-key ADSBDB aircraft and route details on demand.

The core shared navigation pages remain **Overview**, **Live traffic**, and **Watch area**. Watch Area includes the receiver log, radio profile, GPS source, and feeder portal status.

## Dashboard appearance

Use **Dashboard appearance** to select `auto`, `light`, or `dark`. Automatic follows the browser or Home Assistant display preference. Light and Dark force the selected Baiamonte palette regardless of the device theme. The fullscreen TV view remains optimized for a dark wall display independently.

In Watch Area, ADSBHub **Connected** means the TCP session is open. **Feeding** and **Receiving** mean bytes have actually moved in that direction since the app started. **Both flowing** is the strongest confirmation that the enabled outbound and inbound paths are working.

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
- **ADSBHub outbound is Reconnecting:** confirm the local decoder is running, outbound TCP `5001` is allowed, and ADSBHub has the public address shown in Watch Area.
- **ADSBHub inbound is Waiting for access:** confirm ADSBHub has activated aggregated-data access for the public address and that this station is actively sharing. Inbound access is independent from the outbound connection.
- **TV port does not appear to change:** only edit the host-side value under **Network**. Internal port `8099` is fixed for Home Assistant ingress. Save the network setting, then restart the app.
- **Port conflict:** leave optional external ports disabled unless you explicitly need them. The sidebar dashboard works through ingress on its own internal port.
- **VHF stream stays on Starting:** confirm a second RTL-SDR is attached, set **VHF radio device** to its index, and make sure it differs from **ADS-B Radio Device**.
