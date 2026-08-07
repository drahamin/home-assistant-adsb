#!/bin/bash

if [[ ! -f /data/options.json ]]; then
  echo "Baiamonte ADS-B: /data/options.json was not found" >&2
  return 1 2>/dev/null || exit 1
fi

supervisor_config=""
if [[ -n "${SUPERVISOR_TOKEN:-}" ]]; then
  supervisor_config=$(curl -sf --connect-timeout 3 --max-time 8 \
    -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    -H "Content-Type: application/json" \
    http://supervisor/core/api/config || true)
fi

latitude=$(jq -r '.latitude // empty' <<<"${supervisor_config:-{}}")
longitude=$(jq -r '.longitude // empty' <<<"${supervisor_config:-{}}")
elevation=$(jq -r '.elevation // empty' <<<"${supervisor_config:-{}}")

os_major=""
if [[ -n "${SUPERVISOR_TOKEN:-}" ]]; then
  os_major=$(curl -sf --connect-timeout 3 --max-time 8 \
    -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    http://supervisor/os/info | jq -r '.data.version // empty' | grep -oE '^[0-9]+' || true)
fi

jq_filter='to_entries | map("\(.key)=\(.value)\u0000")[]'
if [[ -n "${os_major}" && "${os_major}" -ge 16 ]]; then
  jq_filter='to_entries | map(select(.key != "SYSTEM_HTTP_ULIMIT_N" and .key != "SYSTEM_FR24FEED_ULIMIT_N")) | map("\(.key)=\(.value)\u0000")[]'
fi

while IFS= read -r -d '' line; do
  line=${line//HOMEASSISTANT_LATITUDE/${latitude}}
  line=${line//HOMEASSISTANT_LONGITUDE/${longitude}}
  line=${line//HOMEASSISTANT_ELEVATION/${elevation}}
  export "${line}"
done < <(jq -r "${jq_filter}" /data/options.json)
