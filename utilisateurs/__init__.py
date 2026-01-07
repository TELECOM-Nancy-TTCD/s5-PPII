from flask import Blueprint, render_template, request, abort, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from typing import List
from datetime import datetime, timedelta

from tools import get_db, has_permission, hash_password
from database import Utilisateur

utilisateurs_bp = Blueprint('utilisateurs', __name__)

@utilisateurs_bp.route('/utilisateurs', methods=['GET'], endpoint='utilisateurs')
@login_required
def utilisateurs():
    """Liste des utilisateurs (même URL et endpoint que précédemment)."""
    recherche_utilisateurs = request.args.get("q", "").lower()

    conn = get_db().db  # récupérer la connexion sqlite depuis l'objet Database
    conn.row_factory = None
    # On exécute une requête simple en SQL pour minimiser les dépendances
    cur = conn.cursor()
    cur.execute("""SELECT u.*, r.nom AS role_nom
                      FROM Utilisateurs u
                               LEFT JOIN Roles r ON u.role_id = r.role_id""")
    utilisateurs_db = cur.fetchall()
    cur.close()

    if recherche_utilisateurs:
        def matches(u):
            try:
                nom = (u[4] or '') if len(u) > 4 else ''
                prenom = (u[5] or '') if len(u) > 5 else ''
                email = (u[1] or '') if len(u) > 1 else ''
                role_nom = (u[-1] or '') if len(u) > 0 else ''
                return (recherche_utilisateurs in nom.lower() or
                        recherche_utilisateurs in prenom.lower() or
                        recherche_utilisateurs in email.lower() or
                        (role_nom and recherche_utilisateurs in str(role_nom).lower()))
            except Exception:
                return False

        utilisateurs_db = [u for u in utilisateurs_db if matches(u)]

    return render_template("utilisateurs/utilisateurs.html", utilisateurs_db=utilisateurs_db,
                           recherche_utilisateurs=recherche_utilisateurs)


@utilisateurs_bp.route('/utilisateurs/<int:uid>', endpoint='utilisateurs_detail')
@login_required
def utilisateurs_detail(uid: int):
    db = get_db()
    utilisateur = db.get_user_by_id(uid)
    if utilisateur is None:
        abort(404)

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


@utilisateurs_bp.route('/utilisateurs/create', methods=['GET', 'POST'], endpoint='create_user')
@login_required
def create_user():
    if not has_permission(current_user, 'peut_gerer_utilisateurs'):
        abort(403)

    user_added_successfully = False
    db = get_db()

    if request.method == 'POST':
        email = request.form.get("e-mail")
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

    roles_possibles = get_db().get_all_roles(sort_by="hierarchie")

    return render_template("utilisateurs/create_utilisateur.html",
                           context={"success": user_added_successfully, "roles_possibles": roles_possibles})


@utilisateurs_bp.route('/utilisateurs/<int:user_id>/supprimer', methods=['POST'], endpoint='supprimer_utilisateur')
@login_required
def supprimer_utilisateur(user_id: int):
    if not has_permission(current_user, 'administrateur'):
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


@utilisateurs_bp.route('/utilisateurs/<int:utilisateur_id>/edit', methods=['GET', 'POST'], endpoint='edit_utilisateur')
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
            return jsonify({'errors': errors}), 400

        email = request.form.get("e-mail")
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

    roles_possibles = get_db().get_all_roles(sort_by="hierarchie")

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


@utilisateurs_bp.route('/utilisateurs/creer', methods=['GET', 'POST'], endpoint='creer_utilisateur')
@login_required
def creer_utilisateur():
    if not has_permission(current_user, 'peut_gerer_utilisateurs'):
        abort(403)

    user_added_successfully = False
    db = get_db()

    if request.method == 'POST':
        email = request.form.get("e-mail")
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

    roles_possibles = get_db().get_all_roles(sort_by="hierarchie")

    return render_template("utilisateurs/create_utilisateur.html",
                           context={"success": user_added_successfully, "roles_possibles": roles_possibles})


@utilisateurs_bp.route('/utilisateurs/<int:user_id>/supprimer_utilisateur', methods=['POST'], endpoint='supprimer_utilisateur_explicite')
@login_required
def supprimer_utilisateur_explicite(user_id: int):
    if not has_permission(current_user, 'administrateur'):
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


@utilisateurs_bp.route('/utilisateurs/<int:utilisateur_id>/edit_utilisateur', methods=['GET', 'POST'], endpoint='edit_utilisateur_explicite')
@login_required
def edit_utilisateur_explicite(utilisateur_id: int):
    db = get_db()
    utilisateur = db.get_user_by_id(utilisateur_id)
    if utilisateur is None:
        return abort(404)

    if not has_permission(current_user,'peut_gerer_utilisateurs') and utilisateur.utilisateur_id != current_user.utilisateur_id:
        return abort(403)

    if request.method == 'POST':
        errors = False
        if errors:
            return jsonify({'errors': errors}), 400

        email = request.form.get("e-mail")
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

    roles_possibles = get_db().get_all_roles(sort_by="hierarchie")

    return render_template("utilisateurs/edit_utilisateur.html", context={"roles_possibles": roles_possibles},
                           utilisateur=utilisateur, Utilisateur=Utilisateur)


try:
    import utilisateurs.roles
except Exception:
    pass
