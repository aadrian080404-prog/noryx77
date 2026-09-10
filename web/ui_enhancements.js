(() => {
  const $ = (id) => document.getElementById(id);
  const style = document.createElement('style');
  style.textContent = `
    :root{--n7-glass:rgba(11,17,27,.78);--n7-glass-strong:rgba(9,14,22,.92);--n7-edge:rgba(132,166,218,.26);--n7-led:#78aaff;--n7-led-hot:#dce9ff}
    .noryx-core-led{display:inline-flex;align-items:center;gap:9px;font-weight:850;letter-spacing:.12em;position:relative}
    .noryx-core-led i{width:8px;height:8px;border-radius:50%;background:var(--n7-led);box-shadow:0 0 7px var(--n7-led),0 0 18px rgba(120,170,255,.6),0 0 30px rgba(120,170,255,.18);position:relative;display:inline-block;flex:none}
    .noryx-core-led i:after{content:"";position:absolute;inset:-6px;border:1px solid rgba(120,170,255,.34);border-top-color:var(--n7-led-hot);border-radius:50%;animation:noryx-led-spin 1.35s linear infinite}
    .noryx-core-led i:before{content:"";position:absolute;inset:-11px;border:1px solid rgba(120,170,255,.16);border-bottom-color:rgba(120,170,255,.72);border-radius:50%;animation:noryx-led-spin 2.2s linear infinite reverse}
    .noryx-chat-core{display:flex;align-items:center;gap:10px;margin:0 0 22px;padding:9px 12px;border:1px solid rgba(120,170,255,.18);background:linear-gradient(135deg,rgba(13,21,33,.9),rgba(7,12,20,.72));border-radius:12px;color:#91a0b7;font-size:9px;letter-spacing:.16em;text-transform:uppercase;width:max-content;box-shadow:inset 0 1px rgba(255,255,255,.035),0 10px 30px rgba(0,0,0,.18)}
    .noryx-chat-core i{width:7px;height:7px;border-radius:50%;background:var(--n7-led);box-shadow:0 0 10px var(--n7-led),0 0 20px rgba(120,170,255,.32);animation:noryx-led-pulse 1.4s ease-in-out infinite}
    .noryx-welcome-greeting{position:fixed;left:50%;top:15%;transform:translate(-50%,-8px);z-index:80;padding:11px 17px;border:1px solid rgba(132,166,218,.34);background:rgba(11,17,27,.94);border-radius:13px;box-shadow:0 18px 55px rgba(0,0,0,.6),inset 0 1px rgba(255,255,255,.05);color:#f4f7fc;font-size:14px;letter-spacing:.01em;animation:noryx-greeting-in .28s ease forwards}
    .noryx-welcome-greeting.hide{animation:noryx-greeting-out .35s ease forwards}
    .drawer{width:min(390px,94vw);padding:22px 20px;background:linear-gradient(180deg,rgba(12,18,29,.97),rgba(6,10,17,.98));border-left:1px solid rgba(132,166,218,.24);backdrop-filter:blur(28px) saturate(135%);box-shadow:-35px 0 100px rgba(0,0,0,.68),inset 1px 0 rgba(255,255,255,.025)}
    .drawer h2{display:flex;align-items:center;gap:10px;padding:10px 48px 14px 2px;margin:0 0 8px;font-size:18px;font-weight:780;letter-spacing:-.025em;border-bottom:1px solid rgba(132,166,218,.12)}
    .drawer h2:before{content:"";width:8px;height:8px;border-radius:50%;background:var(--n7-led);box-shadow:0 0 10px var(--n7-led),0 0 24px rgba(120,170,255,.3);animation:noryx-led-pulse 1.5s ease-in-out infinite}
    .drawer .icon{background:rgba(13,20,31,.86);border-color:rgba(132,166,218,.2);transition:.18s ease}
    .drawer .icon:hover{transform:scale(1.04);border-color:rgba(132,166,218,.42);background:rgba(20,31,48,.96)}
    .drawer .row{position:relative;margin:0 0 2px;padding:16px 13px;border:1px solid rgba(132,166,218,.11);border-radius:13px;background:linear-gradient(145deg,rgba(17,27,42,.68),rgba(8,13,21,.52));box-shadow:inset 0 1px rgba(255,255,255,.025),0 8px 24px rgba(0,0,0,.12);transition:.18s ease}
    .drawer .row:hover{border-color:rgba(132,166,218,.23);transform:translateX(-1px)}
    .drawer .row label{margin-bottom:8px;color:#7387a4;font-size:8px;font-weight:800;letter-spacing:.19em}
    .drawer .row div{color:#d5deec;font-size:11px;line-height:1.6}
    .drawer .cards{grid-template-columns:1fr;gap:9px;margin:12px 0 2px}
    .drawer .cards:before{content:"CAPACITÀ RAPIDE";display:block;grid-column:1/-1;color:#667995;font-size:8px;font-weight:800;letter-spacing:.18em;padding:4px 2px 1px}
    .drawer .card{min-height:auto;padding:13px 14px;border-color:rgba(132,166,218,.12);background:linear-gradient(145deg,rgba(17,27,42,.72),rgba(8,13,21,.66));border-radius:13px;box-shadow:inset 0 1px rgba(255,255,255,.025),0 9px 25px rgba(0,0,0,.14)}
    .drawer .card:after{background:rgba(157,191,255,.08)}
    .drawer .card b{font-size:9px;letter-spacing:.13em}
    .drawer .card span{font-size:10px;color:#8294ad}
    .overlay{background:rgba(0,0,0,.64);backdrop-filter:blur(5px) saturate(80%)}
    .top #clear{font-size:0;position:relative;overflow:visible;transition:.18s ease}
    .top #clear:before{content:"";position:absolute;left:50%;top:50%;width:12px;height:12px;transform:translate(-50%,-50%);border:1.5px solid #9eb4d5;border-radius:50%;box-shadow:0 0 12px rgba(120,170,255,.15)}
    .top #clear:after{content:"";position:absolute;left:50%;top:50%;width:4px;height:4px;transform:translate(-50%,-50%);border:1px solid #78aaff;border-radius:50%;box-shadow:0 0 8px #78aaff}
    .top #clear:hover{transform:translateY(-1px);border-color:rgba(132,166,218,.42);box-shadow:0 8px 25px rgba(0,0,0,.3)}
    .composer{box-shadow:0 25px 75px rgba(0,0,0,.58),inset 0 1px rgba(255,255,255,.045),0 0 0 1px rgba(120,170,255,.025)}
    .composer:focus-within{border-color:rgba(132,166,218,.5);box-shadow:0 25px 80px rgba(0,0,0,.64),0 0 0 3px rgba(127,169,255,.07),inset 0 1px rgba(255,255,255,.06)}
    @keyframes noryx-led-spin{to{transform:rotate(360deg)}}
    @keyframes noryx-led-pulse{0%,100%{opacity:.42;transform:scale(.84)}50%{opacity:1;transform:scale(1.1)}}
    @keyframes noryx-greeting-in{to{opacity:1;transform:translate(-50%,0)}}
    @keyframes noryx-greeting-out{to{opacity:0;transform:translate(-50%,-8px);pointer-events:none}}
    @media(max-width:760px){.drawer{width:min(390px,94vw);padding:18px 15px}.drawer .row{padding:14px 12px}.noryx-welcome-greeting{top:11%;max-width:calc(100vw - 34px);text-align:center}.noryx-chat-core{margin-bottom:17px}.top #clear{min-width:37px}}
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
    topButton.textContent = '';
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
