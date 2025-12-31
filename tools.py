import os
from flask import g
import redis
from database import Database

# Utiliser une valeur par défaut si la variable d'environnement n'est pas fournie
DATABASE = os.getenv('DATABASE', 'database/database.db')


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