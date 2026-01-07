import os, base64, redis
from flask import g
from database import Database
from hashlib import scrypt


# Utiliser une valeur par défaut si la variable d'environnement n'est pas fournie
DATABASE = os.getenv('DATABASE', 'database/database.db')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = Database(
            redis_client=redis.Redis(host='localhost', port=6379, db=0),
            database=DATABASE
        )
    return db

def has_permission(user, permission: str) -> bool:
    role = user.role
    if role is None:
        return False
    return getattr(role, permission, False) or getattr(role, 'administrateur', False)



def hash_password(mdp: str) -> str:
    """Fonction qui hash et sale le mot de passe,
    Les 16 premiers octets sont le salt, le reste le mdp."""
    salt = os.urandom(16)  # Génération d'un salt

    mdp_hache = scrypt(mdp.encode(), salt=salt, n=2 ** 14, r=8, p=1)  # Hachage du mdp avec le salt

    # Encodage en B64, et remise en forme texte pour stockage.
    return base64.b64encode(salt + mdp_hache).decode()


def verify_password(mdp_entre: str, stored_hash: str) -> bool:
    """Fonction qui vérifie le mot de passe avec le hashé.
    Il est impossible de revenir au mdp depuis le hash, donc on hache l'entrée avec le même salt et on vérifie l'égalité
    Le résultat est un booléen."""

    octets_decodes = base64.b64decode(stored_hash)  # Bytes obtenus par décodage en B64
    salt = octets_decodes[:16]

    mdp_hache_stocke = octets_decodes[16:]
    mdp_hache_entre = scrypt(mdp_entre.encode(), salt=salt, n=2 ** 14, r=8, p=1)  # Hachage du mdp avec le salt

    return mdp_hache_entre == mdp_hache_stocke