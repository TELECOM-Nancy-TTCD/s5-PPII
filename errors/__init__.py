from flask import Blueprint, render_template

errors_bp = Blueprint('errors', __name__)

# Ici les pages d'erreur.
@errors_bp.app_errorhandler(404)
def page_not_found(error=None):
    """Fonction pour l'erreur 404"""
    return render_template("errors/404.html"), 404


@errors_bp.app_errorhandler(500)
def server_error(error=None):
    """Fonction pour l'erreur 500"""
    return render_template("errors/500.html"), 500


@errors_bp.app_errorhandler(403)
def forbidden_error(error=None):
    """Fonction pour l'erreur 403"""
    return render_template("errors/403.html"), 403