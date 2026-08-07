ARG BUILD_FROM=thomx/fr24feed-piaware:2.6.1
FROM ${BUILD_FROM}

ENV TZ=UTC \
    S6_CMD_WAIT_FOR_SERVICES_MAXTIME=30000 \
    BAIAMONTE_DASHBOARD_PORT=8099

ADD https://github.com/hassio-addons/bashio/archive/v0.15.0.tar.gz /tmp/bashio.tar.gz
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl jq python3 \
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
COPY rootfs /
RUN chmod +x /etc/s6-overlay/s6-rc.d/baiamonte-dashboard/run \
    && touch /etc/s6-overlay/s6-rc.d/user/contents.d/baiamonte-dashboard

LABEL io.hass.type="app" \
      io.hass.name="Baiamonte ADS-B" \
      io.hass.description="Tenuta Baiamonte airspace watch and multi-portal ADS-B feeder" \
      io.hass.url="https://github.com/drahamin/home-assistant-adsb"
