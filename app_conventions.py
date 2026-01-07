from flask import Blueprint, render_template, request, abort, flash
from flask_login import login_required, current_user

from dotenv import load_dotenv

from database import Convention, Projet
from tools import get_db, has_permission

conventions_bp = Blueprint('conventions', __name__, url_prefix='/conventions')

load_dotenv()


def get_projets_by_convention(id_convention):
    c = get_db().cursor()
    c.execute("SELECT * FROM Projets WHERE convention_id= ?", (id_convention,))
    projets = []
    for projet in c.fetchall():
        projets.append({"id": projet[0], "convention_id": projet[1],
                        "nom_projet": projet[2], "description": projet[3],
                        "budget": projet[4], "date_debut": projet[6],
                        "date_fin": projet[7], "statut": projet[8],
                        "doc_dossier": projet[9]})
    return projets


def get_client(id):
    c = get_db().cursor()
    c.execute("SELECT * FROM Clients WHERE client_id=?", (id,))
    for client in c.fetchall():
        return {"id": client[0], "nom_entreprise": client[1],
                "contact_nom": client[2], "contact_email": client[3],
                "contact_telephone": client[4], "type_client": client[5],
                "interlocuteur_principal": client[6], "localisation_lat": client[7],
                "localisation_lng": client[8], "addresse": client[9]}
    return {}


def get_convention(id):
    c = get_db().cursor()
    c.execute("SELECT * FROM Conventions WHERE convention_id=?", (id,))
    for convention in c.fetchall():
        return {"id": convention[0], "nom": convention[1],
                "description": convention[2], "date_debut": convention[3],
                "date_fin": convention[4], "doc_contract": convention[5],
                "client_id": convention[6], "nom_client": get_client(convention[6])["nom_entreprise"]}
    return {}


def liste_conventions():
    c = get_db().cursor()
    c.execute("SELECT * FROM Conventions")
    conventions = []
    for convention in c.fetchall():
        conventions.append(get_convention(convention[0]))
    return conventions


def get_utilisateur(id):
    c = get_db().cursor()
    c.execute("SELECT utilisateur_id,nom,prenom FROM Utilisateurs WHERE utilisateur_id=?", (id,))
    for utilisateur in c.fetchall():
        return {"id": utilisateur[0], "nom": utilisateur[1], "prenom": utilisateur[2]}
    return {}


@conventions_bp.route('/', methods=['GET'])
@login_required
def index():
    recherche_conventions = request.args.get("q", "").lower().strip()

    db = get_db()

    if recherche_conventions:
        def match_convention(c):
            return (recherche_conventions in (c.nom or "").lower()
                    or recherche_conventions in (c.date_debut or "").lower()
                    or recherche_conventions in (c.date_fin or "").lower()
                    or recherche_conventions in (c.nom_client or "").lower())

        conventions = db.get_all_conventions(key=match_convention)
    else:
        conventions = db.get_all_conventions()

    peut_gerer_csv = has_permission(current_user, 'peut_exporter_csv')

    return render_template('conventions/liste_conventions.html', context=conventions,
                           recherche_conventions=recherche_conventions, peut_gerer_csv=peut_gerer_csv)


@conventions_bp.route('/<int:id>')
@login_required
def convention(id: int):
    db = get_db()
    conv = db.get_convention_by_id(id)
    if conv is None:
        abort(404)
    client = conv.client
    return render_template('conventions/convention_template.html', context={"convention": conv,
                                                                            "client": client, "projets": conv.projets,
                                                                            "utilisateur": client.interlocuteur_principal})


# Oui cette fonction est ici pour raison de facilité, je souhaiterais que quelqu'un la bouge dans les conventions si possible
@conventions_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_convention():
    if not has_permission(current_user, 'peut_gerer_projets'):
        abort(403)

    added_successfully = False
    db = get_db()

    if request.method == 'POST':
        e = request.form
        l = [None]
        for i in e.keys():
            l.append(e[i])

        l = tuple(l)

        # Insertion de None = NULL dans la colonne primary key l'autoincrément est automatique
        conv = Convention.from_db_row(db, l)
        if conv.date_debut > conv.date_fin:
            flash("Date de fin invalide", 'danger')
            return render_template("conventions/create_convention.html",
                                   context={"success": added_successfully, "clients": db.get_all_clients()})
        else:
            conv.save()

        added_successfully = True

    # Obtention des clients possibles
    clients = db.get_all_clients()

    return render_template("conventions/create_convention.html",
                           context={"success": added_successfully, "clients": clients})


# Création d'un projet pour une convention
@conventions_bp.route("/<int:convention_id>/create_projet", methods=["GET", "POST"])
@login_required
def create_projet_convention(convention_id):
    if not has_permission(current_user, 'peut_gerer_projets'):
        abort(403)

    projet = get_db().get_convention_by_id(convention_id)
    # Tentative d'entrée de projet sur une convention qui n'existe pas
    if projet == None:
        abort(404)

    added_successfully = False
    db = get_db()

    if request.method == 'POST':
        e = request.form
        l = [None, convention_id]
        for i in e.keys():
            l.append(e[i])

        l = tuple(l)

        projet = Projet.from_db_row(db, l)

        # Vérification de la contrainte de date
        if projet.date_debut > projet.date_fin:
            flash("Date de fin invalide", 'danger')
        else:
            # Insertion de None = NULL dans la colonne primary key l'autoincrément est automatique
            projet.save()

            added_successfully = True

    return render_template("conventions/create_projet.html",
                           context={"success": added_successfully, "default_convention": projet})
