# Scraper — shalomconsultoria.com.br → listings.json

Gera o JSON estático (`data/listings.json`) consumido pelo
[widget de vitrine](../showcase-widget), com um registro por imóvel: foto,
bairro, tipo, valor e link. Feito pra rodar periodicamente (cron ou systemd
timer) e sobrescrever sempre o mesmo arquivo.

## ⚠️ Antes do primeiro uso

O `scrape_shalom.py` foi escrito **sem acesso ao HTML ao vivo do site**
(bloqueado no ambiente onde este código foi desenvolvido). Os seletores CSS
em `SELECTORS`, no topo do arquivo, são um ponto de partida baseado em
padrões comuns de sites de imobiliária — **abra a página de listagem no
navegador, inspecione um card de imóvel e ajuste os seletores** (`card`,
`title`, `photo`, `bairro`, `tipo`, `valor`, `link`, `next_page`) antes de
colocar em produção. O resto do pipeline (paginação, parsing de valor
pt-BR, escrita atômica do JSON) é independente do site.

Confira também `robots.txt` e os termos de uso do site antes de agendar
execuções periódicas, e mantenha o intervalo (`--pause`) educado com o
servidor.

## Uso local

```bash
cd scraper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scrape_shalom.py --output data/listings.json
```

Opções principais: `--base-url`, `--max-pages`, `--pause` (segundos entre
requisições). O script falha (exit code 1) sem sobrescrever a saída se
nenhum imóvel for extraído — evita publicar um JSON vazio por causa de um
seletor desatualizado.

Um fixture de exemplo (`data/listings.sample.json`) fica versionado pra
testar o widget sem depender do scraper — veja `frontend/vitrine.html`.

## Execução periódica (systemd timer)

Exemplos em [`../deploy/shalom-scraper.service`](../deploy/shalom-scraper.service)
e [`../deploy/shalom-scraper.timer`](../deploy/shalom-scraper.timer), no
mesmo padrão do `deploy/reels-api.service` já usado pela API. Ajuste
`WorkingDirectory`, `ExecStart` e o schedule (`OnCalendar`) conforme seu
servidor, depois:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now shalom-scraper.timer
```

Alternativa simples via cron (a cada 6h):

```
0 */6 * * * cd /opt/shalom/scraper && .venv/bin/python scrape_shalom.py >> /var/log/shalom-scraper.log 2>&1
```

## Publicando o JSON gerado

O widget só precisa que `data/listings.json` seja servido como arquivo
estático (Nginx, mesmo bucket do frontend, etc.) — nenhuma API é necessária
em runtime. Se o widget for consumir o JSON de outro domínio (app de vídeo
ou Vitrini Imóveis hospedados separadamente), garanta CORS liberado pra
leitura (`Access-Control-Allow-Origin`) no servidor que expõe o JSON.
