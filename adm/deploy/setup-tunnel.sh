#!/usr/bin/env bash
# Instala/configura o túnel Cloudflare como serviço permanente (systemd),
# pra ficar acessível de qualquer lugar sem depender de terminal aberto.
#
# Uso (no servidor, como root):
#   curl -fsSL https://raw.githubusercontent.com/vitorcl-cmyk/pipeline-video-shalom/claude/shalom-adm-build-kq0j6m/adm/deploy/setup-tunnel.sh | bash
#
# Aviso: sem domínio próprio configurado no Cloudflare, a URL gerada é
# aleatória (algo.trycloudflare.com) e só muda se o serviço reiniciar
# (reboot do servidor, por exemplo). Para uma URL fixa de verdade
# (ex.: adm.shalomconsultoria.com.br), é preciso migrar o DNS do domínio
# para o Cloudflare — combine isso à parte antes de fazer.
set -euo pipefail

APP_DIR="/opt/shalom-adm"
SERVICE_NAME="cloudflared-quicktunnel"

if [ "$(id -u)" -ne 0 ]; then
  echo "Rode como root (ou com sudo)." >&2
  exit 1
fi

if [ ! -f /usr/local/bin/cloudflared ]; then
  echo "==> Baixando cloudflared"
  curl -Ls https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
  chmod +x /usr/local/bin/cloudflared
fi

echo "==> Instalando serviço systemd"
cp "$APP_DIR/adm/deploy/cloudflared-quicktunnel.service" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "==> Aguardando o túnel subir (pode levar até 30s)..."
URL=""
for i in $(seq 1 15); do
  sleep 2
  URL=$(journalctl -u "${SERVICE_NAME}" --no-pager -n 80 2>/dev/null | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | tail -n 1 || true)
  if [ -n "$URL" ]; then
    break
  fi
done

echo ""
if [ -n "$URL" ]; then
  echo "==> URL atual do túnel: ${URL}"
else
  echo "==> Ainda não consegui capturar a URL automaticamente."
  echo "    Rode este comando em alguns segundos para ver:"
  echo "    journalctl -u ${SERVICE_NAME} --no-pager -n 50 | grep trycloudflare"
fi

echo ""
echo "Comandos úteis:"
echo "  systemctl status ${SERVICE_NAME}                          # ver se está rodando"
echo "  journalctl -u ${SERVICE_NAME} --no-pager -n 50 | grep trycloudflare   # ver a URL atual"
