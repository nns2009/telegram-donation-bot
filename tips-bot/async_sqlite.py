import asyncio
import functools

import peewee
from peewee_async import AsyncDatabase
import playhouse.sqlite_ext as sqlite_ext

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

__all__ = ["SqliteDatabase", "SqliteExtDatabase"]


class AsyncSqliteConnection:
    def __init__(self, *, database=None, loop=None, timeout=None, **kwargs):
        self._created_connections = []
        self.loop = loop
        self.database = database
        self.timeout = timeout
        self.connect_kwargs = kwargs

    async def acquire(self):
        conn = aiosqlite.connect(database=self.database, **self.connect_kwargs)
        self._created_connections.append(conn)
        return await conn.__aenter__()

    def release(self, conn):
        if conn in self._created_connections:
            self._created_connections.remove(conn)

        async def _internal():
            await conn.commit()
            await conn.__aexit__(None, None, None)

        loop = self.loop or asyncio.get_event_loop()
        loop.create_task(_internal())

    async def connect(self):
        pass

    async def close(self):
        for conn in self._created_connections:
            await conn.__aexit__(None, None, None)
        self._created_connections = []

    async def cursor(self, conn=None, *args, **kwargs):
        in_transaction = conn is not None
        if not conn:
            conn = await self.acquire()
        cursor = await conn.cursor()
        cursor.release = functools.partial(
            self.release_cursor, cursor,
            in_transaction=in_transaction)
        return cursor

    async def release_cursor(self, cursor, in_transaction=False):
        conn = cursor._conn
        await cursor.__aexit__(None, None, None)
        if not in_transaction:
            self.release(conn)


class AsyncSqliteMixin(AsyncDatabase):
    if aiosqlite:
        import sqlite3

        Error = sqlite3.Error

    def init_async(self, conn_class=AsyncSqliteConnection):
        if not aiosqlite:
            raise Exception("Error, aiosqlite is not installed!")
        self._async_conn_cls = conn_class

    @property
    def connect_kwargs_async(self):
        return {**self.connect_kwargs}

    async def last_insert_id_async(self, cursor):
        return cursor.lastrowid


class SqliteDatabase(AsyncSqliteMixin, peewee.SqliteDatabase):
    def init(self, database, **kwargs):
        super().init(database, **kwargs)
        self.init_async()

    @property
    def connect_params_async(self):
        kwargs = self.connect_params.copy()
        return kwargs


class SqliteExtDatabase(SqliteDatabase, sqlite_ext.SqliteExtDatabase):
    pass
