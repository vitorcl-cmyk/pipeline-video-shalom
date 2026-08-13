# Reels Imobiliário — Vídeos Cinematográficos com FastAPI + FFmpeg

Gera vídeos verticais (estilo Reels/Stories, 1080x1920) a partir de fotos de
imóveis: efeito Ken Burns por foto, transições crossfade entre elas e uma
trilha ambiente 100% sintetizada pelo próprio FFmpeg (sem áudio externo).

## Estrutura do projeto

```
backend/
  app/
    main.py        # rotas da API (auth, upload, jobs, download)
    pipeline.py     # motor FFmpeg (Ken Burns, crossfade, trilha sintetizada)
    models.py       # SQLAlchemy: User, VideoJob
    auth.py         # hash de senha (bcrypt) e JWT
    schemas.py      # Pydantic (request/response)
    config.py       # configurações via .env
    database.py     # engine/sessão SQLAlchemy
  painel/          # painel de admin, servido pela própria API em /painel
    index.html
    admin.js
    styles.css
  requirements.txt
  .env.example
frontend/
  index.html        # UI (login, upload, lista de vídeos)
  app.js            # lógica (fetch para API, polling de status)
  styles.css
  config.js         # URL base da API
deploy/
  reels-api.service     # exemplo de unit systemd (gunicorn+uvicorn)
  nginx.conf.example     # exemplo de reverse proxy + frontend estático
```

## Pré-requisitos

- Python 3.11+
- FFmpeg instalado e disponível no PATH (`ffmpeg -version` deve funcionar)
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: baixe em https://ffmpeg.org/download.html e adicione ao PATH

## Rodando localmente

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
copy .env.example .env        # Windows (Linux/macOS: cp .env.example .env)
```

Edite `.env` se quiser mudar a `SECRET_KEY`, limites, etc. Por padrão usa
SQLite (`app.db`), o que já funciona sem nenhuma configuração extra.

```bash
uvicorn app.main:app --reload --port 8000
```

A API sobe em `http://localhost:8000`. Documentação interativa (Swagger) em
`http://localhost:8000/docs`.

### 2. Frontend

O frontend é HTML/JS/CSS puro, sem build step. Basta servir os arquivos
estáticos. A forma mais simples:

```bash
cd frontend
python -m http.server 5500
```

Abra `http://localhost:5500`. Confirme que `frontend/config.js` aponta para
`http://localhost:8000` (valor padrão já configurado para desenvolvimento).

### 3. Uso

1. Crie uma conta na aba "Criar conta".
2. Faça login.
3. Selecione várias fotos do imóvel (a ordem de seleção define a ordem no
   vídeo), escolha um estilo (clássico / moderno / suave) e clique em
   "Gerar vídeo".
4. O vídeo é processado em background pelo servidor. A lista de vídeos
   atualiza automaticamente (polling a cada 5s) até o status mudar para
   "Concluído", quando o botão "Baixar" fica disponível.

## Limite diário

Cada usuário pode gerar no máximo **10 vídeos por dia** (`DAILY_VIDEO_LIMIT`
no `.env`). O contador reseta à meia-noite UTC. Ao atingir o limite, a API
responde `429 Too Many Requests`.

## Estilos disponíveis

| Estilo    | Zoom Ken Burns | Transição   | Trilha sintetizada                    |
|-----------|----------------|-------------|----------------------------------------|
| classico  | até 1.15x, lento | fade      | tríade de Sol maior, tom quente        |
| moderno   | até 1.28x, rápido | wipeleft | tétrade grave, mais dinâmica           |
| suave     | até 1.10x, muito lento | dissolve | tríade de Dó maior, pastel/calma  |

A trilha ambiente é gerada inteiramente pelo FFmpeg (`sine` + `amix` +
`lowpass` + `aecho`) — não depende de nenhum arquivo de música externo, então
não há questões de licenciamento.

## Rodando em produção

### Backend (systemd + Gunicorn/Uvicorn)

1. Clone o projeto em `/opt/reels-imobiliario` no servidor.
2. Crie o virtualenv e instale as dependências como acima, mas com
   `pip install -r requirements.txt` dentro de `/opt/reels-imobiliario/backend`.
3. Configure `/opt/reels-imobiliario/backend/.env` com valores de produção:
   - `SECRET_KEY` forte (`openssl rand -hex 32`)
   - `DATABASE_URL` apontando para Postgres (recomendado em produção)
   - `CORS_ORIGINS` restrito ao domínio do frontend
4. Copie `deploy/reels-api.service` para `/etc/systemd/system/reels-api.service`
   e ajuste `User`, `WorkingDirectory` e paths conforme sua instalação.
5. Ative o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable reels-api
sudo systemctl start reels-api
sudo systemctl status reels-api
```

### Nginx (reverse proxy + frontend estático)

1. Copie `deploy/nginx.conf.example` para
   `/etc/nginx/sites-available/reels-imobiliario.conf`, ajuste `server_name`
   e os caminhos de certificado TLS (ex.: via Let's Encrypt/Certbot).
2. Ative o site e recarregue:

```bash
sudo ln -s /etc/nginx/sites-available/reels-imobiliario.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

3. Como o Nginx expõe a API em `/api/`, atualize `frontend/config.js` em
   produção para `API_BASE_URL: "/api"` (mesma origem do frontend, evita
   configurar CORS separadamente).

### Painel de admin

O painel de admin (`backend/painel/`) é servido diretamente pela API via
`StaticFiles`, montado em `/painel`. Não depende do frontend nem de
`config.js` -- as chamadas do `admin.js` usam caminhos relativos
(`/admin/...`), sempre na mesma origem de onde `/painel` foi carregado.

- Local: `http://localhost:8000/painel`
- Produção (atrás do Nginx do `deploy/nginx.conf.example`, que expõe
  `/painel` e `/admin/` diretamente na API): `https://reels.seudominio.com.br/painel`

### Observações de produção

- `client_max_body_size` no Nginx e `MAX_UPLOAD_MB`/`MAX_PHOTOS_PER_JOB` no
  backend devem ser compatíveis com o tamanho/quantidade real de fotos que
  os usuários vão enviar.
- A geração de vídeo roda em background dentro do próprio processo da API
  (via `BackgroundTasks` do FastAPI) — adequado para uso pequeno/médio. Para
  volume alto, considere migrar para uma fila dedicada (Celery/RQ + Redis)
  mantendo a mesma função `pipeline.generate_video`.
- FFmpeg deve estar instalado na máquina que roda o backend (não é uma
  dependência Python).
- Faça backup periódico do diretório `backend/storage/outputs` (vídeos
  gerados) e do banco de dados.

## Endpoints principais

| Método | Rota                     | Descrição                              |
|--------|---------------------------|-----------------------------------------|
| POST   | `/auth/register`          | Cria uma conta                          |
| POST   | `/auth/login`              | Login (OAuth2 form), retorna JWT        |
| GET    | `/auth/me`                 | Dados do usuário autenticado            |
| POST   | `/jobs`                    | Upload de fotos + geração de vídeo      |
| GET    | `/jobs`                    | Lista os vídeos do usuário              |
| GET    | `/jobs/{id}`                | Detalhe de um job                       |
| GET    | `/jobs/{id}/download`       | Baixa o vídeo gerado (MP4)              |
| GET    | `/usage/today`              | Uso do limite diário                    |
| GET    | `/health`                   | Health check                            |

Todas as rotas exceto `/auth/register`, `/auth/login` e `/health` exigem o
header `Authorization: Bearer <token>`.
