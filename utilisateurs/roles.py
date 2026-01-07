from flask import abort, render_template, request, jsonify, Response
import json
from flask_login import current_user, login_required as flask_login_required

from tools import has_permission, get_db
from utilisateurs import utilisateurs_bp
from database import Role
from typing import Dict, Any


# Méta-données des permissions : label lisible et description courte
PERMISSION_META: Dict[str, Dict[str, str]] = {
    'administrateur': {
        'label': 'Administrateur',
        'desc': "Accès complet à l'application et aux paramètres globaux. Utiliser avec précaution."
    },
    'peut_gerer_utilisateurs': {
        'label': 'Gérer les utilisateurs',
        'desc': 'Créer, modifier ou supprimer des comptes utilisateurs et attribuer des rôles.'
    },
    'peut_gerer_roles': {
        'label': 'Gérer les rôles',
        'desc': 'Créer, modifier et supprimer des rôles et leurs permissions.'
    },
    'peut_lire_clients': {
        'label': 'Lire les clients',
        'desc': 'Voir les fiches clients et leurs informations publiques.'
    },
    'peut_gerer_clients': {
        'label': 'Gérer les clients',
        'desc': 'Créer et modifier les fiches clients, contacts et informations liées.'
    },
    'peut_creer_interactions': {
        'label': 'Créer des interactions',
        'desc': 'Ajouter des interactions (emails, appels, notes) liées à un client.'
    },
    'peut_gerer_interactions': {
        'label': 'Gérer les interactions',
        'desc': 'Modifier ou supprimer des interactions créées dans le système.'
    },
    'peut_lire_projets': {
        'label': 'Voir les projets',
        'desc': 'Consulter les projets associés aux clients et conventions.'
    },
    'peut_gerer_projets': {
        'label': 'Gérer les projets',
        'desc': 'Créer et administrer les projets et leur avancement.'
    },
    'peut_gerer_jalons': {
        'label': 'Gérer les jalons',
        'desc': 'Créer/modifier les jalons d’un projet et marquer leur complétion.'
    },
    'peut_assigner_intervenants': {
        'label': 'Assigner intervenants',
        'desc': 'Attribuer des intervenants aux projets.'
    },
    'peut_lire_intervenants': {
        'label': 'Voir les intervenants',
        'desc': 'Consulter la liste des intervenants et leurs compétences.'
    },
    'peut_modifier_intervenants': {
        'label': 'Modifier intervenants',
        'desc': 'Modifier les informations des intervenants.'
    },
    'peut_acceder_documents': {
        'label': 'Accéder aux documents',
        'desc': 'Télécharger et consulter les documents liés aux clients/projets.'
    },
    'peut_gerer_competences': {
        'label': 'Gérer les compétences',
        'desc': 'Créer et organiser les compétences des intervenants.'
    },
    'peut_lancer_matching': {
        'label': 'Lancer le matching',
        'desc': 'Exécuter le processus de matching entre projets et intervenants.'
    },
    'peut_exporter_csv': {
        'label': 'Exporter CSV',
        'desc': 'Exporter des listes (clients, projets, etc.) au format CSV.'
    }
}

def normalize_hierarchies(db) -> bool:
    """Vérifie et réindexe les hiérarchies des rôles pour qu'elles soient une séquence 0..n-1.
    Retourne True si des modifications ont été effectuées.
    """
    try:
        roles = db.get_all_roles(sort_by='hierarchie')
        # Trier en plaçant les hiérarchies None à la fin, et conserver un ordre stable par role_id
        def _key(r):
            h = getattr(r, 'hierarchie', None)
            return (h is None, h if h is not None else 10**9, getattr(r, 'role_id', 0))

        sorted_roles = sorted(roles, key=_key)
        changed = False
        for idx, r in enumerate(sorted_roles):
            try:
                if getattr(r, 'hierarchie', None) != idx:
                    r.hierarchie = int(idx)
                    r.save()
                    changed = True
            except Exception:
                # si une sauvegarde échoue, on continue et on signale la modification partielle
                changed = True
        return changed
    except Exception:
        return False

@utilisateurs_bp.route('/utilisateurs/roles', methods=['GET'])
@flask_login_required
def roles():
    """Affiche la liste des rôles."""
    if not has_permission(current_user, 'peut_gerer_roles'):
        abort(403)

    db = get_db()
    # ensure hierarchies are normalized before rendering
    try:
        normalize_hierarchies(db)
    except Exception:
        pass
    roles = db.get_all_roles(sort_by="hierarchie")

    return render_template('utilisateurs/roles.html', roles=roles, permission_meta=PERMISSION_META, role=None)

@utilisateurs_bp.route('/utilisateurs/roles/<int:id>', methods=['GET'])
@flask_login_required
def role_detail(id: int):
    """Affiche le détail d'un rôle (réutilise le template principal en passant la variable `role`)."""
    if not has_permission(current_user, 'peut_gerer_roles'):
        print("User lacks permission to manage roles")
        print(f"Current user: {current_user}")
        print(f"User role: {getattr(current_user, 'role', None)}")
        abort(403)

    db = get_db()
    try:
        normalize_hierarchies(db)
    except Exception:
        pass
    roles = db.get_all_roles(sort_by="hierarchie")
    role = db.get_role_by_id(id)

    return render_template('utilisateurs/roles.html', roles=roles, role=role, permission_meta=PERMISSION_META)

# --- API JSON pour la gestion des rôles ---

@utilisateurs_bp.route('/api/utilisateurs/roles/<int:role_id>', methods=['GET'])
@flask_login_required
def get_role_json(role_id: int):
    if not has_permission(current_user, 'peut_gerer_roles'):
        abort(403)
    db = get_db()
    role = db.get_role_by_id(role_id)
    if role is None:
        return jsonify({'error': 'Rôle introuvable'}), 404
    return jsonify({'role': role.to_dict()}), 200


@utilisateurs_bp.route('/api/utilisateurs/roles', methods=['POST', 'PUT'])
@flask_login_required
def create_role_api():
    """Crée un nouveau rôle via JSON POST/PUT {nom, hierarchie, ...permissions} et renvoie le rôle créé."""
    if not has_permission(current_user, 'peut_gerer_roles'):
        return abort(403)
    db = get_db()
    data = request.get_json(force=True, silent=True) or {}
    name = data.get('nom')
    if not name or str(name).strip() == '':
        return jsonify({'error': 'Le nom du rôle est requis'}), 400

    # Préparer un dict avec toutes les clés de Role.FIELD_NAMES
    defaults: Dict[str, Any] = {f: None for f in Role.FIELD_NAMES}
    defaults['role_id'] = None
    defaults['nom'] = str(name).strip()

    # Pour sécurité, IGNORER toute hiérarchie fournie depuis le client ; calculer côté serveur
    try:
        existing = db.get_all_roles(sort_by='hierarchie')
        max_h = -1
        for r in existing:
            try:
                if r.hierarchie is not None and int(r.hierarchie) > max_h:
                    max_h = int(r.hierarchie)
            except Exception:
                continue
        defaults['hierarchie'] = max_h + 1
    except Exception:
        defaults['hierarchie'] = 0

    # permissions booléennes
    requested_permissions = []
    for key in Role.FIELD_NAMES:
        if key.startswith('peut_') or key == 'administrateur':
            v = data.get(key, False)
            if isinstance(v, str):
                v = v.lower() in ('1', 'true', 't', 'yes', 'y')
            else:
                v = bool(v)
            defaults[key] = v
            if v:
                requested_permissions.append(key)

    # Protection: s'assurer que le créateur ne peut pas attribuer des permissions qu'il ne possède pas
    forbidden = [p for p in requested_permissions if not has_permission(current_user, p)]
    if forbidden:
        return jsonify({'error': "Vous ne pouvez pas attribuer ces permissions: %s" % ", ".join(forbidden)}), 403

    try:
        role = Role(db, defaults)
        role.save()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Normaliser les hiérarchies pour éviter doublons ou trous (ex: 3,4,5,5)
    try:
        normalize_hierarchies(db)
        # recharger le rôle pour avoir la valeur correcte de hiérarchie
        role = db.get_role_by_id(role.role_id)
    except Exception:
        pass

    # Renvoyer également la liste actualisée des rôles pour mise à jour côté client
    try:
        roles = db.get_all_roles(sort_by='hierarchie')
        roles_list = [r.to_dict() for r in roles]
    except Exception:
        roles_list = []

    return jsonify({'role': role.to_dict(), 'roles': roles_list}), 201


@utilisateurs_bp.route('/api/utilisateurs/roles/<int:role_id>', methods=['POST'])
@flask_login_required
def update_role(role_id: int):
    """Met à jour les champs modifiables d'un rôle via JSON."""
    if not has_permission(current_user, 'peut_gerer_roles'):
        return abort(403)

    db = get_db()
    role = db.get_role_by_id(role_id)
    if role is None:
        return jsonify({'error': 'Rôle introuvable'}), 404

    # Empêcher la modification de son propre rôle
    try:
        if current_user and current_user.role and getattr(current_user.role, 'role_id', None) == getattr(role, 'role_id', None):
            return jsonify({'error': "Vous ne pouvez pas modifier votre propre rôle."}), 403
    except Exception:
        pass

    # Protection hiérarchique : on ne peut pas modifier un rôle plus élevé que soi
    try:
        current_hier = getattr(current_user.role, 'hierarchie', None)
        target_hier = getattr(role, 'hierarchie', None)
        if current_hier is not None and target_hier is not None and target_hier < current_hier:
            return jsonify({'error': 'Vous ne pouvez pas modifier un rôle supérieur au vôtre.'}), 403
    except Exception:
        pass

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'Données JSON attendues'}), 400

    # Champs autorisés à la modification
    allowed = {
        'nom',
        'administrateur', 'peut_gerer_utilisateurs', 'peut_gerer_roles',
        'peut_lire_clients', 'peut_gerer_clients', 'peut_creer_interactions', 'peut_gerer_interactions',
        'peut_lire_projets', 'peut_gerer_projets', 'peut_gerer_jalons', 'peut_assigner_intervenants',
        'peut_lire_intervenants', 'peut_modifier_intervenants', 'peut_acceder_documents', 'peut_gerer_competences',
        'peut_lancer_matching', 'peut_exporter_csv'
    }

    # If permissions are being changed, ensure the current user actually has those permissions
    requested_permissions = []
    for k, v in data.items():
        if k in allowed and (k == 'administrateur' or k.startswith('peut_')) and getattr(role, k, False) != bool(v):
            requested_permissions.append(k)

    forbidden = [p for p in requested_permissions if not has_permission(current_user, p)]
    if forbidden:
        return jsonify({'error': 'Vous ne pouvez pas modifier ces permissions: %s' % ", ".join(forbidden)}), 403

    changed = False
    for k, v in data.items():
        if k not in allowed:
            # explicitly ignore hierarchie or any other non-allowed fields
            continue
        # conversion de type simple
        elif k in ('administrateur',) or k.startswith('peut_'):
            # accepter true/false, 0/1, 'true'/'false'
            if isinstance(v, str):
                val = v.lower() in ('1', 'true', 't', 'yes', 'y')
            else:
                val = bool(v)
            setattr(role, k, val)
        else:
            setattr(role, k, v)
        changed = True

    if changed:
        try:
            role.save()
            # si la hiérarchie a été modifiée (ou pour nettoyer les doublons), normaliser
            normalize_hierarchies(db)
            role = db.get_role_by_id(role_id)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'role': role.to_dict()}), 200


@utilisateurs_bp.route('/api/utilisateurs/roles/<int:role_id>/delete', methods=['DELETE'])
@flask_login_required
def delete_role(role_id: int):
    if not has_permission(current_user, 'peut_gerer_roles'):
        return abort(403)
    db = get_db()
    role = db.get_role_by_id(role_id)
    if role is None:
        return jsonify({'error': 'Rôle introuvable'}), 404

    # Empêcher la suppression de son propre rôle
    try:
        if current_user and current_user.role and getattr(current_user.role, 'role_id', None) == getattr(role, 'role_id', None):
            return jsonify({'error': "Vous ne pouvez pas supprimer votre propre rôle."}), 403
    except Exception:
        pass

    # Protection hiérarchique : on ne peut pas supprimer un rôle supérieur à soi
    try:
        current_hier = getattr(current_user.role, 'hierarchie', None)
        target_hier = getattr(role, 'hierarchie', None)
        if current_hier is not None and target_hier is not None and target_hier < current_hier:
            return jsonify({'error': 'Vous ne pouvez pas supprimer un rôle supérieur au vôtre.'}), 403
    except Exception:
        pass

    try:
        role.delete()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    # réindexer après suppression
    try:
        normalize_hierarchies(db)
    except Exception:
        pass
    return jsonify({'message': 'Rôle supprimé'}), 200


@utilisateurs_bp.route('/api/utilisateurs/roles/reorder', methods=['POST'])
@flask_login_required
def reorder_roles():
    if not has_permission(current_user, 'peut_gerer_roles'):
        return abort(403)
    data = request.get_json(force=True, silent=True)
    if not data or 'order' not in data or not isinstance(data['order'], list):
        payload = {'error': 'Payload invalide, attendue: {order: [ids]}'}
        return Response(json.dumps(payload, ensure_ascii=False), status=400, mimetype='application/json')

    db = get_db()
    order = data['order']

    # Protection: empêcher qu'un rôle non-précédemment au-dessus du rôle de l'utilisateur
    # soit promu au-dessus de celui-ci par le reorder.
    try:
        # compute the current position index of the user's role among ordered roles
        try:
            # normalize hierarchies to ensure stable ordering
            try:
                normalize_hierarchies(db)
            except Exception:
                pass
            old_roles = db.get_all_roles(sort_by='hierarchie')
        except Exception:
            old_roles = []

        # build a map role_id -> index in old_roles
        old_index_map = {}
        for i, r in enumerate(old_roles):
            try:
                rid = getattr(r, 'role_id')
                # normalize to int for reliable comparisons
                try:
                    rid_key = int(rid)
                except Exception:
                    rid_key = rid
                old_index_map[rid_key] = i
            except Exception:
                continue

        # build a normalized id helper
        def norm_id(val):
            try:
                return int(val)
            except Exception:
                return str(val)

        # build old ordered list of normalized ids
        old_order_ids = []
        for r in old_roles:
            try:
                old_order_ids.append(norm_id(getattr(r, 'role_id')))
            except Exception:
                continue

        # determine current user's index in old_order_ids
        current_index = None
        try:
            cur_rid = getattr(current_user.role, 'role_id', None)
            if cur_rid is not None:
                cur_norm = norm_id(cur_rid)
                if cur_norm in old_order_ids:
                    current_index = old_order_ids.index(cur_norm)
        except Exception:
            current_index = None

        if current_index is None:
            payload = {'error': "Impossible de déterminer la position de votre rôle ; opération interdite."}
            return Response(json.dumps(payload, ensure_ascii=False), status=403, mimetype='application/json')

        # compute sets of ids above the user's role before and after
        old_above_set = set(old_order_ids[:current_index])
        new_order_norm = [norm_id(x) for x in order]
        new_above_set = set(new_order_norm[:current_index])

        # if any role is newly placed above the user's role, forbid
        promoted = new_above_set - old_above_set
        if promoted:
            payload = {'error': "Vous ne pouvez pas placer un rôle au-dessus de votre rôle."}
            return Response(json.dumps(payload, ensure_ascii=False), status=403, mimetype='application/json')
    except Exception:
        # si l'étape de vérification échoue, on continue avec l'opération (favoriser disponibilité);
        # cependant on ne laisse pas fuiter d'erreurs internes
        pass

    # NOTE: apply the new order (caller has permission)
    try:
        for idx, rid in enumerate(order):
            role = db.get_role_by_id(rid)
            if role is None:
                continue
            role.hierarchie = int(idx)
            role.save()
        # s'assurer que tout est bien séquentiel
        normalize_hierarchies(db)
    except Exception as e:
        payload = {'error': str(e)}
        return Response(json.dumps(payload, ensure_ascii=False), status=500, mimetype='application/json')

    payload = {'message': 'Ordre appliqué'}
    return Response(json.dumps(payload, ensure_ascii=False), status=200, mimetype='application/json')
