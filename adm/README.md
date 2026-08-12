# Shalom ADM — administração de locação

Sistema próprio para administrar imóveis alugados pela Shalom (proprietários,
inquilinos, imóveis, contratos), inspirado no Nido ADM, construído para não
depender mais de um fornecedor terceiro (o motivo original: o Nido ADM nunca
conseguiu integrar com o Banco Inter).

Este módulo vive dentro do repositório `pipeline-video-shalom` como uma
aplicação independente (`adm/`), com seu próprio backend e frontend — não
compartilha banco de dados nem código com o gerador de vídeos.

## O que já está pronto (v0.1 — cadastros essenciais)

- Login da equipe (JWT). Cadastro de novos usuários **desabilitado por
  padrão** (`ALLOW_REGISTRATION=false` no `.env`) enquanto o app está em fase
  de teste e acessível pela internet — ligue temporariamente no `.env` +
  reinicie o serviço quando precisar criar um usuário novo.
- **Esqueci minha senha**: gera um código de redefinição, mas como ainda não
  há servidor de e-mail configurado, o código não é enviado por e-mail — fica
  registrado no log da aplicação (`journalctl -u shalom-adm-api | grep
  "Código de redefinição"`), visível só para quem tem acesso ao servidor.
- **Proprietários**: dados pessoais, contato e dados bancários (para repasse).
- **Inquilinos**: dados pessoais e contato.
- **Imóveis**: endereço, tipo, valores de IPTU/condomínio, vinculado a um proprietário.
- **Contratos de locação**: vincula imóvel + inquilino, valor do aluguel, taxa
  de administração, índice de reajuste, vencimento, fiador.
  - O status do imóvel (`disponivel` / `alugado`) é atualizado automaticamente
    conforme contratos são criados/encerrados.
- **Dashboard**: contagens gerais, contratos vencendo em 30 dias, receita de
  aluguel e de administração projetadas (soma dos contratos ativos), contas
  pendentes.
- **Contas fixas e variáveis por contrato** (inspirado na tela equivalente do
  Nido ADM): cada contrato pode ter contas do tipo **fixa** (mesmo valor todo
  mês, ex.: taxa de condomínio quando não é rateada) ou **variável** (o valor
  muda mês a mês, caso típico da **água** em apartamentos onde o condomínio
  faz o rateio do consumo entre as unidades). Contas variáveis exigem um
  lançamento mensal manual com o valor daquele mês; contas fixas geram o
  lançamento automaticamente a partir do valor cadastrado. Acesse pelo botão
  "Contas" na lista de Contratos.
- **Cobrança mensal consolidada**: emite a cobrança do mês (aluguel + contas)
  por contrato, pedindo o valor de cada conta variável pendente antes de
  fechar o total. Histórico de cobranças emitidas por contrato.
  - Contas fixas podem ter **meses sem cobrança** (ex.: IPTU parcelado que
    não cobra em dezembro/janeiro em São Paulo) — marque os meses na conta
    e a cobrança do mês pula automaticamente, sem pedir valor.
  - Botão **"Ver cobrança"** mostra o recibo itemizado (Descrição/Valor +
    Total, no mesmo formato do boleto emitido no Banco Inter) com um resumo
    em texto pronto pra copiar e colar no campo de informações do boleto ou
    mandar direto pro inquilino.
- **Reajuste de contrato**: a coluna "Reajuste" na lista de Contratos mostra
  a próxima data (12 meses após o início ou o último reajuste) e sinaliza em
  laranja/vermelho quando está próxima ou atrasada. Como não há como buscar
  o índice IGP-M/IPCA do mês automaticamente (sem acesso externo), o usuário
  informa o percentual (consultado à parte no Banco Central) e o sistema
  calcula o novo valor do aluguel e mantém histórico por contrato. Acesse
  pelo botão "Reajustar contrato" na tela de Contas.
- **Usuários**: gerenciar quem tem acesso ao painel (criar, editar, excluir)
  estando logado — não depende mais de SSH nem de `ALLOW_REGISTRATION`.
- **Receita por contrato**: coluna "Receita adm." na lista de Contratos
  mostra quanto cada locação gera pra Shalom (aluguel × taxa de
  administração).
- **Próximo vencimento**: a lista de Contratos vem sempre ordenada pelo
  contrato ativo cujo boleto vence mais cedo (baseado no dia de vencimento
  do contrato) — quem precisa de atenção primeiro aparece no topo.
- **Repasse ao proprietário**: cada cobrança emitida já mostra quanto vai
  pro proprietário (aluguel − taxa de administração; as contas do mês não
  entram no repasse, são repassadas direto pra quem cobra).
- **Depósito caução com correção monetária automática**: informe o valor e
  a data do depósito no contrato e o sistema mantém atualizado, mês a mês,
  quanto o proprietário precisa devolver ao inquilino — sem precisar
  digitar nada manualmente. A correção usa a taxa oficial da poupança
  (Lei do Inquilinato, art. 38), buscada automaticamente na API pública do
  Banco Central (SGS, série 195 — diferente da "Calculadora do Cidadão",
  que é só um formulário HTML sem API pra automação). No servidor de
  produção, um timer do systemd roda essa busca sozinho todo dia 1 do mês
  (`adm/deploy/setup-caucao-timer.sh`); se a API do BCB estiver fora do ar
  num mês, o botão "Corrigir caução" na tela de Contas permite informar o
  percentual manualmente como alternativa, e a próxima execução automática
  recupera o período em atraso. Histórico completo de correções (fonte,
  percentual, valor anterior/novo) por contrato.
- **Análise de Ficha (triagem de candidato a inquilino por CPF/CNPJ)**:
  alternativa interna ao Detetive Alude. Digite um CPF ou CNPJ e o sistema
  já consulta automaticamente o que é gratuito e legítimo — dados
  cadastrais e societários (CNPJ, via BrasilAPI com fallback ReceitaWS) e
  servidor público federal/sanções CEIS (CPF, via Portal da Transparência,
  precisa de uma chave gratuita em `PORTAL_TRANSPARENCIA_TOKEN`) — e
  organiza no mesmo relatório o que precisa ser colado manualmente (SPC/
  Serasa pago) ou consultado à parte (judicial: não existe API nacional
  gratuita por CPF/CNPJ, então o sistema gera o link direto de consulta do
  TJSP em vez de fingir uma automação que não existe). Fecha com um
  parecer final (aprovado / aprovado com ressalvas / reprovado) e um
  relatório de texto pronto pra copiar. Fica solta, sem vínculo com um
  Inquilino cadastrado — a triagem acontece antes do candidato virar
  Inquilino no sistema.

## Estrutura

```
adm/
  backend/
    app/
      main.py          # monta o FastAPI e registra os routers
      models.py         # SQLAlchemy: User, Owner, Tenant, Property, Contract, Charge, ChargeLaunch
      schemas.py         # Pydantic (request/response)
      auth.py             # hash de senha (bcrypt) e JWT
      database.py          # engine/sessão SQLAlchemy
      config.py             # configurações via .env
      routers/
        auth.py, owners.py, tenants.py, properties.py, contracts.py, charges.py, dashboard.py
    requirements.txt
    .env.example
  frontend/
    index.html    # login + shell do app (sidebar + páginas)
    app.js         # lógica (fetch para API, modais de cadastro)
    styles.css
    config.js       # URL base da API
```

## Rodando localmente

### Backend

```bash
cd adm/backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8010
```

API em `http://localhost:8010`, documentação Swagger em `/docs`. Usa SQLite
(`adm.db`) por padrão — sem configuração extra.

### Frontend

```bash
cd adm/frontend
python3 -m http.server 5510
```

Abra `http://localhost:5510`. Confirme que `frontend/config.js` aponta para
`http://localhost:8010`.

### Uso

1. Crie uma conta na aba "Criar conta" (é a conta da equipe Shalom, não de
   proprietário/inquilino).
2. Cadastre proprietários e inquilinos.
3. Cadastre imóveis vinculando a um proprietário.
4. Crie contratos vinculando imóvel + inquilino — o imóvel muda para
   "Alugado" automaticamente.
5. Acompanhe tudo pelo Dashboard.

## Dados vindos do Nido ADM

Não foi possível migrar os dados automaticamente: o ambiente onde este
projeto é construído não tem acesso de rede ao `app.nidoadm.com.br` (bloqueio
de política de rede do ambiente), então não foi feito login/scraping na conta
Nido ADM da Shalom. Para trazer os dados existentes, exporte os cadastros do
Nido ADM (CSV/Excel/relatórios) e me envie os arquivos — dá pra escrever um
script de importação em `adm/backend/scripts/` a partir deles.

## Roadmap (próximos módulos)

1. **Conciliação bancária com o Banco Inter**: usar a
   [API oficial do Banco Inter](https://developers.inter.co/) (conta PJ) para
   consultar extrato/pagamentos automaticamente e casar com as cobranças em
   aberto. Pré-requisito: certificado + credenciais de API geradas no
   Internet Banking PJ do Inter (registro de aplicação) — isso depende de
   ação da Shalom junto ao banco, não é algo que o código resolve sozinho.
   O boleto em si (barras/Pix) continua sendo emitido manualmente no site
   do Inter — o "Ver cobrança" já deixa o valor e o resumo prontos pra
   colar lá.
2. **Documentos**: upload de contrato assinado, comprovantes, laudos de
   vistoria por imóvel/contrato.
3. **Permissões**: hoje qualquer usuário logado vê e edita tudo (inclusive
   outros usuários); se a equipe crescer, adicionar papéis (admin / operacional).
4. **Portal do proprietário / inquilino**: acesso separado e mais simples
   pra cada um ver só os próprios dados, sem o painel completo da equipe.
5. **Régua de inadimplência**: lembretes automáticos (WhatsApp/e-mail) pra
   cobranças vencidas — depende de integração paga de envio.

## Produção

Mesmo padrão do projeto de vídeos: Gunicorn+Uvicorn atrás de Nginx, Postgres
em vez de SQLite (`DATABASE_URL` no `.env`), `SECRET_KEY` forte gerada com
`openssl rand -hex 32`, `CORS_ORIGINS` restrito ao domínio do frontend.

### Deploy rápido (servidor Debian/Ubuntu, via SSH como root)

```bash
curl -fsSL https://raw.githubusercontent.com/vitorcl-cmyk/pipeline-video-shalom/claude/shalom-adm-build-kq0j6m/adm/deploy/deploy.sh | bash
```

O script (`adm/deploy/deploy.sh`) é idempotente — instala dependências,
clona/atualiza o repositório em `/opt/shalom-adm`, sobe o backend como
serviço systemd (`shalom-adm-api`) e configura o Nginx para servir o
frontend + proxy da API na porta **669**. Rodar de novo atualiza tudo
(`git pull` + reinstala dependências + reinicia o serviço).

Comandos úteis depois do deploy:

```bash
systemctl status shalom-adm-api      # status do backend
journalctl -u shalom-adm-api -f      # logs em tempo real
```

### Acesso externo (fora da rede local / celular)

Se a porta 669 não estiver liberada no roteador (comum em provedor
residencial com CGNAT), use um túnel Cloudflare permanente rodando como
serviço no próprio servidor — assim continua acessível mesmo com o PC/
notebook desligado:

```bash
curl -fsSL https://raw.githubusercontent.com/vitorcl-cmyk/pipeline-video-shalom/claude/shalom-adm-build-kq0j6m/adm/deploy/setup-tunnel.sh | bash
```

O comando mostra a URL atual do túnel (`https://algo.trycloudflare.com`) no
final. Como não há domínio próprio configurado no Cloudflare, essa URL é
aleatória e só muda se o serviço reiniciar. Pra recuperar a URL depois:

```bash
journalctl -u cloudflared-quicktunnel --no-pager -n 50 | grep trycloudflare
```

Para uma URL fixa de verdade (ex.: `adm.shalomconsultoria.com.br`), é
necessário migrar o DNS do domínio para o Cloudflare — combine essa etapa
separadamente antes de fazer, pois mexe num domínio de produção.

### Correção automática do depósito caução

Depois do primeiro `deploy.sh`, rode uma vez pra ligar a correção mensal
automática da caução (busca a taxa da poupança na API do Banco Central):

```bash
curl -fsSL https://raw.githubusercontent.com/vitorcl-cmyk/pipeline-video-shalom/claude/shalom-adm-build-kq0j6m/adm/deploy/setup-caucao-timer.sh | bash
```

Isso instala um timer do systemd (`shalom-adm-caucao.timer`) que roda a
correção sozinho todo dia 1 do mês às 3h, e já testa rodando uma vez na
hora. Comandos úteis:

```bash
systemctl list-timers shalom-adm-caucao.timer   # ver quando roda de novo
journalctl -u shalom-adm-caucao.service -f       # ver o resultado da última execução
systemctl start shalom-adm-caucao.service         # rodar manualmente agora
```
