(() => {
  const TILE_SIZE = 256;
  const MIN_LATITUDE = -85.05112878;
  const MAX_LATITUDE = 85.05112878;
  const WEATHER_METADATA_URL = 'https://api.rainviewer.com/public/weather-maps.json';
  const WEATHER_CACHE_MS = 5 * 60 * 1000;
  let weatherMetadata = null;
  let weatherFetchedAt = 0;
  let weatherRequest = null;

  function worldPoint(latitude, longitude, zoom) {
    const latitudeClamped = Math.max(MIN_LATITUDE, Math.min(MAX_LATITUDE, latitude));
    const sine = Math.sin(latitudeClamped * Math.PI / 180);
    const scale = TILE_SIZE * 2 ** zoom;
    return {
      x: (longitude + 180) / 360 * scale,
      y: (0.5 - Math.log((1 + sine) / (1 - sine)) / (4 * Math.PI)) * scale,
    };
  }

  function geographicPoint(x, y, zoom) {
    const scale = TILE_SIZE * 2 ** zoom;
    const longitude = x / scale * 360 - 180;
    const mercator = Math.PI * (1 - 2 * y / scale);
    const latitude = Math.atan(Math.sinh(mercator)) * 180 / Math.PI;
    return {lat: latitude, lon: longitude};
  }

  function usablePoint(point) {
    return point && Number.isFinite(point.lat) && Number.isFinite(point.lon);
  }

  async function latestWeatherFrame() {
    if (weatherMetadata && Date.now() - weatherFetchedAt < WEATHER_CACHE_MS) return weatherMetadata;
    if (!weatherRequest) {
      weatherRequest = fetch(WEATHER_METADATA_URL, {cache: 'no-store'})
        .then(response => {
          if (!response.ok) throw new Error(`RainViewer metadata ${response.status}`);
          return response.json();
        })
        .then(payload => {
          const frames = payload?.radar?.past || [];
          const latest = frames[frames.length - 1];
          if (!payload.host || !latest?.path) throw new Error('RainViewer returned no radar frame');
          weatherFetchedAt = Date.now();
          weatherMetadata = {host: payload.host, ...latest};
          return weatherMetadata;
        })
        .finally(() => { weatherRequest = null; });
    }
    return weatherRequest;
  }

  class BaiamonteMap {
    constructor(container, options = {}) {
      this.container = container;
      this.interactive = Boolean(options.interactive);
      this.manualCenter = null;
      this.manualZoom = null;
      this.currentView = null;
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
        const action = event.target.closest('button')?.dataset.mapAction;
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
        this.dragStart = {
          x: event.clientX,
          y: event.clientY,
          world: worldPoint(this.currentView.center.lat, this.currentView.center.lon, this.currentView.zoom),
          zoom: this.currentView.zoom,
        };
      });
      this.container.addEventListener('pointermove', event => {
        if (!this.dragStart) return;
        const world = {
          x: this.dragStart.world.x - (event.clientX - this.dragStart.x),
          y: this.dragStart.world.y - (event.clientY - this.dragStart.y),
        };
        this.manualCenter = geographicPoint(world.x, world.y, this.dragStart.zoom);
        this.manualZoom = this.dragStart.zoom;
        this.notifyViewChange();
      });
      const stopDragging = () => {
        this.dragStart = null;
        this.container.classList.remove('dragging');
      };
      this.container.addEventListener('pointerup', stopDragging);
      this.container.addEventListener('pointercancel', stopDragging);
    }

    notifyViewChange() {
      if (this.viewChangePending) return;
      this.viewChangePending = true;
      requestAnimationFrame(() => {
        this.viewChangePending = false;
        this.container.dispatchEvent(new CustomEvent('baiamonte-map-change'));
      });
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

    render(center, points = []) {
      const width = this.container.clientWidth || 900;
      const height = this.container.clientHeight || 500;
      const safeCenter = usablePoint(center) ? center : {lat: 37.847, lon: 14.925};
      const automaticZoom = this.chooseZoom(safeCenter, points, width, height);
      const zoom = this.manualZoom ?? automaticZoom;
      const viewCenter = this.manualCenter ?? safeCenter;
      const centerWorld = worldPoint(viewCenter.lat, viewCenter.lon, zoom);
      const left = centerWorld.x - width / 2;
      const top = centerWorld.y - height / 2;
      const tileCount = 2 ** zoom;
      const minX = Math.floor(left / TILE_SIZE);
      const maxX = Math.floor((left + width) / TILE_SIZE);
      const minY = Math.max(0, Math.floor(top / TILE_SIZE));
      const maxY = Math.min(tileCount - 1, Math.floor((top + height) / TILE_SIZE));

      this.tiles.replaceChildren();
      for (let tileY = minY; tileY <= maxY; tileY += 1) {
        for (let tileX = minX; tileX <= maxX; tileX += 1) {
          const wrappedX = ((tileX % tileCount) + tileCount) % tileCount;
          const image = document.createElement('img');
          image.alt = '';
          image.draggable = false;
          image.src = `api/map-tile/${zoom}/${wrappedX}/${tileY}.png`;
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

    async render(view, configuration = {}) {
      if (!configuration.enabled) {
        this.setVisible(false);
        this.layer.replaceChildren();
        return;
      }
      this.status.hidden = false;
      this.status.textContent = 'Loading live rain radar…';
      try {
        const frame = await latestWeatherFrame();
        if (!configuration.enabled) return;
        const sourceZoom = Math.min(view.zoom, 7);
        const zoomScale = 2 ** (view.zoom - sourceZoom);
        const renderedTileSize = TILE_SIZE * zoomScale;
        const tileCount = 2 ** sourceZoom;
        const minX = Math.floor(view.left / renderedTileSize);
        const maxX = Math.floor((view.left + view.width) / renderedTileSize);
        const minY = Math.max(0, Math.floor(view.top / renderedTileSize));
        const maxY = Math.min(tileCount - 1, Math.floor((view.top + view.height) / renderedTileSize));
        const opacity = Math.max(0.1, Math.min(1, Number(configuration.opacity ?? 0.55)));
        const signature = [frame.path, sourceZoom, minX, maxX, minY, maxY,
          Math.round(view.left), Math.round(view.top), opacity].join(':');
        if (signature !== this.signature) {
          this.layer.replaceChildren();
          this.layer.style.opacity = opacity;
          for (let tileY = minY; tileY <= maxY; tileY += 1) {
            for (let tileX = minX; tileX <= maxX; tileX += 1) {
              const wrappedX = ((tileX % tileCount) + tileCount) % tileCount;
              const image = document.createElement('img');
              image.alt = '';
              image.draggable = false;
              image.src = `${frame.host}${frame.path}/256/${sourceZoom}/${wrappedX}/${tileY}/2/1_1.png`;
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
      } catch (error) {
        this.layer.hidden = true;
        this.attribution.hidden = true;
        this.status.hidden = false;
        this.status.textContent = 'Rain radar unavailable';
        console.error('Weather overlay unavailable', error);
      }
    }
  }

  window.BaiamonteMap = BaiamonteMap;
  window.BaiamonteWeatherMap = BaiamonteWeatherMap;
})();
