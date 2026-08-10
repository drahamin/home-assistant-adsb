(() => {
  const coreRender = render;
  render = function (data) {
    coreRender(data);
    const hub = data.adsbhub || {};
    if ((hub.inbound_error || '').includes('closed port 5002 without sending data')) {
      document.querySelector('#adsbhub-inbound').textContent = 'Access not active';
    }
  };
})();
