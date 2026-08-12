#!/usr/bin/env bash
# Instala o timer systemd que corrige automaticamente o valor dos
# depósitos caução todo dia 1 às 3h, buscando a taxa da poupança na API
# pública do Banco Central (SGS, série 195) — sem precisar digitar nada
# todo mês. Rode de novo depois de um `deploy.sh` se o serviço/timer
# ainda não existir (deploy.sh não mexe nisso sozinho).
#
# Uso (no servidor, como root):
#   curl -fsSL https://raw.githubusercontent.com/vitorcl-cmyk/pipeline-video-shalom/claude/shalom-adm-build-kq0j6m/adm/deploy/setup-caucao-timer.sh | bash
set -euo pipefail

APP_DIR="/opt/shalom-adm"
SERVICE_NAME="shalom-adm-caucao"

if [ "$(id -u)" -ne 0 ]; then
  echo "Rode como root (ou com sudo)." >&2
  exit 1
fi

echo "==> Instalando serviço + timer systemd"
cp "$APP_DIR/adm/deploy/${SERVICE_NAME}.service" "/etc/systemd/system/${SERVICE_NAME}.service"
cp "$APP_DIR/adm/deploy/${SERVICE_NAME}.timer" "/etc/systemd/system/${SERVICE_NAME}.timer"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.timer"
systemctl restart "${SERVICE_NAME}.timer"

echo "==> Testando agora (roda a correção uma vez, imediatamente)"
systemctl start "${SERVICE_NAME}.service"
sleep 2
journalctl -u "${SERVICE_NAME}.service" --no-pager -n 30

echo ""
echo "==> Pronto. A partir de agora, todo dia 1 do mês às 3h a correção roda sozinha."
echo "Comandos úteis:"
echo "  systemctl list-timers ${SERVICE_NAME}.timer     # ver quando roda de novo"
echo "  journalctl -u ${SERVICE_NAME}.service -f         # ver o resultado da última execução"
echo "  systemctl start ${SERVICE_NAME}.service           # rodar manualmente agora"
