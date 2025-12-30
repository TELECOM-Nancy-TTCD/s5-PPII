import os
import sys
import json
import pytest

# Ensure project root is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database import Database, Interaction, Client, Utilisateur, redis_key


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


def test_interaction_crud_and_cache(db, fake_redis):
    ensure_interactions_table(db)

    # ensure user and client exist
    db.execute("INSERT OR IGNORE INTO Utilisateurs (utilisateur_id, email, mot_de_passe_hashed, mot_de_passe_expire, nom, prenom, role_id, est_intervenant) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
               (1001, 'u1001@example.com', 'hp', None, 'NomU1', 'Pren1', 1, 0))
    db.execute("INSERT OR IGNORE INTO Clients (client_id, nom_entreprise, contact_email, type_client) VALUES (?, ?, ?, ?)",
               (2001, 'Cli2001', 'c2001@example.com', 'Actif'))

    # insert interaction
    db.execute("INSERT INTO Interactions (interaction_id, date_time_interaction, contenu, client_id, utilisateur_id) VALUES (?, ?, ?, ?, ?)",
               (3001, '2025-01-01 12:00:00', 'Hello world', 2001, 1001))
    db.commit()

    inter = db.get_interaction_by_id(3001)
    assert inter is not None
    assert inter.interaction_id == 3001
    assert inter.contenu == 'Hello world'

    # per-item cache should have been set by _try_cache in _RowInitMixin
    cache_key = redis_key(Interaction.__name__.lower(), 3001)
    cached = fake_redis.get(cache_key)
    assert cached is not None
    obj = json.loads(cached)
    assert obj.get('contenu') == 'Hello world'


def test_interaction_client_and_user_properties_and_cache(db, fake_redis):
    ensure_interactions_table(db)

    # insert user, client, interaction
    db.execute("INSERT OR IGNORE INTO Utilisateurs (utilisateur_id, email, mot_de_passe_hashed, mot_de_passe_expire, nom, prenom, role_id, est_intervenant) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
               (1101, 'u1101@example.com', 'hp', None, 'U1101', 'P1101', 1, 0))
    db.execute("INSERT OR IGNORE INTO Clients (client_id, nom_entreprise, contact_email, type_client) VALUES (?, ?, ?, ?)",
               (2101, 'Cli2101', 'c2101@example.com', 'Actif'))
    db.execute("INSERT OR IGNORE INTO Interactions (interaction_id, date_time_interaction, contenu, client_id, utilisateur_id) VALUES (?, ?, ?, ?, ?)",
               (3101, '2025-02-02 09:00:00', 'Interaction1', 2101, 1101))
    db.commit()

    inter = db.get_interaction_by_id(3101)
    assert inter is not None

    # properties fetched from DB
    client = inter.client
    user = inter.utilisateur
    assert client.client_id == 2101
    assert user.utilisateur_id == 1101

    # Now cache client and user and remove from DB to ensure properties use cache
    client_cache_key = redis_key(getattr(Client, 'CACHE_PREFIX', None) or Client.__name__.lower(), 2101)
    user_cache_key = redis_key(getattr(Utilisateur, 'CACHE_PREFIX', None) or Utilisateur.__name__.lower(), 1101)
    fake_redis.setex(client_cache_key, 1800, json.dumps(client.to_dict()))
    fake_redis.setex(user_cache_key, 1800, json.dumps(user.to_dict()))

    db.execute("DELETE FROM Clients WHERE client_id = ?", (2101,))
    db.execute("DELETE FROM Utilisateurs WHERE utilisateur_id = ?", (1101,))
    db.commit()

    # Access properties again; should be resolved from cache
    client_cached = inter.client
    user_cached = inter.utilisateur
    assert client_cached.client_id == 2101
    assert user_cached.utilisateur_id == 1101


def test_get_all_interactions_and_filter_and_cache(db, fake_redis):
    ensure_interactions_table(db)

    # create users/clients and interactions
    db.execute("INSERT OR IGNORE INTO Utilisateurs (utilisateur_id, email, mot_de_passe_hashed, mot_de_passe_expire, nom, prenom, role_id, est_intervenant) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
               (1201, 'u1201@example.com', 'hp', None, 'U1201', 'P1201', 1, 0))
    db.execute("INSERT OR IGNORE INTO Utilisateurs (utilisateur_id, email, mot_de_passe_hashed, mot_de_passe_expire, nom, prenom, role_id, est_intervenant) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
               (1202, 'u1202@example.com', 'hp', None, 'U1202', 'P1202', 1, 0))
    db.execute("INSERT OR IGNORE INTO Clients (client_id, nom_entreprise, contact_email, type_client) VALUES (?, ?, ?, ?)",
               (2201, 'Cli2201', 'c2201@example.com', 'Actif'))

    db.execute("INSERT OR IGNORE INTO Interactions (interaction_id, date_time_interaction, contenu, client_id, utilisateur_id) VALUES (?, ?, ?, ?, ?)",
               (3201, '2025-03-01 10:00:00', 'A', 2201, 1201))
    db.execute("INSERT OR IGNORE INTO Interactions (interaction_id, date_time_interaction, contenu, client_id, utilisateur_id) VALUES (?, ?, ?, ?, ?)",
               (3202, '2025-03-02 11:00:00', 'B', 2201, 1202))
    db.execute("INSERT OR IGNORE INTO Interactions (interaction_id, date_time_interaction, contenu, client_id, utilisateur_id) VALUES (?, ?, ?, ?, ?)",
               (3203, '2025-03-03 12:00:00', 'C', 2201, 1201))
    db.commit()

    # get_all_interactions should return all interactions and populate 'interactions:all' cache
    all_inters = db.get_all_interactions()
    assert any(i.interaction_id == 3201 for i in all_inters)
    assert any(i.interaction_id == 3202 for i in all_inters)
    assert any(i.interaction_id == 3203 for i in all_inters)

    cache_key = redis_key(Interaction.DATABASE_NAME.lower(), None, 'all')
    cached = fake_redis.get(cache_key)
    assert cached is not None
    cached_ids = json.loads(cached)
    assert 3201 in cached_ids and 3202 in cached_ids and 3203 in cached_ids

    # filter by user_id should return only interactions by that user
    inters_user1201 = db.get_all_interactions(user_id=1201)
    assert all(i.utilisateur_id == 1201 for i in inters_user1201)


if __name__ == '__main__':
    pytest.main()

