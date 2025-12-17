from flask import Blueprint, request, render_template, abort, jsonify
import os
from datetime import datetime, date

from flask_login import login_required, current_user

from tools import get_db, has_permission
from database import Interaction

interactions_bp = Blueprint('interactions', __name__, template_folder="templates/interactions", static_folder="static", url_prefix="/interactions")

DATABASE= os.getenv('DATABASE')

# Helper validator
def validate_interaction_form(form):
    """
    Validate interaction form data from request.form or similar mapping.
    Returns a dict mapping field_name -> error_message for invalid fields.
    Expected field names: 'client-id', 'type', 'interaction-date', 'title', 'content'
    """
    errors = {}

    client_id = form.get('client-id') or form.get('client_id') or form.get('client')
    if not client_id or str(client_id).strip() == '':
        errors['client-id'] = 'Le client est requis.'

    type_val = form.get('type') or form.get('type_interaction')
    allowed_types = getattr(Interaction, 'interactions_types', None) or []
    if not type_val or type_val.strip() == '':
        errors['type'] = 'Le type d\'interaction est requis.'
    elif allowed_types and type_val not in allowed_types:
        errors['type'] = 'Type d\'interaction invalide.'

    date_val = form.get('interaction-date') or form.get('date_interaction') or form.get('date')
    parsed = None
    parsed_is_datetime = False
    if not date_val or str(date_val).strip() == '':
        errors['interaction-date'] = 'La date est requise.'
    else:
        # Try parsing as date (YYYY-MM-DD) or datetime-local (YYYY-MM-DDTHH:MM)
        for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M'):
            try:
                parsed = datetime.strptime(date_val, fmt)
                parsed_is_datetime = (fmt == '%Y-%m-%dT%H:%M')
                break
            except Exception:
                parsed = None
        if parsed is None:
            errors['interaction-date'] = 'Format de date invalide. Utiliser YYYY-MM-DD ou YYYY-MM-DDTHH:MM.'
        else:
            # Check not in the future
            now = datetime.now()
            if parsed_is_datetime:
                if parsed > now:
                    errors['interaction-date'] = 'La date/heure ne peut pas être supérieure à la date actuelle.'
            else:
                # date-only: compare dates (ignore time)
                if parsed.date() > now.date():
                    errors['interaction-date'] = 'La date ne peut pas être supérieure à la date du jour.'

    title = form.get('title') or form.get('titre')
    if not title or str(title).strip() == '':
        errors['title'] = 'Le titre est requis.'

    content = form.get('content') or form.get('contenu') or form.get('notes')
    if not content or str(content).strip() == '':
        errors['content'] = 'Le contenu est requis.'

    return errors

@interactions_bp.route('/')
@login_required
def interactions_home():
    if not has_permission(current_user, 'peut_gerer_interactions') and not has_permission(current_user, 'peut_creer_interactions'):
        return abort(403)

     # Récupération des paramètres de pagination
    page = request.args.get("p", 0, type=int)
    limit = request.args.get("l", 10, type=int)
    db = get_db()
    interactions = db.get_all_interactions(limit=10)
    return render_template("interactions/interactions.html", interactions=interactions, Interaction=Interaction, page=page, limit=limit)

@interactions_bp.route('/<int:interaction_id>')
@login_required
def interaction_detail(interaction_id):
    if not has_permission(current_user, 'peut_gerer_interactions') and not has_permission(current_user, 'peut_creer_interactions'):
        return abort(403)

    db = get_db()
    interaction = db.get_interaction_by_id(interaction_id)
    if interaction is None:
        return abort(404)

    return render_template("interactions/view_interaction.html", interaction=interaction)

@interactions_bp.route('/<int:interaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_interaction(interaction_id):
    db = get_db()
    interaction = db.get_interaction_by_id(interaction_id)
    if interaction is None:
        return abort(404)

    if not has_permission(current_user, 'peut_gerer_interactions') and interaction.utilisateur_id != current_user.utilisateur_id:
        return abort(403)


     # Gestion du formulaire soumis
    if request.method == 'POST':
        errors = validate_interaction_form(request.form)
        if errors:
            return jsonify({'errors': errors}), 400

        interaction.client_id = request.form['client-id']
        interaction.utilisateur_id = current_user.utilisateur_id
        interaction.type_interaction_id = request.form['type']
        interaction.date_time_interaction = request.form['interaction-date']
        interaction.contenu = request.form['content']
        interaction.titre = request.form['title']
        interaction.save()

        return jsonify({'message': 'Interaction updated successfully'}), 200

    return render_template("interactions/edit_interaction.html", interaction=interaction, Interaction=Interaction)

@interactions_bp.route('/<int:interaction_id>/delete', methods=['DELETE'])
@login_required
def delete_interaction(interaction_id):
    db = get_db()
    interaction = db.get_interaction_by_id(interaction_id)
    if interaction is None:
        return abort(404)

    if not has_permission(current_user, 'peut_gerer_interactions') and interaction.utilisateur_id != current_user.utilisateur_id:
        return abort(403)

    interaction.delete()
    return jsonify({'message': 'Interaction deleted successfully'}), 200

@interactions_bp.route('/create', methods=['GET', 'PUT'])
@login_required
def create_interaction():
    if not has_permission(current_user, 'peut_gerer_interactions') and not has_permission(current_user, 'peut_creer_interactions'):
        return abort(403)

     # Gestion du formulaire soumis
    db = get_db()
    if request.method == 'PUT':
        errors = validate_interaction_form(request.form)
        if errors:
            return jsonify({'errors': errors}), 400

        interaction_data = {
            'client_id': request.form['client-id'],
            'utilisateur_id': current_user.utilisateur_id,
            'type_interaction_id': request.form['type'],
            'date_time_interaction': request.form['interaction-date'],
            'contenu': request.form['content'],
            'titre': request.form['title']
        }
        Interaction.from_dict(db, interaction_data).save()

        return jsonify({'message': 'Interaction created successfully'}), 201

     # Récupération des informations déjà présentes dans l'URL pour le formulaire
    # Supporter plusieurs variantes de noms (provenant du modal, du form inline ou d'un lien externe)
    def pick(*names, default=''):
        for n in names:
            v = request.args.get(n)
            if v is not None and v != '':
                return v
        return default

    interaction_form_data = {
        # client id can come as client_id or client-id (hidden field)
        'client_id': pick('client_id', 'client-id', 'clientId', 'client'),
        # client display name: client_name or client-search
        'client_name': pick('client_name', 'client-name', 'client-search', 'clientDisplayName'),
        # type can come as type_interaction or type
        'type_interaction': pick('type_interaction', 'type', 'interaction_type', 'support'),
        # date can be date_interaction or interaction-date
        'date_interaction': pick('date_interaction', 'interaction-date', 'date', 'date_time_interaction'),
        # content can be contenu or content or notes
        'contenu': pick('contenu', 'content', 'notes', 'body', 'description'),
        # title support title or titre
        'title': pick('title', 'titre', 'objet', 'subject'),
        # utilisateur (optional)
        'utilisateur_id': pick('utilisateur_id', 'user_id', 'uid', 'utilisateur'),
        'utilisateur_name': pick('utilisateur_name', 'user_name', 'username'),
    }

    return render_template("interactions/create_interaction.html", Interaction=Interaction, form_data=interaction_form_data)