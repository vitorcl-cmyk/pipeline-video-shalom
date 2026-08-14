#!/bin/bash
# ============================================================
# RedeImóvel — Setup completo
# Servidor: vitor.serveftp.com
# IP interno: 192.168.15.32
# Porta: 700
# ============================================================

# 1. PROXY NIDO (Python - porta 8765)
cat > /usr/local/bin/proxy-nido.py << 'EOF'
import urllib.request, http.server

NIDO_URL = 'http://integracoes.nidoimovel.com.br/9a4400501febb2a95e79248486a5f6d3/Outros/12/SL.xml'

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/xml; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        req = urllib.request.Request(NIDO_URL, headers={'Accept-Encoding': 'identity'})
        data = urllib.request.urlopen(req).read()
        self.wfile.write(data)
    def log_message(self, *a): pass

http.server.HTTPServer(('0.0.0.0', 8765), Handler).serve_forever()
EOF

# 2. SERVIÇO SYSTEMD PROXY
cat > /etc/systemd/system/proxy-nido.service << 'EOF'
[Unit]
Description=Proxy Nido XML
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/proxy-nido.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable proxy-nido
systemctl restart proxy-nido

# 3. NGINX - configuração porta 700
cat > /etc/nginx/sites-available/redeimovel << 'EOF'
server {
    listen 700;
    root /var/www/redeimovel;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /nido-proxy {
        proxy_pass http://127.0.0.1:8765;
        add_header Access-Control-Allow-Origin *;
    }
}
EOF

mkdir -p /var/www/redeimovel
ln -sf /etc/nginx/sites-available/redeimovel /etc/nginx/sites-enabled/redeimovel
nginx -t && systemctl reload nginx

# 4. HTML DO SITE
cat > /var/www/redeimovel/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>RedeImóvel — Corretores Verificados</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--primary:#0f2d4a;--accent:#00c49a;--light:#f4f7fb;--text:#1a2636;--muted:#6b7a8d}
body{font-family:'Segoe UI',sans-serif;color:var(--text);background:var(--light)}
nav{background:var(--primary);padding:0 24px;height:64px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.logo{color:#fff;font-size:1.4rem;font-weight:800}.logo span{color:var(--accent)}
.btn-nav{background:var(--accent);color:var(--primary);border:none;padding:9px 20px;border-radius:8px;font-weight:700;cursor:pointer}
.nav-menu{display:flex;gap:28px;list-style:none}
.nav-menu a{color:rgba(255,255,255,.85);text-decoration:none;font-size:.9rem;font-weight:500}
.nav-menu a:hover{color:#fff}
.nav-actions{display:flex;align-items:center;gap:12px}
.btn-ghost{background:transparent;color:#fff;border:2px solid rgba(255,255,255,.3);padding:8px 18px;border-radius:8px;font-weight:600;cursor:pointer;font-size:.85rem}
.btn-ghost:hover{border-color:#fff}
/* Sem foto ainda: o gradiente abaixo é o placeholder do hero.
   Quando tiver a imagem, troque por: background:linear-gradient(135deg,rgba(15,45,74,.85),rgba(26,74,114,.75)),url('sua-foto.jpg') center/cover; */
.hero{background:linear-gradient(135deg,#0f2d4a,#1a4a72);padding:56px 24px 44px;text-align:center;color:#fff}
.hero h1{font-size:2.2rem;font-weight:900;margin-bottom:12px}
.hero h1 em{color:var(--accent);font-style:normal}
.hero p{color:rgba(255,255,255,.75);margin-bottom:28px}
.search-card{background:#fff;border-radius:16px;max-width:760px;margin:0 auto;box-shadow:0 12px 40px rgba(0,0,0,.25);overflow:hidden;text-align:left}
.tabs{display:flex;border-bottom:1px solid #eee}
.tab{flex:0 0 auto;padding:14px 26px;border:none;background:none;font-size:.9rem;font-weight:600;color:var(--muted);cursor:pointer;border-bottom:3px solid transparent}
.tab.active{color:var(--primary);border-color:var(--accent)}
.search-row{display:flex;flex-wrap:wrap}
.search-row select,.search-row input{border:none;padding:16px;font-size:.92rem;flex:1;min-width:140px;outline:none;border-right:1px solid #eee;font-family:inherit;color:var(--text)}
.search-row button{background:var(--accent);color:#fff;border:none;padding:16px 30px;font-weight:700;cursor:pointer;font-size:.92rem}
.stats{display:flex;justify-content:center;gap:40px;margin-top:32px}
.stat strong{display:block;font-size:1.8rem;font-weight:900;color:var(--accent)}
.stat span{font-size:.8rem;color:rgba(255,255,255,.6)}
.selo{background:#fff;border-bottom:3px solid var(--accent);padding:16px 24px;display:flex;justify-content:center;gap:32px;flex-wrap:wrap}
.selo-item{display:flex;align-items:center;gap:8px;font-size:.85rem}
.cidades-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:18px}
.cidade-card{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.06);cursor:pointer;transition:transform .2s}
.cidade-card:hover{transform:translateY(-4px)}
.cidade-img{height:110px;display:flex;align-items:center;justify-content:center;font-size:2.1rem;color:#fff}
.cidade-body{padding:14px}
.cidade-nome{font-weight:700;font-size:.95rem;margin-bottom:2px}
.cidade-qtd{font-size:.78rem;color:var(--muted);margin-bottom:8px}
.cidade-link{font-size:.78rem;color:var(--accent);font-weight:600}
.section{padding:48px 24px;max-width:1200px;margin:0 auto}
.sec-title{font-size:1.5rem;font-weight:800;color:var(--primary);margin-bottom:4px}
.sec-title span{color:var(--accent)}
.sec-sub{color:var(--muted);font-size:.88rem;margin-bottom:24px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}
.card{background:#fff;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.07);overflow:hidden;cursor:pointer;transition:transform .2s}
.card:hover{transform:translateY(-4px)}
.card-img{height:180px;display:flex;align-items:center;justify-content:center;font-size:3rem;position:relative}
.badges{position:absolute;top:10px;left:10px;display:flex;gap:6px}
.badge{padding:3px 9px;border-radius:4px;font-size:.7rem;font-weight:700;color:#fff}
.b1{background:var(--primary)}.b2{background:var(--accent)}.b3{background:#f5a623}
.card-body{padding:14px}
.price{font-size:1.2rem;font-weight:900;color:var(--primary)}
.cond{font-size:.75rem;color:var(--muted);margin-bottom:4px}
.ctitle{font-size:.88rem;font-weight:600;margin-bottom:2px}
.cloc{font-size:.78rem;color:var(--muted);margin-bottom:10px}
.feats{display:flex;gap:10px;font-size:.78rem;color:var(--muted);padding:8px 0;border-top:1px solid #f0f0f0;border-bottom:1px solid #f0f0f0;margin-bottom:10px}
.crfoot{display:flex;align-items:center;justify-content:space-between}
.cravatar{width:28px;height:28px;border-radius:50%;background:var(--primary);display:flex;align-items:center;justify-content:center;color:#fff;font-size:.7rem;font-weight:700;margin-right:6px}
.crname{font-size:.75rem;font-weight:600}.crcreci{font-size:.68rem;color:var(--muted)}
.wbtn{background:#25d366;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:.75rem;font-weight:700;cursor:pointer}
.loading{grid-column:1/-1;text-align:center;padding:40px;color:var(--muted)}
.planos{background:var(--primary);padding:56px 24px}
.planos-inner{max-width:960px;margin:0 auto;text-align:center}
.planos-inner h2{color:#fff;font-size:1.5rem;font-weight:800;margin-bottom:8px}
.planos-inner p{color:rgba(255,255,255,.65);margin-bottom:32px}
.pgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}
.pcard{background:rgba(255,255,255,.08);border:2px solid rgba(255,255,255,.15);border-radius:14px;padding:28px 20px}
.pcard.dest{border-color:var(--accent);background:rgba(0,196,154,.1)}
.pnome{color:rgba(255,255,255,.7);font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.ppreco{color:#fff;font-size:2rem;font-weight:900;margin-bottom:4px}
.ppreco small{font-size:.82rem;font-weight:400;opacity:.7}
.pdesc{color:rgba(255,255,255,.6);font-size:.82rem;margin-bottom:16px}
.pfeat{list-style:none;text-align:left}
.pfeat li{color:rgba(255,255,255,.8);font-size:.82rem;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.08)}
.pfeat li::before{content:"✓ ";color:var(--accent)}
.pbtn{margin-top:18px;width:100%;padding:11px;border-radius:8px;border:2px solid rgba(255,255,255,.4);background:transparent;color:#fff;font-weight:700;cursor:pointer;transition:all .2s}
.pbtn:hover{background:rgba(255,255,255,.15)}
footer{background:#081a2c;color:rgba(255,255,255,.45);text-align:center;padding:24px;font-size:.8rem}
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:200;align-items:center;justify-content:center}
.modal-bg.open{display:flex}
.modal{background:#fff;border-radius:16px;padding:32px;max-width:460px;width:92%;position:relative;max-height:90vh;overflow-y:auto}
.mc{position:absolute;top:12px;right:16px;background:none;border:none;font-size:1.3rem;cursor:pointer;color:var(--muted)}
.modal h2{color:var(--primary);margin-bottom:6px}
.modal p{color:var(--muted);font-size:.85rem;margin-bottom:16px}
.modal input,.modal textarea{width:100%;padding:11px 13px;border:2px solid #e2e8f0;border-radius:8px;font-size:.88rem;margin-bottom:10px;outline:none;font-family:inherit}
.modal input:focus,.modal textarea:focus{border-color:var(--accent)}
.modal textarea{height:80px;resize:none}
.msub{width:100%;padding:13px;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:.95rem;font-weight:700;cursor:pointer;margin-bottom:8px}
.mwpp{width:100%;padding:13px;background:#25d366;color:#fff;border:none;border-radius:8px;font-size:.95rem;font-weight:700;cursor:pointer}
.filtros{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
.fbtn{padding:7px 16px;border-radius:20px;border:2px solid #dde3ec;background:#fff;color:var(--muted);font-size:.82rem;cursor:pointer;font-weight:500;transition:all .2s}
.fbtn.active,.fbtn:hover{border-color:var(--accent);color:var(--accent);background:#f0fdfb}
</style>
</head>
<body>

<nav>
  <div class="logo">Rede<span>Imóvel</span></div>
  <ul class="nav-menu">
    <li><a href="#imoveis">Comprar</a></li>
    <li><a href="#imoveis">Alugar</a></li>
    <li><a href="#bairros">Bairros</a></li>
  </ul>
  <div class="nav-actions">
    <button class="btn-ghost" onclick="openM('modal-ct')">Entrar</button>
    <button class="btn-nav" onclick="openM('modal-an')">Anunciar</button>
  </div>
</nav>

<div class="hero">
  <div style="display:inline-flex;align-items:center;gap:8px;background:rgba(0,196,154,.15);border:1px solid rgba(0,196,154,.4);border-radius:20px;padding:5px 14px;font-size:.8rem;color:var(--accent);font-weight:600;margin-bottom:18px">✅ Corretores com CRECI Verificado</div>
  <h1>Encontre seu <em>imóvel</em></h1>
  <p>Todos os corretores têm CRECI ativo e avaliações reais de clientes</p>
  <div class="search-card">
    <div class="tabs">
      <button class="tab active" id="tab-venda" onclick="setTab('Venda')">Comprar</button>
      <button class="tab" id="tab-locacao" onclick="setTab('Locação')">Alugar</button>
    </div>
    <div class="search-row">
      <select id="f-tipo">
        <option value="">Tipo</option>
        <option>Apartamento</option>
        <option>Comercial</option>
      </select>
      <input type="text" id="f-local" placeholder="Digite o bairro ou a cidade...">
      <button onclick="buscar()">🔍 Buscar</button>
    </div>
  </div>
  <div class="stats">
    <div class="stat"><strong id="tot-imoveis">--</strong><span>Imóveis</span></div>
    <div class="stat"><strong>✅</strong><span>CRECI Verificado</span></div>
    <div class="stat"><strong id="tot-bairros">--</strong><span>Bairros atendidos</span></div>
  </div>
</div>

<div class="selo">
  <div class="selo-item">✅ <strong>CRECI Verificado</strong></div>
  <div class="selo-item">⭐ <strong>Avaliações Reais</strong></div>
  <div class="selo-item">🤖 <strong>Anúncios com IA</strong></div>
  <div class="selo-item">📊 <strong>Preço Justo</strong></div>
</div>

<div class="section" id="bairros">
  <div class="sec-title">Bairros em <span>destaque</span></div>
  <div class="sec-sub">Os bairros com mais imóveis disponíveis na RedeImóvel</div>
  <div class="cidades-grid" id="bairros-grid"><div class="loading">⏳ Carregando bairros...</div></div>
</div>

<div class="section" id="imoveis">
  <div class="sec-title">Imóveis em <span>Destaque</span></div>
  <div class="sec-sub">Anunciados por corretores verificados da Shalom Consultoria</div>
  <div class="filtros">
    <button class="fbtn active" onclick="filtrar(this,'Todos')">Todos</button>
    <button class="fbtn" onclick="filtrar(this,'Venda')">Venda</button>
    <button class="fbtn" onclick="filtrar(this,'Locação')">Locação</button>
  </div>
  <div class="cards" id="cards"><div class="loading">⏳ Carregando imóveis...</div></div>
</div>

<div class="planos">
  <div class="planos-inner">
    <h2>Planos para Corretores e Imobiliárias</h2>
    <p>Sem taxa de adesão. Cancele quando quiser.</p>
    <div class="pgrid">
      <div class="pcard">
        <div class="pnome">Autônomo</div>
        <div class="ppreco">R$ 2<small>/imóvel/mês</small></div>
        <div class="pdesc">Até 20 imóveis</div>
        <ul class="pfeat"><li>Perfil com CRECI</li><li>WhatsApp direto</li><li>Avaliações de clientes</li></ul>
        <button class="pbtn" onclick="openM('modal-an')">Começar</button>
      </div>
      <div class="pcard dest">
        <div class="pnome">⭐ Profissional</div>
        <div class="ppreco">R$ 2<small>/imóvel/mês</small></div>
        <div class="pdesc">Até 100 imóveis + IA</div>
        <ul class="pfeat"><li>Perfil com CRECI</li><li>IA para gerar anúncios</li><li>CRM de leads</li><li>Avaliação de mercado</li></ul>
        <button class="pbtn" onclick="openM('modal-an')">Assinar</button>
      </div>
      <div class="pcard">
        <div class="pnome">Imobiliária</div>
        <div class="ppreco">R$ 1<small>/imóvel/mês</small></div>
        <div class="pdesc">500+ imóveis</div>
        <ul class="pfeat"><li>Imóveis ilimitados</li><li>Múltiplos corretores</li><li>Integração XML/API</li><li>Relatórios</li></ul>
        <button class="pbtn" onclick="openM('modal-an')">Falar</button>
      </div>
    </div>
  </div>
</div>

<footer>© 2026 RedeImóvel — Corretores com CRECI verificado. Intermediadores — não participamos das negociações.</footer>

<div class="modal-bg" id="modal-ct">
  <div class="modal">
    <button class="mc" onclick="closeM('modal-ct')">✕</button>
    <h2>Falar com Corretor</h2>
    <p id="mct-desc">Entre em contato direto</p>
    <input type="text" placeholder="Seu nome">
    <input type="tel" placeholder="WhatsApp com DDD">
    <input type="email" placeholder="E-mail">
    <textarea placeholder="Mensagem..."></textarea>
    <button class="msub">📧 Enviar</button>
    <button class="mwpp">💬 WhatsApp</button>
  </div>
</div>

<div class="modal-bg" id="modal-an">
  <div class="modal">
    <button class="mc" onclick="closeM('modal-an')">✕</button>
    <h2>Anuncie na RedeImóvel</h2>
    <p>Preencha e entraremos em contato em até 24h</p>
    <input type="text" placeholder="Nome completo">
    <input type="text" placeholder="CRECI">
    <input type="tel" placeholder="WhatsApp com DDD">
    <input type="email" placeholder="E-mail">
    <input type="number" placeholder="Qtd de imóveis" oninput="calcP(this)">
    <div id="pbox" style="display:none;background:#f0fdfb;border:2px solid var(--accent);border-radius:8px;padding:12px;margin-bottom:10px;font-size:.85rem;color:var(--primary);font-weight:700"></div>
    <button class="msub">✅ Solicitar cadastro</button>
    <button class="mwpp">💬 WhatsApp</button>
  </div>
</div>

<script>
const PROXY = 'http://vitor.serveftp.com:700/nido-proxy';
const cores = [['#1a3c5e','#2a6090'],['#1a5e3c','#2a9060'],['#3c1a5e','#602a90'],['#5e3a1a','#906028'],['#1a4e5e','#2a7890'],['#5e1a3a','#902a60']];
let todos = [], ativo = 'Todos', tabFin = 'Venda';

fetch(PROXY).then(r => r.text()).then(txt => {
  const xml = new DOMParser().parseFromString(txt, 'text/xml');
  const items = xml.querySelectorAll('Imovel');
  if (!items.length) throw new Error('XML vazio');
  todos = Array.from(items).map((im, i) => {
    const g = t => im.querySelector(t)?.textContent?.trim() || '';
    const pv = g('PrecoVenda'), pl = g('PrecoLocacao');
    const fin = g('TransactionType') === 'For Sale' ? 'Venda' : 'Locação';
    const pr = fin === 'Venda' ? pv : pl;
    const prn = parseFloat(pr.replace(/\./g,'').replace(',','.')) || 0;
    const prFmt = prn > 0 ? 'R$ ' + prn.toLocaleString('pt-BR') : 'Consulte';
    const cd = g('PrecoCondominio');
    return {
      tipo: parseInt(g('QtdDormitorios')) > 0 ? 'Apartamento' : 'Comercial',
      bairro: g('Bairro'), cidade: g('Cidade'), uf: g('UF'),
      desc: g('Observacao'), prFmt, fin,
      cond: cd && cd !== '0,00' ? '+ R$ ' + cd + ' cond.' : '',
      area: g('AreaUtil') || g('AreaTotal'),
      qts: g('QtdDormitorios') || '—',
      vgs: g('QtdVagas') || '—',
      bnh: g('QtdBanheiros') || '—',
      cod: g('CodigoImovel'), idx: i
    };
  });
  document.getElementById('tot-imoveis').textContent = todos.length + '+';
  render(todos);
  renderBairros(todos);
}).catch(e => {
  document.getElementById('cards').innerHTML = '<div class="loading">⚠️ ' + e.message + '</div>';
  document.getElementById('bairros-grid').innerHTML = '<div class="loading">⚠️ ' + e.message + '</div>';
});

function renderBairros(lista) {
  const porBairro = {};
  lista.forEach(im => {
    if (!im.bairro) return;
    if (!porBairro[im.bairro]) porBairro[im.bairro] = { cidade: im.cidade, qtd: 0 };
    porBairro[im.bairro].qtd++;
  });
  const top = Object.entries(porBairro).sort((a, b) => b[1].qtd - a[1].qtd).slice(0, 8);
  document.getElementById('tot-bairros').textContent = Object.keys(porBairro).length + '+';
  const grid = document.getElementById('bairros-grid');
  if (!top.length) { grid.innerHTML = '<div class="loading">Nenhum bairro encontrado.</div>'; return; }
  grid.innerHTML = '';
  top.forEach(([bairro, info], i) => {
    const cor = cores[i % cores.length];
    grid.innerHTML += `<div class="cidade-card" onclick="buscarBairro('${bairro}')">
      <div class="cidade-img" style="background:linear-gradient(135deg,${cor[0]},${cor[1]})">📍</div>
      <div class="cidade-body">
        <div class="cidade-nome">${bairro}</div>
        <div class="cidade-qtd">${info.qtd} imóve${info.qtd === 1 ? 'l' : 'is'} — ${info.cidade}</div>
        <span class="cidade-link">Ver imóveis em ${bairro} →</span>
      </div>
    </div>`;
  });
}

function render(lista) {
  const c = document.getElementById('cards');
  if (!lista.length) { c.innerHTML = '<div class="loading">Nenhum imóvel encontrado.</div>'; return; }
  c.innerHTML = '';
  lista.slice(0, 12).forEach((im, i) => {
    const cor = cores[i % cores.length];
    c.innerHTML += `<div class="card" onclick="openCt('${im.cod}','${im.bairro}')">
      <div class="card-img" style="background:linear-gradient(135deg,${cor[0]},${cor[1]})">
        <div class="badges">
          <span class="badge b1">${im.tipo}</span>
          <span class="badge b2">${im.fin}</span>
          <span class="badge b3">✅ Verificado</span>
        </div>🏠
      </div>
      <div class="card-body">
        <div class="price">${im.prFmt}</div>
        <div class="cond">${im.cond}</div>
        <div class="ctitle">${im.tipo} — ${im.bairro}</div>
        <div class="cloc">📍 ${im.bairro}, ${im.cidade} — ${im.uf}</div>
        <div class="feats"><span>📐 ${im.area}m²</span><span>🛏 ${im.qts}</span><span>🚗 ${im.vgs}</span><span>🚿 ${im.bnh}</span></div>
        <div class="crfoot">
          <div style="display:flex;align-items:center">
            <div class="cravatar">SL</div>
            <div><div class="crname">Shalom Consultoria</div><div class="crcreci">CRECI-J 43.195-J ✅</div></div>
          </div>
          <button class="wbtn" onclick="event.stopPropagation();openCt('${im.cod}','${im.bairro}')">💬</button>
        </div>
      </div>
    </div>`;
  });
}

function filtrar(btn, tipo) {
  document.querySelectorAll('.fbtn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active'); ativo = tipo;
  render(tipo === 'Todos' ? todos : todos.filter(im => im.fin === tipo));
}

function setTab(fin) {
  tabFin = fin;
  document.getElementById('tab-venda').classList.toggle('active', fin === 'Venda');
  document.getElementById('tab-locacao').classList.toggle('active', fin === 'Locação');
}

function buscar() {
  const tipo = document.getElementById('f-tipo').value;
  const local = document.getElementById('f-local').value.trim().toLowerCase();
  aplicarFiltro(im => im.fin === tabFin
    && (!tipo || im.tipo === tipo)
    && (!local || im.bairro.toLowerCase().includes(local) || im.cidade.toLowerCase().includes(local)));
}

function buscarBairro(bairro) {
  document.getElementById('f-local').value = bairro;
  aplicarFiltro(im => im.bairro === bairro);
}

function aplicarFiltro(fn) {
  document.querySelectorAll('.fbtn').forEach(b => b.classList.remove('active'));
  document.querySelector('.fbtn').classList.add('active'); ativo = 'Todos';
  render(todos.filter(fn));
  document.getElementById('imoveis').scrollIntoView({ behavior: 'smooth' });
}

function openM(id) { document.getElementById(id).classList.add('open'); }
function closeM(id) { document.getElementById(id).classList.remove('open'); }
function openCt(cod, bairro) {
  document.getElementById('mct-desc').textContent = 'Imóvel ' + cod + ' — ' + bairro + ' | Shalom Consultoria';
  openM('modal-ct');
}
document.querySelectorAll('.modal-bg').forEach(bg => {
  bg.addEventListener('click', e => { if (e.target === bg) bg.classList.remove('open'); });
});
function calcP(el) {
  const q = parseInt(el.value) || 0, p = q >= 500 ? 1 : 2, tot = q * p;
  const b = document.getElementById('pbox');
  if (!q) { b.style.display = 'none'; return; }
  b.style.display = 'block';
  b.textContent = (q >= 500 ? 'Plano Imobiliária' : q > 20 ? 'Plano Profissional' : 'Plano Autônomo') +
    ' — R$ ' + tot.toLocaleString('pt-BR') + '/mês (' + q + ' imóveis × R$ ' + p + ')';
}
</script>
</body>
</html>
HTMLEOF

echo "✅ RedeImóvel instalado em http://vitor.serveftp.com:700"
echo "✅ Proxy Nido rodando em http://localhost:8765"
echo ""
echo "⚠️  Lembrete: Liberar porta 700 no roteador"
echo "   Port Forwarding: 700 → 192.168.15.32:700 TCP"
