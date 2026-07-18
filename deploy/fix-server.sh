#!/bin/bash
# Срочный фикс: миграции + Nginx
# Запуск: bash deploy/fix-server.sh

set -e

VPS="root@194.58.104.148"

echo "=== Фикс: миграции и проверка Nginx ==="

ssh $VPS << 'ENDSSH'
set -e

echo "--- 1. Проверяю .env ---"
cd /opt/wms-ai/wms-ai-new
if [ ! -f .env ]; then
    echo "ОШИБКА: .env не найден!"
    exit 1
fi
cat .env
echo ""

echo "--- 2. Проверяю venv ---"
if [ ! -d venv ]; then
    echo "Создаю venv..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "OK: зависимости установлены"
echo ""

echo "--- 3. Применяю миграции ---"
python3 manage.py migrate --verbosity=2
echo ""

echo "--- 4. Проверяю таблицу django_session ---"
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='django_session'\")
result = cursor.fetchone()
if result:
    print('OK: таблица django_session существует')
else:
    print('ОШИБКА: таблица django_session НЕ существует!')
"
echo ""

echo "--- 5. Создаю superuser если нужно ---"
python3 manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser создан')
else:
    print('Superuser уже существует')
"
echo ""

echo "--- 6. Collectstatic ---"
python3 manage.py collectstatic --noinput
echo ""

echo "--- 7. Перезапускаю gunicorn ---"
systemctl restart wms-ai-new
sleep 1
systemctl status wms-ai-new --no-pager -l
echo ""

echo "--- 8. Проверяю Nginx конфиг ---"
cat /etc/nginx/sites-available/wms-ai-new
echo ""

echo "--- 9. Проверяю активные конфиги Nginx ---"
ls -la /etc/nginx/sites-enabled/
echo ""

echo "--- 10. Проверяю Nginx syntax ---"
nginx -t
echo ""

echo "--- 11. Перезапускаю Nginx ---"
systemctl restart nginx
sleep 1
echo "OK: Nginx перезапущен"
echo ""

echo "--- 12. Тестирую локально ---"
curl -s -o /dev/null -w "HTTP %{http_code}" http://127.0.0.1:8001/login/ 2>/dev/null || echo "gunicorn не отвечает"
echo ""
curl -s -o /dev/null -w "HTTP %{http_code}" http://127.0.0.1/new/login 2>/dev/null || echo "Nginx не отвечает"
echo ""

echo "=== Готово! ==="
echo "Попробуй: http://wms-ai.ru/new/login"
ENDSSH
