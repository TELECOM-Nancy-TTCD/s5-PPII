import redis
from flask import Blueprint, request, render_template, abort
import os

from flask_login import login_required, current_user

from tools import get_db, has_permission
from database import Interaction

interactions_bp = Blueprint('interactions', __name__, template_folder="templates/interactions", static_folder="static")

DATABASE= os.getenv('DATABASE')

@interactions_bp.route('/interactions')
@login_required
def interactions_home():
    if not has_permission(current_user, 'peut_gerer_interactions'):
        return abort(403)

     # Récupération des paramètres de pagination
    page = request.args.get("p", 0, type=int)
    limit = request.args.get("l", 10, type=int)
    db = get_db()
    interactions = db.get_all_interactions(limit=10)
    return render_template("interactions/interactions.html", interactions=interactions, Interaction=Interaction, page=page, limit=limit)

@interactions_bp.route('/interactions/<int:interaction_id>')
@login_required
def interaction_detail(interaction_id):
    if not has_permission(current_user, 'peut_gerer_interactions'):
        return abort(403)

    db = get_db()
    interaction = db.get_interaction_by_id(interaction_id)
    if interaction is None:
        return abort(404)

    return render_template("interactions/view_interaction.html", interaction=interaction)

@interactions_bp.route('/interactions/<int:interaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_interaction(interaction_id):
    if not has_permission(current_user, 'peut_gerer_interactions'):
        return abort(403)

    db = get_db()
    interaction = db.get_interaction_by_id(interaction_id)
    if interaction is None:
        return abort(404)

     # Gestion du formulaire soumis
    if request.method == 'POST':
        interaction.type_interaction_id = request.form['type']
        interaction.date_time_interaction = request.form['interaction-date']
        interaction.contenu = request.form['content']
        interaction.titre = request.form['title']
        interaction.save()

        return "Interaction updated successfully", 200

    return render_template("interactions/edit_interaction.html", interaction=interaction, Interaction=Interaction)

@interactions_bp.route('/interactions/<int:interaction_id>/delete', methods=['DELETE'])
@login_required
def delete_interaction(interaction_id):
    if not has_permission(current_user, 'peut_gerer_interactions'):
        return abort(403)

    db = get_db()
    interaction = db.get_interaction_by_id(interaction_id)
    if interaction is None:
        return abort(404)

    interaction.delete()
    return "Interaction deleted successfully", 200

@interactions_bp.route('/interactions/create', methods=['GET', 'POST'])
@login_required
def create_interaction():
    if not has_permission(current_user, 'peut_gerer_interactions'):
        return abort(403)

     # Gestion du formulaire soumis
    db = get_db()
    if request.method == 'POST':
        interaction_data = {
            'client_id': request.form['client-id'],
            'utilisateur_id': current_user.utilisateur_id,
            'type_interaction_id': request.form['type'],
            'date_time_interaction': request.form['interaction-date'],
            'contenu': request.form['content'],
            'titre': request.form['title']
        }
        Interaction.from_dict(db, interaction_data).save()

        return "Interaction created successfully", 201

     # Récupération des informations déjà présentes dans l'URL pour le formulaire
    interaction_form_data = {
        'client_id': request.args.get('client_id', ''),
        'type_interaction': request.args.get('type_interaction', ''),
        'date_interaction': request.args.get('date_interaction', ''),
        'notes': request.args.get('notes', '')
    }

    return render_template("interactions/create_interaction.html", Interaction=Interaction, form_data=interaction_form_data)