import datetime
import json
import logging
import sqlite3
import unicodedata
from typing import Any, List, Optional, cast, Sequence, Mapping, Dict, Tuple
from flask_login import UserMixin


def normalize_text(s: Optional[str]) -> str:
    """Normalize a text for consistent comparisons and cache keys (lower, strip, remove accents)."""
    if s is None:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


# Builder de clés Redis exporté
def redis_key(resource: str, id_: Optional[Any] = None, suffix: Optional[str] = None) -> str:
    """
    Construit une clé Redis simple et consistante.
    Exemples:
      redis_key('user', 123) -> 'user:123'
      redis_key('Utilisateurs', None, 'email:jean.dupont@example.com') -> 'utilisateurs:email:jean.dupont@example.com'
    Note: le resource peut être le DATABASE_NAME (avec majuscule initiale) ou un préfixe plus court ('user').
    """
    parts: List[str] = [str(resource)]
    if id_ is not None:
        parts.append(str(id_))
    if suffix is not None:
        parts.append(str(suffix))
    return ":".join(parts).lower()


class Database:
    def __init__(self, redis_client: Any, database: str | bytes, **kwargs):
        """Initialise la connexion à la base de données SQLite et stocke le client Redis.

        :param redis_client: instance du client Redis utilisée pour le caching et index secondaires
        :param database: chemin vers le fichier SQLite ou bytes pour un in-memory DB
        :param kwargs: arguments optionnels passés à sqlite3.connect
        :raises ValueError: si redis_client ou database est invalide
        :raises RuntimeError: si la connexion SQLite échoue
        """
        if not redis_client:
            raise ValueError("A valid redis_client must be provided")
        if not database:
            raise ValueError("A valid database path must be provided")
        self.redis_client = redis_client
        try:
            self.db = sqlite3.connect(database, **kwargs)
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to connect to database: {e}") from e

    def invalidate_project(self, projet_id: int):
        try:
            self.redis_client.delete(f"projets:{projet_id}")
            self.redis_client.delete(f"projets:{projet_id}:jalons")
            self.redis_client.delete(f"projets:{projet_id}:competences")
            self.redis_client.delete(f"projets:{projet_id}:intervenants")
        except Exception:
            pass

    def close(self):
        """Ferme la connexion SQLite associée à cette instance Database."""
        self.db.close()

    def commit(self):
        """Valide la transaction courante sur la base SQLite.

        Lève RuntimeError en cas d'erreur SQLite.
        """
        try:
            self.db.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to commit transaction: {e}") from e

    def execute(self, query: str, params: Sequence[Any] | Mapping[str, Any] | Any = ()) -> sqlite3.Cursor:
        """Execute une requête SQL et retourne le curseur résultant.

        :param query: requête SQL (optionnellement paramétrée)
        :param params: paramètres pour la requête (tuple/list ou dict)
        :return: sqlite3.Cursor pointant sur les résultats
        :raises RuntimeError: si sqlite renvoie une erreur
        """
        try:
            return self.db.execute(query, params)
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to execute query: {e}") from e

    def cursor(self):
        """Retourne un nouveau curseur SQLite (équivalent de connection.cursor())."""
        return self.db.cursor()

    # Méthode utilitaire pour interroger un index Redis secondaire (exact match)
    def _get_index_ids(self, database_name: str, field: str, value: str) -> Optional[List[int]]:
        """
        Interroge l'index Redis secondaire pour `database_name`/`field` = normalized(value).
        Retourne la liste d'ids (entiers) ou None si l'index n'existe pas.
        """
        if not value:
            return None
        try:
            key = redis_key(f"index:{database_name}", suffix=f"{field}:{normalize_text(value)}")
            members = self.redis_client.smembers(key)
            if not members:
                return None
            ids: List[int] = []
            for m in members:
                # redis-py peut renvoyer bytes ou str
                if isinstance(m, bytes):
                    m = m.decode()
                try:
                    ids.append(int(m))
                except Exception:
                    # ignorer les valeurs non-int
                    continue
            return ids
        except Exception:
            return None

    def get_user_by_id(self, user_id: int) -> Optional['Utilisateur']:
        """Récupère un utilisateur par son identifiant.

        Cherche d'abord dans le cache Redis, puis interroge la table SQLite si nécessaire.
        :param user_id: identifiant de l'utilisateur
        :return: instance Utilisateur ou None si non trouvée
        """
        cached_user = self.redis_client.get(redis_key(getattr(Utilisateur, 'CACHE_PREFIX', None) or Utilisateur.__name__.lower(), user_id))
        if cached_user:
            return Utilisateur.from_db_row(self, json.loads(cached_user))
        cursor = self.execute(f"SELECT * FROM {Utilisateur.DATABASE_NAME} WHERE utilisateur_id = ?", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            user = Utilisateur.from_db_row(self, row)
            return user
        return None

    def get_users_by_ids(self, user_ids: List[int]) -> List['Utilisateur']:
        """Récupère une liste d'utilisateurs à partir d'une liste d'identifiants.

        Les utilisateurs absents sont ignorés.
        :param user_ids: liste d'identifiants
        :return: liste d'objets Utilisateur existants
        """
        users = []
        for uid in user_ids:
            user = self.get_user_by_id(uid)
            if user:
                users.append(user)
        return users

    def get_user_by_email(self, email: str) -> 'Utilisateur':
        """Récupère un utilisateur par email.

        Tente d'abord d'utiliser un index secondaire Redis pour une recherche exacte, sinon interroge la BDD.
        Lève ValueError si aucun utilisateur trouvé.
        :param email: adresse email recherchée
        :return: instance Utilisateur
        """
        # Tenter d'utiliser l'index Redis secondaire pour recherche exacte
        ids = self._get_index_ids(Utilisateur.DATABASE_NAME, 'email', email)
        if ids:
            # on s'attend à un seul résultat sur email ; prendre le premier
            user = self.get_user_by_id(ids[0])
            if user:
                return user
        # Requête d'égalité sur l'email — on s'attend à un seul résultat
        cursor = self.execute(f"SELECT * FROM {Utilisateur.DATABASE_NAME} WHERE email = ?", (email,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            user = Utilisateur.from_db_row(self, row)
            return user
        raise ValueError(f"User with email {email} not found")

    def get_users_by_name(self, nom: str = None, prenom: str = None) -> List['Utilisateur']:
        """Récupère les utilisateurs correspondant au nom et/ou prénom donnés.

        Au moins l'un des paramètres doit être fourni. Utilise les index Redis secondaires si possible.
        :param nom: nom de famille (optionnel)
        :param prenom: prénom (optionnel)
        :return: liste d'objets Utilisateur correspondant
        """
        if nom is None and prenom is None:
            raise ValueError("At least one of 'nom' or 'prenom' must be provided")

        # Tenter d'utiliser les index Redis secondaires (recherche exacte)
        ids_sets: List[set] = []
        if nom is not None:
            ids = self._get_index_ids(Utilisateur.DATABASE_NAME, 'nom', nom)
            if ids:
                ids_sets.append(set(ids))
        if prenom is not None:
            ids = self._get_index_ids(Utilisateur.DATABASE_NAME, 'prenom', prenom)
            if ids:
                ids_sets.append(set(ids))
        if ids_sets:
            # intersecter les sets si plusieurs critères, sinon prendre le seul set
            result_ids = set.intersection(*ids_sets) if len(ids_sets) > 1 else ids_sets[0]
            users = [self.get_user_by_id(uid) for uid in result_ids]
            return [user for user in users if user is not None]

        query = f"SELECT * FROM {Utilisateur.DATABASE_NAME} WHERE "
        params = []
        conditions = []
        if nom is not None:
            conditions.append("nom = ?")
            params.append(nom)
        if prenom is not None:
            conditions.append("prenom = ?")
            params.append(prenom)
        query += " AND ".join(conditions)
        cursor = self.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        users = [Utilisateur.from_db_row(self, row) for row in rows]
        return users

    def get_users_by_text_search(self, text: str) -> List['Utilisateur']:
        """Recherche floue (LIKE) sur nom, prénom et email et retourne les utilisateurs correspondants.

        :param text: texte de recherche (substring)
        :return: liste d'objets Utilisateur
        """
        like_pattern = f"%{text}%"
        cursor = self.execute(
            f"SELECT * FROM {Utilisateur.DATABASE_NAME} WHERE nom LIKE ? OR prenom LIKE ? OR email LIKE ?",
            (like_pattern, like_pattern, like_pattern)
        )
        rows = cursor.fetchall()
        cursor.close()
        users = [Utilisateur.from_db_row(self, row) for row in rows]
        return users

    def get_all_users(self, limit: int = 0, *, sort_by: Optional[str] = None, sort_dir: str = 'asc', offset: int = 0, key=lambda x: True) -> List['Utilisateur']:
        """
        Récupère tous les utilisateurs de la base de données.
        :param limit: Nombre maximum d'utilisateurs à récupérer (0 pour aucune limite)
        :param sort_by: nom de champ pour trier (doit être dans Utilisateur.FIELD_NAMES)
        :param sort_dir: 'asc' ou 'desc'
        :param offset: Nombre d'enregistrements à ignorer avant de commencer à collecter le résultat (pour la pagination)
        :param key: Fonction de filtrage optionnelle
        :return: Liste des objets Utilisateur
        """
        def _apply_python_sort(objs: List[Any], attr: str, direction: str) -> List[Any]:
            reverse = direction.lower() == 'desc'
            def _k(o: Any):
                v = getattr(o, attr, None)
                # Normaliser pour la comparaison: None -> (1, None) pour les pousser en fin
                if v is None:
                    return (1, None)
                # Les chaînes en minuscules pour tri insensible à la casse
                if isinstance(v, str):
                    return (0, v.lower())
                return (0, v)
            try:
                return sorted(objs, key=_k, reverse=reverse)
            except Exception:
                return objs

        cached_users = self.redis_client.get(redis_key(Utilisateur.DATABASE_NAME.lower(), None, "all"))
        if cached_users:
            all_users_id = json.loads(cached_users)
            users = [self.get_user_by_id(uid) for uid in all_users_id]
            users = [user for user in users if user is not None and key(user)]
            if sort_by:
                if sort_by not in getattr(Utilisateur, 'FIELD_NAMES', []):
                    raise ValueError(f"Invalid sort_by field for users: {sort_by}")
                users = _apply_python_sort(users, sort_by, sort_dir)
            # Appliquer offset+limit côté cache si demandés (offset pris en compte seulement si limit>0)
            if limit > 0:
                if offset and offset > 0:
                    users = users[offset:]
                return users[:limit]
            return users
        # Construire la clause ORDER BY si nécessaire (sécurisée en vérifiant les champs autorisés)
        order_clause = ""
        if sort_by:
            if sort_by not in getattr(Utilisateur, 'FIELD_NAMES', []):
                raise ValueError(f"Invalid sort_by field for users: {sort_by}")
            if sort_dir.lower() not in ('asc', 'desc'):
                raise ValueError('sort_dir must be "asc" or "desc"')
            order_clause = f" ORDER BY {sort_by} {sort_dir.upper()}"
        # Si limit>0, appliquer LIMIT et OFFSET en SQL (OFFSET utile pour pagination fenêtre).
        if limit > 0:
            query_tail = f" LIMIT ? OFFSET ?"
            sql_params = (limit, offset)
        else:
            query_tail = ""
            sql_params = ()
        cursor = self.execute(f"SELECT * FROM {Utilisateur.DATABASE_NAME}" + order_clause + query_tail, sql_params)
        rows = cursor.fetchall()
        cursor.close()

        if limit == 0:
            # Mettre en cache les IDs des utilisateurs
            all_users_id = [row[0] for row in rows]  # Supposant que l'ID est dans la première colonne
            self.redis_client.setex(redis_key(Utilisateur.DATABASE_NAME.lower(), None, "all"), 1_800, json.dumps(all_users_id))

        users = [Utilisateur.from_db_row(self, row) for row in rows]
        users = [user for user in users if key(user)]
        if sort_by:
            users = _apply_python_sort(users, sort_by, sort_dir)
        return users

    def get_client_by_id(self, client_id: int) -> Optional['Client']:
        """Récupère un client par son identifiant.

        Cherche d'abord dans le cache Redis, puis en base de données.
        :param client_id: identifiant du client
        :return: instance Client ou None si non trouvée
        """
        cached_client = self.redis_client.get(redis_key(getattr(Client, 'CACHE_PREFIX', None) or Client.__name__.lower(), client_id))
        if cached_client:
            return Client.from_db_row(self, json.loads(cached_client))
        cursor = self.execute(f"SELECT * FROM {Client.DATABASE_NAME} WHERE client_id = ?", (client_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            client = Client.from_db_row(self, row)
            return client
        return None

    def get_all_clients(self, limit: int = 0, *, sort_by: Optional[str] = None, sort_dir: str = 'asc', offset: int = 0, key=lambda x: True) -> List['Client']:
        """
        Récupère tous les clients de la base de données.
        :param limit: Nombre maximum de clients à récupérer (0 pour aucune limite)
        :param sort_by: nom de champ pour trier (doit être dans Client.FIELD_NAMES)
        :param sort_dir: 'asc' ou 'desc'
        :param offset: Nombre d'enregistrements à ignorer avant de commencer à collecter le résultat (pour la pagination)
        :param key: Fonction de filtrage optionnelle
        :return: Liste des objets Client
        """
        def _apply_python_sort(objs: List[Any], attr: str, direction: str) -> List[Any]:
            reverse = direction.lower() == 'desc'
            def _k(o: Any):
                v = getattr(o, attr, None)
                if v is None:
                    return (1, None)
                if isinstance(v, str):
                    return (0, v.lower())
                return (0, v)
            try:
                return sorted(objs, key=_k, reverse=reverse)
            except Exception:
                return objs

        cached_clients = self.redis_client.get(redis_key(Client.DATABASE_NAME.lower(), None, "all"))
        if cached_clients:
            all_clients_id = json.loads(cached_clients)
            clients = [self.get_client_by_id(cid) for cid in all_clients_id]
            clients = [client for client in clients if client is not None and key(client)]
            if sort_by:
                if sort_by not in getattr(Client, 'FIELD_NAMES', []):
                    raise ValueError(f"Invalid sort_by field for clients: {sort_by}")
                clients = _apply_python_sort(clients, sort_by, sort_dir)
            if limit > 0:
                if offset and offset > 0:
                    clients = clients[offset:]
                return clients[:limit]
            return clients
        order_clause = ""
        if sort_by:
            if sort_by not in getattr(Client, 'FIELD_NAMES', []):
                raise ValueError(f"Invalid sort_by field for clients: {sort_by}")
            if sort_dir.lower() not in ('asc', 'desc'):
                raise ValueError('sort_dir must be "asc" or "desc"')
            order_clause = f" ORDER BY {sort_by} {sort_dir.upper()}"
        if limit > 0:
            query_tail = " LIMIT ? OFFSET ?"
            sql_params = (limit, offset)
        else:
            query_tail = ""
            sql_params = ()
        cursor = self.execute(f"SELECT * FROM {Client.DATABASE_NAME}" + order_clause + query_tail, sql_params)  # TODO: Décider si la coupe doit être faite en SQL ou en Python
        rows = cursor.fetchall()
        cursor.close()

        if limit == 0:
            # Mettre en cache les IDs des clients
            all_clients_id = [row[0] for row in rows]  # Supposant que l'ID est dans la première colonne
            self.redis_client.setex(redis_key(Client.DATABASE_NAME.lower(), None, "all"), 1_800, json.dumps(all_clients_id))

        clients = [Client.from_db_row(self, row) for row in rows]
        clients = [client for client in clients if key(client)]
        if sort_by:
            clients = _apply_python_sort(clients, sort_by, sort_dir)
        return clients

    def get_convention_by_id(self, convention_id: int) -> Optional['Convention']:
        """Récupère une convention par son identifiant.

        Cherche d'abord dans le cache Redis, puis en base de données.
        :param convention_id: identifiant de la convention
        :return: instance Convention ou None si non trouvée
        """
        cached_convention = self.redis_client.get(redis_key(getattr(Convention, 'CACHE_PREFIX', None) or Convention.__name__.lower(), convention_id))
        if cached_convention:
            return Convention.from_db_row(self, json.loads(cached_convention))
        cursor = self.execute(f"SELECT * FROM {Convention.DATABASE_NAME} WHERE convention_id = ?", (convention_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            convention = Convention.from_db_row(self, row)
            return convention
        return None

    def get_all_conventions(self, limit: int = 0, *, key=lambda x: True) -> List['Convention']:
        """Récupère toutes les conventions (optionnellement limitées).

        :param limit: nombre maximum de conventions à récupérer (0 = aucun)
        :param key: fonction de filtrage optionnelle
        :return: liste d'objets Convention
        """
        cached_conventions = self.redis_client.get(redis_key(Convention.DATABASE_NAME.lower(), None, "all"))
        if cached_conventions:
            all_conventions_id = json.loads(cached_conventions)
            conventions = [self.get_convention_by_id(cid) for cid in all_conventions_id]
            conventions = [convention for convention in conventions if convention is not None and key(convention)]
            if limit > 0:
                return conventions[:limit]
            return conventions
        cursor = self.execute(f"SELECT * FROM {Convention.DATABASE_NAME} " + (" LIMIT ?" if limit > 0 else ""), (limit,) if limit > 0 else ())  # TODO: Décider si la coupe doit être faite en SQL ou en Python
        rows = cursor.fetchall()
        cursor.close()

        if limit == 0:
            # Mettre en cache les IDs des conventions
            all_conventions_id = [row[0] for row in rows]  # Supposant que l'ID est dans la première colonne
            self.redis_client.setex(redis_key(Convention.DATABASE_NAME.lower(), None, "all"), 1_800, json.dumps(all_conventions_id))

        conventions = [Convention.from_db_row(self, row) for row in rows]
        conventions = [convention for convention in conventions if key(convention)]
        return conventions


    def get_role_by_id(self, role_id: int) -> Optional['Role']:
        cached_role = self.redis_client.get(
            redis_key(getattr(Role, 'CACHE_PREFIX', None) or Role.__name__.lower(), role_id))
        if cached_role:
            return Role.from_db_row(self, json.loads(cached_role))
        cursor = self.execute(f"SELECT * FROM {Role.DATABASE_NAME} WHERE role_id = ?", (role_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            role = Role.from_db_row(self, row)
            return role
        return None

    def get_all_roles(self, limit: int = 0, *, sort_by: Optional[str] = None, sort_dir: str = 'asc', offset: int = 0, key=lambda x: True) -> List['Role']:
        """Récupère tous les rôles

        :param limit: nombre maximum de rôles à récupérer (0 = aucun)
        :param sort_by: nom de champ pour trier (doit être dans Role.FIELD_NAMES)
        :param sort_dir: 'asc' ou 'desc'
        :param offset: Nombre d'enregistrements à ignorer avant de commencer à collecter le résultat (pour la pagination)
        :param key: fonction de filtrage optionnelle
        :return: liste d'objets Role
        """
        def _apply_python_sort(objs: List[Any], attr: str, direction: str) -> List[Any]:
            reverse = direction.lower() == 'desc'
            def _k(o: Any):
                v = getattr(o, attr, None)
                if v is None:
                    return (1, None)
                if isinstance(v, str):
                    return (0, v.lower())
                return (0, v)
            try:
                return sorted(objs, key=_k, reverse=reverse)
            except Exception:
                return objs

        cached_roles = self.redis_client.get(redis_key(Role.DATABASE_NAME.lower(), None, "all"))
        if cached_roles:
            all_roles_id = json.loads(cached_roles)
            roles = [self.get_role_by_id(cid) for cid in all_roles_id]
            roles = [role for role in roles if role is not None and key(role)]
            if sort_by:
                if sort_by not in getattr(Role, 'FIELD_NAMES', []):
                    raise ValueError(f"Invalid sort_by field for roles: {sort_by}")
                roles = _apply_python_sort(roles, sort_by, sort_dir)
            if limit > 0:
                if offset and offset > 0:
                    roles = roles[offset:]
                return roles[:limit]
            return roles
        order_clause = ""
        if sort_by:
            if sort_by not in getattr(Role, 'FIELD_NAMES', []):
                raise ValueError(f"Invalid sort_by field for roles: {sort_by}")
            if sort_dir.lower() not in ('asc', 'desc'):
                raise ValueError('sort_dir must be "asc" or "desc"')
            order_clause = f" ORDER BY {sort_by} {sort_dir.upper()}"
        if limit > 0:
            query_tail = " LIMIT ? OFFSET ?"
            sql_params = (limit, offset)
        else:
            query_tail = ""
            sql_params = ()
        cursor = self.execute(f"SELECT * FROM {Role.DATABASE_NAME}" + order_clause + query_tail, sql_params)  # TODO: Décider si la coupe doit être faite en SQL ou en Python
        rows = cursor.fetchall()
        cursor.close()

        if limit == 0:
            # Mettre en cache les IDs des roles
            all_roles_id = [row[0] for row in rows]  # Supposant que l'ID est dans la première colonne
            # Note: utiliser Role.DATABASE_NAME ici (correction d'une clef erronée précédemment)
            try:
                self.redis_client.setex(redis_key(Role.DATABASE_NAME.lower(), None, "all"), 1_800, json.dumps(all_roles_id))
            except Exception:
                pass

        roles = [Role.from_db_row(self, row) for row in rows]
        roles = [role for role in roles if key(role)]
        if sort_by:
            roles = _apply_python_sort(roles, sort_by, sort_dir)
        return roles


    def get_project_id(self, project_id: int) -> Optional['Projet']:
        """Récupère un projet par son identifiant.

        :param project_id: identifiant du projet
        :return: instance Projet ou None si non trouvée
        """
        cached_project = self.redis_client.get(
            redis_key(getattr(Projet, 'CACHE_PREFIX', None) or Projet.__name__.lower(), project_id))
        if cached_project:
            return Projet.from_db_row(self, json.loads(cached_project))
        cursor = self.execute(f"SELECT * FROM {Projet.DATABASE_NAME} WHERE projet_id = ?", (project_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            project = Projet.from_db_row(self, row)
            return project
        return None

    def get_all_projects(self, limit: int = 0, *, sort_by: Optional[str] = None, sort_dir: str = 'asc', offset: int = 0, key=lambda x: True) -> List['Projet']:
        """Récupère tous les projets (optionnellement limités et filtrés).

        :param limit: limite sur le nombre de projets (0 = aucun)
        :param sort_by: nom de champ pour trier (doit être dans Projet.FIELD_NAMES)
        :param sort_dir: 'asc' ou 'desc'
        :param offset: Nombre d'enregistrements à ignorer avant de commencer à collecter le résultat (pour la pagination)
        :param key: fonction de filtrage optionnelle
        :return: liste d'objets Projet
        """
        def _apply_python_sort(objs: List[Any], attr: str, direction: str) -> List[Any]:
            reverse = direction.lower() == 'desc'
            def _k(o: Any):
                v = getattr(o, attr, None)
                if v is None:
                    return (1, None)
                if isinstance(v, str):
                    return (0, v.lower())
                return (0, v)
            try:
                return sorted(objs, key=_k, reverse=reverse)
            except Exception:
                return objs

        cached_projects = self.redis_client.get(redis_key(Projet.DATABASE_NAME.lower(), None, "all"))
        if cached_projects:
            all_projects_id = json.loads(cached_projects)
            projects = [self.get_project_id(pid) for pid in all_projects_id]
            projects = [project for project in projects if project is not None and key(project)]
            if sort_by:
                if sort_by not in getattr(Projet, 'FIELD_NAMES', []):
                    raise ValueError(f"Invalid sort_by field for projects: {sort_by}")
                projects = _apply_python_sort(projects, sort_by, sort_dir)
            if limit > 0:
                if offset and offset > 0:
                    projects = projects[offset:]
                return projects[:limit]
            return projects
        order_clause = ""
        if sort_by:
            if sort_by not in getattr(Projet, 'FIELD_NAMES', []):
                raise ValueError(f"Invalid sort_by field for projects: {sort_by}")
            if sort_dir.lower() not in ('asc', 'desc'):
                raise ValueError('sort_dir must be "asc" or "desc"')
            order_clause = f" ORDER BY {sort_by} {sort_dir.upper()}"
        if limit > 0:
            query_tail = " LIMIT ? OFFSET ?"
            sql_params = (limit, offset)
        else:
            query_tail = ""
            sql_params = ()
        cursor = self.execute(f"SELECT * FROM {Projet.DATABASE_NAME}" + order_clause + query_tail, sql_params)  # TODO: Décider si la coupe doit être faite en SQL ou en Python
        rows = cursor.fetchall()
        cursor.close()
        if limit == 0:
            # Mettre en cache les IDs des projets
            all_projects_id = [row[0] for row in rows]  # Supposant que l'ID est dans la première colonne
            self.redis_client.setex(redis_key(Projet.DATABASE_NAME.lower(), None, "all"), 1_800, json.dumps(all_projects_id))
        projects = [Projet.from_db_row(self, row) for row in rows]
        projects = [project for project in projects if key(project)]
        if sort_by:
            projects = _apply_python_sort(projects, sort_by, sort_dir)
        return projects

    def get_interaction_by_id(self, interaction_id: int) -> Optional['Interaction']:
        """Récupère une interaction par son identifiant.

        :param interaction_id: identifiant de l'interaction
        :return: instance Interaction ou None si non trouvée
        """
        cached_interaction = self.redis_client.get(
            redis_key(getattr(Interaction, 'CACHE_PREFIX', None) or Interaction.__name__.lower(), interaction_id))
        if cached_interaction:
            return Interaction.from_db_row(self, json.loads(cached_interaction))
        cursor = self.execute(f"SELECT * FROM {Interaction.DATABASE_NAME} WHERE interaction_id = ?", (interaction_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            interaction = Interaction.from_db_row(self, row)
            return interaction
        return None

    def get_all_interactions(self, project_id : int | None = None, user_id: int | None = None, limit: int = 0, *, sort_by: Optional[str] = None, sort_dir: str = 'asc', offset: int = 0, text: Optional[str] = None, key=lambda x: True) -> List['Interaction']:
        """Récupère les interactions, optionnellement filtrées par projet ou utilisateur.

        Utilise le cache Redis si disponible. Retourne une liste d'objets Interaction.
        :param project_id: filtrer par projet_id (optionnel)
        :param user_id: filtrer par utilisateur_id (optionnel)
        :param limit: nombre maximal d'interactions (0 = aucun)
        :param sort_by: nom de champ pour trier (doit être dans Interaction.FIELD_NAMES)
        :param sort_dir: 'asc' ou 'desc'
        :param offset: Nombre d'enregistrements à ignorer avant de commencer à collecter le résultat (pour la pagination)
        :param key: fonction de filtrage optionnelle
        :return: liste d'objets Interaction
        """
        def _apply_python_sort(objs: List[Any], attr: str, direction: str) -> List[Any]:
            reverse = direction.lower() == 'desc'
            def _k(o: Any):
                v = getattr(o, attr, None)
                if v is None:
                    return (1, None)
                if isinstance(v, str):
                    return (0, v.lower())
                return (0, v)
            try:
                return sorted(objs, key=_k, reverse=reverse)
            except Exception:
                return objs

        # Mappage d'alias pour faciliter l'utilisation de paramètres courts
        INTERACTION_FIELD_ALIASES = {
            'date': 'date_time_interaction',
            'date_time': 'date_time_interaction',
            'datetime': 'date_time_interaction',
            'titre': 'titre',
            'title': 'titre'
        }

        def _map_interaction_field(name: Optional[str]) -> Optional[str]:
            """Mappe un alias de champ vers le nom réel attendu dans Interaction.FIELD_NAMES.
            Conserve les formes pointées (relation.colonne) telles quelles.
            """
            if not name:
                return None
            s = str(name)
            # Si la valeur contient un point, c'est une relation (ex: client.nom_entreprise) -> laisser telle quelle
            if '.' in s:
                return s
            return INTERACTION_FIELD_ALIASES.get(s, s)

        cached_interactions = self.redis_client.get(redis_key(Interaction.DATABASE_NAME.lower(), None, "all"))
        if cached_interactions:
            all_interactions_id = json.loads(cached_interactions)
            interactions = [self.get_interaction_by_id(iid) for iid in all_interactions_id]
            interactions = [interaction for interaction in interactions if interaction is not None and key(interaction)]
            if project_id is not None:
                interactions = [interaction for interaction in interactions if getattr(interaction, 'projet_id', None) == project_id]
            if user_id is not None:
                interactions = [interaction for interaction in interactions if getattr(interaction, 'utilisateur_id', None) == user_id]
            if sort_by:
                # Normaliser quelques alias de relation utilisés dans les templates
                REL_ALIAS = {
                    'interlocuteur': 'utilisateur',
                    'interlocuteurs': 'utilisateur',
                    'user': 'utilisateur',
                    'entreprise': 'client',
                    'client': 'client',
                    'utilisateur': 'utilisateur'
                }
                sb = str(sort_by)
                # mapper les alias (ex: 'date' -> 'date_time_interaction', 'title' -> 'titre')
                sb = _map_interaction_field(sort_by)
                # Supporter uniquement la forme pointée: 'client.nom_entreprise' ou 'utilisateur.nom_prenom'
                if '.' in sb:
                    rel, col = sb.split('.', 1)
                    rel = rel.lower().strip()
                    col = col.strip()
                    rel_norm = REL_ALIAS.get(rel, rel)
                    if rel_norm == 'client':
                        # N'accepter que la forme avec underscore pour la colonne (ex: 'nom_entreprise')
                        col_norm = col
                        if '.' in col_norm:
                            raise ValueError(f"Invalid client sort field format: {col} (use underscore, e.g. 'nom_entreprise')")
                        if col_norm not in getattr(Client, 'FIELD_NAMES', []):
                            raise ValueError(f"Invalid client sort field: {col}")
                        interactions = sorted(interactions, key=lambda i: ((getattr(i.client, col_norm) or '').lower()), reverse=(sort_dir.lower() == 'desc'))
                    elif rel_norm == 'utilisateur':
                        # Support tri composite nom + prenom
                        if col == 'nom_prenom':
                            interactions = sorted(interactions, key=lambda i: (((getattr(i.utilisateur, 'nom') or '').lower(), (getattr(i.utilisateur, 'prenom') or '').lower())), reverse=(sort_dir.lower() == 'desc'))
                        else:
                            if col not in getattr(Utilisateur, 'FIELD_NAMES', []):
                                raise ValueError(f"Invalid utilisateur sort field: {col}")
                            interactions = sorted(interactions, key=lambda i: ((getattr(i.utilisateur, col) or '').lower()), reverse=(sort_dir.lower() == 'desc'))
                    else:
                        raise ValueError(f"Unsupported relation for sort_by in cache: {rel}")
                else:
                    # Tri sur un champ de la table Interaction (tri Python) — n'accepte pas les variantes avec '_'
                    # Appliquer le mapping d'alias (ex: 'date' -> 'date_time_interaction')
                    sb_mapped = _map_interaction_field(sb)
                    if sb_mapped not in getattr(Interaction, 'FIELD_NAMES', []):
                        raise ValueError(f"Invalid sort_by field for interactions: {sb}")
                    interactions = _apply_python_sort(interactions, sb_mapped, sort_dir)
            # Appliquer offset+limit côté cache si demandés (offset pris en compte seulement si limit>0)
            if limit > 0:
                if offset and offset > 0:
                    interactions = interactions[offset:]
                return interactions[:limit]
            return interactions
        # Construire la requête en supportant d'éventuels JOINs si on trie sur des champs liés
        # Par défaut on interroge la table d'interactions aliasée en 'i'
        base_table = Interaction.DATABASE_NAME
        query = f"SELECT i.* FROM {base_table} i"
        params: List[Any] = []
        joins: List[str] = []
        conditions: List[str] = []
        if project_id is not None:
            conditions.append("i.projet_id = ?")
            params.append(project_id)
        if user_id is not None:
            conditions.append("i.utilisateur_id = ?")
            params.append(user_id)

        # Détecter si le tri porte sur une colonne liée (client.xxx ou utilisateur.xxx)
        order_clause = ""
        if sort_by:
            # Support explicite du tri composite pour l'utilisateur (nom + prenom)
            # mapper les alias si besoin (ex: 'date' -> 'date_time_interaction') mais garder la forme pointée
            s_raw = str(sort_by)
            s_mapped = _map_interaction_field(s_raw)
            if s_mapped == 'utilisateur.nom_prenom' or s_raw == 'utilisateur.nom_prenom':
                joins.append(f"JOIN {Utilisateur.DATABASE_NAME} u ON i.utilisateur_id = u.utilisateur_id")
                if sort_dir.lower() not in ('asc', 'desc'):
                    raise ValueError('sort_dir must be "asc" or "desc"')
                order_clause = f" ORDER BY u.nom {sort_dir.upper()}, u.prenom {sort_dir.upper()}"
            else:
                # On n'accepte que la syntaxe avec '.' pour relation.colonne (ex: client.nom_entreprise)
                s = s_mapped if s_mapped is not None else str(sort_by)
                if '.' in s:
                    rel, col = s.split('.', 1)
                    rel = rel.lower()
                    col = col.strip()
                    # Normaliser quelques alias de relation utilisés dans les templates
                    REL_ALIAS = {
                        'interlocuteur': 'utilisateur',
                        'interlocuteurs': 'utilisateur',
                        'user': 'utilisateur',
                        'entreprise': 'client',
                        'client': 'client',
                        'utilisateur': 'utilisateur'
                    }
                    rel_norm = REL_ALIAS.get(rel, rel)
                    if rel_norm == 'client':
                        # N'accepter que la forme avec underscore pour la colonne (ex: 'nom_entreprise')
                        col_norm = col
                        if '.' in col_norm:
                            raise ValueError(f"Invalid client sort field format: {col} (use underscore, e.g. 'nom_entreprise')")
                        if col_norm not in getattr(Client, 'FIELD_NAMES', []):
                            raise ValueError(f"Invalid client sort field: {col}")
                        # Ajouter JOIN vers la table Clients
                        joins.append(f"JOIN {Client.DATABASE_NAME} c ON i.client_id = c.client_id")
                        if sort_dir.lower() not in ('asc', 'desc'):
                            raise ValueError('sort_dir must be "asc" or "desc"')
                        order_clause = f" ORDER BY c.{col_norm} {sort_dir.upper()}"
                    elif rel_norm in ('utilisateur', 'user', 'utilisateur_id', 'utilisateur'):
                        # Valider le champ côté Utilisateur
                        if col not in getattr(Utilisateur, 'FIELD_NAMES', []):
                            raise ValueError(f"Invalid utilisateur sort field: {col}")
                        joins.append(f"JOIN {Utilisateur.DATABASE_NAME} u ON i.utilisateur_id = u.utilisateur_id")
                        if sort_dir.lower() not in ('asc', 'desc'):
                            raise ValueError('sort_dir must be "asc" or "desc"')
                        order_clause = f" ORDER BY u.{col} {sort_dir.upper()}"
                    else:
                        raise ValueError(f"Unsupported relation for sort_by: {rel}")
                else:
                    # Tri sur un champ de la table Interaction (après mapping d'alias)
                    sort_field = _map_interaction_field(str(sort_by))
                    if sort_field not in getattr(Interaction, 'FIELD_NAMES', []):
                        raise ValueError(f"Invalid sort_by field for interactions: {sort_by}")
                    if sort_dir.lower() not in ('asc', 'desc'):
                        raise ValueError('sort_dir must be "asc" or "desc"')
                    order_clause = f" ORDER BY i.{sort_field} {sort_dir.upper()}"

        # Assembler JOINs et conditions
        if joins:
            query += ' ' + ' '.join(joins)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        # Ajouter clause ORDER BY si nécessaire
        query += order_clause
        # Appliquer LIMIT/OFFSET si demandé
        if limit > 0:
            query += " LIMIT ? OFFSET ?"
            params.append(limit)
            params.append(offset)
        cursor = self.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        if limit == 0:
            # Mettre en cache les IDs des interactions
            all_interactions_id = [row[0] for row in rows]  # Supposant que l'ID est dans la première colonne
            self.redis_client.setex(redis_key(Interaction.DATABASE_NAME.lower(), None, "all"), 1_800, json.dumps(all_interactions_id))
        interactions = [Interaction.from_db_row(self, row) for row in rows]
        interactions = [interaction for interaction in interactions if key(interaction)]
        # Si un sort_by est demandé, appliquer le tri Python final uniquement si c'est un champ d'Interaction
        if sort_by:
            mapped_final = _map_interaction_field(sort_by)
            # Si mapped_final contient un point c'est un tri lié (déjà appliqué par SQL/join) -> ne rien faire
            if mapped_final and '.' not in mapped_final and mapped_final in getattr(Interaction, 'FIELD_NAMES', []):
                interactions = _apply_python_sort(interactions, mapped_final, sort_dir)
        return interactions

    def count_interactions(self, project_id: int | None = None, user_id: int | None = None, text: Optional[str] = None) -> int:
        """
        Compte le nombre d'interactions correspondant aux filtres fournis en SQL.

        :param project_id: filtrer par projet_id (optionnel)
        :param user_id: filtrer par utilisateur_id (optionnel)
        :param text: recherche texte libre (appliquée sur plusieurs colonnes via LIKE)
        :return: nombre d'interactions correspondantes
        """
        base_table = Interaction.DATABASE_NAME
        query = f"SELECT COUNT(*) FROM {base_table} i"
        params: List[Any] = []
        joins: List[str] = []
        conditions: List[str] = []

        # join clients/utilisateurs only if needed for text search
        if text:
            # We'll need client and utilisateur columns in the WHERE (nom_entreprise, contact_email, nom, prenom)
            joins.append(f"JOIN {Client.DATABASE_NAME} c ON i.client_id = c.client_id")
            joins.append(f"JOIN {Utilisateur.DATABASE_NAME} u ON i.utilisateur_id = u.utilisateur_id")
            like = f"%{text.lower()}%"
            # search across several columns similar to interaction_filter, use LOWER(...) to be case-insensitive
            conditions.append("(CAST(i.interaction_id AS TEXT) LIKE ? OR LOWER(c.nom_entreprise) LIKE ? OR LOWER(c.contact_email) LIKE ? OR LOWER(u.nom) LIKE ? OR LOWER(u.prenom) LIKE ? OR LOWER(i.type_interaction_id) LIKE ? OR LOWER(i.titre) LIKE ? OR LOWER(i.contenu) LIKE ?)")
            params.extend([like] * 8)

        if project_id is not None:
            conditions.append("i.projet_id = ?")
            params.append(project_id)
        if user_id is not None:
            conditions.append("i.utilisateur_id = ?")
            params.append(user_id)

        if joins:
            query += ' ' + ' '.join(joins)
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        cursor = self.execute(query, tuple(params))
        row = cursor.fetchone()
        cursor.close()
        try:
            return int(row[0]) if row and row[0] is not None else 0
        except Exception:
            return 0


class DBObject:
    def __init__(self, db: Database):
        self.db = db

    def __repr__(self) -> str:
        """Représentation textuelle simple de l'objet (utile pour le débogage)."""
        return f"<{self.__class__.__name__}>"



# Classe utilitaire pour faciliter l'initialisation depuis un tuple ou dict
class _RowInitMixin:
    """
    Mixin pour initialiser un objet depuis une ligne de base de données (tuple) ou un dictionnaire.
    Utilise la liste FIELD_NAMES pour mapper les champs.
    Fournit aussi la gestion centralisée du cache Redis.
    """
    FIELD_NAMES: List[str] = []

    # Nom de la base de donnée pour les saves
    DATABASE_NAME : str

    # Durée de mise en cache par défaut (30 minutes)
    CACHE_TTL: int = 1_800
    # Préfixe de clé Redis par défaut ; peut être surchargé par les classes (ex: Utilisateur -> 'user')
    CACHE_PREFIX: Optional[str] = None

    # Champs à indexer dans Redis pour recherche exacte (secondary indexes)
    SECONDARY_INDEX_FIELDS: List[str] = []

    db: Optional[Database]

    def _init_from(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]]):
        """Initialise les attributs d'une instance à partir d'une ligne (tuple/list) ou d'un dict.

        Si data est None, initialise les champs listés dans FIELD_NAMES à None.
        :param db: instance de Database
        :param data: tuple/list ou dict représentant les valeurs des champs
        :raises TypeError: si data n'est pas du bon type
        """
        self.db = db
        if data is None:
            # initialise les champs à None
            for f in self.FIELD_NAMES:
                setattr(self, f, None)
            return

        if isinstance(data, dict):
            for f in self.FIELD_NAMES:
                setattr(self, f, data.get(f))
        elif isinstance(data, (list, tuple)):
            # Accept tuples that may be shorter than FIELD_NAMES (backwards compatibility with older schemas)
            if len(data) != len(self.FIELD_NAMES):
                logging.warning("Data tuple length (%d) doesn't match FIELD_NAMES (%d) for %s; filling missing fields with None",
                                len(data), len(self.FIELD_NAMES), self.__class__.__name__)
            # Assign available values and default missing ones to None
            for f, v in zip(self.FIELD_NAMES, list(data) + [None] * max(0, len(self.FIELD_NAMES) - len(data))):
                setattr(self, f, v)
        else:
            raise TypeError("data must be a dict, tuple/list or None")

        # Après l'initialisation des champs, tenter de mettre l'objet en cache Redis
        # Si la classe implémente _patch(), on évite de cacher prématurément l'objet non patché.
        if not hasattr(self, '_patch'):
            try:
                self._try_cache()
            except Exception:
                # Ne pas lever d'erreur si Redis n'est pas disponible ou si sérialisation échoue
                pass

    @classmethod
    def from_db_row(cls, db: Database, row: Tuple[Any, ...] | Dict[str, Any]):
        """Constructeur de classe alternatif à partir d'une ligne de résultat SQL ou d'un dict.

        :param db: instance de Database
        :param row: tuple contenant les valeurs des champs dans l'ordre FIELD_NAMES
        :return: instance de la classe
        """
        # Cast cls to Any so static analyzers won't complain about varying __init__ signatures
        return cast(Any, cls)(db, row)

    @classmethod
    def from_dict(cls, db: Database, data: Dict[str, Any]):
        """Constructeur de classe alternatif à partir d'un dictionnaire.

        :param db: instance de Database
        :param data: dictionnaire contenant les valeurs des champs
        :return: instance de la classe
        """
        # Cast cls to Any so static analyzers won't complain about varying __init__ signatures
        return cast(Any, cls)(db, data)

    @classmethod
    def get_by_id(cls, db: 'Database', id: int) -> Optional[Any]:
        """Récupère une instance de la classe par son identifiant.

        Essaie d'abord d'utiliser le cache Redis (si présent), sinon effectue une requête SQL
        sur la table déterminée par `DATABASE_NAME` et le champ d'identifiant trouvé dans `FIELD_NAMES`.
        :param db: instance de Database
        :param id: identifiant à rechercher
        :return: instance de la classe ou None si non trouvé
        :raises ValueError: si aucun champ d'identifiant n'est défini pour la classe
        """
        # Tenter le cache Redis si disponible
        cache_prefix = getattr(cls, 'CACHE_PREFIX', None) or cls.__name__.lower()
        try:
            cached = getattr(db, 'redis_client', None)
            if cached is not None:
                payload = db.redis_client.get(redis_key(cache_prefix, id))
                if payload:
                    return cls.from_db_row(db, json.loads(payload))
        except Exception:
            # Ne pas bloquer en cas d'erreur cache
            pass

        # Déterminer le champ d'identifiant (ex: 'user_id', 'client_id', ...)
        id_field = next((f for f in getattr(cls, 'FIELD_NAMES', []) if isinstance(f, str) and f.endswith('_id')), None)
        if id_field is None:
            raise ValueError(f"No ID field defined for class {cls.__name__}")

        # Déterminer le nom de la table
        database_name = getattr(cls, 'DATABASE_NAME', None)
        if database_name is None:
            database_name = cls.__name__ + 's'

        cursor = db.execute(f"SELECT * FROM {database_name} WHERE {id_field} = ?", (id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            return cls.from_db_row(db, row)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise l'objet en dictionnaire en ne conservant que les champs listés dans FIELD_NAMES."""
        return {f: getattr(self, f) for f in self.FIELD_NAMES}

    # Méthodes de cache centralisées
    def _cache_key(self) -> Optional[str]:
        """Construit la clé Redis de l'objet à partir du champ d'identifiant présent dans FIELD_NAMES.

        :return: clé Redis sous la forme '<prefix>:<id>' ou None si non déterminable
        """
        # Détermine la clé Redis en utilisant soit CACHE_PREFIX, soit le nom de la classe en minuscule
        prefix = self.CACHE_PREFIX if self.CACHE_PREFIX is not None else self.__class__.__name__.lower()
        if not self.FIELD_NAMES:
            return None
        # Assurer que le nom de champ est bien une chaîne pour satisfaire les analyseurs statiques
        try:
            id_field = next(f for f in self.FIELD_NAMES if f.endswith('_id'))
            if not isinstance(id_field, str):
                id_field = str(id_field)
        except Exception:
            return None
        id_val = getattr(self, id_field, None)
        if id_val is None:
            return None
        return f"{prefix}:{id_val}"

    def _try_cache(self) -> None:
        """Tente d'écrire l'objet sérialisé dans Redis en respectant le TTL (CACHE_TTL).

        Ne lève pas d'erreur si Redis n'est pas disponible.
        """
        # Tente d'écrire l'objet en cache Redis si possible
        if not hasattr(self, 'db') or self.db is None:
            return
        redis_client = getattr(self.db, 'redis_client', None)
        if redis_client is None:
            return
        key = self._cache_key()
        if key is None:
            return
        payload = json.dumps(self.to_dict(), default=str)
        redis_client.setex(key, self.CACHE_TTL, payload)

    # Méthodes pour gérer les index secondaires Redis (recherches exactes)
    def _set_secondary_indexes(self) -> None:
        """
        Pour chaque champ dans SECONDARY_INDEX_FIELDS, ajoute l'id courant dans le set Redis
        correspondant à la valeur normalisée du champ.
        Clef: redis_key(f"index:{DATABASE_NAME}", suffix=f"{field}:{normalized_value}")
        Valeurs: ensemble d'ids (SADD)
        """
        if not self.SECONDARY_INDEX_FIELDS:
            return
        try:
            id_field = next((f for f in self.FIELD_NAMES if f.endswith('_id')), None)
            if id_field is None:
                return
            id_val = getattr(self, id_field, None)
            if id_val is None:
                return
            for field in self.SECONDARY_INDEX_FIELDS:
                if not hasattr(self, field):
                    continue
                raw_value = getattr(self, field)
                if raw_value is None:
                    continue
                normalized = normalize_text(str(raw_value))
                key = redis_key(f"index:{getattr(self, 'DATABASE_NAME')}", suffix=f"{field}:{normalized}")
                try:
                    # Utiliser SADD pour garder la liste des ids correspondant à cette valeur exacte
                    self.db.redis_client.sadd(key, str(id_val))
                    # Appliquer TTL en utilisant expire
                    self.db.redis_client.expire(key, self.CACHE_TTL)
                except Exception:
                    # Ne pas lever d'erreur si Redis n'est pas disponible
                    continue
        except Exception:
            pass

    def _delete_secondary_indexes(self) -> None:
        """
        Supprime l'id courant des sets d'index secondaires.
        """
        if not self.SECONDARY_INDEX_FIELDS:
            return
        try:
            id_field = next((f for f in self.FIELD_NAMES if f.endswith('_id')), None)
            if id_field is None:
                return
            id_val = getattr(self, id_field, None)
            if id_val is None:
                return
            for field in self.SECONDARY_INDEX_FIELDS:
                if not hasattr(self, field):
                    continue
                raw_value = getattr(self, field)
                if raw_value is None:
                    continue
                normalized = normalize_text(str(raw_value))
                key = redis_key(f"index:{getattr(self, 'DATABASE_NAME')}", suffix=f"{field}:{normalized}")
                try:
                    self.db.redis_client.srem(key, str(id_val))
                    # Optionnel: supprimer la clé si le set est maintenant vide
                    try:
                        members = self.db.redis_client.smembers(key)
                        if not members:
                            self.db.redis_client.delete(key)
                    except Exception:
                        pass
                except Exception:
                    continue
        except Exception:
            pass

    def save(self):
        """Sauvegarde (INSERT OR REPLACE) de l'objet dans la base SQLite et mise à jour des caches.

        Met à jour les index secondaires Redis, le cache de la liste "all" et l'entrée individuelle.
        """
        # Standardiser le nom de la table/cache utilisé
        database_name = getattr(self, 'DATABASE_NAME', None)
        if database_name is None:
            database_name = self.__class__.__name__ + "s"  # Pluriel simple par défaut
            logging.warning("Using default DATABASE_NAME '%s' for class %s. It's recommended to explicitly set DATABASE_NAME.", database_name, self.__class__.__name__)
        # Préparer les champs et valeurs
        fields = ', '.join(self.FIELD_NAMES)
        placeholders = ', '.join(['?'] * len(self.FIELD_NAMES))
        values = tuple(getattr(self, f) for f in self.FIELD_NAMES)

        # Exécuter l'insertion et récupérer le curseur si possible
        cursor = None
        try:
            cursor = self.db.execute(
                f"INSERT OR REPLACE INTO {database_name} ({fields}) VALUES ({placeholders})",
                values
            )
            # Commit après exécution
            self.db.commit()
        except Exception as e:
            # Propager l'exception pour que l'appelant puisse traiter l'erreur
            raise

        # Si l'objet n'avait pas d'ID et que SQLite a généré un lastrowid, l'affecter
        try:
            id_field = next((f for f in self.FIELD_NAMES if f.endswith('_id')), None)
            if id_field:
                current_id = getattr(self, id_field, None)
                if (current_id is None or current_id == '') and cursor is not None:
                    try:
                        new_id = getattr(cursor, 'lastrowid', None)
                        if new_id is not None and new_id != 0:
                            setattr(self, id_field, int(new_id))
                    except Exception:
                        pass
        except Exception:
            pass

        # Mettre à jour les index secondaires Redis
        try:
            self._set_secondary_indexes()
        except Exception:
            pass

        # Mettre à jour (ou invalider) le cache 'all' pour la ressource
        try:
            all_key = redis_key(database_name.lower(), None, "all")
            try:
                redis_client = getattr(self.db, 'redis_client', None)
            except Exception:
                redis_client = None

            # If redis available, prefer to invalidate caches completely to avoid stale search/index results
            if redis_client is not None:
                try:
                    # Supprimer la clé 'all' afin de forcer une reconstruction propre au prochain accès
                    try:
                        redis_client.delete(all_key)
                    except Exception:
                        pass

                    # Invalider les index secondaires pour cette table (pattern: index:<database_name>:*)
                    index_pattern = f"index:{database_name.lower()}:*"
                    try:
                        # Utiliser scan_iter si disponible (plus sûr en production)
                        if hasattr(redis_client, 'scan_iter'):
                            keys_iter = redis_client.scan_iter(match=index_pattern)
                            keys = list(keys_iter)
                        elif hasattr(redis_client, 'keys'):
                            keys = redis_client.keys(index_pattern)
                        else:
                            keys = []
                        if keys:
                            try:
                                # delete accepts multiple args in redis-py
                                redis_client.delete(*keys)
                            except Exception:
                                # fallback: delete one by one
                                for k in keys:
                                    try:
                                        redis_client.delete(k)
                                    except Exception:
                                        pass
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

        # Enfin, mettre en cache l'entrée individuelle
        try:
            self._try_cache()
        except Exception:
            pass

    def delete(self):
        """Supprime l'objet de la base de données et nettoie les index/caches Redis associés.

        :raises ValueError: si aucun champ d'identifiant n'est défini ou si la valeur d'identifiant est None
        """
        # Supprime l'objet de la base de données
        id_field = next((f for f in self.FIELD_NAMES if f.endswith('_id')), None)
        if id_field is None:
            raise ValueError("No ID field found for deletion")
        id_val = getattr(self, id_field, None)
        if id_val is None:
            raise ValueError("ID value is None, cannot delete")

        database_name = getattr(self, 'DATABASE_NAME', None)
        if database_name is None:
            database_name = self.__class__.__name__ + "s"
        else:
            database_name = str(database_name)

        self.db.execute(
            f"DELETE FROM {database_name} WHERE {id_field} = ?",
            (id_val,)
        )
        self.db.commit()

        # Supprimer des index secondaires Redis
        try:
            self._delete_secondary_indexes()
        except Exception:
            pass

        # Supprimer du cache Redis
        try:
            key = self._cache_key()
            if key:
                self.db.redis_client.delete(key)
            # Mettre à jour le cache de tous les objets
            try:
                cached_ids = self.db.redis_client.get(redis_key(database_name.lower(), None, "all"))
            except Exception:
                cached_ids = None
            if cached_ids:
                try:
                    ids_list = json.loads(cached_ids)
                except Exception:
                    ids_list = []
                if id_val in ids_list:
                    ids_list.remove(id_val)
                    try:
                        self.db.redis_client.setex(redis_key(database_name.lower(), None, "all"), self.CACHE_TTL, json.dumps(ids_list))
                    except Exception:
                        pass
        except Exception:
            pass


class Role(DBObject, _RowInitMixin):
    """
    Représente un rôle utilisateur avec ses permissions.

    role_id: identifiant unique du rôle

    nom: nom du rôle

    hierarchie: niveau hiérarchique du rôle, plus le nombre est bas, plus le rôle est élevé

    Permissions (booléens) indiquant les actions autorisées pour ce rôle.
    """
    FIELD_NAMES = [
        'role_id', 'nom', 'hierarchie', 'administrateur',
        'peut_gerer_utilisateurs', 'peut_gerer_roles',
        'peut_lire_clients', 'peut_gerer_clients', 'peut_creer_interactions', 'peut_gerer_interactions',
        'peut_lire_projets', 'peut_gerer_projets', 'peut_gerer_jalons', 'peut_assigner_intervenants',
        'peut_lire_utilisateurs', 'peut_acceder_documents', 'peut_gerer_competences',
        'peut_lancer_matching', 'peut_exporter_csv'
    ]

    DATABASE_NAME = "Roles"

    role_id: int
    nom: str
    hierarchie: int

    administrateur: bool # Possède toutes les permissions
    peut_gerer_utilisateurs: bool # Peut créer, modifier et supprimer des utilisateurs
    peut_gerer_roles: bool # Peut créer, modifier, supprimer et ajouter aux utilisateurs des rôles
    peut_lire_clients: bool # Peut voir la liste des clients et leurs détails
    peut_gerer_clients: bool # Peut créer, modifier et supprimer des clients

    peut_creer_interactions: bool # Peut créer des interactions liées aux projets
    peut_gerer_interactions: bool # Peut modifier et supprimer des interactions

    peut_lire_projets: bool # Peut voir la liste des projets et leurs détails
    peut_gerer_projets: bool # Peut créer, modifier et supprimer des projets
    peut_gerer_jalons: bool # Peut créer, modifier et supprimer des jalons de projets
    peut_assigner_intervenants: bool # Peut assigner des intervenants aux projets
    peut_lire_utilisateurs: bool # Peut voir la liste des utilisateurs et leurs détails
    peut_acceder_documents: bool # Peut accéder aux documents liés aux intervenants et projets
    peut_gerer_competences: bool # Peut créer, modifier et supprimer des compétences des intervenants
    peut_lancer_matching: bool # Peut lancer le processus de matching entre projets et intervenants
    peut_exporter_csv: bool # Peut exporter des données au format CSV

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._init_from(db, data)

    @classmethod
    def get_by_id(cls, db: Database, id: int) -> Optional['Role']:
        """Récupère un rôle par son identifiant (cache Redis puis SQL)."""
        try:
            cached = db.redis_client.get(redis_key(getattr(cls, 'CACHE_PREFIX', None) or cls.__name__.lower(), id))
            if cached:
                return cls.from_db_row(db, json.loads(cached))
        except Exception:
            pass
        id_field = next((f for f in getattr(cls, 'FIELD_NAMES', []) if isinstance(f, str) and f.endswith('_id')), None)
        if id_field is None:
            raise ValueError(f"No ID field defined for class {cls.__name__}")
        database_name = getattr(cls, 'DATABASE_NAME', None) or cls.__name__ + 's'
        cursor = db.execute(f"SELECT * FROM {database_name} WHERE {id_field} = ?", (id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            return cls.from_db_row(db, row)
        return None

    @property
    def users(self):
        """Retourne la liste des utilisateurs associés à ce rôle.

        Utilise le cache Redis si disponible, sinon interroge la table Utilisateurs.
        :return: liste d'instances Utilisateur
        """
        cached_users = self.db.redis_client.get(
            redis_key(getattr(Role, 'CACHE_PREFIX', None) or Role.__name__.lower(), self.role_id, "users"))
        if cached_users:
            users_ids = json.loads(cached_users)
            users = [self.db.get_user_by_id(uid) for uid in users_ids]
            return [user for user in users if user is not None]
        cursor = self.db.execute(f"SELECT * FROM {Utilisateur.DATABASE_NAME} WHERE role_id = ?", (self.role_id,))
        rows = cursor.fetchall()
        cursor.close()
        users = [Utilisateur.from_db_row(self.db, row) for row in rows]
        # Mettre en cache les IDs des utilisateurs
        users_ids = [user.utilisateur_id for user in users]
        self.db.redis_client.setex(
            redis_key(getattr(Role, 'CACHE_PREFIX', None) or Role.__name__.lower(), self.role_id, "users"), 1_800, json.dumps(users_ids))
        return users


class Utilisateur(UserMixin, DBObject, _RowInitMixin):
    """
    Représente un utilisateur du site. Il peut être intervenant ou membre de TNS.

    utilisateur_id: identifiant unique de l'utilisateur

    email: adresse email de l'utilisateur

    mot_de_passe_hashed: mot de passe hashé de l'utilisateur

    mot_de_passe_expire: date où le mot de passe est expiré (format 'YYYY-MM-DD')

    nom: nom de l'utilisateur

    prenom: prénom de l'utilisateur

    role_id:  identifiant du rôle de l'utilisateur (clé étrangère vers Role)

    role: propriété pour accéder à l'objet Role associé

    est_intervenant: indique si l'utilisateur est un intervenant

    heures_dispo_semaine: nombre d'heures disponibles par semaine (si intervenant)

    doc_carte_vitale: chemin vers le document de la carte vitale (si intervenant)

    doc_cni: chemin vers le document de la carte nationale d'identité (si intervenant)

    doc_adhesion: chemin vers le document d'adhésion (si intervenant)

    doc_rib: chemin vers le document du RIB (si intervenant)
    """
    FIELD_NAMES = [
        'utilisateur_id', 'email', 'mot_de_passe_hashed', 'mot_de_passe_expire',
        'nom', 'prenom', 'avatar', 'role_id',
        'est_intervenant', 'heures_dispo_semaine',
        'doc_carte_vitale', 'doc_cni', 'doc_adhesion', 'doc_rib'
    ]

    DATABASE_NAME = "Utilisateurs"

    utilisateur_id: int
    email: str
    mot_de_passe_hashed: str
    mot_de_passe_expire: Optional[datetime.date]
    nom: str
    prenom: str
    avatar: Optional[str]
    role_id: int
    est_intervenant: bool
    heures_dispo_semaine: Optional[int]
    doc_carte_vitale: Optional[str]
    doc_cni: Optional[str]
    doc_adhesion: Optional[str]
    doc_rib: Optional[str]

    CACHE_PREFIX = 'user'
    SECONDARY_INDEX_FIELDS = ['email', 'nom', 'prenom']

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        """Initialise un objet Utilisateur à partir d'une ligne DB ou d'un dict.

        Effectue un patch post-initialisation (_patch) pour normaliser les types.
        """
        super().__init__(db)
        self._init_from(db, data)
        self._patch()
        # Après patch, mettre en cache l'objet si possible
        try:
            self._try_cache()
        except Exception:
            pass

    # Méthodes attendues par Flask-Login
    def get_id(self) -> str:
        """Retourne l'identifiant utilisateur sous forme de chaîne pour Flask-Login."""
        return str(getattr(self, 'utilisateur_id', ''))

    @property
    def is_active(self) -> bool:
        """Compte actif (toujours True ici, ajuster si vous avez un champ de désactivation)."""
        return True

    @property
    def is_authenticated(self) -> bool:
        """Indique si l'utilisateur est authentifié (True pour instances chargées)."""
        return True

    @property
    def is_anonymous(self) -> bool:
        """Indique si c'est un utilisateur anonyme (toujours False pour nos objets)."""
        return False

    @classmethod
    def get_by_id(cls, db: Database, id: int) -> Optional['Utilisateur']:
        """Récupère un utilisateur par id (cache Redis puis SQL)."""
        return db.get_user_by_id(id)

    def _patch(self):
        """Normalise et convertit certains champs (dates, entiers, booléens, chemins) après lecture de la BDD.

        Assure que les attributs ont les types attendus par le reste du code.
        """
        if not isinstance(self.mot_de_passe_expire, datetime.date):
            if isinstance(self.mot_de_passe_expire, str):
                self.mot_de_passe_expire = datetime.datetime.strptime(self.mot_de_passe_expire, '%Y-%m-%d').date()
            else:
                logging.warning(f"Invalid mot_de_passe_expire for user {self.utilisateur_id} (v={self.mot_de_passe_expire}), setting to None")
                self.mot_de_passe_expire = None
        if not isinstance(self.role_id, int):
            self.role_id = int(self.role_id)
        if not isinstance(self.est_intervenant, bool):
            self.est_intervenant = bool(self.est_intervenant)
        if self.heures_dispo_semaine is not None and not isinstance(self.heures_dispo_semaine, int):
            self.heures_dispo_semaine = int(self.heures_dispo_semaine)
        if self.doc_carte_vitale is not None and not isinstance(self.doc_carte_vitale, str):
            self.doc_carte_vitale = str(self.doc_carte_vitale)
        if self.doc_cni is not None and not isinstance(self.doc_cni, str):
            self.doc_cni = str(self.doc_cni)
        if self.doc_adhesion is not None and not isinstance(self.doc_adhesion, str):
            self.doc_adhesion = str(self.doc_adhesion)
        if self.doc_rib is not None and not isinstance(self.doc_rib, str):
            self.doc_rib = str(self.doc_rib)

    @property
    def role(self) -> Role:
        """Retourne l'objet Role associé à cet utilisateur.

        Interroge la méthode get_role_by_id de la base et lève ValueError si non trouvé.
        :return: instance Role
        """
        cached_role = self.db.get_role_by_id(self.role_id)
        if cached_role:
            return cached_role
        raise ValueError(f"Role with id {self.role_id} not found")

    @property
    def competences(self) -> list['Competence'] | None:
        """
        Récupère les compétences associées à l'utilisateur.
        :return: Liste des objets Compétence ou None si aucune compétence
        """
        cached_competences_ids = self.db.redis_client.get(
            redis_key(getattr(Utilisateur, 'CACHE_PREFIX', None) or Utilisateur.__name__.lower(), self.utilisateur_id,
                      "competences"))
        not_cached_competences = False
        if cached_competences_ids:
            competences_ids = json.loads(cached_competences_ids)
            competences = []
            for cid in competences_ids:
                cached_competence = self.db.redis_client.get(f"competence:{cid}")
                if cached_competence:
                    competences.append(Competence.from_db_row(self.db, json.loads(cached_competence)))
                else:
                    not_cached_competences = True
                    break
            if len(competences) == len(competences_ids):
                return competences  # Toutes les compétences étaient en cache
        if not_cached_competences or not cached_competences_ids:
            cursor = self.db.execute(
                "SELECT c.* FROM competences c "
                "JOIN Intervenant_competences uc ON c.competence_id = uc.competence_id "
                "WHERE uc.intervenant_id = ?", (self.utilisateur_id,))
            rows = cursor.fetchall()
            competences = [Competence.from_db_row(self.db, row) for row in rows]
            cursor.close()
            # Mettre en cache les IDs des compétences
            competences_ids = [competence.competence_id for competence in competences]
            self.db.redis_client.setex(
                redis_key(getattr(Utilisateur, 'CACHE_PREFIX', None) or Utilisateur.__name__.lower(),
                          self.utilisateur_id, "competences"), 1_800, json.dumps(competences_ids))
            return competences
        return None


class Intervenant(Utilisateur):
    """
    Représente un intervenant, qui est un type spécial d'utilisateur.

    Hérite de la classe Utilisateur.

    Il va représenter un utilisateur avec son poste sur un projet

    poste: poste de l'intervenant sur le projet (ex: 'Chef de projet', 'Développeur', etc.)

    projet_id: identifiant du projet sur lequel l'intervenant travaille (clé étrangère vers Projet)
    """
    poste: str
    projet_id: int
    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db, data)

    def save(self):
        """Sauvegarde spécifique pour un Intervenant : stocke la ligne dans Travaille_sur puis délègue au save parent.

        Permet de conserver le poste et l'association projet/utilisateur.
        """
        # Vérifier si la propriété 'poste' a été changée et la sauvegarder dans la table appropriée
        if hasattr(self, 'poste'):
            self.db.execute(
                "INSERT OR REPLACE INTO Travaille_sur (utilisateur_id, poste, projet_id) VALUES (?, ?, ?)",
                (self.utilisateur_id, self.poste, self.projet_id)
            )
            self.db.commit()
        super().save()


class Client(DBObject, _RowInitMixin):
    """
    Représente un client de TNS.

    client_id: identifiant unique du client

    nom_entreprise: nom de l'entreprise cliente

    contact_nom: nom du contact principal chez le client

    contact_email: email du contact principal chez le client

    contact_telephone: téléphone du contact principal chez le client

    type_client: 'prospect', 'actif', 'ancien' : Pour différencier les prospects des clients.

    interlocuteur_principal_id: identifiant de l'utilisateur qui est l'interlocuteur principal pour ce client (clé étrangère vers Utilisateur)

    interlocuteur_principal: propriété pour accéder à l'objet Utilisateur associé
    """
    FIELD_NAMES = [
        'client_id', 'nom_entreprise', 'contact_nom', 'contact_email', 'contact_telephone', 'type_client',
        'interlocuteur_principal_id', 'localisation_lat', 'localisation_lng', 'address'
    ]
    DATABASE_NAME = "Clients"
    SECONDARY_INDEX_FIELDS = ['contact_email', 'nom_entreprise']
    client_id: int
    nom_entreprise: str
    contact_nom: str
    contact_email: str
    contact_telephone: str
    type_client: str
    interlocuteur_principal_id: int
    localisation_lat: Optional[float]
    localisation_lng: Optional[float]
    address: Optional[str]

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        """Initialise un objet Client depuis une ligne DB ou un dict."""
        super().__init__(db)
        self._init_from(db, data)

    @property
    def interlocuteur_principal(self) -> Utilisateur:
        """Retourne l'utilisateur référencé comme interlocuteur principal pour ce client.

        Utilise le cache Redis si disponible, sinon interroge la table Utilisateurs.
        :return: instance Utilisateur
        :raises ValueError: si l'utilisateur associé n'existe pas
        """
        cached_user = self.db.redis_client.get(
            redis_key(getattr(Utilisateur, 'CACHE_PREFIX', None) or Utilisateur.__name__.lower(),
                      self.interlocuteur_principal_id))
        if cached_user:
            return Utilisateur.from_db_row(self.db, json.loads(cached_user))
        cursor = self.db.execute(f"SELECT * FROM {Utilisateur.DATABASE_NAME} WHERE utilisateur_id = ?", (self.interlocuteur_principal_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            user = Utilisateur.from_db_row(self.db, row)
            return user
        raise ValueError(f"User with id {self.interlocuteur_principal_id} not found")

    @property
    def conventions(self) -> list['Convention'] | None:
        cached_conventions_ids = self.db.redis_client.get(
            redis_key(Client.DATABASE_NAME.lower(), self.client_id, "conventions"))
        not_cached_conventions = False
        if cached_conventions_ids:
            conventions_ids = json.loads(cached_conventions_ids)
            conventions = []
            for cid in conventions_ids:
                cached_convention = self.db.redis_client.get(f"convention:{cid}")
                if cached_convention:
                    conventions.append(Convention.from_db_row(self.db, json.loads(cached_convention)))
                else:
                    not_cached_conventions = True
                    break
            if len(conventions) == len(conventions_ids):
                return conventions  # Toutes les conventions étaient en cache
        if not_cached_conventions or not cached_conventions_ids:
            cursor = self.db.execute(f"SELECT * FROM {Convention.DATABASE_NAME} WHERE client_id = ?", (self.client_id,))
            rows = cursor.fetchall()
            conventions = [Convention.from_db_row(self.db, row) for row in rows]
            cursor.close()
            # Mettre en cache les IDs des conventions
            conventions_ids = [convention.convention_id for convention in conventions]
            self.db.redis_client.setex(redis_key(Client.DATABASE_NAME.lower(), self.client_id, "conventions"), 1_800, json.dumps(conventions_ids))
            return conventions
        return None

    @property
    def interactions(self) -> list['Interaction'] | None:
        cached_interactions_ids = self.db.redis_client.get(
            redis_key(Client.DATABASE_NAME.lower(), self.client_id, "interactions"))
        not_cached_interactions = False
        if cached_interactions_ids:
            interactions_ids = json.loads(cached_interactions_ids)
            interactions = []
            for iid in interactions_ids:
                cached_interaction = self.db.redis_client.get(f"interaction:{iid}")
                if cached_interaction:
                    interactions.append(Interaction.from_db_row(self.db, json.loads(cached_interaction)))
                else:
                    not_cached_interactions = True
                    break
            if len(interactions) == len(interactions_ids):
                return interactions  # Toutes les interactions étaient en cache
        if not_cached_interactions or not cached_interactions_ids:
            cursor = self.db.execute(f"SELECT * FROM {Interaction.DATABASE_NAME} WHERE client_id = ?", (self.client_id,))
            rows = cursor.fetchall()
            interactions = [Interaction.from_db_row(self.db, row) for row in rows]
            cursor.close()
            # Mettre en cache les IDs des interactions
            interactions_ids = [interaction.interaction_id for interaction in interactions]
            self.db.redis_client.setex(redis_key(Client.DATABASE_NAME.lower(), self.client_id, "interactions"), 1_800, json.dumps(interactions_ids))
            return interactions
        return None


class Convention(DBObject, _RowInitMixin):
    """
    Représente une convention entre TNS et un client.

    convention_id: identifiant unique de la convention

    nom_convention: nom de la convention

    description: description de la convention

    date_debut: date de début de la convention (format 'YYYY-MM-DD')

    date_fin: date de fin de la convention (format 'YYYY-MM-DD')

    doc_contrat: chemin vers le document du contrat de la convention

    client_id: identifiant du client associé à la convention (clé étrangère vers Client)

    client: propriété pour accéder à l'objet Client associé
    """

    FIELD_NAMES = [
        'convention_id', 'nom_convention', 'description', 'date_debut', 'date_fin', 'doc_contrat', 'client_id'
    ]
    DATABASE_NAME = "Conventions"
    convention_id: int
    nom_convention: str
    description: str
    date_debut: str
    date_fin: str
    doc_contrat: Optional[str]
    client_id: int

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._init_from(db, data)

    @property
    def client(self) -> Client:
        """Retourne l'objet Client associé à cette convention.

        Utilise le cache Redis si disponible, sinon interroge la table Clients.
        :return: instance Client
        :raises ValueError: si le client n'existe pas
        """
        cached_client = self.db.redis_client.get(
            redis_key(getattr(Client, 'CACHE_PREFIX', None) or Client.__name__.lower(), self.client_id))
        if cached_client:
            return Client.from_db_row(self.db, json.loads(cached_client))
        cursor = self.db.execute(f"SELECT * FROM {Client.DATABASE_NAME} WHERE client_id = ?", (self.client_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            client = Client.from_db_row(self.db, row)
            return client
        raise ValueError(f"Client with id {self.client_id} not found")

    @property
    def projets(self) -> list['Projet'] | None:
        """Liste des projets associés à cette convention (utilise cache si possible)."""
        cached_projets_ids = self.db.redis_client.get(
            redis_key(Convention.DATABASE_NAME.lower(), self.convention_id, "projets"))
        not_cached_projets = False
        if cached_projets_ids:
            projets_ids = json.loads(cached_projets_ids)
            projets = []
            for pid in projets_ids:
                cached_projet = self.db.redis_client.get(f"projet:{pid}")
                if cached_projet:
                    projets.append(Projet.from_db_row(self.db, json.loads(cached_projet)))
                else:
                    not_cached_projets = True
                    break
            if len(projets) == len(projets_ids):
                return projets  # Tous les projets étaient en cache
        if not_cached_projets or not cached_projets_ids:
            cursor = self.db.execute(f"SELECT * FROM {Projet.DATABASE_NAME} WHERE convention_id = ?", (self.convention_id,))
            rows = cursor.fetchall()
            projets = [Projet.from_db_row(self.db, row) for row in rows]
            cursor.close()
            # Mettre en cache les IDs des projets
            projets_ids = [projet.projet_id for projet in projets]
            self.db.redis_client.setex(redis_key(Convention.DATABASE_NAME.lower(), self.convention_id, "projets"), 1_800, json.dumps(projets_ids))
            return projets
        return None


class Projet(DBObject, _RowInitMixin):
    """
    Représente un projet géré par TNS pour un client.

    projet_id: identifiant unique du projet

    convention_id: identifiant de la convention associée au projet (clé étrangère vers Convention)

    nom_projet: nom du projet

    description: description du projet

    budget: budget alloué au projet

    date_debut: date de début du projet (format 'YYYY-MM-DD')

    date_fin: date de fin du projet (format 'YYYY-MM-DD')

    statut: statut actuel du projet ('en_cours', 'termine', 'annule', etc.)

    doc_dossier: chemin vers du dossier Google Drive des documents du projet (Contrat, missions, jalons, etc)
    """
    FIELD_NAMES = [
        'projet_id', 'convention_id', 'nom_projet', 'description', 'budget', 'charge_travail', 'date_debut', 'date_fin', 'statut',
        'doc_dossier'
    ]
    DATABASE_NAME = "Projets"
    projet_id: int
    convention_id: int
    nom_projet: str
    description: str
    budget: float
    charge_travail : int
    date_debut: str
    date_fin: str
    statut: str
    doc_dossier: Optional[str]

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._init_from(db, data)

    @property
    def convention(self) -> Convention:
        """Retourne l'objet Convention associé à ce projet.

        :return: instance Convention
        :raises ValueError: si la convention n'existe pas
        """
        cached_convention = self.db.redis_client.get(
            redis_key(getattr(Convention, 'CACHE_PREFIX', None) or Convention.__name__.lower(), self.convention_id))
        if cached_convention:
            return Convention.from_db_row(self.db, json.loads(cached_convention))
        cursor = self.db.execute(f"SELECT * FROM {Convention.DATABASE_NAME} WHERE convention_id = ?", (self.convention_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            convention = Convention.from_db_row(self.db, row)
            return convention
        raise ValueError(f"Convention with id {self.convention_id} not found")

    def save(self):
        """Sauvegarde le projet puis invalide la clé de cache de la liste de projets de la convention associée.

        On délègue d'abord au comportement générique `save()` pour l'INSERT/REPLACE,
        la mise à jour des index secondaires et la mise en cache individuelle.
        Ensuite, on supprime explicitement la clé `conventions:<convention_id>:projets`
        pour forcer la reconstruction de la liste à la prochaine lecture.
        """
        # Appeler la logique de sauvegarde générique (INSERT/REPLACE + commit + cache individuel)
        super().save()
        # Invalider la liste des projets de la convention associée
        try:
            key = redis_key(Convention.DATABASE_NAME.lower(), self.convention_id, "projets")
            if getattr(self.db, 'redis_client', None) is not None:
                try:
                    self.db.redis_client.delete(key)
                except Exception:
                    # Ne pas propager une erreur de cache
                    pass
        except Exception:
            pass

    @property
    def jalons(self) -> list['Jalon'] | None:
        """Liste des jalons du projet par ordre de date de fin descendante (montre les jalons en cours d'abord) (utilise cache si possible)."""
        cached_jalons_ids = self.db.redis_client.get(redis_key(Projet.DATABASE_NAME.lower(), self.projet_id, "jalons"))
        not_cached_jalons = False
        if cached_jalons_ids:
            jalons_ids = json.loads(cached_jalons_ids)
            jalons = []
            for jid in jalons_ids:
                cached_jalon = self.db.redis_client.get(f"jalon:{jid}")
                if cached_jalon:
                    jalons.append(Jalon.from_db_row(self.db, json.loads(cached_jalon)))
                else:
                    not_cached_jalons = True
                    break
            if len(jalons) == len(jalons_ids):
                return jalons  # Tous les jalons étaient en cache
        if not_cached_jalons or not cached_jalons_ids:
            cursor = self.db.execute(f"SELECT * FROM {Jalon.DATABASE_NAME} WHERE projet_id = ? ORDER BY date(date_fin) DESC NULLS FIRST", (self.projet_id,))
            rows = cursor.fetchall()
            jalons = [Jalon.from_db_row(self.db, row) for row in rows]
            cursor.close()
            # Mettre en cache les IDs des jalons
            jalons_ids = [jalon.jalon_id for jalon in jalons]
            self.db.redis_client.setex(redis_key(Projet.DATABASE_NAME.lower(), self.projet_id, "jalons"), 1_800, json.dumps(jalons_ids))
            return jalons
        return None

    @property
    def competences(self) -> list[Any] | None:
        """
        Récupère les compétences associées au projet.
        :return: Liste des objets Compétence ou None si aucune compétence
        """
        cached_competences_ids = self.db.redis_client.get(
            redis_key(Projet.DATABASE_NAME.lower(), self.projet_id, "competences"))
        not_cached_competences = False
        if cached_competences_ids:
            competences_ids = json.loads(cached_competences_ids)
            competences = []
            for cid in competences_ids:
                cached_competence = self.db.redis_client.get(f"competence:{cid}")
                if cached_competence:
                    competences.append(Competence.from_db_row(self.db, json.loads(cached_competence)))
                else:
                    not_cached_competences = True
                    break
            if len(competences) == len(competences_ids):
                return competences  # Toutes les compétences étaient en cache
        if not_cached_competences or not cached_competences_ids:
            cursor = self.db.execute(
                "SELECT c.* FROM competences c "
                "JOIN projet_competences pc ON c.competence_id = pc.competence_id "
                "WHERE pc.projet_id = ?", (self.projet_id,))
            rows = cursor.fetchall()
            competences = [Competence.from_db_row(self.db, row) for row in rows]
            cursor.close()
            # Mettre en cache les IDs des compétences
            competences_ids = [competence.competence_id for competence in competences]
            self.db.redis_client.setex(redis_key(Projet.DATABASE_NAME.lower(), self.projet_id, "competences"), 1_800, json.dumps(competences_ids))
            return competences
        return None

    @property
    def intervenants(self) -> list[Any] | None:
        """
        Renvoie toutes les personnes et leur poste qui interviennent sur ce projet. (Chef(s) de projet et intervenant(s))
        :return: Liste des objets Utilisateur ou None si aucun intervenant
        """
        # Tentative d'utilisation du cache Redis. Le cache stocke une liste d'objets simples
        # contenant {"utilisateur_id": ..., "poste": ...} afin de pouvoir reconstituer
        # des objets Intervenant avec leur poste/projet sans dupliquer la totalité des données utilisateur.
        cached = None
        try:
            cached = self.db.redis_client.get(redis_key(Projet.DATABASE_NAME.lower(), self.projet_id, "intervenants"))
        except Exception:
            cached = None

        if cached:
            try:
                entries = json.loads(cached)
                intervenants: list[Intervenant] = []
                incomplete_cache = False
                for entry in entries:
                    uid = entry.get("utilisateur_id")
                    poste = entry.get("poste")
                    user = self.db.get_user_by_id(uid)
                    if user is None:
                        incomplete_cache = True
                        break
                    # Construire un Intervenant à partir de l'utilisateur et attacher le poste/projet
                    interv = Intervenant(self.db, user.to_dict())
                    if poste is not None:
                        interv.poste = poste
                    interv.projet_id = self.projet_id
                    intervenants.append(interv)
                if not incomplete_cache:
                    return intervenants if intervenants else None
            except Exception:
                # Si le cache est corrompu ou invalide, on ignore et on interroge la BDD
                pass

        # Interroger la table Travaille_sur. On tente d'abord de lire la colonne `poste`.
        rows: list[tuple] = []
        try:
            cursor = self.db.execute(
                "SELECT utilisateur_id, poste FROM Travaille_sur WHERE projet_id = ?",
                (self.projet_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
        except Exception:
            # Si la colonne `poste` n'existe pas (schéma plus ancien), on récupère au moins
            # les utilisateur_id et on posera `poste = None`.
            try:
                cursor = self.db.execute(
                    "SELECT utilisateur_id FROM Travaille_sur WHERE projet_id = ?",
                    (self.projet_id,)
                )
                rows = [(r[0], None) for r in cursor.fetchall()]
                cursor.close()
            except Exception:
                # En cas d'erreur, retourner None
                return None

        result: list[Intervenant] = []
        cache_entries: list[dict] = []
        for row in rows:
            if not row:
                continue
            uid = row[0]
            poste = row[1] if len(row) > 1 else None
            # Normaliser certains types (ex: 0/1) en None si ce n'est pas une chaîne
            if poste is not None and not isinstance(poste, str):
                poste = None

            user = self.db.get_user_by_id(uid)
            if user is None:
                # Utilisateur inexistant -> ignorer
                continue
            interv = Intervenant(self.db, user.to_dict())
            if poste is not None:
                interv.poste = poste
            interv.projet_id = self.projet_id
            result.append(interv)
            cache_entries.append({"utilisateur_id": uid, "poste": poste})

        # Mettre en cache la liste des intervenants (utilisateur_id + poste)
        if cache_entries:
            try:
                self.db.redis_client.setex(redis_key(Projet.DATABASE_NAME.lower(), self.projet_id, "intervenants"), 1_800, json.dumps(cache_entries))
            except Exception:
                pass

        return result if result else None


class Competence(DBObject, _RowInitMixin):
    """
    Représente une compétence pouvant être associée à un intervenant ou un projet.

    competence_id: identifiant unique de la compétence

    nom: nom de la compétence

    competence_parent: identifiant de la compétence parente (clé étrangère vers Competence), ou None si pas de parent
    """
    FIELD_NAMES = ['competence_id', 'nom', 'competence_parent']
    DATABASE_NAME = "Competences"

    competence_id: int
    nom: str
    competence_parent: Optional[int]

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._init_from(db, data)

    @property
    def parent(self) -> Optional['Competence']:
        """Retourne la compétence parente si elle existe, sinon None.

        Interroge le cache Redis puis la table Competences.
        :return: instance Competence ou None
        :raises ValueError: si l'id parent est défini mais que l'enregistrement est introuvable
        """
        if self.competence_parent is None:
            return None
        cached_competence = self.db.redis_client.get(
            redis_key(getattr(Competence, 'CACHE_PREFIX', None) or Competence.__name__.lower(), self.competence_parent))
        if cached_competence:
            return Competence.from_db_row(self.db, json.loads(cached_competence))
        cursor = self.db.execute(f"SELECT * FROM {Competence.DATABASE_NAME} WHERE competence_id = ?", (self.competence_parent,))
        row = cursor.fetchone()
        if row:
            competence = Competence.from_db_row(self.db, row)
            return competence
        raise ValueError(f"Competence with id {self.competence_parent} not found")


class Jalon(DBObject, _RowInitMixin):
    """
    Représente un jalon dans un projet.

    jalon_id: identifiant unique du jalon

    description: description du jalon

    date_fin: date de fin prévue du jalon (format 'YYYY-MM-DD')

    est_complete: indique si le jalon est complété

    projet_id: identifiant du projet associé au jalon (clé étrangère vers Projet)
    """
    FIELD_NAMES = ['jalon_id', 'description', 'date_fin', 'est_complete', 'projet_id']
    DATABASE_NAME = "Jalons"

    jalon_id: int
    description: str
    date_fin: str
    est_complete: bool
    projet_id: int

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._init_from(db, data)

    @property
    def projet(self) -> Projet:
        """Retourne l'objet Projet associé à ce jalon.

        :return: instance Projet
        :raises ValueError: si le projet associé n'existe pas
        """
        projet = self.db.get_project_id(self.projet_id)
        if projet:
            return projet
        raise ValueError(f"Projet with id {self.projet_id} not found")


class Interaction(DBObject, _RowInitMixin):
    """
    Représente une interaction entre un utilisateur et un client.

    interaction_id: identifiant unique de l'interaction

    date_time_interaction: date et heure de l'interaction (format 'YYYY-MM-DD HH:MM:SS')

    contenu: contenu de l'interaction (texte)

    client_id: identifiant du client associé à l'interaction (clé étrangère vers Client)

    utilisateur_id: identifiant de l'utilisateur ayant effectué l'interaction (clé étrangère vers Utilisateur)
    """

    FIELD_NAMES = ['interaction_id', 'date_time_interaction', 'titre', 'contenu', 'type_interaction_id', 'client_id', 'utilisateur_id']
    DATABASE_NAME = "Interactions"

    types_names = {
        "email": "Email",
        "phone": "Appel téléphonique",
        "meeting": "Réunion",
        "textmessage": "Message texte",
        "other": "Autre",
        "Email": "email",
        "Appel téléphonique": "phone",
        "Réunion": "meeting",
        "Message texte": "textmessage",
        "Autre": "other"
    }

    interactions_types = ['email', 'phone', 'meeting', 'textmessage', 'other']

    interaction_id: int
    date_time_interaction: datetime.datetime
    type_interaction_id: str # ('email', 'phone', 'meeting', 'textmessage', 'other')
    titre: str
    contenu: str
    client_id: int
    utilisateur_id: int

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._init_from(db, data)
        self._patch()
        # Après patch, mettre en cache l'objet si possible
        try:
            self._try_cache()
        except Exception:
            pass

    def _patch(self):
        """Valide le type d'interaction avant de sauvegarder."""
        if self.type_interaction_id not in self.interactions_types:
            raise ValueError(f"Invalid interaction type: {self.type_interaction_id}. Must be one of {self.interactions_types}")
        if isinstance(self.date_time_interaction, str):
            if ' ' in self.date_time_interaction:
                self.date_time_interaction = datetime.datetime.strptime(self.date_time_interaction, '%Y-%m-%d %H:%M:%S')
            else:
                self.date_time_interaction = datetime.datetime.strptime(self.date_time_interaction, '%Y-%m-%d')
        if isinstance(self.date_time_interaction, datetime.date) and not isinstance(self.date_time_interaction, datetime.datetime):
            self.date_time_interaction = datetime.datetime.combine(self.date_time_interaction, datetime.time.min)

    @classmethod
    def get_by_id(cls, db: Database, id: int) -> Optional['Interaction']:
        """Récupère une interaction par id (cache Redis puis SQL)."""
        return db.get_interaction_by_id(id)

    @property
    def client(self) -> Client:
        """Retourne le client associé à cette interaction.

        :raises ValueError: si le client n'existe pas
        :return: instance Client
        """
        client = self.db.get_client_by_id(self.client_id)
        if client:
            return client
        raise ValueError(f"Client with id {self.client_id} not found")

    @property
    def utilisateur(self) -> Utilisateur:
        """Retourne l'utilisateur associé à cette interaction.

        :raises ValueError: si l'utilisateur n'existe pas
        :return: instance Utilisateur
        """
        user = self.db.get_user_by_id(self.utilisateur_id)
        if user:
            return user
        raise ValueError(f"User with id {self.utilisateur_id} not found")

    @property
    def type_interaction(self) -> str:
        """Retourne le type d'interaction associé à cette interaction.

        :raises ValueError: si le type d'interaction n'existe pas
        :return: instance InteractionType
        """
        return self.types_names.get(self.type_interaction_id, "Inconnu")

