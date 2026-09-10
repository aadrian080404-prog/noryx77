from __future__ import annotations

from pathlib import Path


UI_CSS = r'''
<style id="noryx7-ui-wave10">
/* NORYX7 premium interface: visual hierarchy stays clean; capabilities live in + settings. */
.cards{display:none!important}
.drawer{background:#080d15!important;backdrop-filter:none!important;-webkit-backdrop-filter:none!important;opacity:1!important}
.drawer .fabric-grid{display:grid;gap:10px;margin:4px 0 18px}
.drawer .fabric-card{position:relative;border:1px solid #26364d;border-radius:13px;padding:13px;background:linear-gradient(145deg,#101a28,#0b111b);overflow:hidden}
.drawer .fabric-card:before{content:"";position:absolute;inset:-1px;border-radius:14px;padding:1px;background:conic-gradient(from 0deg,transparent,#80a9ff,transparent 38%,#ffffff55,transparent 70%);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;animation:noryx-led-spin 2.8s linear infinite;opacity:.72}
.drawer .fabric-card b{display:block;font-size:10px;letter-spacing:.14em;margin-bottom:5px}.drawer .fabric-card span{font-size:10px;color:#7f8da2;line-height:1.5}
.noryx-core-pill{position:relative;display:inline-flex;align-items:center;gap:8px;padding-left:11px!important;overflow:visible!important}
.noryx-core-led{width:8px;height:8px;border-radius:50%;position:relative;display:inline-block;background:#9ec2ff;box-shadow:0 0 7px #80b3ff,0 0 17px #4e8fff;flex:none}
.noryx-core-led:before{content:"";position:absolute;inset:-5px;border-radius:50%;border:1px solid #77aaff88;border-top-color:#d8e7ff;animation:noryx-led-spin 1.4s linear infinite}
.noryx-core-led:after{content:"";position:absolute;inset:-9px;border-radius:50%;border:1px solid #6b9fff22;border-left-color:#6b9fff99;animation:noryx-led-spin 2.4s linear infinite reverse}
.msg.assistant .avatar{position:relative;border-color:#5879a5;box-shadow:0 0 11px #6da5ff33,inset 0 1px #fff1}
.msg.assistant .avatar:after{content:"";position:absolute;inset:-4px;border-radius:12px;border:1px solid #76a9ff55;border-top-color:#cce0ff;animation:noryx-led-spin 1.8s linear infinite}
.noryx-greeting{position:fixed;left:50%;top:46%;transform:translate(-50%,-50%);z-index:80;pointer-events:none;font-size:clamp(26px,5vw,46px);font-weight:720;letter-spacing:-.045em;color:#f5f8ff;text-align:center;white-space:nowrap;animation:noryx-greeting-in .45s ease,noryx-greeting-out .7s ease 2s forwards;text-shadow:0 0 28px #8bb5ff22}
.noryx-greeting em{font-style:normal;color:#a8c4ff}
.noryx-ad{display:none;align-items:center;justify-content:center;gap:7px;margin:7px auto 0;font-size:9px;color:#65758b}
.noryx-ad a{color:#a8c4ff;text-decoration:none;border-bottom:1px solid #5d78a044}.noryx-ad a:hover{color:#dbe7ff}
@keyframes noryx-led-spin{to{transform:rotate(360deg)}}
@keyframes noryx-greeting-in{from{opacity:0;filter:blur(7px);transform:translate(-50%,-45%) scale(.97)}to{opacity:1;filter:none;transform:translate(-50%,-50%) scale(1)}}
@keyframes noryx-greeting-out{to{opacity:0;filter:blur(6px);transform:translate(-50%,-55%) scale(1.02)}}
</style>
'''

UI_JS = r'''
<script id="noryx7-ui-wave10-script">
(function(){
  const q=id=>document.getElementById(id);
  const drawer=q('drawer'), overlay=q('overlay'), clear=q('clear'), close=q('close'), settings=q('settings'), model=q('model'), welcome=q('welcome');
  if(!drawer||!model)return;
  function open(){drawer.classList.add('open');overlay&&overlay.classList.add('open')}
  function shut(){drawer.classList.remove('open');overlay&&overlay.classList.remove('open')}
  if(clear)clear.onclick=open;
  if(settings)settings.onclick=open;
  if(close)close.onclick=shut;
  if(overlay)overlay.onclick=shut;

  /* The + panel is the single home for runtime capabilities. */
  const h=drawer.querySelector('h2');
  if(h && !drawer.querySelector('.fabric-grid')){
    const grid=document.createElement('div');grid.className='fabric-grid';
    grid.innerHTML='<div class="fabric-card"><b>HYPERSYNTH CORE</b><span>Decomposizione, pianificazione, simulazione e controllo del flusso cognitivo.</span></div><div class="fabric-card"><b>MODEL FABRIC</b><span>Routing dinamico tra provider e modelli realmente disponibili.</span></div><div class="fabric-card"><b>VERIFICATION</b><span>Identità, esecuzione, provenienza e ammissione del risultato.</span></div><div class="fabric-card"><b>AGENT FABRIC</b><span>Agenti coordinati per esecuzione, verifica e consenso.</span></div>';
    h.after(grid);
  }

  function setCorePill(){
    model.classList.add('noryx-core-pill');
    model.innerHTML='<span class="noryx-core-led" aria-hidden="true"></span><span>HYPERSYNTH CORE</span>';
  }
  setCorePill();
  new MutationObserver(setCorePill).observe(model,{childList:true,subtree:true,characterData:true});

  /* Opening greeting: visible once, then removed from DOM. */
  if(!sessionStorage.getItem('noryx7.greeting.wave10')){
    sessionStorage.setItem('noryx7.greeting.wave10','1');
    const g=document.createElement('div');g.className='noryx-greeting';g.innerHTML='Ciao, cosa posso fare <em>per te?</em>';
    document.body.appendChild(g);setTimeout(()=>g.remove(),3100);
  }

  /* Sponsored loading placement. The destination is supplied by the existing monetization boundary. */
  fetch('/api/monetization/loading-offer',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(o=>{
    if(!o||!o.enabled||!o.destination)return;
    const wrap=document.querySelector('.composer-wrap');if(!wrap||wrap.querySelector('.noryx-ad'))return;
    const ad=document.createElement('div');ad.className='noryx-ad';ad.style.display='flex';
    const a=document.createElement('a');a.href=o.destination;a.target='_blank';a.rel='sponsored noopener noreferrer';a.textContent=o.label||'Scopri la proposta sponsorizzata';
    ad.append('Pubblicità',a);wrap.appendChild(ad);
  }).catch(()=>{});

  /* Keep the mobile side menu independent from the + settings drawer. */
  const side=q('side'),menu=q('menu');
  if(menu&&side){menu.onclick=()=>side.classList.toggle('open');}
  document.addEventListener('click',e=>{if(e.target.closest('#side .side-link'))side&&side.classList.remove('open')});

  /* When chat becomes active, the central marketing cards stay gone. */
  if(welcome)welcome.querySelectorAll('.cards').forEach(x=>x.remove());
})();
</script>
'''


def build_ui_index(source: Path, target: Path) -> Path:
    html = source.read_text(encoding="utf-8")
    html = html.replace("</head>", UI_CSS + "</head>", 1)
    html = html.replace("</body>", UI_JS + "</body>", 1)
    target.write_text(html, encoding="utf-8")
    return target
