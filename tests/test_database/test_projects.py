import json
import os
import sys
import pytest

# Ensure project root is discoverable (conftest also does this, but keep for safety)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database import Database, Projet, Convention, Jalon, Competence, Utilisateur, redis_key


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


def ensure_jalons_table(db: Database):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS Jalons (
            jalon_id INTEGER PRIMARY KEY,
            description TEXT,
            date_fin TEXT,
            est_complete INTEGER,
            projet_id INTEGER
        )
        """
    )


def ensure_competences_tables(db: Database):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS competences (
            competence_id INTEGER PRIMARY KEY,
            nom TEXT,
            competence_parent INTEGER
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS projet_competences (
            projet_id INTEGER,
            competence_id INTEGER
        )
        """
    )


def test_project_basic_and_get_all(db):
    ensure_conventions_table(db)
    ensure_projets_table(db)

    # create a convention and a project
    db.execute("INSERT INTO Conventions (convention_id, nom_convention, description, date_debut, date_fin, doc_contrat, client_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
               (1001, 'Conv A', 'desc', '2025-01-01', '2025-12-31', None, None))
    db.execute("INSERT INTO Projets (projet_id, convention_id, nom_projet, description, budget, date_debut, date_fin, statut, doc_dossier) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (2001, 1001, 'Projet X', 'pdesc', 12345.0, '2025-02-01', '2025-11-30', 'en_cours', None))
    db.commit()

    p = db.get_project_id(2001)
    assert p is not None
    assert p.projet_id == 2001
    assert p.nom_projet == 'Projet X'

    all_projects = db.get_all_projects()
    assert any(pr.projet_id == 2001 for pr in all_projects)


def test_jalons_and_cache(db, fake_redis):
    ensure_projets_table(db)
    ensure_jalons_table(db)

    # Create project and two jalons
    db.execute("INSERT INTO Projets (projet_id, convention_id, nom_projet, statut) VALUES (?, ?, ?, ?)", (3001, None, 'P3001', 'en_cours'))
    db.execute("INSERT INTO Jalons (jalon_id, description, date_fin, est_complete, projet_id) VALUES (?, ?, ?, ?, ?)",
               (4001, 'Jalon 1', '2025-06-01', 0, 3001))
    db.execute("INSERT INTO Jalons (jalon_id, description, date_fin, est_complete, projet_id) VALUES (?, ?, ?, ?, ?)",
               (4002, 'Jalon 2', '2025-09-01', 1, 3001))
    db.commit()

    p = db.get_project_id(3001)
    assert p is not None
    jalons = p.jalons
    assert isinstance(jalons, list)
    assert {j.jalon_id for j in jalons} == {4001, 4002}

    # cache key should exist
    cache_key = redis_key(Projet.DATABASE_NAME.lower(), 3001, 'jalons')
    cached = fake_redis.get(cache_key)
    assert cached is not None
    ids = json.loads(cached)
    assert 4001 in ids and 4002 in ids


def test_competences_for_project(db, fake_redis):
    ensure_projets_table(db)
    ensure_competences_tables(db)

    # Insert project and competences mapping
    db.execute("INSERT INTO Projets (projet_id, nom_projet) VALUES (?, ?)", (5001, 'P5001'))
    db.execute("INSERT INTO competences (competence_id, nom, competence_parent) VALUES (?, ?, ?)", (6001, 'Python', None))
    db.execute("INSERT INTO projet_competences (projet_id, competence_id) VALUES (?, ?)", (5001, 6001))
    db.commit()

    p = db.get_project_id(5001)
    assert p is not None
    comps = p.competences
    assert isinstance(comps, list)
    assert any(c.competence_id == 6001 and c.nom == 'Python' for c in comps)

    cache_key = redis_key(Projet.DATABASE_NAME.lower(), 5001, 'competences')
    cached = fake_redis.get(cache_key)
    assert cached is not None
    cached_ids = json.loads(cached)
    assert 6001 in cached_ids


def test_intervenants_list_and_cache(db, fake_redis):
    # ensure projects table exists
    ensure_projets_table(db)

    # create two users and a project, and Travaille_sur entries
    db.execute("INSERT INTO Utilisateurs (utilisateur_id, email, mot_de_passe_hashed, mot_de_passe_expire, nom, prenom, role_id, est_intervenant) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
               (7001, 'u7001@example.com', 'hp', None, 'Nom1', 'Prenom1', 1, 1))
    db.execute("INSERT INTO Utilisateurs (utilisateur_id, email, mot_de_passe_hashed, mot_de_passe_expire, nom, prenom, role_id, est_intervenant) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
               (7002, 'u7002@example.com', 'hp', None, 'Nom2', 'Prenom2', 1, 1))
    db.execute("INSERT INTO Projets (projet_id, nom_projet) VALUES (?, ?)", (8001, 'P8001'))
    db.execute("INSERT INTO Travaille_sur (utilisateur_id, poste, projet_id) VALUES (?, ?, ?)", (7001, 'Dev', 8001))
    db.execute("INSERT INTO Travaille_sur (utilisateur_id, poste, projet_id) VALUES (?, ?, ?)", (7002, 'Chef', 8001))
    db.commit()

    p = db.get_project_id(8001)
    assert p is not None
    intervs = p.intervenants
    assert isinstance(intervs, list)
    # check we have intervenants with project id and poste
    assert any(getattr(i, 'projet_id', None) == 8001 and getattr(i, 'poste', None) == 'Dev' for i in intervs)
    assert any(getattr(i, 'projet_id', None) == 8001 and getattr(i, 'poste', None) == 'Chef' for i in intervs)

    cache_key = redis_key(Projet.DATABASE_NAME.lower(), 8001, 'intervenants')
    cached = fake_redis.get(cache_key)
    assert cached is not None
    cached_entries = json.loads(cached)
    assert any(e.get('utilisateur_id') == 7001 for e in cached_entries)
    assert any(e.get('poste') == 'Chef' for e in cached_entries)


if __name__ == '__main__':
    pytest.main()

