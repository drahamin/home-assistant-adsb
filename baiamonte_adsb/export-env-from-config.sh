#!/bin/bash

options_file="${BAIAMONTE_OPTIONS_FILE:-/data/options.json}"

if [[ ! -f "${options_file}" ]]; then
  echo "Baiamonte ADS-B: ${options_file} was not found" >&2
  return 1 2>/dev/null || exit 1
fi

supervisor_config='{}'
if [[ -n "${SUPERVISOR_TOKEN:-}" ]]; then
  supervisor_response=$(curl -sf --connect-timeout 3 --max-time 8 \
    -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    -H "Content-Type: application/json" \
    http://supervisor/core/api/config || true)
  if jq -e . >/dev/null 2>&1 <<<"${supervisor_response}"; then
    supervisor_config="${supervisor_response}"
  fi
fi

latitude=$(jq -r '.latitude // empty' <<<"${supervisor_config}")
longitude=$(jq -r '.longitude // empty' <<<"${supervisor_config}")
elevation=$(jq -r '.elevation // empty' <<<"${supervisor_config}")

gps_enabled=$(jq -r '.GPS_USE_USB // false' "${options_file}")
gps_file="${BAIAMONTE_GPS_JSON:-/run/baiamonte/gps.json}"
if [[ "${gps_enabled}" == "true" ]]; then
  gps_timeout=$(jq -r '.GPS_FIX_TIMEOUT // 30' "${options_file}")
  gps_waited=0
  while [[ ! -s "${gps_file}" && "${gps_waited}" -lt "${gps_timeout}" ]]; do
    sleep 1
    gps_waited=$((gps_waited + 1))
  done
  if [[ -s "${gps_file}" ]] && jq -e '.lat | numbers' "${gps_file}" >/dev/null 2>&1 \
    && jq -e '.lon | numbers' "${gps_file}" >/dev/null 2>&1; then
    latitude=$(jq -r '.lat' "${gps_file}")
    longitude=$(jq -r '.lon' "${gps_file}")
    gps_elevation=$(jq -r '.alt // empty' "${gps_file}")
    if [[ -n "${gps_elevation}" ]]; then
      elevation="${gps_elevation}"
    fi
  fi
fi

os_major=""
if [[ -n "${SUPERVISOR_TOKEN:-}" ]]; then
  os_major=$(curl -sf --connect-timeout 3 --max-time 8 \
    -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    http://supervisor/os/info | jq -r '.data.version // empty' | grep -oE '^[0-9]+' || true)
fi

jq_filter='to_entries[] | "\(.key)=\(.value)\u0000"'
if [[ -n "${os_major}" && "${os_major}" -ge 16 ]]; then
  jq_filter='to_entries[] | select(.key != "SYSTEM_HTTP_ULIMIT_N" and .key != "SYSTEM_FR24FEED_ULIMIT_N") | "\(.key)=\(.value)\u0000"'
fi

while IFS= read -r -d '' line; do
  line=${line//HOMEASSISTANT_LATITUDE/${latitude}}
  line=${line//HOMEASSISTANT_LONGITUDE/${longitude}}
  line=${line//HOMEASSISTANT_ELEVATION/${elevation}}
  export "${line}"
done < <(jq -j "${jq_filter}" "${options_file}")
