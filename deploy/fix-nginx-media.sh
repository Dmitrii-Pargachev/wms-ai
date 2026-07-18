#!/bin/bash
# Fix Nginx: add media location
set -e

VPS="root@194.58.104.148"

ssh $VPS << 'ENDSSH'
set -e

echo "--- 1. Создаю media директорию ---"
mkdir -p /opt/wms-ai/wms-ai-new/media/avatars
chmod 755 /opt/wms-ai/wms-ai-new/media
chmod 755 /opt/wms-ai/wms-ai-new/media/avatars
echo "OK: media создана"

echo "--- 2. Проверяю Nginx конфиг ---"
NGINX_CONF="/etc/nginx/sites-available/wms-ai-new"
if grep -q "location /media" "$NGINX_CONF" 2>/dev/null; then
    echo "OK: media location уже есть"
else
    echo "Добавляю media location..."
    sed -i '/server_name /a\
    location /media/ {\
        alias /opt/wms-ai/wms-ai-new/media/;\
        expires 30d;\
    }' "$NGINX_CONF"
    echo "OK: media location добавлен"
fi

echo "--- 3. Проверяю синтаксис Nginx ---"
nginx -t

echo "--- 4. Перезапускаю Nginx ---"
systemctl reload nginx
echo "OK: Nginx перезапущен"

echo "--- 5. Проверяю доступность ---"
curl -s -o /dev/null -w "HTTP %{http_code}" http://127.0.0.1:8001/ || echo "gunicorn не отвечает"
echo ""
ENDSSH

echo "=== Готово! ==="
