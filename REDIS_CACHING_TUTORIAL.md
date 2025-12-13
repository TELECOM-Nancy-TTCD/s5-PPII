# Tutoriel : Caching avec Redis en composant Docker

Ce tutoriel montre comment ajouter Redis comme service Docker (via docker-compose) et comment l'utiliser pour mettre en cache des objets et des collections (par ex. tous les utilisateurs) depuis l'application Python du projet.

Contenu :
1) docker-compose minimal avec Redis
2) dépendances Python
3) branchement du client Redis à la classe `Database`
4) exemples : cache d'un objet, cache d'une liste (tous les utilisateurs)
5) invalidation du cache
6) bonnes pratiques et dépannage

---

## 1) docker-compose minimal
Créez (ou adaptez) un fichier `docker-compose.yml` à la racine du projet pour lancer Redis :

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    container_name: projet_redis
    restart: unless-stopped
    ports:
      - "6379:6379" # Expose pour le développement local
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

Démarrage :

```bash
# depuis la racine du dépôt
docker compose up -d
```

Vérifiez que Redis tourne :

```bash
docker compose ps
# ou
redis-cli ping
# devrait répondre: PONG
```

---

## 2) dépendances Python
Installez le client Redis pour Python (redis-py).

```bash
pip install -r requirements.txt
```

---

## 3) Brancher Redis à la classe `Database`
Dans `database/classes.py` la classe `Database` prend déjà un `redis_client`. Exemple d'initialisation (script d'entrée de l'application) :

```python
import sqlite3
import redis
from database import Database

# connexion redis (host = nom du service docker compose lorsque exécuté dans un réseau compose)
r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

db = Database(r, 'database/database.db')
```

Important : `decode_responses=True` permet de récupérer des chaînes plutôt que des bytes, ce qui simplifie la sérialisation JSON.

---

## 4) Exemples d'utilisation
### 4.1 Mettre en cache un objet (ex: `Utilisateur`)
Dans le code présent, le mixin `_RowInitMixin` essaie déjà de mettre en cache chaque objet après son initialisation en utilisant `setex(key, ttl, payload)`. La clé par défaut est construite ainsi : `<prefix>:<id>` où `prefix` est le nom de la classe en minuscule (ou `CACHE_PREFIX` si défini) et `id` est le premier champ dans `FIELD_NAMES` (généralement l'identifiant).

Exemple d'utilisation :

```python
# récupération via la DB
user = db.get_user_by_id(42)
# après l'instanciation, un appel à redis.setex('user:42', ttl, json_payload) est tenté automatiquement
```

La sérialisation stocke un dict construit par `to_dict()` contenant uniquement les champs listés dans `FIELD_NAMES`.

### 4.2 Mettre en cache une liste d'objets (ex: tous les utilisateurs)
Le pattern recommandé :
- stocker sous une clé dédiée la liste sérialisée (par ex. `users:all`), contenant une liste de dicts (représentation `to_dict()` de chaque objet) ou une liste d'IDs (si vous préférez mettre en cache individuellement les objets et seulement garder la liste des IDs).
- utiliser une méthode utilitaire centralisée pour lire/écrire cette collection et la reconstruire en objets si nécessaire.

Exemple d'une méthode utilitaire à ajouter dans `Database` (expliquée ici, à copier dans `database/classes.py`) :

```python
import json
from typing import Callable, List, Any

# méthode utilitaire (à ajouter dans Database)
def _get_cached_objects(self, cache_key: str, cls: Any, loader: Callable[[], List[Any]], ttl: int = 1800) -> List[Any]:
    """Charge une collection depuis Redis ou, à défaut, depuis la BD via loader().
    - cache_key : clé Redis (ex: 'users:all')
    - cls : la classe (ex: Utilisateur) ayant from_db_row
    - loader : callable qui charge la liste d'objets (instanciés) depuis la BD
    """
    redis_client = getattr(self, 'redis_client', None)
    if redis_client is not None:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                rows = json.loads(cached)
                # rows est une liste de dicts; on reconstruit les objets
                return [cls.from_db_row(self, row) for row in rows]
            except Exception:
                # si échec, on continue et charge depuis la BD
                pass

    objs = loader()
    if redis_client is not None:
        try:
            redis_client.setex(cache_key, ttl, json.dumps([o.to_dict() for o in objs]))
        except Exception:
            pass
    return objs
```

Et un exemple d'utilisation pour récupérer tous les utilisateurs avec cache :

```python
# méthode à placer dans Database
def get_all_users_cached(self, limit: int = 0) -> List['Utilisateur']:
    cache_key = 'users:all' if limit <= 0 else f'users:all:limit:{limit}'

    def loader():
        cursor = self.db.execute('SELECT * FROM utilisateurs' + (" LIMIT ?" if limit > 0 else ""), (limit,) if limit > 0 else ())
        rows = cursor.fetchall()
        cursor.close()
        return [Utilisateur.from_db_row(self, row) for row in rows]

    return self._get_cached_objects(cache_key, Utilisateur, loader)
```

Deux approches sur ce que vous stockez :
- stocker la liste complète d'objets sous `users:all` (pratique, simple) ; ou
- stocker séparément chaque utilisateur sous `user:<id>` et ne stocker sous `users:all` qu'une liste d'IDs. Avantage : invalidation plus fine (modifier un utilisateur implique juste mettre à jour `user:<id>` et/ou rafraîchir `users:all`).

---

## 5) Invalidation du cache
Très important : toujours invalider la clé de collection quand la BD change. Stratégies :

- Après un INSERT/UPDATE/DELETE sur les utilisateurs, supprimer `users:all` :

```python
# après modification en base
self.redis_client.delete('users:all')
# ou si vous stockez IDs: mettre à jour la liste ou supprimer la clé
```

- Pour des invalidations plus fines :
  - mettre à jour `user:<id>` directement (setex) quand l'objet change
  - supprimer `users:all` seulement si nécessaire (ex: on préfère l'invalidation totale après un changement structurel)

---

## 6) Tests locaux rapides
1. Démarrer Redis via docker compose

```bash
docker compose up -d
```

2. Démarrer une REPL Python et essayer :

```python
from database.classes import Database, Utilisateur
import sqlite3
import redis

conn = sqlite3.connect('database/database.db')
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
db = Database(conn, r)

# première lecture (devrait charger depuis sqlite)
users = db.get_all_users_cached()

# deuxième lecture (devrait être servie depuis Redis)
users2 = db.get_all_users_cached()
```

Utilisez `redis-cli` pour inspecter les clés :

```bash
redis-cli keys '*user*'
redis-cli get 'users:all'
```

---

## Bonnes pratiques
- Définir des TTL raisonnables (ex : 30 minutes) pour éviter la staleness indéfinie.
- Invalider le cache systématiquement lors des opérations d'écriture.
- Pour de très grandes collections, préférez stocker une liste d'IDs et chercher les objets individuellement en parallèle.
- Pensez à utiliser une clé versionnée pour faciliter les invalidations de masse, ex: `users:all:v2`.

---

## Dépannage
- Si `redis_client` renvoie `None` : vérifiez l'initialisation et l'adresse/nom d'hôte (`redis` dans docker-compose ou `localhost` pour un client local).
- Erreurs de désérialisation : assurez-vous d'utiliser `decode_responses=True` pour que redis retourne des chaînes et non des bytes.
- Pour les tests, mockez `redis.Redis` pour contrôler `get`/`setex`/`delete` et vérifier que les appels sont correctement faits.
