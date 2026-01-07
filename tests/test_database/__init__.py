"""Unit tests for test_database.py module."""

# Ensure project root is on sys.path so `import database` resolves to the local package
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
import sqlite3
import pytest

from database import Database


def test_connection_and_basic_execute():
    fake_redis = object()  # not used directly here; we only test basic Database execute
    db = Database(fake_redis, ":memory:")
    # Execute a simple create/insert/select
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    db.execute("INSERT INTO t (id, name) VALUES (?, ?)", (1, 'Alice'))
    cursor = db.execute("SELECT name FROM t WHERE id = ?", (1,))
    row = cursor.fetchone()
    assert row[0] == 'Alice'
    cursor.close()
    db.close()



if __name__ == '__main__':
    pytest.main()
