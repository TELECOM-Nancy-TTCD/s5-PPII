from flask import Blueprint, request, render_template
from flask_login import login_required

from tools import get_db

errors_bp = Blueprint('errors', __name__, template_folder="templates/errors")

# Ici les pages d'erreur.
@errors_bp.errorhandler(404)
def page_not_found():
    """Fonction pour l'erreur 404"""
    return render_template("errors/404.html"), 404


@errors_bp.errorhandler(500)
def serveur_error():
    """Fonction pour l'erreur 500"""
    return render_template("errors/500.html"), 500


@errors_bp.errorhandler(403)
def serveur_error():
    """Fonction pour l'erreur 403"""
    return render_template("errors/403.html"), 403