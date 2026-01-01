from flask import Blueprint

bp_utilisateurs = Blueprint('utilisateurs', __name__)


# Importer les sous-modules qui attachent des routes au blueprint.
# Cela garantit que les routes définies dans `interactions/roles.py` sont
# bien enregistrées lorsque ce package est importé.
try:
    # Import local pour éviter import circulaire au démarrage
    import utilisateurs.roles  # noqa: F401
except Exception:
    # En environnement de test léger, l'import peut échouer; laisser passer
    pass
