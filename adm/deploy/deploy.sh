#!/usr/bin/env bash
# Deploy do Shalom ADM em um servidor Debian/Ubuntu (apt) via SSH, como root.
#
# Uso (no próprio servidor, como root):
#   curl -fsSL https://raw.githubusercontent.com/vitorcl-cmyk/pipeline-video-shalom/claude/shalom-adm-build-kq0j6m/adm/deploy/deploy.sh | bash
#
# Idempotente: pode rodar de novo a qualquer momento para atualizar
# (git pull + reinstala deps + reinicia o serviço).
set -euo pipefail

REPO_URL="https://github.com/vitorcl-cmyk/pipeline-video-shalom.git"
BRANCH="claude/shalom-adm-build-kq0j6m"
APP_DIR="/opt/shalom-adm"
BACKEND_DIR="$APP_DIR/adm/backend"
FRONTEND_DIR="$APP_DIR/adm/frontend"
SERVICE_NAME="shalom-adm-api"
BACKEND_PORT=8010
PUBLIC_PORT=669

if [ "$(id -u)" -ne 0 ]; then
  echo "Rode como root (ou com sudo)." >&2
  exit 1
fi

echo "==> Instalando dependências do sistema"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git nginx

echo "==> Clonando/atualizando o repositório em $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

echo "==> Configurando ambiente virtual Python"
cd "$BACKEND_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "==> Gerando .env de produção (primeira instalação)"
  SECRET=$(openssl rand -hex 32)
  cat > "$BACKEND_DIR/.env" <<EOF
SECRET_KEY=$SECRET
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./adm.db
CORS_ORIGINS=["*"]
EOF
else
  echo "==> .env já existe, mantendo configuração atual"
fi

echo "==> Instalando serviço systemd"
cp "$APP_DIR/adm/deploy/shalom-adm-api.service" /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "==> Apontando frontend para /api (mesma origem, sem CORS)"
cat > "$FRONTEND_DIR/config.js" <<EOF
window.APP_CONFIG = {
  API_BASE_URL: "/api",
};
EOF

echo "==> Configurando Nginx na porta $PUBLIC_PORT"
cp "$APP_DIR/adm/deploy/nginx.conf.example" /etc/nginx/sites-available/shalom-adm.conf
ln -sf /etc/nginx/sites-available/shalom-adm.conf /etc/nginx/sites-enabled/shalom-adm.conf
nginx -t
systemctl reload nginx

echo ""
echo "==> Pronto! Shalom ADM disponível em http://vitor.serveftp.com:${PUBLIC_PORT}/"
echo "    Backend (systemd): systemctl status ${SERVICE_NAME}"
echo "    Logs:              journalctl -u ${SERVICE_NAME} -f"
