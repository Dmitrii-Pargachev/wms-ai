class TenantDatabaseRouter:
    """
    Роутер баз данных для мульти-тенантности.
    Направляет запросы в нужную БД на основе текущего бизнеса.
    """

    def __init__(self):
        self._current_db = None

    def set_current_db(self, db_name: str):
        """Установить текущую БД."""
        self._current_db = db_name

    def get_current_db(self) -> str:
        """Получить текущую БД."""
        return self._current_db or 'default'

    def db_for_read(self, model, **hints):
        """Определить БД для чтения."""
        # Accounts models (Business, BusinessMembership) always use default
        if model._meta.app_label == 'accounts':
            return 'default'

        # All other models use current tenant database
        # Never fall back to 'default' — each business has its own DB
        return self._current_db

    def db_for_write(self, model, **hints):
        """Определить БД для записи."""
        # Accounts models always use default
        if model._meta.app_label == 'accounts':
            return 'default'

        # All other models use current tenant database
        # Never fall back to 'default' — each business has its own DB
        return self._current_db

    def allow_relation(self, obj1, obj2, **hints):
        """Разрешить связи между объектами."""
        # Allow relations within the same database
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Разрешить миграции."""
        # All apps migrate on default database (needed for demo data and management commands)
        if db == 'default':
            return True

        # Tenant databases get all app migrations too
        return True


# Singleton
_router = None


def get_tenant_router() -> TenantDatabaseRouter:
    """Получить экземпляр TenantDatabaseRouter."""
    global _router
    if _router is None:
        _router = TenantDatabaseRouter()
    return _router
