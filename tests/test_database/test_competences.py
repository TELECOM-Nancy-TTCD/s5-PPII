import os
import sys
import json
import pytest

# Ensure project root is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database import Database, Competence, redis_key


def ensure_competences_table(db: Database):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS Competences
        (
            competence_id     INTEGER PRIMARY KEY,
            nom               VARCHAR UNIQUE NOT NULL,
            competence_parent INT
        );
        """
    )
    db.commit()


def test_competence_parent_db_and_cache(db, fake_redis):
    ensure_competences_table(db)

    # Insert parent and child
    db.execute("INSERT INTO Competences (competence_id, nom, competence_parent) VALUES (?, ?, ?)", (9001, 'ParentComp', None))
    db.execute("INSERT INTO Competences (competence_id, nom, competence_parent) VALUES (?, ?, ?)", (9002, 'ChildComp', 9001))
    db.commit()

    # Load child from DB via SELECT and from_db_row
    cursor = db.execute("SELECT * FROM Competences WHERE competence_id = ?", (9002,))
    row = cursor.fetchone()
    cursor.close()
    child = Competence.from_db_row(db, row)

    # parent should be loaded from DB
    parent = child.parent
    assert parent is not None
    assert parent.competence_id == 9001
    assert parent.nom == 'ParentComp'

    # Now cache the parent and remove it from DB to ensure parent property uses cache
    cache_key = redis_key(getattr(Competence, 'CACHE_PREFIX', None) or Competence.__name__.lower(), 9001)
    fake_redis.setex(cache_key, 1800, json.dumps(parent.to_dict()))

    # remove parent row from DB
    db.execute("DELETE FROM Competences WHERE competence_id = ?", (9001,))
    db.commit()

    # Recreate child object (fresh) and access parent -> should come from cache
    cursor = db.execute("SELECT * FROM Competences WHERE competence_id = ?", (9002,))
    row = cursor.fetchone()
    cursor.close()
    child2 = Competence.from_db_row(db, row)
    parent_cached = child2.parent
    assert parent_cached is not None
    assert parent_cached.competence_id == 9001
    assert parent_cached.nom == 'ParentComp'


def test_competence_save_and_delete(db, fake_redis):
    ensure_competences_table(db)

    data = {'competence_id': 9101, 'nom': 'SaveComp', 'competence_parent': None}
    comp = Competence(db, data)
    comp.save()

    # Check DB row exists
    cursor = db.execute("SELECT nom FROM Competences WHERE competence_id = ?", (9101,))
    row = cursor.fetchone()
    cursor.close()
    assert row is not None and row[0] == 'SaveComp'

    # Check cache exists
    cache_key = redis_key(getattr(Competence, 'CACHE_PREFIX', None) or Competence.__name__.lower(), 9101)
    cached = fake_redis.get(cache_key)
    assert cached is not None
    payload = json.loads(cached)
    assert payload.get('nom') == 'SaveComp'

    # Delete and ensure removal
    comp.delete()
    cursor = db.execute("SELECT nom FROM Competences WHERE competence_id = ?", (9101,))
    assert cursor.fetchone() is None
    cursor.close()
    assert fake_redis.get(cache_key) is None


def test_competence_parent_missing_raises(db):
    ensure_competences_table(db)

    # Insert a child that references a non-existing parent
    db.execute("INSERT INTO Competences (competence_id, nom, competence_parent) VALUES (?, ?, ?)", (9201, 'OrphanChild', 99999))
    db.commit()

    cursor = db.execute("SELECT * FROM Competences WHERE competence_id = ?", (9201,))
    row = cursor.fetchone()
    cursor.close()
    child = Competence.from_db_row(db, row)

    with pytest.raises(ValueError):
        _ = child.parent


if __name__ == '__main__':
    pytest.main()

