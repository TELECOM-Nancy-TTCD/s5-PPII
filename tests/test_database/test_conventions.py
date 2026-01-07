import os
import sys
import json
import pytest

# Ensure project root is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database import Database, Convention, Projet, Client, redis_key


def ensure_conventions_table(db: Database):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS Conventions (
            convention_id INTEGER PRIMARY KEY,
            nom_convention TEXT,
            description TEXT,
            date_debut TEXT,
            date_fin TEXT,
            doc_contrat TEXT,
            client_id INTEGER
        )
        """
    )


def ensure_projets_table(db: Database):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS Projets (
            projet_id INTEGER PRIMARY KEY,
            convention_id INTEGER,
            nom_projet TEXT,
            description TEXT,
            budget REAL,
            date_debut TEXT,
            date_fin TEXT,
            statut TEXT,
            doc_dossier TEXT
        )
        """
    )


def ensure_clients_table(db: Database):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS Clients (
            client_id INTEGER PRIMARY KEY,
            nom_entreprise TEXT,
            contact_nom TEXT,
            contact_email TEXT,
            contact_telephone TEXT,
            type_client TEXT,
            interlocuteur_principal_id INTEGER,
            localisation_lat REAL,
            localisation_lng REAL,
            address TEXT
        )
        """
    )


def test_convention_basic_and_cache(db, fake_redis):
    ensure_conventions_table(db)
    ensure_clients_table(db)

    # Create a client and a convention via SQL
    db.execute("INSERT INTO Clients (client_id, nom_entreprise, contact_email, type_client) VALUES (?, ?, ?, ?)", (110, 'Cli110', 'c110@example.com', 'Actif'))
    db.execute(
        "INSERT INTO Conventions (convention_id, nom_convention, description, date_debut, date_fin, doc_contrat, client_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (210, 'Conv210', 'desc', '2025-01-01', '2025-12-31', None, 110)
    )
    db.commit()

    conv = db.get_convention_by_id(210)
    assert conv is not None
    assert conv.convention_id == 210
    assert conv.nom_convention == 'Conv210'

    # After loading, an individual cache entry should exist (Convention.from_db_row calls _try_cache)
    cache_key = redis_key(getattr(Convention, 'CACHE_PREFIX', None) or Convention.__name__.lower(), 210)
    cached = fake_redis.get(cache_key)
    assert cached is not None
    payload = json.loads(cached)
    assert payload.get('nom_convention') == 'Conv210'


def test_convention_client_property_and_cache(db, fake_redis):
    ensure_conventions_table(db)
    ensure_clients_table(db)

    # Insert client and convention
    db.execute("INSERT INTO Clients (client_id, nom_entreprise, contact_email, type_client) VALUES (?, ?, ?, ?)", (120, 'Cli120', 'c120@example.com', 'Actif'))
    db.execute("INSERT INTO Conventions (convention_id, nom_convention, client_id) VALUES (?, ?, ?)", (220, 'Conv220', 120))
    db.commit()

    conv = db.get_convention_by_id(220)
    assert conv is not None

    # client should be fetched from DB
    client = conv.client
    assert client.client_id == 120
    assert client.contact_email == 'c120@example.com'

    # Now cache the client and delete DB row to ensure conv.client uses cache
    client_cache_key = redis_key(getattr(Client, 'CACHE_PREFIX', None) or Client.__name__.lower(), 120)
    fake_redis.setex(client_cache_key, 1800, json.dumps(client.to_dict()))
    db.execute("DELETE FROM Clients WHERE client_id = ?", (120,))
    db.commit()

    conv2 = db.get_convention_by_id(220)
    client_from_cache = conv2.client
    assert client_from_cache.client_id == 120
    assert client_from_cache.contact_email == 'c120@example.com'


def test_convention_projects_list_and_cache(db, fake_redis):
    ensure_conventions_table(db)
    ensure_projets_table(db)

    # create convention and two projects linked to it
    db.execute("INSERT INTO Conventions (convention_id, nom_convention) VALUES (?, ?)", (230, 'Conv230'))
    db.execute("INSERT INTO Projets (projet_id, convention_id, nom_projet) VALUES (?, ?, ?)", (3301, 230, 'Pr1'))
    db.execute("INSERT INTO Projets (projet_id, convention_id, nom_projet) VALUES (?, ?, ?)", (3302, 230, 'Pr2'))
    db.commit()

    conv = db.get_convention_by_id(230)
    assert conv is not None

    projets = conv.projets
    assert isinstance(projets, list)
    ids = [p.projet_id for p in projets]
    assert 3301 in ids and 3302 in ids

    # The module caches the list of project ids under key 'conventions:<id>:projets'
    cache_key = redis_key(Convention.DATABASE_NAME.lower(), 230, 'projets')
    cached = fake_redis.get(cache_key)
    assert cached is not None
    cached_ids = json.loads(cached)
    assert 3301 in cached_ids and 3302 in cached_ids


def test_convention_save_and_delete(db, fake_redis):
    ensure_conventions_table(db)
    ensure_clients_table(db)

    # prepare data and ensure client exists
    db.execute("INSERT INTO Clients (client_id, nom_entreprise, contact_email, type_client) VALUES (?, ?, ?, ?)", (130, 'Cli130', 'c130@example.com', 'Actif'))
    db.commit()

    data = {
        'convention_id': 240,
        'nom_convention': 'Conv240',
        'description': 'd',
        'date_debut': None,
        'date_fin': None,
        'doc_contrat': None,
        'client_id': 130
    }
    c = Convention(db, data)
    c.save()

    # DB row exists
    cursor = db.execute("SELECT nom_convention FROM Conventions WHERE convention_id = ?", (240,))
    row = cursor.fetchone()
    cursor.close()
    assert row is not None and row[0] == 'Conv240'

    # individual cache exists (key 'convention:240')
    cache_key = redis_key(getattr(Convention, 'CACHE_PREFIX', None) or Convention.__name__.lower(), 240)
    cached = fake_redis.get(cache_key)
    assert cached is not None
    obj = json.loads(cached)
    assert obj.get('nom_convention') == 'Conv240'

    # delete
    c.delete()
    cursor = db.execute("SELECT nom_convention FROM Conventions WHERE convention_id = ?", (240,))
    assert cursor.fetchone() is None
    cursor.close()
    assert fake_redis.get(cache_key) is None


if __name__ == '__main__':
    pytest.main()

