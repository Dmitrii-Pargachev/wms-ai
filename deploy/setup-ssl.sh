#!/bin/bash
# Настройка SSL для wms-ai.ru
# Запускать на сервере: bash deploy/setup-ssl.sh
set -e

echo "=== Устанавливаю certbot ==="
apt-get update -qq
apt-get install -y -qq certbot python3-certbot-nginx

echo "=== Получаю сертификат для wms-ai.ru ==="
# Wildcard требует DNS-01 challenge
# Если сертификат уже есть в другом месте — скопируй его
certbot certonly --dns-manual \
  --preferred-challenges dns \
  -d "wms-ai.ru" \
  -d "*.wms-ai.ru" \
  --agree-tos \
  --email admin@wms-ai.ru

echo "=== Обновляю Nginx конфиг ==="
cat > /etc/nginx/sites-available/wms-ai-new << 'NGINX'
server {
    listen 80;
    server_name wms-ai.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name wms-ai.ru;

    ssl_certificate /etc/letsencrypt/live/wms-ai.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wms-ai.ru/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /media/ {
        alias /opt/wms-ai/wms-ai-new/media/;
        expires 30d;
    }

    location /static/ {
        alias /opt/wms-ai/wms-ai-new/staticfiles/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name ~^(?<subdomain>.+)\.wms-ai\.ru$;

    ssl_certificate /etc/letsencrypt/live/wms-ai.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wms-ai.ru/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /media/ {
        alias /opt/wms-ai/wms-ai-new/media/;
        expires 30d;
    }

    location /static/ {
        alias /opt/wms-ai/wms-ai-new/staticfiles/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

echo "=== Проверяю синтаксис Nginx ==="
nginx -t

echo "=== Перезапускаю Nginx ==="
systemctl reload nginx

echo "=== Настраиваю автообновление сертификата ==="
echo "0 0 1 * * root certbot renew --quiet && systemctl reload nginx" > /etc/cron.d/certbot-renew

echo "=== Готово! ==="
echo "Попробуй: https://wms-ai.ru"
