"""Tests unitaires pour la gestion des rôles utilisateurs dans la base de données."""
import json

import pytest

from database import Database, Utilisateur, Role, redis_key, normalize_text


def ensure_competences_tables(db: Database):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS Competences
        (
            competence_id     INTEGER PRIMARY KEY,
            nom               VARCHAR UNIQUE NOT NULL,

            -- sous-compétence (relation réflexive)
            competence_parent INT
        );
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS Intervenant_competences
        (
            intervenant_id INT,
            competence_id  INT,

            niveau         INT NOT NULL
                CHECK (niveau BETWEEN 0 AND 10)
        );
        """
    )


def ensure_roles_table(db: Database):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS Roles (
    role_id INTEGER PRIMARY KEY,
    nom VARCHAR,
    hierarchie INT, -- pour la modification de rôles, on ne peut destituer un individu d'un role plus haut

    peut_gerer_utilisateurs BOOLEAN DEFAULT false,
    peut_gerer_roles BOOLEAN DEFAULT false,
    
    peut_lire_clients BOOLEAN DEFAULT false,
    peut_gerer_clients BOOLEAN DEFAULT false, 
    peut_gerer_interactions BOOLEAN DEFAULT false,
    
    peut_lire_projets BOOLEAN DEFAULT false,
    peut_gerer_projets BOOLEAN DEFAULT false,
    peut_gerer_jalons BOOLEAN DEFAULT false,
    peut_assigner_intervenants BOOLEAN DEFAULT false,

    peut_lire_intervenants BOOLEAN DEFAULT false,
    peut_modifier_intervenants BOOLEAN DEFAULT false, 
    peut_acceder_documents BOOLEAN DEFAULT false,
    peut_gerer_competences BOOLEAN DEFAULT false,

    peut_lancer_matching BOOLEAN DEFAULT false,
    peut_exporter_csv BOOLEAN DEFAULT false
    
);
        """
    )

def ensure_users_table(db: Database):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS Utilisateurs
        (
            utilisateur_id        INTEGER PRIMARY KEY,
            email                 VARCHAR UNIQUE NOT NULL,
            mot_de_passe_hashed   VARCHAR NOT NULL,
            mot_de_passe_expire   DATE,
            nom                   VARCHAR NOT NULL,
            prenom                VARCHAR NOT NULL,
            role_id               INT NOT NULL,
            est_intervenant       BOOLEAN DEFAULT false,
            heures_dispo_semaine  INT,
            doc_carte_vitale      VARCHAR,
            doc_cni               VARCHAR,
            doc_adhesion          VARCHAR,
            doc_rib               VARCHAR,

            FOREIGN KEY (role_id) REFERENCES Roles (role_id)
        );
        """
    )

def insert_user(db: Database, user_id: int, email: str, nom: str, prenom: str, role_id: int):
    """Insère un utilisateur dans la base de données pour les tests."""
    db.execute(
        "INSERT INTO Utilisateurs (utilisateur_id, email, mot_de_passe_hashed, mot_de_passe_expire, nom, prenom, role_id, est_intervenant, heures_dispo_semaine, doc_carte_vitale, doc_cni, doc_adhesion, doc_rib) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, email, 'hp', None, nom, prenom, role_id, 0, None, None, None, None, None)
    )

def insert_role(db: Database, role_id: int, nom: str, hierarchie: int):
    """Insère un rôle dans la base de données pour les tests."""
    db.execute(
        "INSERT INTO Roles (role_id, nom, hierarchie) VALUES (?, ?, ?)",
        (role_id, nom, hierarchie)
    )

"""Test des utilisateurs"""

def test_user_crud_and_caching(db, fake_redis):
    ensure_roles_table(db)
    ensure_users_table(db)
    # Create a role for the user
    insert_role(db, 1, 'User', 10)
    db.commit()
    # Insert a role and a user directly via SQL

    insert_user(db, 10, 'jean.dupont@example.com', 'Dupont', 'Jean', 1)
    db.commit()

    # get_user_by_id should read from DB and return an Utilisateur
    user = db.get_user_by_id(10)
    assert user is not None
    assert user.utilisateur_id == 10
    assert user.email == 'jean.dupont@example.com'
    assert user.nom == 'Dupont'
    assert user.prenom == 'Jean'

    # get_user_by_email should succeed (no redis index present yet)
    user2 = db.get_user_by_email('jean.dupont@example.com')
    assert user2.utilisateur_id == 10

    # get_all_users should populate the 'utilisateurs:all' cache
    all_users = db.get_all_users()
    assert any(u.utilisateur_id == 10 for u in all_users)
    cached = fake_redis.get(redis_key(Utilisateur.DATABASE_NAME.lower(), None, 'all'))
    assert cached is not None
    cached_ids = json.loads(cached)
    assert 10 in cached_ids

    # Test secondary index: manually add index entry in redis and ensure get_user_by_email uses it
    email = 'alice.smith@example.com'
    # insert new user directly in SQL
    db.execute(
        "INSERT INTO Utilisateurs (utilisateur_id, email, mot_de_passe_hashed, mot_de_passe_expire, nom, prenom, role_id, est_intervenant, heures_dispo_semaine, doc_carte_vitale, doc_cni, doc_adhesion, doc_rib) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (11, email, 'hpwd', '2025-12-31', 'Smith', 'Alice', 1, 0, None, None, None, None, None)
    )
    db.commit()
    index_key = redis_key(f"index:{Utilisateur.DATABASE_NAME}", suffix=f"email:{normalize_text(email)}")
    fake_redis.sadd(index_key, '11')

    # Should return the user with id 11
    found = db.get_user_by_email(email)
    assert found.utilisateur_id == 11


def test_save_and_delete(db, fake_redis):
    # Create a new user object and save it via Utilisateur.save()
    user_data = {
        'utilisateur_id': 99,
        'email': 'save.test@example.com',
        'mot_de_passe_hashed': 'pw',
        # Use None for mot_de_passe_expire to avoid json serialization issues with datetime.date
        'mot_de_passe_expire': None,
        'nom': 'Tester',
        'prenom': 'Save',
        'role_id': 1,
        'est_intervenant': 0,
        'heures_dispo_semaine': None,
        'doc_carte_vitale': None,
        'doc_cni': None,
        'doc_adhesion': None,
        'doc_rib': None,
    }
    # Ensure role exists
    db.execute("INSERT INTO Roles (role_id, nom, hierarchie) VALUES (?, ?, ?)", (1, 'User', 10))
    db.commit()

    u = Utilisateur(db, user_data)
    # Save should INSERT into the DB and update redis caches
    u.save()

    # Check DB row exists
    cursor = db.execute("SELECT email FROM Utilisateurs WHERE utilisateur_id = ?", (99,))
    row = cursor.fetchone()
    assert row is not None and row[0] == 'save.test@example.com'
    cursor.close()

    # Check individual cache exists
    cache_key = redis_key(Utilisateur.CACHE_PREFIX, 99)
    cached = fake_redis.get(cache_key)
    assert cached is not None
    obj = json.loads(cached)
    assert obj['email'] == 'save.test@example.com'

    # Delete and ensure removal
    u.delete()
    cursor = db.execute("SELECT email FROM Utilisateurs WHERE utilisateur_id = ?", (99,))
    assert cursor.fetchone() is None
    cursor.close()
    # Cache should be removed
    assert fake_redis.get(cache_key) is None


def test_user_competences_and_cache(db):
    ensure_competences_tables(db)
    # Ensure roles and competences tables exist
    db.execute("INSERT INTO Roles (role_id, nom, hierarchie) VALUES (?, ?, ?)", (1, 'User', 10))
    db.execute("INSERT INTO Competences (competence_id, nom) VALUES (?, ?)", (101, 'Python'))
    db.execute("INSERT INTO Intervenant_competences (intervenant_id, competence_id, niveau) VALUES (?, ?, ?)", (30, 101, 5))
    db.commit()

    # Insert user
    insert_user(db, 30, "user.competance@example.org", "Competance", "User", 1)
    db.commit()
    user = db.get_user_by_id(30)
    assert user is not None
    competences = user.competences
    assert isinstance(competences, list)
    assert any(c.competence_id == 101 and c.nom == 'Python' for c in competences)


"""Tests des rôles"""

def test_role_crud(db):
    # Insert a role directly via SQL
    db.execute("INSERT INTO Roles (role_id, nom, hierarchie) VALUES (?, ?, ?)", (5, 'Manager', 5))
    db.commit()

    role = db.get_role_by_id(5)
    assert role is not None
    assert role.role_id == 5
    assert role.nom == 'Manager'
    assert role.hierarchie == 5

    cursor = db.execute("SELECT role_id FROM Roles")
    rows = cursor.fetchall()
    cursor.close()
    assert any(r[0] == 5 for r in rows)

    # Test de get_all_roles
    roles = db.get_all_roles()
    assert any(r.role_id == 5 for r in roles)


def test_role_save_and_delete(db, fake_redis):
    role_data = {
        "role_id": 4,
        "nom": "Président",
        "hierarchie": 1
    }

    r = Role(db, role_data)
    # Save doit ajouter le role dans la DB et l'enregistrer dans redis
    r.save()

    # Vérification si jamais le rôle existe dans la base de donnée
    cursor = db.execute("SELECT nom FROM Roles WHERE role_id=?", (4,))
    row = cursor.fetchone()
    assert row[0] == "Président"
    cursor.close()

    # Vérification du cache Redis
    cache_key = redis_key(getattr(Role, 'CACHE_PREFIX', None) or Role.__name__.lower(), 4)
    cached = fake_redis.get(cache_key)
    assert cached is not None
    obj = json.loads(cached)
    assert obj.get('nom') == "Président"

    # Vérification du delete
    r.delete()
    cursor = db.execute("SELECT nom FROM Roles WHERE role_id=?", (4,))
    assert cursor.fetchone() is None
    cursor.close()
    # Cache should be removed
    assert fake_redis.get(cache_key) is None

def test_get_user_role(db):
    # Insert role and user
    db.execute("INSERT INTO Roles (role_id, nom, hierarchie) VALUES (?, ?, ?)", (2, 'User', 10))
    db.execute(
        "INSERT INTO Utilisateurs (utilisateur_id, email, mot_de_passe_hashed, mot_de_passe_expire, nom, prenom, role_id, est_intervenant, heures_dispo_semaine, doc_carte_vitale, doc_cni, doc_adhesion, doc_rib) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (20, 'role.user', 'pwd', '2025-12-31', 'User', 'Role', 2, 0, None, None, None, None, None)
    )
    db.commit()
    user = db.get_user_by_id(20)
    assert user is not None
    role = user.role
    assert role is not None
    assert role.role_id == 2
    assert role.nom == 'User'


if __name__ == '__main__':
    pytest.main([__file__])
