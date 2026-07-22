"""
Database Connection — MySQL (Production)
Sử dụng aiomysql cho async MySQL access.
Hỗ trợ connection pool, prepared statements, và transaction management.
"""
import os
import json
import re
import logging
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from config.settings import settings

log = logging.getLogger("ai-property-advisor")

_IS_INITIALIZED = False


class Database:
    """MySQL database connection manager using aiomysql"""

    def __init__(self):
        self._pool = None
        self._aiomysql = None
        self.backend = "mysql"

    @property
    def is_mysql(self) -> bool:
        return True

    async def connect(self) -> None:
        """Initialize MySQL connection pool. Falls back to mock mode if MySQL unavailable."""
        url = settings.DATABASE_URL
        if not url.startswith("mysql://"):
            log.warning("DATABASE_URL is not MySQL (%s). Using mock mode.", url)
            return

        try:
            import aiomysql as mysql_driver
            self._aiomysql = mysql_driver
            # Parse MySQL URL: mysql://user:pass@host:port/db
            parts = url.replace("mysql://", "").split("@")
            user_pass = parts[0].split(":")
            host_port_db = parts[1].split("/")
            host_port = host_port_db[0].split(":")

            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ""
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 3306
            db_name = host_port_db[1] if len(host_port_db) > 1 else "hdbhms"

            self._pool = await mysql_driver.create_pool(
                host=host,
                port=port,
                user=user,
                password=password,
                db=db_name,
                minsize=1,
                maxsize=5,
                charset='utf8mb4',
                autocommit=True,
            )
            log.info("MySQL pool created: %s@%s:%d/%s", user, host, port, db_name)
        except Exception as e:
            log.warning("MySQL connection failed: %s. Using mock mode.", e)
            self._pool = None

    async def close(self) -> None:
        """Close the connection pool"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            log.info("MySQL pool closed")

    def _convert_params(self, query: str, args: tuple = ()) -> tuple:
        """
        Convert $1, $2, ... positional parameters to MySQL %s format,
        and expand args to match the number of %s placeholders.
        
        Handles repeated $N references: if $1 appears 3 times in the query,
        the arg for $1 is repeated 3 times in the output.
        
        Returns: (mysql_query, expanded_args_tuple)
        """
        refs = re.findall(r'\$(\d+)', query)
        # Replace all $N with %s
        mysql_query = re.sub(r'\$(\d+)', r'%s', query)
        # Build expanded args matching each %s position
        expanded = []
        for ref in refs:
            idx = int(ref) - 1
            if idx < len(args):
                expanded.append(args[idx])
            else:
                expanded.append(None)
        return mysql_query, tuple(expanded)

    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return all rows as dictionaries.
        Returns empty list if in mock mode (no MySQL pool).
        """
        if self._pool is None:
            return []
        mysql_query, expanded_args = self._convert_params(query, args)
        import aiomysql
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(mysql_query, expanded_args or None)
                rows = await cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a SELECT query and return the first row"""
        if self._pool is None:
            return None
        mysql_query, expanded_args = self._convert_params(query, args)
        import aiomysql
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(mysql_query, expanded_args or None)
                row = await cursor.fetchone()
                return self._row_to_dict(row) if row else None

    async def execute(self, query: str, *args) -> str:
        """Execute an INSERT/UPDATE/DELETE query"""
        if self._pool is None:
            return "OK"
        mysql_query, expanded_args = self._convert_params(query, args)
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(mysql_query, expanded_args or None)
                return "OK"

    async def executemany(self, query: str, args_list: List[tuple]) -> None:
        """Execute a query with multiple parameter sets"""
        if self._pool is None:
            return
        # For executemany, don't expand args (each tuple should match)
        mysql_query = re.sub(r'\$(\d+)', r'%s', query)
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(mysql_query, args_list)

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert MySQL row to dict with proper type handling"""
        if row is None:
            return {}
        result = {}
        for key, value in dict(row).items():
            if isinstance(value, (date, datetime)):
                result[key] = value.isoformat()
            elif isinstance(value, bytes):
                result[key] = value.decode('utf-8', errors='replace')
            elif isinstance(value, Decimal):
                result[key] = float(value)
            else:
                result[key] = value
        return result

    async def ensure_schema(self) -> bool:
        """Ensure the MySQL schema is created. Returns True if tables exist."""
        if self._pool is None:
            return False
        try:
            import aiomysql
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()")
                    row = await cursor.fetchone()
                    count = row[0] if row else 0
                    log.info("MySQL tables: %d tables found", count)
                    return count > 0
        except Exception as e:
            log.warning("Failed to check schema: %s", e)
            return False


db = Database()


async def init_db() -> None:
    """Initialize database connection"""
    global _IS_INITIALIZED
    if _IS_INITIALIZED:
        return
    await db.connect()
    has_tables = await db.ensure_schema()
    if not has_tables:
        log.warning("No tables found. Run schema_mysql.sql first or use seed data.")
    else:
        log.info("Schema verified OK")
    _IS_INITIALIZED = True
    log.info("Database initialized (MySQL)")


async def close_db() -> None:
    """Close database connection"""
    await db.close()


async def get_db() -> Database:
    """Get database instance (ensure connected)"""
    if db._pool is None:
        await db.connect()
    return db
