import json
import sqlite3
from typing import Any, Dict, Tuple, List, Optional, cast, Sequence, Mapping


class Database:
    def __init__(self, redis_client: Any, database: str | bytes, **kwargs):
        if not redis_client:
            raise ValueError("A valid redis_client must be provided")
        if not database:
            raise ValueError("A valid database path must be provided")
        self.redis_client = redis_client
        try:
            self.db = sqlite3.connect(database, **kwargs)
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to connect to database: {e}") from e

    def close(self):
        self.db.close()

    def commit(self):
        try:
            self.db.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to commit transaction: {e}") from e

    def execute(self, query: str, params: Sequence[Any] | Mapping[str, Any] | Any = ()) -> sqlite3.Cursor:
        """Execute a SQL query with optional parameters.
        `params` is usually a sequence (tuple/list) or a mapping (dict) accepted by sqlite3.
        """
        try:
            return self.db.execute(query, params)
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to execute query: {e}") from e

    def cursor(self):
        return self.db.cursor()

    def get_user_by_id(self, user_id: int) -> Optional['Utilisateur']:
        cached_user = self.redis_client.get(f"user:{user_id}")
        if cached_user:
            return Utilisateur.from_db_row(self, json.loads(cached_user))
        cursor = self.execute("SELECT * FROM utilisateurs WHERE utilisateur_id = ?", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            user = Utilisateur.from_db_row(self, row)
            return user
        return None

    def get_all_users(self, limit: int = 0, *, key=lambda x: True) -> List['Utilisateur']:
        """
        Récupère tous les utilisateurs de la base de données.
        :param limit: Nombre maximum d'utilisateurs à récupérer (0 pour aucune limite)
        :param key: Fonction de filtrage optionnelle
        :return: Liste des objets Utilisateur
        """
        cached_users = self.redis_client.get("users:all")
        if cached_users:
            all_users_id = json.loads(cached_users)
            users = [self.get_user_by_id(uid) for uid in all_users_id]
            users = [user for user in users if user is not None and key(user)]
            if limit > 0:
                return users[:limit]
            return users
        cursor = self.execute("SELECT * FROM Utilisateurs " + (" LIMIT ?" if limit > 0 else ""), (limit,) if limit > 0 else ())  # TODO: Décider si la coupe doit être faite en SQL ou en Python
        rows = cursor.fetchall()
        cursor.close()

        if limit == 0:
            # Mettre en cache les IDs des utilisateurs
            all_users_id = [row[0] for row in rows]  # Supposant que l'ID est dans la première colonne
            self.redis_client.setex("users:all", 1_800, json.dumps(all_users_id))

        users = [Utilisateur.from_db_row(self, row) for row in rows if key(Utilisateur.from_db_row(self, row))]
        return users

    def get_client_by_id(self, client_id: int) -> Optional['Client']:
        cached_client = self.redis_client.get(f"client:{client_id}")
        if cached_client:
            return Client.from_db_row(self, json.loads(cached_client))
        cursor = self.db.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            client = Client.from_db_row(self, row)
            return client
        return None

    def get_all_clients(self, limit: int = 0, *, key=lambda x: True) -> List['Client']:
        """
        Récupère tous les clients de la base de données.
        :param limit: Nombre maximum de clients à récupérer (0 pour aucune limite)
        :param key: Fonction de filtrage optionnelle
        :return: Liste des objets Client
        """
        cached_clients = self.redis_client.get("clients:all")
        if cached_clients:
            all_clients_id = json.loads(cached_clients)
            clients = [self.get_client_by_id(cid) for cid in all_clients_id]
            clients = [client for client in clients if client is not None and key(client)]
            if limit > 0:
                return clients[:limit]
            return clients
        cursor = self.execute("SELECT * FROM clients " + (" LIMIT ?" if limit > 0 else ""), (limit,) if limit > 0 else ())  # TODO: Décider si la coupe doit être faite en SQL ou en Python
        rows = cursor.fetchall()
        cursor.close()

        if limit == 0:
            # Mettre en cache les IDs des clients
            all_clients_id = [row[0] for row in rows]  # Supposant que l'ID est dans la première colonne
            self.redis_client.setex("clients:all", 1_800, json.dumps(all_clients_id))

        clients = [Client.from_db_row(self, row) for row in rows if key(Client.from_db_row(self, row))]
        return clients


class DBObject:
    def __init__(self, db: Database):
        self.db = db

    def __repr__(self) -> str:
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

    def _init_from(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]]):
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
            assert len(data) == len(self.FIELD_NAMES), f"Data tuple must have exactly {len(self.FIELD_NAMES)} elements"
            for f, v in zip(self.FIELD_NAMES, data):
                setattr(self, f, v)
        else:
            raise TypeError("data must be a dict, tuple/list or None")

        # Après l'initialisation des champs, tenter de mettre l'objet en cache Redis
        try:
            self._try_cache()
        except Exception:
            # Ne pas lever d'erreur si Redis n'est pas disponible ou si sérialisation échoue
            pass

    @classmethod
    def from_db_row(cls, db: Database, row: Tuple[Any, ...]):
        # Cast cls to Any so static analyzers won't complain about varying __init__ signatures
        return cast(Any, cls)(db, row)

    def to_dict(self) -> Dict[str, Any]:
        return {f: getattr(self, f) for f in self.FIELD_NAMES}

    def __dict__(self):
        return self.to_dict()

    # Méthodes de cache centralisées
    def _cache_key(self) -> Optional[str]:
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
        # Tente d'écrire l'objet en cache Redis si possible
        if not hasattr(self, 'db') or self.db is None:
            return
        redis_client = getattr(self.db, 'redis_client', None)
        if redis_client is None:
            return
        key = self._cache_key()
        if key is None:
            return
        # Sérialise uniquement les champs déclarés dans FIELD_NAMES
        payload = json.dumps(self.to_dict())
        # Utiliser setex pour définir TTL
        redis_client.setex(key, self.CACHE_TTL, payload)

    def save(self):
        # Sauvegarde l'objet dans la base de données
        fields = ', '.join(self.FIELD_NAMES)
        placeholders = ', '.join(['?'] * len(self.FIELD_NAMES))
        values = (getattr(self, f) for f in self.FIELD_NAMES)
        # Exécuter l'insertion
        self.db.execute(
            f"INSERT OR REPLACE INTO {self.DATABASE_NAME} ({fields}) VALUES ({placeholders})",
            tuple(values)
        )
        self.db.commit()

        # Vérifier si l'identifiant était dans le cache de tous les objets
        cached_ids = self.db.redis_client.get(f"{self.DATABASE_NAME}s:all")
        if cached_ids:
            ids_list = json.loads(cached_ids)
            id_field = next((f for f in self.FIELD_NAMES if f.endswith('_id')), None)
            if id_field:
                id_val = getattr(self, id_field, None)
                if id_val is not None and id_val not in ids_list:
                    ids_list.append(id_val)
                    self.db.redis_client.setex(f"{self.DATABASE_NAME}s:all", 1_800, json.dumps(ids_list))

        # Mettre à jour le cache Redis après la sauvegarde
        try:
            self._try_cache()
        except Exception:
            pass

    def delete(self):
        # Supprime l'objet de la base de données
        id_field = next((f for f in self.FIELD_NAMES if f.endswith('_id')), None)
        if id_field is None:
            raise ValueError("No ID field found for deletion")
        id_val = getattr(self, id_field, None)
        if id_val is None:
            raise ValueError("ID value is None, cannot delete")
        self.db.execute(
            f"DELETE FROM {self.DATABASE_NAME} WHERE {id_field} = ?",
            (id_val,)
        )
        self.db.commit()

        # Supprimer du cache Redis
        try:
            key = self._cache_key()
            if key:
                self.db.redis_client.delete(key)
            # Mettre à jour le cache de tous les objets
            cached_ids = self.db.redis_client.get(f"{self.DATABASE_NAME}s:all")
            if cached_ids:
                ids_list = json.loads(cached_ids)
                if id_val in ids_list:
                    ids_list.remove(id_val)
                    self.db.redis_client.setex(f"{self.DATABASE_NAME}s:all", 1_800, json.dumps(ids_list))
        except Exception:
            pass

    def __del__(self):
        # Nettoyage si nécessaire
        self.delete()


class Role(DBObject, _RowInitMixin):
    """
    Représente un rôle utilisateur avec ses permissions.

    role_id: identifiant unique du rôle

    nom: nom du rôle

    hierarchie: niveau hiérarchique du rôle, plus le nombre est bas, plus le rôle est élevé

    Permissions (booléens) indiquant les actions autorisées pour ce rôle.
    """
    FIELD_NAMES = [
        'role_id', 'nom', 'hierarchie',
        'peut_gerer_utilisateurs', 'peut_gerer_roles',
        'peut_lire_clients', 'peut_gerer_clients', 'peut_gerer_interactions',
        'peut_lire_projets', 'peut_gerer_projets', 'peut_gerer_jalons', 'peut_assigner_intervenants',
        'peut_lire_intervenants', 'peut_modifier_intervenants', 'peut_acceder_documents', 'peut_gerer_competences',
        'peut_lancer_matching', 'peut_exporter_csv'
    ]

    role_id: int
    nom: str
    hierarchie: int
    peut_gerer_utilisateurs: bool
    peut_gerer_roles: bool
    peut_lire_clients: bool
    peut_gerer_clients: bool
    peut_gerer_interactions: bool
    peut_lire_projets: bool
    peut_gerer_projets: bool
    peut_gerer_jalons: bool
    peut_assigner_intervenants: bool
    peut_lire_intervenants: bool
    peut_modifier_intervenants: bool
    peut_acceder_documents: bool
    peut_gerer_competences: bool
    peut_lancer_matching: bool
    peut_exporter_csv: bool

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._init_from(db, data)


class Utilisateur(DBObject, _RowInitMixin):
    """
    Représente un utilisateur du site. Il peut être intervenant ou membre de TNS.

    utilisateur_id: identifiant unique de l'utilisateur

    email: adresse email de l'utilisateur

    mot_de_passe_hashed: mot de passe hashé de l'utilisateur

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
        'utilisateur_id', 'email', 'mot_de_passe_hashed',
        'nom', 'prenom', 'role_id',
        'est_intervenant', 'heures_dispo_semaine',
        'doc_carte_vitale', 'doc_cni', 'doc_adhesion', 'doc_rib'
    ]
    utilisateur_id: int
    email: str
    mot_de_passe_hashed: str
    nom: str
    prenom: str
    role_id: int
    est_intervenant: bool
    heures_dispo_semaine: Optional[int]
    doc_carte_vitale: Optional[str]
    doc_cni: Optional[str]
    doc_adhesion: Optional[str]
    doc_rib: Optional[str]

    CACHE_PREFIX = 'user'

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._patch()
        self._init_from(db, data)

    def _patch(self):
        # Méthode pour patcher les données si nécessaire (ex: mise à jour de schéma)
        if not isinstance(self.utilisateur_id, int):
            self.utilisateur_id = int(self.utilisateur_id)
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
        cached_role = self.db.redis_client.get(f"role:{self.role_id}")
        if cached_role:
            return Role.from_db_row(self.db, json.loads(cached_role))
        cursor = self.db.execute("SELECT * FROM roles WHERE role_id = ?", (self.role_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            role = Role.from_db_row(self.db, row)
            return role
        raise ValueError(f"Role with id {self.role_id} not found")


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
        super().__init__(db)
        self._init_from(db, data)

    @property
    def interlocuteur_principal(self) -> Utilisateur:
        cached_user = self.db.redis_client.get(f"user:{self.interlocuteur_principal_id}")
        if cached_user:
            return Utilisateur.from_db_row(self.db, json.loads(cached_user))
        cursor = self.db.execute("SELECT * FROM utilisateurs WHERE utilisateur_id = ?",
                                    (self.interlocuteur_principal_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            user = Utilisateur.from_db_row(self.db, row)
            return user
        raise ValueError(f"User with id {self.interlocuteur_principal_id} not found")

    @property
    def conventions(self) -> list[Any] | None:
        cached_conventions_ids = self.db.redis_client.get(f"client:{self.client_id}:conventions")
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
            cursor = self.db.execute("SELECT * FROM conventions WHERE client_id = ?", (self.client_id,))
            rows = cursor.fetchall()
            conventions = [Convention.from_db_row(self.db, row) for row in rows]
            cursor.close()
            # Mettre en cache les IDs des conventions
            conventions_ids = [convention.convention_id for convention in conventions]
            self.db.redis_client.setex(f"client:{self.client_id}:conventions", 1_800, json.dumps(conventions_ids))
            return conventions
        return None

    @property
    def interactions(self) -> list[Any] | None:
        cached_interactions_ids = self.db.redis_client.get(f"client:{self.client_id}:interactions")
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
            cursor = self.db.execute("SELECT * FROM interactions WHERE client_id = ?", (self.client_id,))
            rows = cursor.fetchall()
            interactions = [Interaction.from_db_row(self.db, row) for row in rows]
            cursor.close()
            # Mettre en cache les IDs des interactions
            interactions_ids = [interaction.interaction_id for interaction in interactions]
            self.db.redis_client.setex(f"client:{self.client_id}:interactions", 1_800, json.dumps(interactions_ids))
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
        cached_client = self.db.redis_client.get(f"client:{self.client_id}")
        if cached_client:
            return Client.from_db_row(self.db, json.loads(cached_client))
        cursor = self.db.execute("SELECT * FROM clients WHERE client_id = ?", (self.client_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            client = Client.from_db_row(self.db, row)
            return client
        raise ValueError(f"Client with id {self.client_id} not found")

    @property
    def projets(self) -> list[Any] | None:
        cached_projets_ids = self.db.redis_client.get(f"convention:{self.convention_id}:projets")
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
            cursor = self.db.execute("SELECT * FROM projets WHERE convention_id = ?", (self.convention_id,))
            rows = cursor.fetchall()
            projets = [Projet.from_db_row(self.db, row) for row in rows]
            cursor.close()
            # Mettre en cache les IDs des projets
            projets_ids = [projet.projet_id for projet in projets]
            self.db.redis_client.setex(f"convention:{self.convention_id}:projets", 1_800, json.dumps(projets_ids))
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
        'projet_id', 'convention_id', 'nom_projet', 'description', 'budget', 'date_debut', 'date_fin', 'statut',
        'doc_dossier'
    ]
    projet_id: int
    convention_id: int
    nom_projet: str
    description: str
    budget: float
    date_debut: str
    date_fin: str
    statut: str
    doc_dossier: Optional[str]

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._init_from(db, data)

    @property
    def convention(self) -> Convention:
        cached_convention = self.db.redis_client.get(f"convention:{self.convention_id}")
        if cached_convention:
            return Convention.from_db_row(self.db, json.loads(cached_convention))
        cursor = self.db.execute("SELECT * FROM conventions WHERE convention_id = ?", (self.convention_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            convention = Convention.from_db_row(self.db, row)
            return convention
        raise ValueError(f"Convention with id {self.convention_id} not found")

    @property
    def jalons(self) -> list[Any] | None:
        cached_jalons_ids = self.db.redis_client.get(f"projet:{self.projet_id}:jalons")
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
            cursor = self.db.execute("SELECT * FROM jalons WHERE projet_id = ?", (self.projet_id,))
            rows = cursor.fetchall()
            jalons = [Jalon.from_db_row(self.db, row) for row in rows]
            cursor.close()
            # Mettre en cache les IDs des jalons
            jalons_ids = [jalon.jalon_id for jalon in jalons]
            self.db.redis_client.setex(f"projet:{self.projet_id}:jalons", 1_800, json.dumps(jalons_ids))
            return jalons
        return None


class Competence(DBObject, _RowInitMixin):
    """
    Représente une compétence pouvant être associée à un intervenant ou un projet.

    competence_id: identifiant unique de la compétence

    nom: nom de la compétence

    competence_parent: identifiant de la compétence parente (clé étrangère vers Competence), ou None si pas de parent
    """
    FIELD_NAMES = ['competence_id', 'nom', 'competence_parent']
    competence_id: int
    nom: str
    competence_parent: Optional[int]

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._init_from(db, data)

    @property
    def parent(self) -> Optional['Competence']:
        if self.competence_parent is None:
            return None
        cached_competence = self.db.redis_client.get(f"competence:{self.competence_parent}")
        if cached_competence:
            return Competence.from_db_row(self.db, json.loads(cached_competence))
        cursor = self.db.execute("SELECT * FROM competences WHERE competence_id = ?", (self.competence_parent,))
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
        cached_projet = self.db.redis_client.get(f"projet:{self.projet_id}")
        if cached_projet:
            return Projet.from_db_row(self.db, json.loads(cached_projet))
        cursor = self.db.execute("SELECT * FROM projets WHERE projet_id = ?", (self.projet_id,))
        row = cursor.fetchone()
        if row:
            projet = Projet.from_db_row(self.db, row)
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

    FIELD_NAMES = ['interaction_id', 'date_time_interaction', 'contenu', 'client_id', 'utilisateur_id']
    interaction_id: int
    date_time_interaction: str
    contenu: str
    client_id: int
    utilisateur_id: int

    def __init__(self, db: Database, data: Optional[Tuple[Any, ...]] | Optional[Dict[str, Any]] = None):
        super().__init__(db)
        self._init_from(db, data)

    @property
    def client(self) -> Client:
        cached_client = self.db.redis_client.get(f"client:{self.client_id}")
        if cached_client:
            return Client.from_db_row(self.db, json.loads(cached_client))
        cursor = self.db.execute("SELECT * FROM clients WHERE client_id = ?", (self.client_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            client = Client.from_db_row(self.db, row)
            return client
        raise ValueError(f"Client with id {self.client_id} not found")

    @property
    def utilisateur(self) -> Utilisateur:
        cached_user = self.db.redis_client.get(f"user:{self.utilisateur_id}")
        if cached_user:
            return Utilisateur.from_db_row(self.db, json.loads(cached_user))
        cursor = self.db.execute("SELECT * FROM utilisateurs WHERE utilisateur_id = ?", (self.utilisateur_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            user = Utilisateur.from_db_row(self.db, row)
            return user
        raise ValueError(f"User with id {self.utilisateur_id} not found")
