from flask import Blueprint

utilisateurs_bp = Blueprint('utilisateurs', __name__)

try:
    import utilisateurs.roles
except Exception:
    pass
