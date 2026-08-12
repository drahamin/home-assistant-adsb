(function(){
  var player=document.querySelector('#vhf-player');
  if(!player)return;
  var source=player.querySelector('source');
  var endpoint=(source&&source.getAttribute('src'))||'api/airband-stream';
  var start=document.querySelector('#vhf-start');
  var stop=document.querySelector('#vhf-stop');
  var state=document.querySelector('#vhf-listener-state');
  var disconnecting=false;

  function setState(message,connected){
    if(state)state.textContent=message;
    if(stop)stop.disabled=!connected;
    if(start)start.disabled=player.disabled||connected;
  }
  function disconnect(message){
    disconnecting=true;
    try{player.pause()}catch(error){}
    player.removeAttribute('src');
    if(source)source.removeAttribute('src');
    player.load();
    setState(message||'Disconnected',false);
    setTimeout(function(){disconnecting=false},0);
  }
  function connect(){
    if(player.disabled)return;
    disconnecting=true;
    if(source)source.setAttribute('src',endpoint);else player.setAttribute('src',endpoint);
    player.load();
    var playing=player.play();
    if(playing&&typeof playing.catch==='function')playing.catch(function(){setState('Press start to listen',false)});
    setTimeout(function(){disconnecting=false},0);
  }

  if(start)start.addEventListener('click',connect);
  if(stop)stop.addEventListener('click',function(){disconnect('Disconnected · stream closed')});
  player.addEventListener('playing',function(){setState('Listening live',true)});
  player.addEventListener('ended',function(){disconnect('Stream ended')});
  player.addEventListener('error',function(){if(!disconnecting&&(player.getAttribute('src')||(source&&source.getAttribute('src'))))disconnect('Stream unavailable')});
  player.addEventListener('pause',function(){if(!disconnecting&&!player.ended)disconnect('Paused · stream closed')});

  var originalRenderAirband=renderAirband;
  renderAirband=function(airband){
    originalRenderAirband(airband);
    var usable=!!(airband&&airband.enabled&&airband.ready&&!airband.device_conflict);
    if(!usable&&(player.currentSrc||player.getAttribute('src')||(source&&source.getAttribute('src'))))disconnect('Disconnected · VHF unavailable');
    if(start)start.disabled=!usable||!player.paused;
  };

  document.addEventListener('click',function(event){
    if(!event.target.closest('.nav,[data-go]'))return;
    setTimeout(function(){var page=document.querySelector('#airband');if(page&&!page.classList.contains('active'))disconnect('Disconnected · VHF page closed')},0);
  });
  document.addEventListener('visibilitychange',function(){if(document.hidden)disconnect('Disconnected · display in background')});
  window.addEventListener('pagehide',function(){disconnect('Disconnected')});
  setState('Disconnected',false);
})();
