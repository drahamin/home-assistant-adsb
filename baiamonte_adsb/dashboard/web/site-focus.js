(function(){
  var MIAMI_SOURCE='Rahamin Miami proxy',stored='';
  try{stored=localStorage.getItem('baiamonte-map-site')||''}catch(error){}
  var requested=stored==='miami'?'miami':'sicily';
  function isPositioned(item){return typeof item.lat==='number'&&typeof item.lon==='number'}
  function isMiami(item){return item.source===MIAMI_SOURCE}
  function selectedAircraft(aircraft,focus){return (aircraft||[]).filter(function(item){return focus==='miami'?isMiami(item):!isMiami(item)})}
  function effectiveFocus(aircraft){
    if(selectedAircraft(aircraft,requested).some(isPositioned))return requested;
    var alternate=requested==='miami'?'sicily':'miami';
    return selectedAircraft(aircraft,alternate).some(isPositioned)?alternate:requested;
  }
  function centerOf(aircraft,fallback){
    var points=aircraft.filter(isPositioned);
    if(!points.length)return fallback;
    var minLat=points[0].lat,maxLat=points[0].lat,minLon=points[0].lon,maxLon=points[0].lon;
    points.forEach(function(item){minLat=Math.min(minLat,item.lat);maxLat=Math.max(maxLat,item.lat);minLon=Math.min(minLon,item.lon);maxLon=Math.max(maxLon,item.lon)});
    return {lat:(minLat+maxLat)/2,lon:(minLon+maxLon)/2,alt:null,source:'Aircraft map focus'};
  }
  function addControls(map,onChange){
    var controls=document.createElement('div');
    controls.className='site-focus-controls';
    controls.innerHTML='<button type="button" data-site="sicily">Sicily</button><button type="button" data-site="miami">Miami</button>';
    controls.addEventListener('click',function(event){
      var button=event.target.closest('button');
      if(!button)return;
      requested=button.getAttribute('data-site');
      try{localStorage.setItem('baiamonte-map-site',requested)}catch(error){}
      onChange();
    });
    map.appendChild(controls);
    return controls;
  }
  function updateControls(controls,focus){Array.prototype.forEach.call(controls.querySelectorAll('button'),function(button){button.classList.toggle('active',button.getAttribute('data-site')===focus)})}

  var overview=document.querySelector('#radar-map');
  if(overview&&typeof renderMap==='function'){
    var overviewControls=addControls(overview,function(){if(typeof mapAircraft!=='undefined')renderMap(mapAircraft,mapLocation,mapWeather)});
    var originalRenderMap=renderMap;
    renderMap=function(aircraft,location,weather){
      var focus=effectiveFocus(aircraft||[]),selected=selectedAircraft(aircraft||[],focus);
      originalRenderMap(selected,focus==='miami'?centerOf(selected,location):location,weather);
      updateControls(overviewControls,focus);
      var label=overview.querySelector('.estate-map-marker b');
      if(label)label.textContent=focus==='miami'?'Rahamin ADS-B · Miami':'Tenuta Baiamonte';
    };
  }

  var tvMap=document.querySelector('#map');
  if(tvMap&&typeof render==='function'){
    var latestTvData=null;
    var tvControls=addControls(tvMap,function(){if(latestTvData)render(latestTvData)});
    var originalRender=render;
    render=function(data){
      latestTvData=data;
      var focus=effectiveFocus(data.aircraft||[]),selected=selectedAircraft(data.aircraft||[],focus);
      var copy=Object.assign({},data,{aircraft:selected,nearest_aircraft:selected.slice(0,10)});
      if(focus==='miami')copy.location=centerOf(selected,data.location||{});
      originalRender(copy);
      updateControls(tvControls,focus);
      var label=tvMap.querySelector('.estate-marker b');
      if(label)label.textContent=focus==='miami'?'Rahamin ADS-B · Miami':'Tenuta Baiamonte';
    };
  }
})();
