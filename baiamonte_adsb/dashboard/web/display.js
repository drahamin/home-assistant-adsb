const $=selector=>document.querySelector(selector);
const $$=selector=>[...document.querySelectorAll(selector)];
const fmt=value=>value===null||value===undefined?'—':Math.round(value).toLocaleString();
const flagFor=code=>code&&code.length===2?[...code].map(character=>String.fromCodePoint(127397+character.charCodeAt())).join(''):'✈';
const geoMap=new BaiamonteMap($('#map'));
const weatherMap=new BaiamonteWeatherMap(geoMap);
let latest=null;

function flightRow(item){
  const distance=typeof item.distance_km==='number'?`${item.distance_km.toFixed(1)} km`:'Distance unavailable';
  const identity=[item.registration,item.aircraft_type,item.operator].filter(Boolean).join(' · ')||`ICAO ${String(item.hex||'').toUpperCase()}`;
  const row=document.createElement('article');
  row.className='flight-row';
  const flag=document.createElement('span');
  flag.className='flag';
  flag.textContent=flagFor(item.country_code);
  const main=document.createElement('div');
  main.className='flight-main';
  const title=document.createElement('div');
  title.className='flight-title';
  const name=document.createElement('h2');
  name.textContent=item.flight||String(item.hex||'Unknown').toUpperCase();
  const altitude=document.createElement('strong');
  altitude.textContent=`${fmt(item.altitude)} ft`;
  title.append(name,altitude);
  const meta=document.createElement('div');
  meta.className='flight-meta';
  for(const text of [distance,`${fmt(item.speed)} kt`,`${fmt(item.track)}°`]){const span=document.createElement('span');span.textContent=text;meta.appendChild(span)}
  const detail=document.createElement('div');
  detail.className='flight-detail';
  const identityNode=document.createElement('span');identityNode.textContent=identity;
  const source=document.createElement('em');source.textContent='ADS-B contact';
  detail.append(identityNode,source);
  main.append(title,meta,detail);
  row.append(flag,main);
  return row;
}

function addEstateMarker(view,location){
  const point=view.project(location.lat,location.lon);
  const marker=document.createElement('div');
  marker.className='estate-marker';
  marker.style.left=`${point.x}px`;
  marker.style.top=`${point.y}px`;
  marker.innerHTML='<span>◆</span><b>Tenuta Baiamonte</b>';
  $('#map').appendChild(marker);
}

function addAircraftMarker(view,item){
  const point=view.project(item.lat,item.lon),map=$('#map');
  if(point.x<0||point.y<0||point.x>map.clientWidth||point.y>map.clientHeight)return;
  const marker=document.createElement('div');
  marker.className='plane';
  marker.style.left=`${point.x}px`;
  marker.style.top=`${point.y}px`;
  marker.innerHTML=`<span class="plane-icon"><i style="--track:${Number(item.track)||0}deg">▲</i></span><span class="plane-label"></span>`;
  marker.querySelector('.plane-label').textContent=item.flight||String(item.hex||'Unknown').toUpperCase();
  map.appendChild(marker);
}

function render(data){
  latest=data;
  const all=data.aircraft||[];
  const positioned=all.filter(item=>typeof item.lat==='number'&&typeof item.lon==='number');
  const contacts=data.nearest_aircraft?.length?data.nearest_aircraft:all;
  const location=data.location||{};
  const center={lat:typeof location.lat==='number'?location.lat:(positioned[0]?.lat??37.847),lon:typeof location.lon==='number'?location.lon:(positioned[0]?.lon??14.925)};
  const view=geoMap.render(center,positioned,data.map_style||'standard');
  weatherMap.render(view,data.weather);
  $$('.plane,.estate-marker').forEach(node=>node.remove());
  addEstateMarker(view,center);
  positioned.forEach(item=>addAircraftMarker(view,item));
  $('#empty').classList.toggle('show',positioned.length===0);
  $('#fleet-count').textContent=positioned.length;
  const list=$('#flight-list');
  list.replaceChildren();
  if(contacts.length)contacts.slice(0,10).forEach(item=>list.appendChild(flightRow(item)));
  else{const empty=document.createElement('div');empty.className='list-empty';empty.textContent='No positioned aircraft in range';list.appendChild(empty)}
  $('#feed-light').classList.toggle('online',Boolean(data.receiver_online));
  $('#feed-status').textContent=data.receiver_online?`Local ADS-B live · ${new Date(data.generated_at*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}`:'Estate receiver starting';
}

async function refresh(){
  try{
    const response=await fetch('api/aircraft',{cache:'no-store'});
    if(!response.ok)throw new Error(response.status);
    render(await response.json());
  }catch(error){$('#feed-status').textContent='ADS-B feed unavailable';$('#empty').classList.add('show');console.error(error)}
}

let resizeTimer;
addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>latest&&render(latest),150)});
refresh();
setInterval(refresh,5000);
