"""Ядро не зависит от веб-фреймворка и драйвера БД: проверяем импорты в коде ядра."""
import ast
import pathlib
import sys
import unittest

FORBIDDEN = {"flask", "fastapi", "django", "starlette", "aiohttp", "bottle", "tornado",
             "sanic", "falcon", "pyramid", "uvicorn", "requests", "http", "urllib",
             "sqlalchemy", "sqlite3", "psycopg2", "psycopg", "asyncpg", "pymysql", "mysql",
             "pymongo", "redis", "peewee", "tortoise", "databases", "dbm", "shelve"}
CORE = pathlib.Path(__file__).resolve().parent.parent / "core"


class CoreIndependence(unittest.TestCase):
    def test_no_framework_or_db_imports(self):
        found = []
        for path in CORE.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""]
                found += [(path.name, n) for n in names if n.split(".")[0] in FORBIDDEN]
        self.assertEqual(found, [])

    def test_importing_core_loads_no_framework(self):
        import core  # noqa: F401
        loaded = {m.split(".")[0] for m in sys.modules}
        self.assertFalse(loaded & {"flask", "fastapi", "django", "sqlalchemy", "psycopg2"})


if __name__ == "__main__":
    unittest.main()
