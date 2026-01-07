import os
import sys
# Ensure project root is on sys.path so `import database` resolves to the local package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from database import Database


class FakeRedis:
    """Simple fake Redis-like client used for tests. Stores values in an in-memory dict.

    Methods implemented: get, setex, set, sadd, srem, smembers, expire, delete
    """
    def __init__(self):
        self.store = {}
        self.sets = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def setex(self, key, ttl, value):
        # TTL is ignored for the fake client
        self.store[key] = value

    def sadd(self, key, member):
        s = self.sets.setdefault(key, set())
        s.add(member)

    def srem(self, key, member):
        s = self.sets.get(key)
        if s:
            s.discard(member)
            if not s:
                # optionally remove empty set
                del self.sets[key]

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def expire(self, key, ttl):
        # ignore TTL in fake
        return True

    def delete(self, key):
        self.store.pop(key, None)
        self.sets.pop(key, None)


def create_minimal_schema(db: Database):
    """Create the minimal set of tables used by the tests."""
    db.execute(
        """
        CREATE TABLE Roles
        (
            role_id                    INTEGER PRIMARY KEY,
            nom                        VARCHAR,
            hierarchie                 INT, -- pour la modification de rôles, on ne peut destituer un individu d'un role plus haut

            administrateur             BOOLEAN DEFAULT false,
            peut_gerer_utilisateurs    BOOLEAN DEFAULT false,
            peut_gerer_roles           BOOLEAN DEFAULT false,

            peut_lire_clients          BOOLEAN DEFAULT false,
            peut_gerer_clients         BOOLEAN DEFAULT false,
            peut_creer_interactions    BOOLEAN DEFAULT false,
            peut_gerer_interactions    BOOLEAN DEFAULT false,

            peut_lire_projets          BOOLEAN DEFAULT false,
            peut_gerer_projets         BOOLEAN DEFAULT false,
            peut_gerer_jalons          BOOLEAN DEFAULT false,
            peut_assigner_intervenants BOOLEAN DEFAULT false,

            peut_lire_utilisateurs     BOOLEAN DEFAULT false,
            peut_acceder_documents     BOOLEAN DEFAULT false,
            peut_gerer_competences     BOOLEAN DEFAULT false,

            peut_lancer_matching       BOOLEAN DEFAULT false,
            peut_exporter_csv          BOOLEAN DEFAULT false

        );
        """
    )
    db.execute(
        """
        CREATE TABLE Utilisateurs (
            utilisateur_id INTEGER PRIMARY KEY,
            email TEXT UNIQUE,
            mot_de_passe_hashed TEXT,
            mot_de_passe_expire DATE,
            nom TEXT,
            prenom TEXT,
            avatar TEXT,
            role_id INTEGER,
            est_intervenant INTEGER,
            heures_dispo_semaine INTEGER,
            doc_carte_vitale TEXT,
            doc_cni TEXT,
            doc_adhesion TEXT,
            doc_rib TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE Travaille_sur (
            utilisateur_id INTEGER,
            poste TEXT,
            projet_id INTEGER
        )
        """
    )

    db.execute(
        """
        CREATE TABLE Clients
        (
            client_id                  INTEGER PRIMARY KEY,
            nom_entreprise             VARCHAR NOT NULL,
            contact_nom                VARCHAR,
            contact_email              VARCHAR,
            contact_telephone          VARCHAR,
            type_client                TEXT    NOT NULL
                CHECK (type_client IN ('Prospect', 'Actif', 'Ancien')),

            interlocuteur_principal_id INT,
            localisation_lat           FLOAT,
            localisation_lng           FLOAT,
            address                    VARCHAR
        )
        """
    )
    db.commit()


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def db(fake_redis):
    """Return a Database instance connected to an in-memory SQLite DB with the fake redis."""
    database = Database(fake_redis, ":memory:")
    create_minimal_schema(database)
    yield database
    # cleanup
    database.close()
