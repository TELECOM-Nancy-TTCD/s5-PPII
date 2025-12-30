import json
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database import Database, Client, Convention, Interaction, Utilisateur, redis_key

# Helpers to create tables needed for client-related tests

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


def ensure_interactions_table(db: Database):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS Interactions (
            interaction_id INTEGER PRIMARY KEY,
            date_time_interaction TEXT,
            contenu TEXT,
            client_id INTEGER,
            utilisateur_id INTEGER
        )
        """
    )


def insert_user(db: Database, user_id: int, email: str):
    db.execute(
        "INSERT INTO Utilisateurs (utilisateur_id, email, mot_de_passe_hashed, mot_de_passe_expire, nom, prenom, role_id, est_intervenant, heures_dispo_semaine, doc_carte_vitale, doc_cni, doc_adhesion, doc_rib) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, email, 'hp', None, 'Nom', 'Prenom', 1, 0, None, None, None, None, None)
    )


def insert_client(db: Database, client_id: int, contact_email: str, interlocuteur_id: int | None = None):
    db.execute(
        "INSERT INTO Clients (client_id, nom_entreprise, contact_nom, contact_email, contact_telephone, type_client, interlocuteur_principal_id, localisation_lat, localisation_lng, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (client_id, f'Entreprise {client_id}', 'Contact', contact_email, '000', 'Actif', interlocuteur_id, None, None, None)
    )


def insert_convention(db: Database, conv_id: int, client_id: int, name: str = 'Conv'):
    db.execute(
        "INSERT INTO Conventions (convention_id, nom_convention, description, date_debut, date_fin, doc_contrat, client_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (conv_id, name, 'desc', '2025-01-01', '2025-12-31', None, client_id)
    )


def insert_interaction(db: Database, inter_id: int, client_id: int, user_id: int, contenu: str = 'Hello'):
    db.execute(
        "INSERT INTO Interactions (interaction_id, date_time_interaction, contenu, client_id, utilisateur_id) VALUES (?, ?, ?, ?, ?)",
        (inter_id, '2025-01-01 10:00:00', contenu, client_id, user_id)
    )


def test_interlocuteur_principal_db_and_cache(db, fake_redis):
    # prepare
    insert_user(db, 201, 'principal@example.com')
    insert_client(db, 50, 'client50@example.com', interlocuteur_id=201)
    db.commit()

    client = db.get_client_by_id(50)
    assert client is not None

    # should fetch from DB and return a Utilisateur
    principal = client.interlocuteur_principal
    assert principal.utilisateur_id == 201
    assert principal.email == 'principal@example.com'

    # Now populate redis cache for the user and ensure property uses cache
    cached_key = redis_key('user', 201)
    # create a serializable payload
    payload = json.dumps(principal.to_dict())
    fake_redis.setex(cached_key, 1800, payload)

    # Invalidate DB row (simulate deletion) so that only cache would allow lookup
    db.execute("DELETE FROM Utilisateurs WHERE utilisateur_id = ?", (201,))
    db.commit()

    client2 = db.get_client_by_id(50)
    # Now interlocuteur_principal should be resolved from cache
    principal2 = client2.interlocuteur_principal
    assert principal2.utilisateur_id == 201
    assert principal2.email == 'principal@example.com'


def test_interlocuteur_principal_missing_raises(db, fake_redis):
    # Insert client pointing to non-existing user
    insert_client(db, 60, 'client60@example.com', interlocuteur_id=9999)
    db.commit()

    client = db.get_client_by_id(60)
    assert client is not None
    with pytest.raises(ValueError):
        _ = client.interlocuteur_principal


def test_conventions_list_and_caching(db, fake_redis):
    ensure_conventions_table(db)

    # Create client and 2 conventions
    insert_client(db, 70, 'client70@example.com')
    insert_convention(db, 301, 70, name='C1')
    insert_convention(db, 302, 70, name='C2')
    db.commit()

    client = db.get_client_by_id(70)
    assert client is not None

    convs = client.conventions
    assert isinstance(convs, list)
    ids = [c.convention_id for c in convs]
    assert 301 in ids and 302 in ids

    # Check cache key set
    # The module code uses redis_key(Client.DATABASE_NAME.lower(), self.client_id, "conventions")
    cache_key = redis_key('clients', 70, 'conventions')
    cached = fake_redis.get(cache_key)
    assert cached is not None
    cached_ids = json.loads(cached)
    assert 301 in cached_ids and 302 in cached_ids

    # Test client without conventions -> should return empty list
    insert_client(db, 71, 'client71@example.com')
    db.commit()
    client_empty = db.get_client_by_id(71)
    assert client_empty is not None
    convs_empty = client_empty.conventions
    assert convs_empty == []


def test_interactions_list_and_cache_behavior(db, fake_redis):
    ensure_interactions_table(db)
    ensure_conventions_table(db)

    # Prepare user, client, interaction
    insert_user(db, 401, 'u401@example.com')
    insert_client(db, 80, 'client80@example.com')
    insert_interaction(db, 501, 80, 401, contenu='First')
    db.commit()

    client = db.get_client_by_id(80)
    assert client is not None

    inters = client.interactions
    # interactions property returns list or None
    assert isinstance(inters, list)
    assert any(i.interaction_id == 501 and i.contenu == 'First' for i in inters)

    # Check cache has been set (list of ids)
    cache_key = redis_key('clients', 80, 'interactions')
    cached = fake_redis.get(cache_key)
    assert cached is not None
    cached_ids = json.loads(cached)
    assert 501 in cached_ids

    # Now test partial cache: simulate cache with an id but missing per-item cache -> should still work and refresh
    fake_redis.delete(cache_key)
    fake_redis.setex(cache_key, 1800, json.dumps([501]))
    # remove any 'interaction:501' entry so that code falls back to DB
    fake_redis.delete('interaction:501')

    client2 = db.get_client_by_id(80)
    inters2 = client2.interactions
    assert isinstance(inters2, list)
    assert any(i.interaction_id == 501 for i in inters2)


if __name__ == '__main__':
    pytest.main()
