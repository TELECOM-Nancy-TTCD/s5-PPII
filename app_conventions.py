from flask import Blueprint, render_template, request, abort
from flask_login import login_required

from dotenv import load_dotenv

from tools import get_db


conventions_bp = Blueprint('conventions',__name__,url_prefix='/conventions')


load_dotenv()

def get_projets_by_convention(id_convention):
    c = get_db().cursor()
    c.execute("SELECT * FROM Projets WHERE convention_id= ?",(id_convention,))
    projets = []
    for projet in c.fetchall():
        projets.append( {"id":projet[0],"convention_id":projet[1],
                "nom_projet":projet[2],"description":projet[3],
                "budget":projet[4],"date_debut":projet[5],
                "date_fin":projet[6],"statut":projet[7],
                "doc_dossier":projet[8]})
    return projets

def get_client(id):
    c = get_db().cursor()
    c.execute("SELECT * FROM Clients WHERE client_id=?", (id,))
    for client in c.fetchall():
        return {"id":client[0],"nom_entreprise":client[1],
                "contact_nom":client[2],"contact_email":client[3],
                "contact_telephone":client[4],"type_client":client[5],
                "interlocuteur_principal":client[6],"localisation_lat":client[7],
                "localisation_lng":client[8],"addresse":client[9]}
    return {}

def get_convention(id):
    c = get_db().cursor()
    c.execute("SELECT * FROM Conventions WHERE convention_id=?",(id,))
    for convention in c.fetchall():
        return {"id":convention[0],"nom":convention[1],
                "description":convention[2],"date_debut":convention[3],
                "date_fin":convention[4],"doc_contract":convention[5],
                "client_id":convention[6],"nom_client":get_client(convention[6])["nom_entreprise"] }
    return {}

def liste_conventions():
    c = get_db().cursor()
    c.execute("SELECT * FROM Conventions")
    conventions = []
    for convention in c.fetchall():
        conventions.append( get_convention( convention[0] )   )
    return conventions

def get_utilisateur(id):
    c = get_db().cursor()
    c.execute("SELECT utilisateur_id,nom,prenom FROM Utilisateurs WHERE utilisateur_id=?",(id,))
    for utilisateur in c.fetchall():
        return {"id":utilisateur[0],"nom":utilisateur[1],"prenom":utilisateur[2]}
    return {}

@conventions_bp.route('/', methods=['GET'])
@login_required
def index():
    recherche_conventions = request.args.get("q", "").lower().strip()

    conventions = liste_conventions()

    if recherche_conventions:
        conventions = [
            c for c in conventions
            if (recherche_conventions in (c["nom"] or "").lower()
                or recherche_conventions in (c["date_debut"] or "").lower()
                or recherche_conventions in (c["date_fin"] or "").lower()
                or recherche_conventions in (c["nom_client"] or "").lower())
        ]

    # Crée un dictionnaire : clé = id de la convention, valeur = liste des projets
    proj_associes_dict = {c["id"]: get_projets_by_convention(c["id"]) for c in conventions}

    return render_template( 'liste_conventions.html',context=conventions, pj_as=proj_associes_dict, recherche_conventions=recherche_conventions)


@conventions_bp.route('/<int:id>')
@login_required
def convention(id : int) :
    conv =  get_convention(id)
    client = get_client( conv["client_id"] )
    return render_template('convention_template.html',context={"convention":conv, 
    "client":get_client( conv["client_id"] ) , "projets": get_projets_by_convention(id), "utilisateur" : get_utilisateur(client["interlocuteur_principal"]) } 
    )
