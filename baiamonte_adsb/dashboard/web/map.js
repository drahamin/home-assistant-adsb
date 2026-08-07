(() => {
  const TILE_SIZE = 256;
  const MIN_LATITUDE = -85.05112878;
  const MAX_LATITUDE = 85.05112878;

  function worldPoint(latitude, longitude, zoom) {
    const latitudeClamped = Math.max(MIN_LATITUDE, Math.min(MAX_LATITUDE, latitude));
    const sine = Math.sin(latitudeClamped * Math.PI / 180);
    const scale = TILE_SIZE * 2 ** zoom;
    return {
      x: (longitude + 180) / 360 * scale,
      y: (0.5 - Math.log((1 + sine) / (1 - sine)) / (4 * Math.PI)) * scale,
    };
  }

  function usablePoint(point) {
    return point && Number.isFinite(point.lat) && Number.isFinite(point.lon);
  }

  class BaiamonteMap {
    constructor(container) {
      this.container = container;
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
      const zoom = this.chooseZoom(safeCenter, points, width, height);
      const centerWorld = worldPoint(safeCenter.lat, safeCenter.lon, zoom);
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
          image.src = `https://tile.openstreetmap.org/${zoom}/${wrappedX}/${tileY}.png`;
          image.style.left = `${tileX * TILE_SIZE - left}px`;
          image.style.top = `${tileY * TILE_SIZE - top}px`;
          this.tiles.appendChild(image);
        }
      }

      return {
        zoom,
        project: (latitude, longitude) => {
          const projected = worldPoint(latitude, longitude, zoom);
          return {x: projected.x - left, y: projected.y - top};
        },
      };
    }
  }

  window.BaiamonteMap = BaiamonteMap;
})();
