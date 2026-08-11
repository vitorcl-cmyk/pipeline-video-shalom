# Shalom ADM — administração de locação

Sistema próprio para administrar imóveis alugados pela Shalom (proprietários,
inquilinos, imóveis, contratos), inspirado no Nido ADM, construído para não
depender mais de um fornecedor terceiro (o motivo original: o Nido ADM nunca
conseguiu integrar com o Banco Inter).

Este módulo vive dentro do repositório `pipeline-video-shalom` como uma
aplicação independente (`adm/`), com seu próprio backend e frontend — não
compartilha banco de dados nem código com o gerador de vídeos.

## O que já está pronto (v0.1 — cadastros essenciais)

- Login da equipe (JWT).
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

1. **Cobrança/financeiro**: já existem as contas fixas/variáveis e seus
   lançamentos mensais; falta gerar o **boleto/cobrança** de fato (aluguel +
   contas do mês, tudo junto) e o **repasse ao proprietário** (aluguel menos
   taxa de administração).
2. **Conciliação bancária com o Banco Inter**: usar a
   [API oficial do Banco Inter](https://developers.inter.co/) (conta PJ) para
   consultar extrato/pagamentos automaticamente e casar com as cobranças em
   aberto. Pré-requisito: certificado + credenciais de API geradas no
   Internet Banking PJ do Inter (registro de aplicação) — isso depende de
   ação da Shalom junto ao banco, não é algo que o código resolve sozinho.
3. **Reajuste de contratos**: cálculo automático de reajuste anual pelo
   índice configurado (IGP-M/IPCA) com alerta próximo ao vencimento.
4. **Documentos**: upload de contrato assinado, comprovantes, laudos de
   vistoria por imóvel/contrato.
5. **Permissões**: hoje qualquer usuário logado vê tudo; se a equipe crescer,
   adicionar papéis (admin / operacional).

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
