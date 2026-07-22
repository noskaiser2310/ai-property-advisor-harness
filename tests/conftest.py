"""
pytest conftest — Shared fixtures và event loop management

Chức năng:
1. Quản lý event loop: session-scoped fixture, tránh "Event loop is closed" từ aiomysql
2. Monkey-patch Database.fetch/fetchrow/execute → không cần MySQL server chạy khi test
3. Cấu hình pytest-asyncio: asyncio_mode = auto (từ pytest.ini)

Event Loop Strategy:
- Tạo event loop duy nhất cho cả session → aiomysql pool dùng chung 1 loop
- Cleanup loop ở cuối session → tránh "Event loop is closed" RuntimeError
- Windows: dùng WindowsProactorEventLoopPolicy (tương thích với aiomysql)
"""

import asyncio
import sys


def pytest_configure(config):
    """
    Hook pytest — chạy TRƯỚC khi test modules được import.

    Monkey-patch Database methods để không cần MySQL:
    - fetch() → return []
    - fetchrow() → return None
    - execute() → return "OK"

    Đồng thời set _IS_INITIALIZED = True để init_db() return ngay lập tức
    khi TestClient khởi tạo lifespan.
    """
    import database.connection as db_module

    # Đánh dấu DB đã init → lifespan của FastAPI sẽ bỏ qua
    db_module._IS_INITIALIZED = True
    db_module.db._pool = None

    # Monkey-patch key methods — không cần chạy aiomysql
    async def mock_fetch(query, *args):
        return []

    async def mock_fetchrow(query, *args):
        return None

    async def mock_execute(query, *args):
        return "OK"

    async def mock_connect():
        db_module.db._pool = None

    async def mock_executemany(query, args_list):
        pass

    db_module.db.fetch = mock_fetch
    db_module.db.fetchrow = mock_fetchrow
    db_module.db.execute = mock_execute
    db_module.db.connect = mock_connect
    db_module.db.executemany = mock_executemany

    # Set event loop policy cho Windows (tương thích aiomysql)
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass  # Python < 3.8 hoặc không có WindowsSelectorEventLoopPolicy


def pytest_unconfigure(config):
    """
    Hook pytest — chạy SAU KHI tất cả tests hoàn thành.

    Cleanup event loop để tránh:
    - RuntimeError: Event loop is closed
    - ResourceWarning: unclosed event loop
    """
    try:
        loop = asyncio.get_event_loop()
        if loop and not loop.is_closed():
            # Cancel all pending tasks (Python 3.12+: no loop param)
            pending = asyncio.all_tasks()
            for task in pending:
                task.cancel()
            # Run loop one last time to let tasks finish cleanup
            if pending:
                try:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except (RuntimeError, asyncio.CancelledError):
                    pass
            loop.close()
    except (RuntimeError, Exception):
        pass  # No running loop — nothing to clean up
