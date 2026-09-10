(() => {
  const $ = (id) => document.getElementById(id);
  const style = document.createElement('style');
  style.textContent = `
    .noryx-core-led{display:inline-flex;align-items:center;gap:7px;font-weight:800;letter-spacing:.12em}
    .noryx-core-led i{width:8px;height:8px;border-radius:50%;background:#78aaff;box-shadow:0 0 7px #78aaff,0 0 18px #78aaff99;position:relative;display:inline-block}
    .noryx-core-led i:after{content:"";position:absolute;inset:-5px;border:1px solid #78aaff66;border-top-color:#dce9ff;border-radius:50%;animation:noryx-led-spin 1.35s linear infinite}
    .noryx-core-led i:before{content:"";position:absolute;inset:-10px;border:1px solid #78aaff22;border-bottom-color:#78aaff88;border-radius:50%;animation:noryx-led-spin 2.2s linear infinite reverse}
    .noryx-chat-core{display:flex;align-items:center;gap:9px;margin:0 0 22px;padding:9px 11px;border:1px solid #1b2637;background:#0a1018cc;border-radius:12px;color:#91a0b7;font-size:9px;letter-spacing:.16em;text-transform:uppercase;width:max-content}
    .noryx-chat-core i{width:7px;height:7px;border-radius:50%;background:#78aaff;box-shadow:0 0 10px #78aaff;animation:noryx-led-pulse 1.4s ease-in-out infinite}
    .noryx-welcome-greeting{position:fixed;left:50%;top:15%;transform:translate(-50%,-8px);z-index:80;padding:11px 17px;border:1px solid #30415b;background:#0b111bf2;border-radius:13px;box-shadow:0 18px 55px #0009;color:#f4f7fc;font-size:14px;letter-spacing:.01em;animation:noryx-greeting-in .28s ease forwards}
    .noryx-welcome-greeting.hide{animation:noryx-greeting-out .35s ease forwards}
    .drawer .cards{grid-template-columns:1fr;gap:8px;margin-top:8px}
    .drawer .card{min-height:auto;padding:13px}
    @keyframes noryx-led-spin{to{transform:rotate(360deg)}}
    @keyframes noryx-led-pulse{0%,100%{opacity:.45;transform:scale(.85)}50%{opacity:1;transform:scale(1.1)}}
    @keyframes noryx-greeting-in{to{opacity:1;transform:translate(-50%,0)}}
    @keyframes noryx-greeting-out{to{opacity:0;transform:translate(-50%,-8px);pointer-events:none}}
  `;
  document.head.appendChild(style);

  const drawer = $('drawer');
  const overlay = $('overlay');
  const settings = $('settings');
  const close = $('close');
  const topButton = $('clear');
  const model = $('model');
  const chat = $('chat');
  const welcome = $('welcome');

  const openSettings = () => {
    if (drawer) drawer.classList.add('open');
    if (overlay) overlay.classList.add('open');
  };
  const closeSettings = () => {
    if (drawer) drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
  };

  if (settings) settings.addEventListener('click', openSettings);
  if (close) close.addEventListener('click', closeSettings);
  if (overlay) overlay.addEventListener('click', closeSettings);

  if (topButton) {
    topButton.textContent = '⚙';
    topButton.title = 'Impostazioni NORYX7';
    topButton.setAttribute('aria-label', 'Impostazioni NORYX7');
    topButton.addEventListener('click', (event) => {
      event.preventDefault();
      openSettings();
    });
  }

  if (model) {
    model.innerHTML = '<span class="noryx-core-led"><i></i> HYPERSYNTH CORE</span>';
  }

  const cards = welcome ? welcome.querySelector('.cards') : null;
  if (cards && drawer) {
    drawer.appendChild(cards);
    cards.style.display = 'grid';
  }

  const greeting = document.createElement('div');
  greeting.className = 'noryx-welcome-greeting';
  greeting.textContent = 'Ciao, cosa posso fare per te?';
  document.body.appendChild(greeting);
  window.setTimeout(() => greeting.classList.add('hide'), 2300);
  window.setTimeout(() => greeting.remove(), 2700);

  const chatCore = document.createElement('div');
  chatCore.className = 'noryx-chat-core';
  chatCore.innerHTML = '<i></i><span>HYPERSYNTH CORE</span>';
  if (chat) chat.insertBefore(chatCore, chat.firstChild);
})();
