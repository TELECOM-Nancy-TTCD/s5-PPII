from typing import cast, Literal

from flask import Flask, Response, render_template, send_file, abort, redirect, url_for, flash, g, request, session
from flask_login import LoginManager, login_user, login_required, current_user, logout_user

from app_conventions import conventions_bp
from hashlib import scrypt
from datetime import datetime, timedelta
from dotenv import load_dotenv

import os, csv, io

load_dotenv()
DATABASE= os.getenv('DATABASE')

import os, base64, sqlite3
from tools import get_db, has_permission

# Importation des blueprints
from interactions import interactions_bp
from clients import clients_bp
from utilisateurs import bp_utilisateurs
import matching




def get_clients():
    """Fonction qui renvoie tout les clients de la DB"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Clients")
    clients = cursor.fetchall()
    conn.close()

    return clients

def get_utilisateurs():
    """Fonction qui renvoie tout les utilisateurs de la DB"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Utilisateurs")
    utilisateurs = cursor.fetchall()
    conn.close()

    return utilisateurs


def format_date(date_value):
    """Fonction qui change le format de la date en un format date classique sous forme de str"""
    if not date_value:
        return ""
    if isinstance(date_value, str):
        try:
            return datetime.fromisoformat(date_value).strftime("%d/%m/%Y")
        except ValueError:
            return datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
    if isinstance(date_value, (datetime,)):
        return date_value.strftime("%d/%m/%Y")

    return str(date_value)


app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Clé pour l'encodage des cookies de session
app.secret_key = os.getenv('SECRET_KEY', b'6031f03d38eede6a7a9c5827a0bd25e418a0d236abf4665cc7c23c7249c36867')


# Blueprints are registered here
app.register_blueprint(conventions_bp)
app.register_blueprint(interactions_bp)
app.register_blueprint(clients_bp)
app.register_blueprint(bp_utilisateurs)

def hash_password(mdp : str):
    """Fonction qui hash et sale le mot de passe,
    Les 16 premiers octets sont le salt, le reste le mdp."""
    salt = os.urandom(16) # Génération d'un salt

    mdp_hache = scrypt(mdp.encode(), salt=salt, n=2**14, r=8, p=1) # Hachage du mdp avec le salt

    # Encodage en B64, et remise en forme texte pour stockage.
    return base64.b64encode(salt+mdp_hache).decode()

def verify_password(mdp_entre : str, stored_hash):
    """Fonction qui vérifie le mot de passe avec le hashé. \n
    Il est impossible de revenir au mdp depuis le hash,donc on hache l'entrée avec le même salt et on vérifie l'égalité \n
    Le résultat est un booléen"""

    octets_decodes = base64.b64decode(stored_hash) # Bytes obtenus par décodage en B64
    salt = octets_decodes[:16]

    mdp_hache_stocke = octets_decodes[16:]
    mdp_hache_entre = scrypt(mdp_entre.encode(), salt=salt, n=2**14, r=8, p=1) # Hachage du mdp avec le salt

    return mdp_hache_entre == mdp_hache_stocke



@login_manager.user_loader
def load_user(uid : str):
    """Fonction qui charge l'utilisateur"""
    return get_db().get_user_by_id(int(uid))

@app.route("/login", methods = ["GET", "POST"])
def login():
    """Fonction pour la route /login \n
    Renvoie les page pour le login et vérifie le mdp"""
    has_failed_login = False

    if request.method == 'POST' :
        c = get_db().cursor()
        adressemail = request.form["Adresse e-mail"]
        mdp = request.form["Mot de passe"]
        c.execute("SELECT utilisateur_id, mot_de_passe_hashed FROM Utilisateurs WHERE email = ?", (adressemail,))

        corresp = c.fetchone()
        has_failed_login = False
        if corresp != None: # Si on trouve un utilisateur avec cet email
            if verify_password(mdp, corresp[1]):

                to_login = corresp[0]
                # Récupérer explicitement l'instance Utilisateur via le wrapper Database
                user = get_db().get_user_by_id(to_login)
                if user is None:
                    has_failed_login = True
                else:
                    login_user(user)  # On login l'utilisateur (instance compatible Flask-Login)

                    # Redirection sûre : si `next` absent, aller à l'accueil
                    next_page = request.args.get("next")
                    if not next_page:
                        return redirect(url_for("accueil"))
                    # TODO: Rendre sage la redirection "next" pour éviter les attaques open redirect
                    return redirect(next_page)


        has_failed_login = True # Si pas d'utilisateur avec ce mail ou que le mdp est faux, on a raté le login

    # Pour un login échouant, on ré-affiche la page avec un message supplémentaire
    # Pour le premier affichage, has_failed_login est à False.
    return render_template('Pages_speciales/login_page.html', has_failed_login=has_failed_login)


@app.route("/")
def accueil():
    """Fonction pour la route / \n
    C'est la fonction de la page d'accueil"""

    return render_template("accueil.html")


# Oui cette fonction est ici pour raison de facilité, je souhaiterais que quelqu'un la bouge dans les conventions si possible
@app.route("/convention/create", methods=["GET", "POST"])
@login_required
def create_convention():

    if not has_permission(current_user, 'peut_gerer_projets'):
        abort(403)

    added_successfully= False
    c = get_db().cursor()


    if request.method == 'POST' :
        e = request.form
        l=[None]
        for i in e.keys() :
            l.append(e[i])
        
        l=tuple(l)

        #Insertion de None = NULL dans la colonne primary key l'autoincrément est automatique
        c.execute("INSERT INTO Conventions VALUES (?, ?, ?, ?, ?, ?, ?)", l)
        get_db().commit()

        added_successfully = True

    #Obtention des clients possibles
    clients = get_db().get_all_clients()
    
    return render_template("create_convention.html", context={"success":added_successfully, "clients": clients})

# Création d'un projet pour une convention
@app.route("/convention/<int:convention_id>/create_projet", methods=["GET", "POST"])
@login_required
def create_projet_convention(convention_id):

    if not has_permission(current_user, 'peut_gerer_projets'):
        abort(403)

    conv = get_db().get_convention_by_id(convention_id)
    #Tentative d'entrée de projet sur une convention qui n'existe pas
    if conv == None:
        abort(404)


    added_successfully= False
    c = get_db().cursor()


    if request.method == 'POST' :
        e = request.form
        l=[None, convention_id]
        for i in e.keys() :
            l.append(e[i])
        
        l=tuple(l)

        # Vérification de la contrainte de date
        if l[5] > l[6] :
            flash("Date de fin invalide", 'danger')
        else:

            #Insertion de None = NULL dans la colonne primary key l'autoincrément est automatique
            c.execute("INSERT INTO Projets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", l)
            get_db().commit()

            added_successfully = True

     
    return render_template("create_projet.html", context={"success":added_successfully, "default_convention": conv })


# Création de projet depuis la page de liste de conventions (il faut alors spécifier la convention)
@app.route("/create_projet", methods=["GET", "POST"])
@login_required
def create_projet_sans_convention_connue():

    if not has_permission(current_user, 'peut_gerer_projets'):
        abort(403)

    added_successfully= False
    c = get_db().cursor()


    if request.method == 'POST' :
        e = request.form
        l=[None]
        for i in e.keys() :
            l.append(e[i])
        
        l=tuple(l)
        
        # Vérification de la contrainte de date
        if l[5] > l[6] :
            flash("Date de fin invalide", 'danger')
        else:

            #Insertion de None = NULL dans la colonne primary key l'autoincrément est automatique
            c.execute("INSERT INTO Projets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", l)
            get_db().commit()

            added_successfully = True

    conventions = get_db().get_all_conventions()
    
    return render_template("create_projet.html", context={"success":added_successfully, "list_conv": conventions })


@app.route("/clients", methods=['GET'])
@login_required
def clients():
    """Fonction pour la route /clients \n
    Permet d'afficher la page avec la liste des clients"""
    # Permet de récuperer le champs de recherche de la page
    recherche_clients = request.args.get("q", "").lower()

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Clients")
    clients_db = cursor.fetchall()
    conn.close()

    # Pour match tout les attribut qui pourraient coller dans la barre de recherche
    if recherche_clients:
        clients_db = [
            u for u in clients_db
            if recherche_clients in u["nom_entreprise"].lower()
            or recherche_clients in u["contact_email"].lower()
            or recherche_clients in u["type_client"].lower()
        ]

    liste_interloc_principaux = []
    db = get_db()
    for c in clients_db :
        # Bon affichage de l'interlocuteur principal
        interlocuteur =db.get_user_by_id(c[6])
        affichage_interlocuteur = interlocuteur.nom + " " + interlocuteur.prenom
        liste_interloc_principaux.append(affichage_interlocuteur)

    return render_template("clients.html", clients_db=clients_db, recherche_clients=recherche_clients, affichage_int = liste_interloc_principaux)


@app.route("/clients/<int:client_id>")
@login_required
def client_detail(client_id):
    """Fonction pour la route /clients/id_client \n
    Affiche la page dédié à un client, ses projets, ses interaction et l'avancement des projets"""

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM Clients WHERE client_id = ?", (client_id,))
    client = c.fetchone()
    if client is None:
        abort(404)
    
    # Bon affichage de l'interlocuteur principal
    interlocuteur =get_db().get_user_by_id(client[6])
    affichage_interlocuteur = interlocuteur.nom + " " + interlocuteur.prenom

    c.execute("""SELECT p.* FROM Projets p JOIN Conventions c ON p.convention_id = c.convention_id WHERE c.client_id = ?""", (client_id,))


    projets_raw = c.fetchall()

    # Calcul du pourcentage de jalon terminés
    projets = []
    for p in projets_raw:

        c.execute("SELECT est_complete FROM Jalons WHERE projet_id = ?", (p["projet_id"],))
        jalons = c.fetchall()
        total_jalons = len(jalons)
        jalons_termines = sum(1 for j in jalons if j["est_complete"])
        progress = int((jalons_termines / total_jalons) * 100) if total_jalons > 0 else 0

        projets.append({
            "projet_id": p["projet_id"],
            "nom_projet": p["nom_projet"],
            "statut": p["statut"],
            "progress": progress
        })

    c.execute("""
        SELECT i.*, u.nom || ' ' || u.prenom AS utilisateur_nom FROM Interactions i
        JOIN Utilisateurs u ON i.utilisateur_id = u.utilisateur_id WHERE i.client_id = ?
        ORDER BY i.date_time_interaction DESC
    """, (client_id,))

    interactions = c.fetchall()
    conn.close()

    return render_template("Pages_speciales/clients_template.html", client=client, projets=projets, interactions=interactions, inter = affichage_interlocuteur)


@app.route("/client/create", methods=["GET", "POST"])
@login_required
def create_client():
    """Fonction pour la route /client/create \n
    C'est la page pour creer un nouveau client"""
    if not has_permission(current_user, 'peut_gerer_clients'):
        abort(403)

    client_added_successfully= False
    c = get_db().cursor()


    if request.method == 'POST' :
        nom_e= request.form["nom_entreprise"]
        nom_c = request.form["contact_nom"]
        email = request.form["contact_email"]
        phone = request.form["contact_telephone"] 
        type = request.form["type_client"]
        interlocuteur = request.form["interlocuteur"]
        lat = request.form["loc_lat"]
        lng = request.form["loc_lng"]
        addr = request.form["address"]

        #Insertion de None = NULL dans la colonne primary key l'autoincrément est automatique
        c.execute("INSERT INTO Clients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",(None, nom_e, nom_c, email, phone, type, interlocuteur, lat, lng, addr))
        get_db().commit()

        client_added_successfully = True

    #Obtention des interlocuteurs possibles
    interlocuteurs_dispo = get_db().get_all_users(sort_by='nom')
    
    return render_template("create_client.html", context={"success":client_added_successfully, "interlocuteurs": interlocuteurs_dispo})


@app.route("/import_clients", methods=["POST"])
def import_clients():
    """Fonction pour la route /import_clients \n
    Permet la gestion du bouton d'import de client sur la page des clients \n
    Cette focntion gère les erreur de csv, et import dans la db les données du csv si elle sont correctes"""

    fichier = request.files.get("fichier")

    if not fichier:
        return "Aucun fichier sélectionné", 400

    try:
        lines = fichier.stream.read().decode("utf-8").splitlines()
        reader = csv.DictReader(lines, delimiter=";")

        colonnes_attendues = [
            "nom_entreprise",
            "contact_nom",
            "contact_email",
            "contact_telephone",
            "type_client",
            "interlocuteur_principal_id",
            "localisation_lat",
            "localisation_lng",
            "address"
        ]

        if reader.fieldnames != colonnes_attendues:
            return "Format CSV invalide (colonnes incorrectes)", 400

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        for row in reader:
            def clean(val):
                return val.strip() if val and val.strip() != "" else None

            c.execute("""
                INSERT INTO Clients (
                    nom_entreprise,
                    contact_nom,
                    contact_email,
                    contact_telephone,
                    type_client,
                    interlocuteur_principal_id,
                    localisation_lat,
                    localisation_lng,
                    address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                clean(row["nom_entreprise"]),
                clean(row["contact_nom"]),
                clean(row["contact_email"]),
                clean(row["contact_telephone"]),
                clean(row["type_client"]),
                int(row["interlocuteur_principal_id"]) if clean(row["interlocuteur_principal_id"]) else None,
                float(row["localisation_lat"]) if clean(row["localisation_lat"]) else None,
                float(row["localisation_lng"]) if clean(row["localisation_lng"]) else None,
                clean(row["address"]),
            ))

        conn.commit()
        conn.close()

        return redirect(url_for("clients"))

    except Exception as e:
        return f"Erreur import CSV : {e}", 500


@app.route("/export_clients")
@login_required
def export_clients():
    """Fonction pour la route /export_clients \n
    Permet d'utiliser le bouton d'export de la page des clients \n
    La fonction crée un csv, va récuperer les données de la DB et télécharge le fichier"""

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT
            client_id,
            nom_entreprise,
            contact_nom,
            contact_email,
            contact_telephone,
            type_client,
            interlocuteur_principal_id,
            localisation_lat,
            localisation_lng,
            address
        FROM Clients
    """)
    clients = c.fetchall()
    conn.close()

    # On indique que l'on utilisera le délimiteur ";"
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "client_id",
        "nom_entreprise",
        "contact_nom",
        "contact_email",
        "contact_telephone",
        "type_client",
        "interlocuteur_principal_id",
        "localisation_lat",
        "localisation_lng",
        "address"
    ])

    for cl in clients:
        writer.writerow([
            cl["client_id"],
            cl["nom_entreprise"],
            cl["contact_nom"],
            cl["contact_email"],
            cl["contact_telephone"],
            cl["type_client"],
            cl["interlocuteur_principal_id"],
            cl["localisation_lat"],
            cl["localisation_lng"],
            cl["address"]
        ])

    output.seek(0)

    # Télécharge le fichier
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name="clients_export.csv"
    )


@app.route("/projet/<int:projet_id>")
@login_required
def projet_detail(projet_id):
    """Fonction pour la route /projet/id_projet \n
    Affiche la page dédiée à un projet"""

    db = get_db()
    projet = db.get_project_id(projet_id)
    if projet is None:
        abort(404)

    projet.date_debut = format_date(projet.date_debut)
    projet.date_fin = format_date(projet.date_fin)
    for j, u in enumerate(projet.jalons):
        if u.date_fin is not None:
            projet.jalons[j].date_fin = datetime.fromisoformat(u.date_fin).strftime("%d/%m/%Y")

    comp_requises = db.cursor().execute(
        "SELECT c.nom, pc.niveau_requis FROM competences c "
        "JOIN projet_competences pc ON c.competence_id = pc.competence_id "
        "WHERE pc.projet_id = ?",
        (projet_id,)
    ).fetchall()

    matching.db = db
    groupes_bruts = matching.best_composition(projet_id)

    rows = db.cursor().execute(
        "SELECT utilisateur_id FROM Travaille_sur WHERE projet_id = ?",
        (projet_id,)
    ).fetchall()
    utilisateurs_affectes = {r[0] for r in rows}

    utilisateurs = db.cursor().execute(
        "SELECT utilisateur_id, prenom, nom FROM Utilisateurs"
    ).fetchall()
    id_to_nom = {u[0]: f"{u[1]} {u[2]}" for u in utilisateurs}

    groupes = []

    for g in groupes_bruts:
        membres_ids = g[0]
        score = g[1] if len(g) > 1 else None
        groupes.append({
            "ids": membres_ids,
            "noms": [id_to_nom.get(uid, f"Utilisateur {uid}") for uid in membres_ids],
            "selectionne": all(uid in utilisateurs_affectes for uid in membres_ids),
            "score": score
        })

    if utilisateurs_affectes and not any(g["selectionne"] for g in groupes):
        groupes.append({
            "ids": list(utilisateurs_affectes),
            "noms": [id_to_nom.get(uid, f"Utilisateur {uid}") for uid in utilisateurs_affectes],
            "selectionne": True
        })

    return render_template(
        "Pages_speciales/projets_template.html",
        projet=projet,
        competences_requises=comp_requises,
        groupes=groupes
    )

@app.route("/projet/<int:projet_id>/selectionner_groupe", methods=["POST"])
@login_required
def selectionner_groupe(projet_id):
    """Fonction qui sert à la selections de l'algorithme de matching"""
    db = get_db()

    groupe_ids_str = request.form.get("groupe_ids", "")
    if not groupe_ids_str:
        flash("Aucun groupe sélectionné.", "error")
        return redirect(url_for("projet_detail", projet_id=projet_id))

    utilisateur_ids = [int(uid) for uid in groupe_ids_str.split(",")]

    db.cursor().execute("DELETE FROM Travaille_sur WHERE projet_id = ?", (projet_id,))
    db.commit()

    for uid in utilisateur_ids:
        db.cursor().execute(
            "INSERT INTO Travaille_sur (utilisateur_id, projet_id) VALUES (?, ?)",
            (uid, projet_id)
        )
    db.commit()

    flash("Groupe sélectionné avec succès.", "success")
    return redirect(url_for("projet_detail", projet_id=projet_id))


@app.route("/projet/<int:projet_id>/ajouter_membres", methods=["GET", "POST"])
@login_required
def ajouter_membres(projet_id):
    """Fonction vers la route projet/id_projet/ajouter_membres \n
    Sert à ajouter des membres manuellement à un projet"""
    db = get_db()

    projet = db.get_project_id(projet_id)
    if projet is None:
        abort(404)

    if request.method == "POST":
        ids_str = request.form.get("utilisateur_ids", "")
        if not ids_str:
            flash("Veuillez entrer au moins un ID d'utilsateur.", "error")
            return redirect(url_for("ajouter_membres", projet_id=projet_id))

        utilisateur_ids = [int(uid.strip()) for uid in ids_str.split(",") if uid.strip().isdigit()]

        if not utilisateur_ids:
            flash("IDs invalides.", "error")
            return redirect(url_for("ajouter_membres", projet_id=projet_id))


        db.cursor().execute("DELETE FROM Travaille_sur WHERE projet_id = ?", (projet_id,))
        db.commit()

        for uid in utilisateur_ids:
            db.cursor().execute(
                "INSERT INTO Travaille_sur (utilisateur_id, projet_id) VALUES (?, ?)",
                (uid, projet_id)
            )
        db.commit()

        flash("Nouveau groupe créé avec succès.", "success")
        return redirect(url_for("projet_detail", projet_id=projet_id))

    utilisateurs = db.cursor().execute(
        "SELECT utilisateur_id, prenom, nom FROM Utilisateurs ORDER BY utilisateur_id"
    ).fetchall()

    return render_template("ajouter_membres.html", projet=projet, utilisateurs=utilisateurs)


@app.route("/projet/<int:projet_id>/ajouter_comp", methods=["GET", "POST"])
@login_required
def projet_ajouter_competences(projet_id):
    '''
    Fonction pour ajouter des compétences à un projet
    '''

    if not has_permission(current_user, 'peut_gerer_competences'):
        abort(403)

    if get_db().get_project_id(projet_id) is None:
        abort(404)

    c = get_db().cursor()
    c.execute("SELECT * FROM Competences ORDER BY competence_id ASC")
    toutes_competences = c.fetchall()
    success=False

    if request.method== "POST":
        comp_requises = list(map(int, request.form.getlist("skills[]")))
        niveaux = list(map(int, request.form.getlist("levels[]")))
        s = c.execute("Select competence_id from projet_competences where projet_id=?", (projet_id,)).fetchall()
        for i in range(len(s)):
            s[i]=s[i][0]
        print(s)
        for i, u in enumerate(comp_requises):
            # Si la compétence est déjà dedans, on skip
            if u in s:
                continue

            s.append(u)
            niveau_associe = niveaux[i]
            c.execute("INSERT INTO projet_competences VALUES (?, ?, ?)", (projet_id, u, niveau_associe))
            get_db().commit()

        success= True


    return render_template("ajouter_competences.html", competences=toutes_competences, success=success )


@app.post("/projet/<int:projet_id>/terminer")
@login_required
def terminer_projet(projet_id):
    """Fonction pour la route projet/id_projet/terminer \n
    Permet de gerer le bouton de fin de projet et de modifier la DB en conséquence"""

    projet = get_db().get_project_id(projet_id)

    if projet == None:
        abort(404)

    # Conversion des dates vers le format usuel
    projet.date_debut = format_date(projet.date_debut)
    projet.date_fin = format_date(projet.date_fin)

    for j, u in enumerate(projet.jalons):
        if u.date_fin!= None :
            projet.jalons[j].date_fin = datetime.fromisoformat(u.date_fin).strftime("%d/%m/%Y")
    projet = get_db().get_project_id(projet_id)

    if projet is None:
        abort(404)

    projet.statut = "Terminé"
    projet.save()

    try:
        get_db().redis_client.delete(f"projets:{projet_id}")

    except Exception:
        pass

    return redirect(url_for("projet_detail", projet_id=projet_id))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("accueil"))

@app.post("/jalon/<int:jalon_id>/modifier")
@login_required
def modifier_jalon(jalon_id):
    """Fonction pour la route /jalon/jalon_id/modifier \n
    Sert pour la pop up de modification des jalons"""
    db = get_db()

    row = db.execute(
        "SELECT projet_id FROM Jalons WHERE jalon_id = ?",
        (jalon_id,)
    ).fetchone()

    if not row:
        abort(404)

    projet_id = row[0]

    description = request.form.get("description")
    date_fin = request.form.get("date_fin") or None
    est_complete = 1 if request.form.get("est_complete") else 0

    db.execute("""
        UPDATE Jalons
        SET description = ?, date_fin = ?, est_complete = ?
        WHERE jalon_id = ?
    """, (description, date_fin, est_complete, jalon_id))

    db.commit()

    db.invalidate_project(projet_id)

    return redirect(url_for("projet_detail", projet_id=projet_id))

@app.post("/jalon/creer")
@login_required
def creer_jalon():
    """Fonction pour la création d'un jalon"""
    db = get_db()

    projet_id = request.form.get("projet_id")
    if not projet_id:
        abort(400)

    description = request.form.get("description_creation")
    date_fin = request.form.get("date_fin_creation") or None
    est_complete = 1 if request.form.get("est_complete_creation") else 0

    db.execute("""
        INSERT INTO Jalons (description, date_fin, est_complete, projet_id)
        VALUES (?, ?, ?, ?)
    """, (description, date_fin, est_complete, projet_id))

    db.commit()
    db.invalidate_project(projet_id)

    return redirect(url_for("projet_detail", projet_id=projet_id))






@app.route("/utilisateurs", methods=["GET"])
@login_required
def utilisateurs():
    """Fonction pour la route /utilisateurs \n
    Affiche la page qui lsite tout les utilisateurs"""

    recherche_utilisateurs = request.args.get("q", "").lower()

    conn = sqlite3.connect('database/database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""SELECT u.*, r.nom AS role_nom FROM Utilisateurs u LEFT JOIN Roles r ON u.role_id = r.role_id""")
    utilisateurs_db = cursor.fetchall()
    conn.close()

    if recherche_utilisateurs:
        utilisateurs_db = [
            u for u in utilisateurs_db
            if recherche_utilisateurs in u["nom"].lower()
            or recherche_utilisateurs in u["prenom"].lower()
            or recherche_utilisateurs in u["email"].lower()
            or (u["role_nom"] and recherche_utilisateurs in u["role_nom"].lower())
        ]

    return render_template("utilisateurs.html", utilisateurs_db=utilisateurs_db, recherche_utilisateurs=recherche_utilisateurs)


@app.route("/utilisateurs/<int:uid>")
@login_required
def utilisateurs_detail(uid):
    """Fonction pour la route /utilisateurs/id_utilisateur \n
    Affiche la page dédié à un utilisateur"""

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM Utilisateurs WHERE utilisateur_id = ?", (uid,))
    utilisateur = c.fetchone()
    conn.close()

    if utilisateur is None:
        abort(404)

    # Obtention des compétences requises et du niveau
    comp_requises = get_db().cursor().execute("SELECT c.nom, ic.niveau FROM competences c JOIN intervenant_competences ic ON c.competence_id = ic.competence_id WHERE ic.intervenant_id = ?", (uid,)).fetchall()


    return render_template("Pages_speciales/utilisateur-template.html", utilisateur=utilisateur, competences_requises=comp_requises)


@app.route("/utilisateurs/<int:uid>/ajouter_comp", methods=["GET", "POST"])
@login_required
def utilisateur_ajouter_competences(uid):
    '''Fonction pour ajouter les compétences d'un utilisateur sur sa page'''

    if not has_permission(current_user, 'peut_gerer_competences'):
        abort(403)

    if get_db().get_user_by_id(uid) is None:
        abort(404)

    c = get_db().cursor()
    c.execute("SELECT * FROM Competences ORDER BY competence_id ASC")
    toutes_competences = c.fetchall()
    success=False

    if request.method== "POST":
        comp_requises = list(map(int, request.form.getlist("skills[]")))
        niveaux = list(map(int, request.form.getlist("levels[]")))
        s = c.execute("Select competence_id from intervenant_competences where intervenant_id=?", (uid,)).fetchall()
        for i in range(len(s)):
            s[i]=s[i][0]
        print(s)
        for i, u in enumerate(comp_requises):
            if u in s:
                continue

            s.append(u)
            niveau_associe = niveaux[i]
            c.execute("INSERT INTO intervenant_competences VALUES (?, ?, ?)", (uid, u, niveau_associe))
            get_db().commit()

        success= True


    return render_template("ajouter_competences.html", competences=toutes_competences, success=success )


@app.route("/utilisateurs/create", methods=["GET", "POST"])
@login_required
def create_user():
    """Fonction pour la route /utilisateurs/create \n
    C'est la page pour creer un nouvel utilisateur"""
    if not has_permission(current_user, 'peut_gerer_utilisateurs'):
        abort(403)

    user_added_successfully= False
    c = get_db().cursor()


    if request.method == 'POST' :
        email = request.form["e-mail"]
        hmdp = hash_password(request.form["mdp"])
        date_expiration_mdp = (datetime.now() + timedelta(days=365)).date()
        nom = request.form["nom"]
        prenom = request.form["prenom"]
        avatar = None
        role_name = request.form["role"]
        est_intervenant = "est_intervenant" in request.form
        heures_dispo_semaine = request.form["h_disp"]
        doc_carte_vitale = request.form["doc_car"]
        doc_cni = request.form["doc_cni"]
        doc_adhesion = request.form["doc_adh"]
        doc_rib = request.form["doc_rib"]

        role_id = c.execute("SELECT role_id FROM Roles WHERE nom = ?", (role_name,)).fetchone()[0]

        #Insertion de None = NULL dans la colonne primary key l'autoincrément est automatique
        c.execute("INSERT INTO Utilisateurs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (None, email, hmdp, date_expiration_mdp, nom, prenom, avatar, role_id, est_intervenant, heures_dispo_semaine, doc_carte_vitale, doc_cni, doc_adhesion, doc_rib))
        get_db().commit()

        user_added_successfully = True

    #Obtention des noms de rôles possibles
    roles_possibles = c.execute("SELECT nom FROM Roles").fetchall()

    return render_template("create_user.html", context={"success":user_added_successfully, "roles_possibles": roles_possibles})


@app.post("/utilisateurs/<int:user_id>/supprimer")
@login_required
def supprimer_utilisateur(user_id):
    """Fonction pour la route /utilisateurs/id_utilisateur/supprimer \n
    Permet de faire fonctionner le bouton de suppression de l'utilisateur"""

    # On vérifier que la personne est bien un ADMIN
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



@app.route("/recherche_avance")
@login_required
def recherche_avance():
    """Fonction pour la route /recherche_avance \n
    Affiche la page de recherche avancé"""

    return render_template("Page_recherche_avance.html")


# Ci dessous les pages du pied de page
@app.route("/cgu")
def cgu():
    """Fonction pour la route /cgu \n
    Affiche la page des CGU"""

    return render_template("./Pages_speciales/cgu.html")


@app.route("/contact")
@login_required
def contact():
    """Fonction pour la route /contact \n
    C'est la fonction de la page de contact"""

    return render_template("./Pages_speciales/contact.html")


@app.route("/rgpd")
@login_required
def rgpd():
    """Fonction pour la route /rgpd \n
    Affiche la page de rgpd et vérifie les rôle pour l'accès"""

    c = get_db().cursor()
    c.execute("SELECT peut_exporter_csv FROM Roles WHERE role_id = ?", (current_user.role_id,))
    droit = c.fetchone()

    if not (droit and droit[0]):
        abort(403)

    return render_template("./Pages_speciales/rgpd.html", droit=droit)


@app.route("/rgpd/download", methods=["POST"])
@login_required
def download_rgpd():
    """Fonction pour la route /rgpd/download \n
    Permet d'utiliser le bouton de téléchargement du csv pour le rgpd \n
    Renvoie un fichier csv avec tout les clients et tout les utilisateurs"""

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT nom_entreprise, contact_email, contact_telephone, address FROM Clients")
    clients = cur.fetchall()


    cur.execute("""SELECT u.nom, u.prenom, u.email, r.nom as role_nom FROM Utilisateurs u LEFT JOIN Roles r ON u.role_id = r.role_id""")
    utilisateurs = cur.fetchall()

    # Permt de mettre le délimiteur ";"
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=cast(Literal[0, 1, 2, 3, 4, 5], csv.QUOTE_MINIMAL))
    writer.writerow(["Type", "Nom", "Prénom", "Email", "Téléphone/Adresse", "Rôle"])

    for cl in clients:
        writer.writerow([
            "Client",
            cl["nom_entreprise"],
            "",
            cl["contact_email"],
            f"{cl['contact_telephone']} / {cl['address']}",
            ""
        ])

    for u in utilisateurs:
        writer.writerow([
            "Utilisateur",
            u["nom"],
            u["prenom"],
            u["email"],
            "",
            u["role_nom"]
        ])

    conn.close()
    output.seek(0)

    csv_data = '\ufeff' + output.getvalue()

    # Télécharge le fichier csv
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition":"attachment;filename=rgpd_export.csv"}
    )


@app.route('/creer_competence', methods=['POST'])
def creer_competence():
    '''Fonction pour la création des compétences'''
    nom = request.form.get('nom_competence', '').strip()
    if not nom:
        return "Nom de compétence requis", 400

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("SELECT competence_id FROM Competences WHERE nom = ?", (nom,))
    exist = cur.fetchone()
    if exist:
        conn.close()
        return f"La compétence '{nom}' existe déjà.", 400

    cur.execute("INSERT INTO Competences (nom, competence_parent) VALUES (?, NULL)", (nom,))
    conn.commit()
    conn.close()

    return redirect(request.referrer or url_for('index'))

#Ici les pages d'erreur.
@app.errorhandler(404)
def page_not_found(error):
    """Fonction pour l'erreur 404"""
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def serveur_error(error):
    """Fonction pour l'erreur 500"""
    return render_template("errors/500.html"), 500

@app.errorhandler(403)
def serveur_error(error):
    """Fonction pour l'erreur 403"""
    return render_template("errors/403.html"), 403


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__ == "__main__":
    app.run(debug=True)
