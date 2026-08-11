(()=>{
  const coreRender=render;
  render=function(data){
    coreRender(data);
    const proxy=data.miami_proxy||{},counts=data.counts||{};
    const count=document.querySelector('#aircraft-count');
    if(count)count.textContent=`${counts.aircraft||0} active · ${counts.local||0} Sicily · ${counts.miami||0} Miami · ${counts.adsbhub||0} ADSBHub`;
    const badge=document.querySelector('#miami-proxy-badge');
    const detail=document.querySelector('#miami-proxy-detail');
    const note=document.querySelector('#miami-proxy-note');
    if(badge)badge.textContent=!proxy.enabled?'Disabled':proxy.online?'Connected':'Reconnecting';
    if(detail)detail.textContent=proxy.online?`${proxy.target_count||0} receiver-local aircraft · ${proxy.displayed_target_count||0} displayed`:'Waiting for the private Miami aircraft endpoint';
    if(note)note.textContent=proxy.error?`Last connection error: ${proxy.error}`:`${proxy.deduplicated_target_count||0} ICAO duplicates removed · display-only, never retransmitted`;
  };
})();
