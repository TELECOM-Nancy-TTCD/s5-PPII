from flask import Blueprint, render_template, request, abort, redirect, url_for, flash
from flask_login import login_required, current_user
from typing import List
from datetime import datetime, timedelta

from tools import get_db, has_permission, hash_password
from database import Utilisateur

utilisateurs_bp = Blueprint('utilisateurs', __name__)

@utilisateurs_bp.route('/utilisateurs', methods=['GET'], endpoint='users')
@login_required
def utilisateurs():
    """Liste des users (même URL et endpoint que précédemment)."""
    recherche_utilisateurs = request.args.get("q", "").lower()

    if not has_permission(current_user, 'peut_lire_utilisateurs'):
        abort(403)

    db = get_db()
    if recherche_utilisateurs:
        def matches(u: Utilisateur):
            return (
                recherche_utilisateurs in u.nom.lower() or
                recherche_utilisateurs in u.prenom.lower() or
                recherche_utilisateurs in u.email.lower() or
                recherche_utilisateurs in u.role.nom.lower()
            )
        users: List[Utilisateur] = db.get_all_users(key=matches)
    else:
        users: List[Utilisateur] = db.get_all_users()

    return render_template("utilisateurs/utilisateurs.html", utilisateurs_db=users,
                           recherche_utilisateurs=recherche_utilisateurs)


@utilisateurs_bp.route('/utilisateurs/<int:uid>', endpoint='utilisateurs_detail')
@login_required
def utilisateurs_detail(uid: int):
    db = get_db()
    utilisateur = db.get_user_by_id(uid)
    if utilisateur is None:
        abort(404)

    if not has_permission(current_user, 'peut_lire_utilisateurs') and current_user.utilisateur_id != utilisateur.utilisateur_id:
        abort(403)

    comp_requises = db.cursor().execute(
        "SELECT c.nom, ic.niveau FROM competences c JOIN intervenant_competences ic ON c.competence_id = ic.competence_id WHERE ic.intervenant_id = ?",
        (uid,)).fetchall()

    peut_gerer_docs = has_permission(current_user, 'peut_gerer_documents')

    return render_template("utilisateurs/utilisateur_template.html", utilisateur=utilisateur,
                           competences_requises=comp_requises, peut_gerer_docs=peut_gerer_docs)


@utilisateurs_bp.route('/utilisateurs/<int:uid>/ajouter_comp', methods=['GET', 'POST'], endpoint='utilisateur_ajouter_competences')
@login_required
def utilisateur_ajouter_competences(uid: int):
    if not has_permission(current_user, 'peut_gerer_competences'):
        abort(403)

    if get_db().get_user_by_id(uid) is None:
        abort(404)

    c = get_db().cursor()
    c.execute("SELECT * FROM Competences ORDER BY competence_id ASC")
    toutes_competences = c.fetchall()
    success = False

    if request.method == "POST":
        comp_requises = list(map(int, request.form.getlist("skills[]")))
        niveaux = list(map(int, request.form.getlist("levels[]")))
        s = c.execute("SELECT competence_id FROM intervenant_competences WHERE intervenant_id=?", (uid,)).fetchall()
        for i in range(len(s)):
            s[i] = s[i][0]
        for i, u in enumerate(comp_requises):
            if u in s:
                continue
            s.append(u)
            niveau_associe = niveaux[i]
            c.execute("INSERT INTO intervenant_competences VALUES (?, ?, ?)", (uid, u, niveau_associe))
            get_db().commit()
        success = True

    return render_template("ajouter_competences.html", competences=toutes_competences, success=success)

@utilisateurs_bp.route('/utilisateurs/<int:user_id>/supprimer', methods=['POST'])
@login_required
def supprimer_utilisateur(user_id: int):
    if not has_permission(current_user, 'peut_gerer_utilisateurs'):
        abort(403)

    user = get_db().get_user_by_id(user_id)
    if not user:
        abort(404)

    try:
        user.delete()
        flash("Utilisateur supprimé avec succès.", "success")
    except Exception as e:
        flash(f"Erreur lors de la suppression: {str(e)}", "danger")

    return redirect(url_for("utilisateurs"))


@utilisateurs_bp.route('/utilisateurs/<int:utilisateur_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_utilisateur(utilisateur_id: int):
    db = get_db()
    utilisateur = db.get_user_by_id(utilisateur_id)
    if utilisateur is None:
        return abort(404)

    if not has_permission(current_user,'peut_gerer_utilisateurs') and utilisateur.utilisateur_id != current_user.utilisateur_id:
        return abort(403)

    if request.method == 'POST':
        errors = False
        if errors:
            return {'errors': errors}, 400

        email = request.form.get("email")
        nom = request.form.get("nom")
        prenom = request.form.get("prenom")
        role_id = request.form.get("role")
        est_intervenant = request.form.get("est_intervenant") == "True"
        heures_dispo_semaine = request.form.get("h_disp")
        doc_carte_vitale = request.form.get("doc_car")
        doc_cni = request.form.get("doc_cni")
        doc_adhesion = request.form.get("doc_adh")
        doc_rib = request.form.get("doc_rib")

        utilisateur.email = email
        utilisateur.nom = nom
        utilisateur.prenom = prenom

        utilisateur.role_id = role_id

        utilisateur.est_intervenant = est_intervenant
        if heures_dispo_semaine and heures_dispo_semaine.isdigit():
            utilisateur.heures_dispo_semaine = heures_dispo_semaine
        utilisateur.doc_carte_vitale = doc_carte_vitale
        utilisateur.doc_cni = doc_cni
        utilisateur.doc_adhesion = doc_adhesion
        utilisateur.doc_rib = doc_rib

        utilisateur.save()

        return redirect(url_for("utilisateurs_detail", uid=utilisateur.utilisateur_id))


    def match_role(r):
        """
        Exclut les rôles qui sont strictement supérieurs à celui de l'utilisateur courant.
        """
        return r.hierarchie >= current_user.role.hierarchie
    roles_possibles = get_db().get_all_roles(sort_by="hierarchie", key=match_role)

    return render_template("utilisateurs/edit_utilisateur.html", context={"roles_possibles": roles_possibles},
                           utilisateur=utilisateur, Utilisateur=Utilisateur)


@utilisateurs_bp.route('/utilisateurs/ajouter_comp', methods=['GET', 'POST'], endpoint='ajouter_competences')
@login_required
def ajouter_competences():
    if not has_permission(current_user, 'peut_gerer_competences'):
        abort(403)

    c = get_db().cursor()
    c.execute("SELECT * FROM Competences ORDER BY competence_id ASC")
    toutes_competences = c.fetchall()
    success = False

    if request.method == "POST":
        uid = request.form.get("uid")
        comp_requises = list(map(int, request.form.getlist("skills[]")))
        niveaux = list(map(int, request.form.getlist("levels[]")))
        s = c.execute("SELECT competence_id FROM intervenant_competences WHERE intervenant_id=?", (uid,)).fetchall()
        for i in range(len(s)):
            s[i] = s[i][0]
        for i, u in enumerate(comp_requises):
            if u in s:
                continue
            s.append(u)
            niveau_associe = niveaux[i]
            c.execute("INSERT INTO intervenant_competences VALUES (?, ?, ?)", (uid, u, niveau_associe))
            get_db().commit()
        success = True
        flash("Compétences ajoutées avec succès.", "success")
        return redirect(url_for("utilisateurs_detail", uid=uid))

    return render_template("ajouter_competences.html", competences=toutes_competences, success=success)


@utilisateurs_bp.route('/utilisateurs/creer', methods=['GET', 'POST'], endpoint='create_user')
@login_required
def creer_utilisateur():
    if not has_permission(current_user, 'peut_gerer_utilisateurs'):
        abort(403)

    user_added_successfully = False
    db = get_db()

    if request.method == 'POST':
        email = request.form.get("email")
        hmdp = hash_password(request.form.get("mdp"))
        date_expiration_mdp = (datetime.now() + timedelta(days=365)).date()
        nom = request.form.get("nom")
        prenom = request.form.get("prenom")
        avatar = None
        role_id = request.form.get("role")
        est_intervenant = "est_intervenant" in request.form
        heures_dispo_semaine = request.form.get("h_disp")
        doc_carte_vitale = request.form.get("doc_car")
        doc_cni = request.form.get("doc_cni")
        doc_adhesion = request.form.get("doc_adh")
        doc_rib = request.form.get("doc_rib")

        user = Utilisateur.from_db_row(db, (None, email, hmdp, date_expiration_mdp, nom, prenom, avatar, role_id, est_intervenant,
                   heures_dispo_semaine, doc_carte_vitale, doc_cni, doc_adhesion, doc_rib))
        user.save()
        user_added_successfully = True

    def match_role(r):
        """
        Exclut les rôles qui sont strictement supérieurs à celui de l'utilisateur courant.
        0: Grande hiérarchie = rôle le plus puissant
        Puis hiérarchie croissante = rôles de plus en plus limités
        """
        return r.hierarchie >= current_user.role.hierarchie
    roles_possibles = get_db().get_all_roles(sort_by="hierarchie", key=match_role)

    return render_template("utilisateurs/create_utilisateur.html",
                           context={"success": user_added_successfully, "roles_possibles": roles_possibles})

try:
    import utilisateurs.roles
except Exception:
    pass
