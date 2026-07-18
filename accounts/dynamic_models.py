import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger('accounts.dynamic')

# Map field types to SQL column definitions
FIELD_TYPE_MAP = {
    'text': 'VARCHAR(255)',
    'number': 'DECIMAL(12,2)',
    'date': 'DATE',
    'select': 'VARCHAR(100)',
    'multiselect': 'TEXT',
    'boolean': 'BOOLEAN DEFAULT 0',
    'email': 'VARCHAR(255)',
    'phone': 'VARCHAR(50)',
    'url': 'VARCHAR(500)',
    'file': 'VARCHAR(500)',
    'relation': 'INTEGER',
}


def _get_db_path(db_alias):
    """Get SQLite file path for a given db_alias."""
    if db_alias == 'default':
        from django.conf import settings
        return str(settings.DATABASES['default']['NAME'])
    slug = db_alias.replace('tenant_', '')
    from tenants.manager import get_tenant_manager
    tm = get_tenant_manager()
    return str(tm.get_db_path(slug))


def _get_conn(db_alias):
    """Get a raw sqlite3 connection for the given alias."""
    db_path = _get_db_path(db_alias)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


class DynamicModelService:
    """Сервис для динамического создания и управления SQL-таблицами."""

    def __init__(self, db_alias):
        self.db_alias = db_alias

    def create_table(self, table_schema):
        """Создать реальную SQL-таблицу из схемы."""
        fields = table_schema.fields.all().order_by('position', 'created_at')
        if not fields.exists():
            raise ValueError("Таблица должна иметь хотя бы одно поле")

        ddl = self._build_create_ddl(table_schema.db_table_name, fields)
        conn = _get_conn(self.db_alias)
        try:
            conn.execute(ddl)
            conn.commit()
            logger.info(f"Created table {table_schema.db_table_name} in {self.db_alias}")
        finally:
            conn.close()

    def alter_table(self, table_schema):
        """Обновить таблицу (добавить колонки)."""
        current_columns = self._get_columns(table_schema.db_table_name)
        fields = table_schema.fields.all().order_by('position', 'created_at')

        conn = _get_conn(self.db_alias)
        try:
            for field in fields:
                if field.name not in current_columns:
                    col_def = self._get_column_def(field)
                    ddl = f"ALTER TABLE {table_schema.db_table_name} ADD COLUMN {col_def}"
                    conn.execute(ddl)
                    logger.info(f"Added column {field.name} to {table_schema.db_table_name}")
            conn.commit()
        finally:
            conn.close()

    def drop_table(self, table_schema):
        """Удалить таблицу."""
        conn = _get_conn(self.db_alias)
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table_schema.db_table_name}")
            conn.commit()
            logger.info(f"Dropped table {table_schema.db_table_name}")
        finally:
            conn.close()

    def insert_row(self, table_name, data):
        """Вставить строку в таблицу."""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        conn = _get_conn(self.db_alias)
        try:
            cursor = conn.execute(sql, list(data.values()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_row(self, table_name, row_id, data):
        """Обновить строку."""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
        conn = _get_conn(self.db_alias)
        try:
            conn.execute(sql, list(data.values()) + [row_id])
            conn.commit()
        finally:
            conn.close()

    def delete_row(self, table_name, row_id):
        """Удалить строку."""
        sql = f"DELETE FROM {table_name} WHERE id = ?"
        conn = _get_conn(self.db_alias)
        try:
            conn.execute(sql, [row_id])
            conn.commit()
        finally:
            conn.close()

    def query_rows(self, table_name, filters=None, sort=None, page=1, per_page=50):
        """Получить строки с фильтрацией, сортировкой и пагинацией."""
        where_clause = ""
        params = []

        if filters:
            conditions = []
            for field, value in filters.items():
                if value is not None and value != '':
                    conditions.append(f"{field} = ?")
                    params.append(value)
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)

        order_clause = f" ORDER BY {sort}" if sort else " ORDER BY id DESC"

        conn = _get_conn(self.db_alias)
        try:
            # Count total
            count_sql = f"SELECT COUNT(*) FROM {table_name}{where_clause}"
            cursor = conn.execute(count_sql, params)
            total = cursor.fetchone()[0]

            # Get rows
            offset = (page - 1) * per_page
            sql = f"SELECT * FROM {table_name}{where_clause}{order_clause} LIMIT ? OFFSET ?"
            cursor = conn.execute(sql, params + [per_page, offset])
            columns = [desc[0] for desc in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return {
                'rows': rows,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page,
            }
        finally:
            conn.close()

    def _build_create_ddl(self, table_name, fields):
        """Построить CREATE TABLE DDL."""
        columns = ['id INTEGER PRIMARY KEY AUTOINCREMENT']
        for field in fields:
            col_def = self._get_column_def(field)
            columns.append(col_def)
        columns.append('created_at DATETIME DEFAULT CURRENT_TIMESTAMP')
        columns.append('updated_at DATETIME DEFAULT CURRENT_TIMESTAMP')
        return f"CREATE TABLE {table_name} ({', '.join(columns)})"

    def _get_column_def(self, field):
        """Получить определение колонки для поля."""
        sql_type = FIELD_TYPE_MAP.get(field.field_type, 'VARCHAR(255)')
        parts = [field.name, sql_type]
        if field.required:
            # SQLite не может ADD COLUMN NOT NULL без DEFAULT
            pass
        return ' '.join(parts)

    def _get_columns(self, table_name):
        """Получить список колонок таблицы."""
        try:
            conn = _get_conn(self.db_alias)
            try:
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                return [row[1] for row in cursor.fetchall()]
            finally:
                conn.close()
        except Exception:
            return []
