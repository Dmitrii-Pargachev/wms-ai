#!/bin/bash
# Деплой WMS-AI на VPS
set -e

VPS="root@194.58.104.148"
REMOTE_DIR="/opt/wms-ai/wms-ai-new"
LOCAL_DIR="/Users/dmitripargacev/PycharmProjects/wms-ai-new"

echo "=== Загружаю файлы ==="
cd $LOCAL_DIR

scp -r config/ $VPS:$REMOTE_DIR/
scp -r tenants/ $VPS:$REMOTE_DIR/
scp -r accounts/ $VPS:$REMOTE_DIR/
scp -r inventory/ $VPS:$REMOTE_DIR/
scp -r analytics/ $VPS:$REMOTE_DIR/
scp -r reports/ $VPS:$REMOTE_DIR/
scp -r integrations/ $VPS:$REMOTE_DIR/
scp -r bot/ $VPS:$REMOTE_DIR/
scp -r templates/ $VPS:$REMOTE_DIR/
scp -r static/ $VPS:$REMOTE_DIR/
scp manage.py requirements.txt $VPS:$REMOTE_DIR/

echo "=== Перезапуск ==="
ssh $VPS "cd /opt/wms-ai/wms-ai-new && source venv/bin/activate && rm -f inventory/migrations/0005_add_business_isolation.py inventory/migrations/0005_business_isolation.py && python3 manage.py migrate --verbosity=0 && systemctl restart wms-ai-new && echo 'OK'"

echo ""
echo "DEPLOY DONE!"
echo "Main: http://wms-ai.ru/"
echo "Demo: http://demo.wms-ai.ru/login/"
