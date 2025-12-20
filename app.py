from flask import Flask, Response, render_template, send_file, abort, redirect, url_for, flash, g, request, session
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user

from app_conventions import conventions_bp
from hashlib import scrypt
from datetime import datetime, timedelta
from dotenv import load_dotenv

import sqlite3, csv, io, redis, os, base64, database


load_dotenv()
DATABASE= os.getenv('DATABASE')


class User(UserMixin):
    '''Définit la classe de l'utilisateur'''
    def __init__(self, id, nom, prenom, role_id):
        self.id=id
        self.nom = nom
        self.prenom = prenom
        self.role_id = role_id
    
    @classmethod
    def get(cls, user_id : str):
        try:
            c = get_db().cursor()
            
            c.execute("SELECT utilisateur_id, nom, prenom, role_id FROM Utilisateurs WHERE utilisateur_id = ?",(int(user_id), ))
            row = c.fetchone()
            
            return cls(*row)
        except:
            return None


def get_db():
    '''Permet de récuperer la DB'''
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = database.Database(
            redis_client=redis.Redis(host='localhost', port=6379, db=0),
            database=DATABASE
        )
    return db

def get_clients():
    '''Fonction qui renvoie tout les clients de la DB'''
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Clients")
    clients = cursor.fetchall()
    conn.close()

    return clients

def get_utilisateurs():
    '''Fonction qui renvoie tout les utilisateurs de la DB'''
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Utilisateurs")
    utilisateurs = cursor.fetchall()
    conn.close()

    return utilisateurs

def can_manage_users(us : User):
    '''Fonction qui va vérifie si une personne à le droit de modifier les utilisateurs \n
    Renvoie un booléen'''

    c = get_db().cursor()
    c.execute('SELECT peut_gerer_utilisateurs FROM Roles WHERE role_id = ?', (us.role_id,))

    donnee_users = c.fetchone()
    if donnee_users == None or donnee_users[0] == False:
        return False

    return True

def format_date(date_value):
    '''Fonction qui change le format de la date en un format date classique sous forme de str'''
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
# Enregistrer le blueprint des conventions sur l'instance unique 'app'
app.register_blueprint(conventions_bp)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Clé pour l'encodage des cookies de session
app.secret_key = b'6031f03d38eede6a7a9c5827a0bd25e418a0d236abf4665cc7c23c7249c36867' 


def hash_password(mdp : str):
    '''Fonction qui hash et sale le mot de passe,
    Les 16 premiers octets sont le salt, le reste le mdp.'''
    salt = os.urandom(16) # Génération d'un salt

    mdp_hache = scrypt(mdp.encode(), salt=salt, n=2**14, r=8, p=1) # Hachage du mdp avec le salt

    # Encodage en B64, et remise en forme texte pour stockage.
    return base64.b64encode(salt+mdp_hache).decode() 
    
def verify_password(mdp_entre : str, stored_hash):
    '''Fonction qui vérifie le mot de passe avec le hashé. \n
    Il est impossible de revenir au mdp depuis le hash,donc on hache l'entrée avec le même salt et on vérifie l'égalité \n
    Le résultat est un booléen'''
    
    octets_decodes = base64.b64decode(stored_hash) # Bytes obtenus par décodage en B64
    salt = octets_decodes[:16]

    mdp_hache_stocke = octets_decodes[16:]
    mdp_hache_entre = scrypt(mdp_entre.encode(), salt=salt, n=2**14, r=8, p=1) # Hachage du mdp avec le salt

    return mdp_hache_entre == mdp_hache_stocke



@login_manager.user_loader
def load_user(uid : str):
    '''Fonction qui charge l'utilisateur'''
    return User.get(uid)



@app.route("/login", methods = ["GET", "POST"])
def login():
    '''Fonction pour la route /login \n
    Renvoie les page pour le login et vérifie le mdp'''
    has_failed_login = False

    if request.method == 'POST' : 
        
        c = get_db().cursor()

        adressemail = request.form["Adresse e-mail"]
        mdp = request.form["Mot de passe"]
        c.execute("SELECT utilisateur_id, mot_de_passe_hashed FROM Utilisateurs WHERE email = ?", (adressemail,))
        
        corresp = c.fetchone()
        if corresp != None: # Si on trouve un utilisateur avec cet email
            if verify_password(mdp, corresp[1]):
                to_login = corresp[0]
                login_user(load_user(to_login)) # On login l'utilisateur correspondant, identifié par son user id

                next_page = request.args.get("next")

                if next_page == None:
                    redirect(url_for("accueil"))

                # TODO : Vérifier que l'URL next est safe
                return redirect(next_page)
        
        has_failed_login = True # Si pas d'utilisateur avec ce mail ou que le mdp est faux, on a raté le login

    # Pour un login échouant, on ré-affiche la page avec un message supplémentaire
    # Pour le premier affichage, has_failed_login est à False.
    return render_template('Pages_speciales/login_page.html', has_failed_login=has_failed_login)


@app.route("/")          
def accueil():
    '''Fonction pour la route / \n
    C'est la fonction de la page d'accueil'''

    return render_template("accueil.html")


@app.route("/clients", methods=['GET'])
@login_required
def clients():
    '''Fonction pour la route /clients \n
    Permet d'afficher la page avec la liste des clients'''
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

    return render_template("clients.html", clients_db=clients_db, recherche_clients=recherche_clients)


@app.route("/clients/<int:client_id>")
@login_required
def client_detail(client_id):
    '''Fonction pour la route /clients/id_client \n
    Affiche la page dédié à un client'''

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM Clients WHERE client_id = ?", (client_id,))
    client = c.fetchone()
    if client is None:
        abort(404)
 
    c.execute("""SELECT p.* FROM Projets p JOIN Conventions c ON p.convention_id = c.convention_id WHERE c.client_id = ?""", (client_id,))
    projets = c.fetchall()
    
    c.execute("""
        SELECT i.*, u.nom || ' ' || u.prenom AS utilisateur_nom FROM Interactions i
        JOIN Utilisateurs u ON i.utilisateur_id = u.utilisateur_id WHERE i.client_id = ?
        ORDER BY i.date_time_interaction DESC
    """, (client_id,))
    
    interactions = c.fetchall()
    conn.close()
    
    return render_template("Pages_speciales/clients_template.html", client=client, projets=projets, interactions=interactions)


@app.route("/import_clients", methods=["POST"])
def import_clients():
    '''Fonction pour la route /import_clients \n
    Permet la gestion du bouton d'import de client sur la page des clients \n
    Cette focntion gère les erreur de csv, et import dans la db les données du csv si elle sont correctes'''

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
    '''Fonction pour la route /export_clients \n
    Permet d'utiliser le bouton d'export de la page des clients \n
    La fonction crée un csv, va récuperer les données de la DB et télécharge le fichier'''

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
    '''Fonction pour la route /projet/id_projet \n
    Affiche la page dédié à un projet'''

    projet = get_db().get_project_id(projet_id)

    if projet == None: 
        abort(404)
    
    # Conversion des dates vers le format usuel
    projet.date_debut = format_date(projet.date_debut)
    projet.date_fin = format_date(projet.date_fin)

    for j, u in enumerate(projet.jalons):
        if u.date_fin!= None :
            projet.jalons[j].date_fin = datetime.fromisoformat(u.date_fin).strftime("%d/%m/%Y")

    return render_template("Pages_speciales/projets_template.html", projet = projet)


@app.post("/projet/<int:projet_id>/terminer")
@login_required
def terminer_projet(projet_id):
    '''Fonction pour la route projet/id_projet/terminer \n
    Permet de gerer le bouton de fin de projet et de modifier la DB en conséquence'''

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


@app.route("/utilisateurs", methods=["GET"])
@login_required
def utilisateurs():
    '''Fonction pour la route /utilisateurs \n
    Affiche la page qui lsite tout les utilisateurs'''

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
    '''Fonction pour la route /utilisateurs/id_utilisateur \n
    Affiche la page dédié à un utilisateur'''

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM Utilisateurs WHERE utilisateur_id = ?", (uid,))
    utilisateur = c.fetchone()
    conn.close()

    if utilisateur is None:
        abort(404)

    return render_template("Pages_speciales/utilisateur-template.html", utilisateur=utilisateur)


@app.route("/utilisateurs/create", methods=["GET", "POST"])
@login_required
def create_user():
    '''Fonction pour la route /utilisateurs/create \n
    C'est la page pour creer un nouvel utilisateur'''
    if not can_manage_users(current_user):
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
    '''Fonction pour la route /utilisateurs/id_utilisateur/supprimer \n
    Permet de faire fonctionner le bouton de suppression de l'utilisateur'''

    # On vérifier que la personne est bien un ADMIN
    if getattr(current_user, 'role_id', None) != 1:
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
    '''Fonction pour la route /recherche_avance \n
    Affiche la page de recherche avancé'''

    return render_template("Page_recherche_avance.html")


# Ci dessous les pages du pied de page
@app.route("/cgu")
def cgu():
    '''Fonction pour la route /cgu \n
    Affiche la page des CGU'''

    return render_template("./Pages_speciales/cgu.html")


@app.route("/contact")
@login_required
def contact():
    '''Fonction pour la route /contact \n
    C'est la fonction de la page de contact'''

    return render_template("./Pages_speciales/contact.html")


@app.route("/rgpd")
@login_required
def rgpd():
    '''Fonction pour la route /rgpd \n
    Affiche la page de rgpd et vérifie les rôle pour l'accès'''

    c = get_db().cursor()
    c.execute("SELECT peut_exporter_csv FROM Roles WHERE role_id = ?", (current_user.role_id,))
    droit = c.fetchone()
    
    if not (droit and droit[0]):
        abort(403)

    return render_template("./Pages_speciales/rgpd.html", droit=droit)


@app.route("/rgpd/download", methods=["POST"])
@login_required
def download_rgpd():
    '''Fonction pour la route /rgpd/download \n
    Permet d'utiliser le bouton de téléchargement du csv pour le rgpd \n
    Renvoie un fichier csv avec tout les clients et tout les utilisateurs'''

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT nom_entreprise, contact_email, contact_telephone, address FROM Clients")
    clients = cur.fetchall()
    

    cur.execute("""SELECT u.nom, u.prenom, u.email, r.nom as role_nom FROM Utilisateurs u LEFT JOIN Roles r ON u.role_id = r.role_id""")
    utilisateurs = cur.fetchall()
    
    # Permt de mettre le délimiteur ";"
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
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


#Ici les pages d'erreur.
@app.errorhandler(404)
def page_not_found(error):
    '''Fonction pour l'erreur 404'''
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def serveur_error(error):
    '''Fonction pour l'erreur 500'''
    return render_template("errors/500.html"), 500


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__ == "__main__":
    app.run(debug=True)
