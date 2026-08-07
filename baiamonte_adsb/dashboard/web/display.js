const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const fmt = value => value === null || value === undefined ? '—' : Math.round(value).toLocaleString();
const flagFor = code => code && code.length === 2
  ? [...code].map(character => String.fromCodePoint(127397 + character.charCodeAt())).join('')
  : '✈';
const geoMap = new BaiamonteMap($('#map'));
const weatherMap = new BaiamonteWeatherMap(geoMap);

$('#display-back').onclick = () => {
  if (history.length > 1) history.back();
  else location.href = './';
};

function renderFlightBoard(aircraft) {
  const list = $('#flight-list');
  const contacts = aircraft.slice(0, 10);
  $('#board-count').textContent = aircraft.length;
  list.replaceChildren();
  if (!contacts.length) {
    const empty = document.createElement('div');
    empty.className = 'flight-empty';
    empty.textContent = 'Waiting for the first aircraft contact';
    list.appendChild(empty);
    return;
  }
  contacts.forEach(item => {
    const row = document.createElement('div');
    row.className = 'flight-row';
    const flag = document.createElement('span');
    flag.className = 'flight-flag';
    flag.textContent = flagFor(item.country_code);
    const copy = document.createElement('span');
    copy.className = 'flight-copy';
    const name = document.createElement('b');
    name.textContent = item.flight || String(item.hex || 'Unknown').toUpperCase();
    const identity = document.createElement('small');
    identity.textContent = [item.registration, item.aircraft_type, item.operator].filter(Boolean).join(' · ')
      || `ICAO ${String(item.hex || '').toUpperCase()}`;
    copy.append(name, identity);
    const metrics = document.createElement('span');
    metrics.className = 'flight-metrics';
    const altitude = document.createElement('b');
    altitude.textContent = `${fmt(item.altitude)} ft`;
    const distance = typeof item.distance_km === 'number' ? `${item.distance_km.toFixed(1)} km · ` : '';
    const motion = document.createElement('small');
    motion.textContent = `${distance}${fmt(item.speed)} kt · ${fmt(item.track)}°`;
    metrics.append(altitude, motion);
    row.append(flag, copy, metrics);
    list.appendChild(row);
  });
}

function addEstateMarker(view, location) {
  const point = view.project(location.lat, location.lon);
  const estate = $('#estate');
  estate.style.left = `${point.x}px`;
  estate.style.top = `${point.y}px`;
}

function addAircraftMarker(view, item) {
  const map = $('#map');
  const point = view.project(item.lat, item.lon);
  if (point.x < 0 || point.y < 0 || point.x > map.clientWidth || point.y > map.clientHeight) return;
  const node = document.createElement('div');
  node.className = 'plane';
  node.style.left = `${point.x}px`;
  node.style.top = `${point.y}px`;
  const icon = document.createElement('span');
  icon.className = 'plane-icon';
  const arrow = document.createElement('i');
  arrow.textContent = '▲';
  arrow.style.setProperty('--track', `${Number(item.track) || 0}deg`);
  icon.appendChild(arrow);
  const label = document.createElement('span');
  label.className = 'plane-label';
  const name = document.createElement('b');
  name.textContent = item.flight || String(item.hex || 'Unknown').toUpperCase();
  const detail = document.createElement('small');
  detail.textContent = `${fmt(item.altitude)} ft · ${fmt(item.speed)} kt`;
  label.append(name, detail);
  node.append(icon, label);
  map.appendChild(node);
}

function render(data) {
  const allAircraft = data.aircraft || [];
  const planes = allAircraft.filter(item => typeof item.lat === 'number' && typeof item.lon === 'number');
  const location = data.location || {};
  const center = {
    lat: typeof location.lat === 'number' ? location.lat : (planes[0]?.lat ?? 37.847),
    lon: typeof location.lon === 'number' ? location.lon : (planes[0]?.lon ?? 14.925),
  };

  $('#aircraft-count').textContent = data.counts.aircraft;
  $('#positioned-count').textContent = data.counts.positioned;
  $('#receiver-state').textContent = data.receiver_online ? 'Online' : 'Starting';
  $('#receiver-light').classList.toggle('online', data.receiver_online);
  $('#empty').classList.toggle('hidden', planes.length > 0);
  renderFlightBoard(data.nearest_aircraft?.length ? data.nearest_aircraft : allAircraft);

  $$('.plane').forEach(node => node.remove());
  const view = geoMap.render(center, planes, data.map_style || 'standard');
  weatherMap.render(view, data.weather);
  addEstateMarker(view, center);
  planes.forEach(item => addAircraftMarker(view, item));

  $('#location').textContent = typeof location.lat === 'number' && typeof location.lon === 'number'
    ? `${location.lat.toFixed(4)}, ${location.lon.toFixed(4)} · ${fmt(location.alt)} m MSL · ${location.source || 'Configured location'}`
    : 'Mount Etna · Sicily';
  $('#updated').textContent = `Updated ${new Date(data.generated_at * 1000).toLocaleTimeString([], {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })}`;
}

async function refresh() {
  try {
    const response = await fetch('api/aircraft', {cache: 'no-store'});
    if (!response.ok) throw new Error(response.status);
    render(await response.json());
  } catch (error) {
    $('#receiver-state').textContent = 'Unavailable';
    console.error('Aircraft feed unavailable', error);
  }
}

refresh();
setInterval(refresh, 5000);
