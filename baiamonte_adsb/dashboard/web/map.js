(() => {
  // Samsung Tizen 2017 browsers use Chromium 47, before the DOM convenience
  // methods used by newer browsers were added.
  if (!Element.prototype.append) Element.prototype.append = function() {
    for (let index = 0; index < arguments.length; index += 1) this.appendChild(arguments[index]);
  };
  if (!Element.prototype.prepend) Element.prototype.prepend = function(node) {
    this.insertBefore(node, this.firstChild);
  };
  if (!Element.prototype.after) Element.prototype.after = function(node) {
    if (this.parentNode) this.parentNode.insertBefore(node, this.nextSibling);
  };
  const TILE_SIZE = 256;
  const MIN_LATITUDE = -85.05112878;
  const MAX_LATITUDE = 85.05112878;
  const WEATHER_METADATA_URL = 'api/weather-maps';
  const WEATHER_CACHE_MS = 5 * 60 * 1000;
  const AIRCRAFT_ICON = '<svg class="aircraft-shape" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2c-.8 0-1.2.8-1.4 1.6L9.4 9 3 13v2l6.2-1.7-.4 5.1-2.4 1.8v1.5l5.6-1.2 5.6 1.2v-1.5l-2.4-1.8-.4-5.1L21 15v-2l-6.4-4-1.2-5.4C13.2 2.8 12.8 2 12 2z"/></svg>';
  const ALTITUDE_BANDS = [
    {maximum: 0, color: '#9b948a', short: 'GND', label: 'Ground'},
    {maximum: 10000, color: '#58b87a', short: '<10k', label: 'Below 10,000 ft'},
    {maximum: 20000, color: '#d4af37', short: '10–20k', label: '10,000–19,999 ft'},
    {maximum: 30000, color: '#e28a45', short: '20–30k', label: '20,000–29,999 ft'},
    {maximum: 40000, color: '#d65d73', short: '30–40k', label: '30,000–39,999 ft'},
    {maximum: Infinity, color: '#9873d1', short: '40k+', label: '40,000 ft and above'},
  ];
  let weatherMetadata = null;
  let weatherFetchedAt = 0;
  let weatherRequest = null;

  function worldPoint(latitude, longitude, zoom) {
    const latitudeClamped = Math.max(MIN_LATITUDE, Math.min(MAX_LATITUDE, latitude));
    const sine = Math.sin(latitudeClamped * Math.PI / 180);
    const scale = TILE_SIZE * Math.pow(2, zoom);
    return {
      x: (longitude + 180) / 360 * scale,
      y: (0.5 - Math.log((1 + sine) / (1 - sine)) / (4 * Math.PI)) * scale,
    };
  }

  function geographicPoint(x, y, zoom) {
    const scale = TILE_SIZE * Math.pow(2, zoom);
    const longitude = x / scale * 360 - 180;
    const mercator = Math.PI * (1 - 2 * y / scale);
    const latitude = Math.atan(Math.sinh(mercator)) * 180 / Math.PI;
    return {lat: latitude, lon: longitude};
  }

  function usablePoint(point) {
    return point && Number.isFinite(point.lat) && Number.isFinite(point.lon);
  }

  function altitudeBand(altitude) {
    const value = Number(altitude);
    if (!Number.isFinite(value)) return {color: '#d4af37', short: 'N/A', label: 'Altitude unavailable'};
    return ALTITUDE_BANDS.find(band => value <= band.maximum);
  }

  function applyAircraftVisual(node, altitude, track) {
    const band = altitudeBand(altitude);
    node.style.setProperty('--aircraft-color', band.color);
    node.style.setProperty('--track', `${Number(track) || 0}deg`);
    node.dataset.altitudeBand = band.short;
    return band;
  }

  function latestWeatherFrame() {
    // Keep one return type for both a fresh request and a cached frame. Map
    // redraws always chain this value with .then(); returning the cached object
    // directly used to abort every pan/zoom after weather had loaded once.
    if (weatherMetadata && Date.now() - weatherFetchedAt < WEATHER_CACHE_MS) return Promise.resolve(weatherMetadata);
    if (!weatherRequest) {
      weatherRequest = fetch(WEATHER_METADATA_URL, {cache: 'no-store'})
        .then(response => {
          if (!response.ok) throw new Error(`RainViewer metadata ${response.status}`);
          return response.json();
        })
        .then(payload => {
          const frames = payload && payload.radar && payload.radar.past || [];
          const latest = frames[frames.length - 1];
          if (!payload.host || !latest || !latest.path) throw new Error('RainViewer returned no radar frame');
          weatherFetchedAt = Date.now();
          weatherMetadata = Object.assign({host: payload.host}, latest);
          return weatherMetadata;
        })
        .then(payload => { weatherRequest = null; return payload; }, error => { weatherRequest = null; throw error; });
    }
    return weatherRequest;
  }

  class BaiamonteMap {
    constructor(container, options = {}) {
      this.container = container;
      this.interactive = Boolean(options.interactive);
      this.initialZoomDelta = Number.isFinite(Number(options.initialZoomDelta)) ? Math.max(-6, Math.min(20, Number(options.initialZoomDelta))) : 0;
      this.manualCenter = null;
      this.manualZoom = null;
      this.currentView = null;
      this.pointers = {};
      this.pinchDistance = 0;
      this.tiles = container.querySelector('.geo-tiles') || document.createElement('div');
      this.tiles.className = 'geo-tiles';
      if (!this.tiles.parentNode) container.prepend(this.tiles);
      this.attribution = container.querySelector('.map-attribution') || document.createElement('a');
      this.attribution.className = 'map-attribution';
      this.attribution.href = 'https://www.openstreetmap.org/copyright';
      this.attribution.target = '_blank';
      this.attribution.rel = 'noopener';
      this.attribution.textContent = '© OpenStreetMap';
      if (!this.attribution.parentNode) container.append(this.attribution);
      this.altitudeLegend = container.querySelector('.altitude-legend') || document.createElement('div');
      this.altitudeLegend.className = 'altitude-legend';
      this.altitudeLegend.setAttribute('aria-label', 'Aircraft altitude color scale');
      this.altitudeLegend.innerHTML = '<b>ALTITUDE</b>' + ALTITUDE_BANDS.map(band => `<span title="${band.label}"><i style="--legend-color:${band.color}"></i>${band.short}</span>`).join('');
      if (!this.altitudeLegend.parentNode) container.append(this.altitudeLegend);
      if (this.interactive) this.enableInteraction();
    }

    enableInteraction() {
      this.container.classList.add('interactive-map');
      this.controls = document.createElement('div');
      this.controls.className = 'map-controls';
      this.controls.innerHTML = '<button type="button" data-map-action="in" aria-label="Zoom in">+</button><button type="button" data-map-action="out" aria-label="Zoom out">−</button><button type="button" data-map-action="reset">Reset</button>';
      this.hint = document.createElement('div');
      this.hint.className = 'map-interaction-hint';
      this.hint.textContent = 'Drag to move · Scroll or + / − to zoom';
      this.container.append(this.controls, this.hint);
      this.controls.addEventListener('click', event => {
        const button = event.target.closest('button');
        const action = button ? button.dataset.mapAction : null;
        if (!action || !this.currentView) return;
        if (action === 'reset') {
          this.manualCenter = null;
          this.manualZoom = null;
        } else {
          this.manualCenter = this.currentView.center;
          const change = action === 'in' ? 1 : -1;
          this.manualZoom = Math.max(5, Math.min(12, this.currentView.zoom + change));
        }
        this.notifyViewChange();
      });
      this.container.addEventListener('wheel', event => {
        if (!this.currentView) return;
        event.preventDefault();
        this.manualCenter = this.currentView.center;
        const change = event.deltaY < 0 ? 1 : -1;
        this.manualZoom = Math.max(5, Math.min(12, this.currentView.zoom + change));
        this.notifyViewChange();
      }, {passive: false});
      this.container.addEventListener('pointerdown', event => {
        if (!this.currentView || event.target.closest('button,a')) return;
        this.container.setPointerCapture(event.pointerId);
        this.container.classList.add('dragging');
        this.pointers[event.pointerId] = {x: event.clientX, y: event.clientY};
        this.dragStart = {
          x: event.clientX,
          y: event.clientY,
          world: worldPoint(this.currentView.center.lat, this.currentView.center.lon, this.currentView.zoom),
          zoom: this.currentView.zoom,
        };
        const points = Object.keys(this.pointers).map(key => this.pointers[key]);
        if (points.length === 2) this.pinchDistance = Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y);
      });
      this.container.addEventListener('pointermove', event => {
        if (!this.pointers[event.pointerId] || !this.dragStart) return;
        this.pointers[event.pointerId] = {x: event.clientX, y: event.clientY};
        const points = Object.keys(this.pointers).map(key => this.pointers[key]);
        if (points.length === 2) {
          const distance = Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y);
          if (this.pinchDistance && Math.abs(distance - this.pinchDistance) > 32) {
            this.manualCenter = this.currentView.center;
            this.manualZoom = Math.max(5, Math.min(12, this.currentView.zoom + (distance > this.pinchDistance ? 1 : -1)));
            this.pinchDistance = distance;
            this.notifyViewChange();
          }
          return;
        }
        const world = {
          x: this.dragStart.world.x - (event.clientX - this.dragStart.x),
          y: this.dragStart.world.y - (event.clientY - this.dragStart.y),
        };
        this.manualCenter = geographicPoint(world.x, world.y, this.dragStart.zoom);
        this.manualZoom = this.dragStart.zoom;
        this.notifyViewChange();
      });
      const stopDragging = event => {
        delete this.pointers[event.pointerId];
        this.pinchDistance = 0;
        this.dragStart = null;
        if (!Object.keys(this.pointers).length) this.container.classList.remove('dragging');
      };
      this.container.addEventListener('pointerup', stopDragging);
      this.container.addEventListener('pointercancel', stopDragging);
      this.container.addEventListener('touchstart', event => {
        if (!this.currentView) return;
        const touches = event.touches;
        if (touches.length === 1) {
          this.touchStart = {x: touches[0].clientX, y: touches[0].clientY,
            world: worldPoint(this.currentView.center.lat, this.currentView.center.lon, this.currentView.zoom), zoom: this.currentView.zoom};
        } else if (touches.length === 2) {
          this.touchDistance = Math.hypot(touches[0].clientX - touches[1].clientX, touches[0].clientY - touches[1].clientY);
        }
      }, false);
      this.container.addEventListener('touchmove', event => {
        if (!this.currentView) return;
        event.preventDefault();
        const touches = event.touches;
        if (touches.length === 2) {
          const distance = Math.hypot(touches[0].clientX - touches[1].clientX, touches[0].clientY - touches[1].clientY);
          if (this.touchDistance && Math.abs(distance - this.touchDistance) > 32) {
            this.manualCenter = this.currentView.center;
            this.manualZoom = Math.max(5, Math.min(12, this.currentView.zoom + (distance > this.touchDistance ? 1 : -1)));
            this.touchDistance = distance;
            this.notifyViewChange();
          }
        } else if (touches.length === 1 && this.touchStart) {
          const world = {x: this.touchStart.world.x - (touches[0].clientX - this.touchStart.x), y: this.touchStart.world.y - (touches[0].clientY - this.touchStart.y)};
          this.manualCenter = geographicPoint(world.x, world.y, this.touchStart.zoom);
          this.manualZoom = this.touchStart.zoom;
          this.notifyViewChange();
        }
      }, false);
      this.container.addEventListener('touchend', () => { this.touchStart = null; this.touchDistance = 0; }, false);
    }

    notifyViewChange() {
      if (this.viewChangePending) return;
      this.viewChangePending = true;
      requestAnimationFrame(() => {
        this.viewChangePending = false;
        this.container.dispatchEvent(new CustomEvent('baiamonte-map-change'));
      });
    }

    resetView() {
      this.manualCenter = null;
      this.manualZoom = null;
    }

    chooseZoom(center, points, width, height) {
      const positions = [center, ...points].filter(usablePoint);
      if (positions.length < 2) return 10;
      for (let zoom = 12; zoom >= 5; zoom -= 1) {
        const origin = worldPoint(center.lat, center.lon, zoom);
        const fits = positions.every(position => {
          const projected = worldPoint(position.lat, position.lon, zoom);
          return Math.abs(projected.x - origin.x) <= Math.max(100, width / 2 - 90)
            && Math.abs(projected.y - origin.y) <= Math.max(80, height / 2 - 75);
        });
        if (fits) return zoom;
      }
      return 5;
    }

    render(center, points = [], style = 'standard') {
      const width = this.container.clientWidth || 900;
      const height = this.container.clientHeight || 500;
      const safeCenter = usablePoint(center) ? center : {lat: 37.847, lon: 14.925};
      const automaticZoom = this.chooseZoom(safeCenter, points, width, height);
      const zoom = this.manualZoom === null ? Math.max(5, Math.min(18, automaticZoom + this.initialZoomDelta)) : this.manualZoom;
      const viewCenter = this.manualCenter === null ? safeCenter : this.manualCenter;
      const centerWorld = worldPoint(viewCenter.lat, viewCenter.lon, zoom);
      const left = centerWorld.x - width / 2;
      const top = centerWorld.y - height / 2;
      const tileCount = Math.pow(2, zoom);
      const minX = Math.floor(left / TILE_SIZE);
      const maxX = Math.floor((left + width) / TILE_SIZE);
      const minY = Math.max(0, Math.floor(top / TILE_SIZE));
      const maxY = Math.min(tileCount - 1, Math.floor((top + height) / TILE_SIZE));
      const safeStyle = ['standard', 'humanitarian', 'topographic', 'dark', 'satellite'].includes(style) ? style : 'standard';
      this.tiles.dataset.style = safeStyle;

      this.tiles.innerHTML = '';
      for (let tileY = minY; tileY <= maxY; tileY += 1) {
        for (let tileX = minX; tileX <= maxX; tileX += 1) {
          const wrappedX = ((tileX % tileCount) + tileCount) % tileCount;
          const image = document.createElement('img');
          image.alt = '';
          image.draggable = false;
          image.src = `api/map-tile/${safeStyle}/${zoom}/${wrappedX}/${tileY}.png`;
          image.style.left = `${tileX * TILE_SIZE - left}px`;
          image.style.top = `${tileY * TILE_SIZE - top}px`;
          this.tiles.appendChild(image);
        }
      }

      this.currentView = {
        zoom,
        center: viewCenter,
        left,
        top,
        width,
        height,
        project: (latitude, longitude) => {
          const projected = worldPoint(latitude, longitude, zoom);
          return {x: projected.x - left, y: projected.y - top};
        },
      };
      return this.currentView;
    }
  }

  class BaiamonteWeatherMap {
    constructor(map) {
      this.map = map;
      this.container = map.container;
      this.layer = this.container.querySelector('.weather-tiles') || document.createElement('div');
      this.layer.className = 'weather-tiles';
      if (!this.layer.parentNode) map.tiles.after(this.layer);
      this.status = this.container.querySelector('.weather-status') || document.createElement('div');
      this.status.className = 'weather-status';
      if (!this.status.parentNode) this.container.append(this.status);
      this.attribution = this.container.querySelector('.weather-attribution') || document.createElement('a');
      this.attribution.className = 'weather-attribution';
      this.attribution.href = 'https://www.rainviewer.com/';
      this.attribution.target = '_blank';
      this.attribution.rel = 'noopener';
      this.attribution.textContent = 'Weather radar · RainViewer';
      if (!this.attribution.parentNode) this.container.append(this.attribution);
      this.signature = '';
      this.setVisible(false);
    }

    setVisible(visible) {
      this.layer.hidden = !visible;
      this.status.hidden = !visible;
      this.attribution.hidden = !visible;
      if (!visible) this.signature = '';
    }

    render(view, configuration = {}) {
      if (!configuration.enabled) {
        this.setVisible(false);
        this.layer.innerHTML = '';
        return;
      }
      this.status.hidden = false;
      this.status.textContent = 'Loading live rain radar…';
      return latestWeatherFrame().then(frame => {
        if (!configuration.enabled) return;
        const sourceZoom = Math.min(view.zoom, 7);
        const zoomScale = Math.pow(2, view.zoom - sourceZoom);
        const renderedTileSize = TILE_SIZE * zoomScale;
        const tileCount = Math.pow(2, sourceZoom);
        const minX = Math.floor(view.left / renderedTileSize);
        const maxX = Math.floor((view.left + view.width) / renderedTileSize);
        const minY = Math.max(0, Math.floor(view.top / renderedTileSize));
        const maxY = Math.min(tileCount - 1, Math.floor((view.top + view.height) / renderedTileSize));
        const opacity = Math.max(0.1, Math.min(1, Number(configuration.opacity === null || configuration.opacity === undefined ? 0.55 : configuration.opacity)));
        const signature = [frame.path, sourceZoom, minX, maxX, minY, maxY,
          Math.round(view.left), Math.round(view.top), opacity].join(':');
        if (signature !== this.signature) {
          this.layer.innerHTML = '';
          this.layer.style.opacity = opacity;
          for (let tileY = minY; tileY <= maxY; tileY += 1) {
            for (let tileX = minX; tileX <= maxX; tileX += 1) {
              const wrappedX = ((tileX % tileCount) + tileCount) % tileCount;
              const image = document.createElement('img');
              image.alt = '';
              image.draggable = false;
              image.src = `api/weather-tile${frame.path}/256/${sourceZoom}/${wrappedX}/${tileY}/2/1_1.png`;
              image.style.left = `${tileX * renderedTileSize - view.left}px`;
              image.style.top = `${tileY * renderedTileSize - view.top}px`;
              image.style.width = `${renderedTileSize}px`;
              image.style.height = `${renderedTileSize}px`;
              this.layer.appendChild(image);
            }
          }
          this.signature = signature;
        }
        this.setVisible(true);
        const timestamp = new Date(frame.time * 1000).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
        this.status.textContent = `LIVE RAIN · ${timestamp}`;
      }).catch(error => {
        this.layer.hidden = true;
        this.attribution.hidden = true;
        this.status.hidden = false;
        this.status.textContent = 'Rain radar unavailable';
        console.error('Weather overlay unavailable', error);
      });
    }
  }

  window.BaiamonteMap = BaiamonteMap;
  window.BaiamonteWeatherMap = BaiamonteWeatherMap;
  window.BaiamonteAircraftVisual = {icon: AIRCRAFT_ICON, altitudeBand, apply: applyAircraftVisual};
})();
