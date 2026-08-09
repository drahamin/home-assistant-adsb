ARG BUILD_FROM=thomx/fr24feed-piaware:2.6.1
FROM ${BUILD_FROM} AS airband-builder

ARG RTL_AIRBAND_VERSION=5.2.0
ARG RTL_AIRBAND_SHA256=840c5f0eb368a2ea61dfb46830ed43b9c4d3371fc7cefd3a0d8fee7bb212f3cb
ARG DEBIAN_FRONTEND=noninteractive
ADD https://github.com/rtl-airband/RTLSDR-Airband/archive/refs/tags/v${RTL_AIRBAND_VERSION}.tar.gz /tmp/rtl-airband.tar.gz
RUN echo "${RTL_AIRBAND_SHA256}  /tmp/rtl-airband.tar.gz" | sha256sum --check \
    && apt-get update \
    && apt-get install -y --no-install-recommends cmake g++ make pkg-config libmp3lame-dev libshout3-dev libconfig++-dev libfftw3-dev librtlsdr-dev \
    && mkdir -p /tmp/RTLSDR-Airband-${RTL_AIRBAND_VERSION} \
    && tar xzf /tmp/rtl-airband.tar.gz --strip-components=1 -C /tmp/RTLSDR-Airband-${RTL_AIRBAND_VERSION} \
    && cmake -S /tmp/RTLSDR-Airband-${RTL_AIRBAND_VERSION} -B /tmp/RTLSDR-Airband-${RTL_AIRBAND_VERSION}/build -DPLATFORM=generic -DRTLSDR=ON -DMIRISDR=OFF -DSOAPYSDR=OFF -DPULSEAUDIO=OFF \
    && cmake --build /tmp/RTLSDR-Airband-${RTL_AIRBAND_VERSION}/build --parallel \
    && cmake --install /tmp/RTLSDR-Airband-${RTL_AIRBAND_VERSION}/build --prefix /opt/rtl-airband

FROM ${BUILD_FROM}

ARG DEBIAN_FRONTEND=noninteractive

ENV TZ=UTC \
    S6_CMD_WAIT_FOR_SERVICES_MAXTIME=90000 \
    BAIAMONTE_DASHBOARD_PORT=8099

ADD https://github.com/hassio-addons/bashio/archive/v0.15.0.tar.gz /tmp/bashio.tar.gz
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl jq python3 icecast2 libmp3lame0 libshout3 libconfig++9v5 libfftw3-double3 librtlsdr0 netcat-openbsd \
    && mkdir -p /tmp/bashio \
    && tar zxf /tmp/bashio.tar.gz --strip 1 -C /tmp/bashio \
    && mv /tmp/bashio/lib /usr/lib/bashio \
    && ln -s /usr/lib/bashio/bashio /usr/bin/bashio \
    && rm -rf /var/lib/apt/lists/* /tmp/bashio /tmp/bashio.tar.gz

ARG SENSORS_VERSION=1.1.2-1
ARG SENSORS_SHA256=2b8e660c304448972779011c3f15e37ba659403508c632bb498bcb41aeb4f75b
ADD https://github.com/plo53/adsb-hassio-sensors/archive/refs/tags/${SENSORS_VERSION}.tar.gz /tmp/adsb-sensors.tar.gz
RUN echo "${SENSORS_SHA256}  /tmp/adsb-sensors.tar.gz" | sha256sum --check \
    && tar xzf /tmp/adsb-sensors.tar.gz "adsb-hassio-sensors-${SENSORS_VERSION}/etc" "adsb-hassio-sensors-${SENSORS_VERSION}/usr" --strip-components=1 -C / \
    && rm /tmp/adsb-sensors.tar.gz

COPY export-env-from-config.sh /export-env-from-config.sh
RUN chmod +x /export-env-from-config.sh \
    && find /etc/s6-overlay/s6-rc.d/ -name script -exec sed -i '1 a\source /export-env-from-config.sh' {} \; \
    && find /etc/s6-overlay/s6-rc.d/ -name run -exec sed -i '1 a\source /export-env-from-config.sh' {} \;

COPY dashboard /opt/baiamonte/dashboard
COPY gps /opt/baiamonte/gps
COPY airband /opt/baiamonte/airband
COPY --from=airband-builder /opt/rtl-airband/bin/rtl_airband /usr/local/bin/rtl_airband
COPY rootfs /
RUN chmod +x /opt/baiamonte/airband/render_config.py \
    /etc/s6-overlay/s6-rc.d/baiamonte-dashboard/run \
    /etc/s6-overlay/s6-rc.d/baiamonte-gps/run \
    /etc/s6-overlay/s6-rc.d/baiamonte-icecast/run \
    /etc/s6-overlay/s6-rc.d/baiamonte-airband/run \
    && touch /etc/s6-overlay/s6-rc.d/user/contents.d/baiamonte-dashboard

LABEL io.hass.type="app" \
      io.hass.name="Baiamonte ADS-B" \
      io.hass.description="Tenuta Baiamonte airspace watch and multi-portal ADS-B feeder" \
      io.hass.url="https://github.com/drahamin/home-assistant-adsb"
