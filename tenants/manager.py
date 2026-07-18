import os
import shutil
from pathlib import Path
from django.conf import settings


class TenantManager:
    """
    Менеджер для управления директориями бизнесов.
    Каждый бизнес имеет свою директорию с БД, ключами и настройками.
    """

    def __init__(self):
        self.base_dir = Path(settings.BASE_DIR).parent / 'businesses'
        self.base_dir.mkdir(exist_ok=True)

    def get_business_dir(self, slug: str) -> Path:
        """Получить путь к директории бизнеса."""
        business_dir = self.base_dir / slug
        business_dir.mkdir(exist_ok=True)
        return business_dir

    def get_db_path(self, slug: str) -> Path:
        """Получить путь к БД бизнеса."""
        return self.get_business_dir(slug) / 'db.sqlite3'

    def get_env_path(self, slug: str) -> Path:
        """Получить путь к .env файлу бизнеса."""
        return self.get_business_dir(slug) / '.env'

    def get_keys_dir(self, slug: str) -> Path:
        """Получить путь к директории ключей бизнеса."""
        keys_dir = self.get_business_dir(slug) / 'keys'
        keys_dir.mkdir(exist_ok=True)
        return keys_dir

    def get_google_credentials_path(self, slug: str) -> Path:
        """Получить путь к ключу Google Service Account."""
        return self.get_keys_dir(slug) / 'google-service-account.json'

    def get_media_dir(self, slug: str) -> Path:
        """Получить путь к медиа файлам бизнеса (аватары и т.д.)."""
        media_dir = self.get_business_dir(slug) / 'media'
        media_dir.mkdir(exist_ok=True)
        return media_dir

    def get_logs_dir(self, slug: str) -> Path:
        """Получить путь к логам бизнеса."""
        logs_dir = self.get_business_dir(slug) / 'logs'
        logs_dir.mkdir(exist_ok=True)
        return logs_dir

    def get_business_config(self, slug: str) -> dict:
        """Получить конфигурацию бизнеса из .env файла."""
        env_path = self.get_env_path(slug)
        config = {}

        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    config[key.strip()] = value.strip()

        return config

    def set_business_config(self, slug: str, config: dict):
        """Сохранить конфигурацию бизнеса в .env файл."""
        env_path = self.get_env_path(slug)

        lines = []
        for key, value in config.items():
            lines.append(f'{key}={value}')

        env_path.write_text('\n'.join(lines) + '\n')

    def setup_business(self, slug: str, name: str, business_type: str = 'retail'):
        """Первоначальная настройка директории бизнеса."""
        business_dir = self.get_business_dir(slug)

        # Create directories
        self.get_keys_dir(slug)
        self.get_media_dir(slug)
        self.get_logs_dir(slug)

        # Create default .env
        default_config = {
            'BUSINESS_NAME': name,
            'BUSINESS_TYPE': business_type,
            'BUSINESS_SLUG': slug,
            'GOOGLE_SHEETS_ENABLED': 'false',
            'GOOGLE_SHEETS_CREDENTIALS': '',
            'GOOGLE_SHEETS_SPREADSHEET_ID': '',
            'FERNET_KEY': '',
        }

        if not self.get_env_path(slug).exists():
            self.set_business_config(slug, default_config)

        return business_dir

    def delete_business(self, slug: str):
        """Удалить директорию бизнеса (с архивированием)."""
        business_dir = self.get_business_dir(slug)
        if business_dir.exists():
            # Archive before delete
            archive_dir = self.base_dir / '_archived'
            archive_dir.mkdir(exist_ok=True)
            shutil.move(str(business_dir), str(archive_dir / f'{slug}_archived'))

    def list_businesses(self) -> list:
        """Список всех бизнесов (директорий)."""
        businesses = []
        if self.base_dir.exists():
            for item in self.base_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_'):
                    config = self.get_business_config(item.name)
                    businesses.append({
                        'slug': item.name,
                        'name': config.get('BUSINESS_NAME', item.name),
                        'type': config.get('BUSINESS_TYPE', 'unknown'),
                    })
        return businesses

    def get_database_config(self, slug: str) -> dict:
        """Получить конфигурацию БД для бизнеса."""
        db_path = self.get_db_path(slug)

        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(db_path),
            'OPTIONS': {
                'timeout': 20,
            },
            'ATOMIC_REQUESTS': False,
            'AUTOCOMMIT': True,
            'CONN_MAX_AGE': 0,
            'CONN_HEALTH_CHECKS': False,
            'HOST': '',
            'PORT': '',
            'USER': '',
            'PASSWORD': '',
            'TIME_ZONE': None,
            'TEST': {
                'CHARSET': None,
                'COLLATION': None,
                'MIGRATE': True,
                'MIRROR': None,
                'NAME': None,
            },
        }


# Singleton
_tenant_manager = None


def get_tenant_manager() -> TenantManager:
    """Получить экземпляр TenantManager."""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager
