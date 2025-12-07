from flask import Flask, session, render_template, request, redirect, url_for, g, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from hashlib import scrypt
import os, base64, sqlite3
import database
import redis

class User(UserMixin):
    def __init__(self, id):
        self.id=str(id)

DATABASE= 'database/database.db'

def get_db():
    db= getattr(g, '_database', None)
    if db is None:
        db = g._database = database.Database(
            redis_client=redis.Redis(host='localhost', port=6379, db=0),
            database=DATABASE
        )
    return db

def get_clients():
    conn = sqlite3.connect('database/database.db')
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Clients")
    clients = cursor.fetchall()
    conn.close()
    return clients

class User(UserMixin):
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

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

app.secret_key = b'6031f03d38eede6a7a9c5827a0bd25e418a0d236abf4665cc7c23c7249c36867' 
# Clé pour l'encodage des cookies de session

def hash_password(mdp : str):
    salt = os.urandom(16) # Génération d'un salt

    mdp_hache = scrypt(mdp.encode(), salt=salt, n=2**14, r=8, p=1) # hachage du mdp avec le salt

    return base64.b64encode(salt+mdp_hache).decode() 
    # encodage en B64, et remise en forme texte pour stockage.
    #Les 16 premiers octets sont le salt, le reste le mdp.


def verify_password(mdp_entre : str, stored_hash):
    
    octets_decodes = base64.b64decode(stored_hash) # bytes obtenus par décodage en B64
    
    salt = octets_decodes[:16]
    mdp_hache_stocke = octets_decodes[16:]
    # Impossible de revenir au mdp depuis le hash, donc on hache l'entrée avec le même salt et on vérifie l'égalité

    mdp_hache_entre = scrypt(mdp_entre.encode(), salt=salt, n=2**14, r=8, p=1) # hachage du mdp avec le salt

    return mdp_hache_entre == mdp_hache_stocke



@login_manager.user_loader
def load_user(uid : str):
    return User.get(uid)




@app.route("/login", methods = ["GET", "POST"])
def login():
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
            
                return redirect(url_for('index')) # TODO: Signaler à l'utilisateur que son login est réussi
        
        has_failed_login = True # Si pas d'utilisateur avec ce mail ou que le mdp est faux, on a raté le login

    # Pour un login échouant, on ré-affiche la page avec un message supplémentaire
    # Pour le premier affichage, has_failed_login est à False.
    return render_template('Pages_speciales/login_page.html', has_failed_login=has_failed_login)


def can_manage_users(us : User):
    c = get_db().cursor()
    c.execute('SELECT peut_gerer_utilisateurs FROM Roles WHERE role_id = ?', (us.role_id,))

    r = c.fetchone()
    if r == None or r[0] == False:
        return False

    return True


@app.route("/users/create", methods=["GET", "POST"])
@login_required
def create_user():
    if not can_manage_users(current_user):
        abort(403)

    user_added_successfully= False
    c = get_db().cursor()

    if request.method == 'POST' :
        email = request.form["e-mail"]
        hmdp = hash_password(request.form["mdp"])
        nom = request.form["nom"]
        prenom = request.form["prenom"]
        role_name = request.form["role"]
        print(role_name)
        est_intervenant = "est_intervenant" in request.form
        heures_dispo = request.form["h_disp"]
        doc_carte_vitale = request.form["doc_car"]
        doc_cni = request.form["doc_cni"]
        doc_adhesion = request.form["doc_adh"]
        doc_rib = request.form["doc_rib"]

        role_id = c.execute("SELECT role_id FROM Roles WHERE nom = ?", (role_name,)).fetchone()[0]
        c.execute("INSERT INTO Utilisateurs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (None, email, hmdp, nom, prenom, role_id, est_intervenant, heures_dispo, doc_carte_vitale, doc_cni, doc_adhesion, doc_rib))
        get_db().commit()
        #Insertion de None = NULL dans la colonne primary key car elle se gère ainsi automatiquement
        user_added_successfully = True

    # Chargement de la page
    roles_possibles = c.execute("SELECT nom FROM Roles").fetchall() #Obtention des noms de rôles possibles

    return render_template("create_user.html", context={"success":user_added_successfully, "roles_possibles": roles_possibles})

# Ici les pages du menus principales (vide) mais utile pour creer le menu
@app.route("/")          
def accueil():
    return render_template("accueil.html")

@app.route("/contact")
@login_required
def contact():
    return render_template("./Pages_speciales/contact.html")

@app.route("/clients")
@login_required
def clients():
    clients_db = get_db().get_all_clients()
    return render_template("clients.html", clients_db=clients_db)

@app.route("/projets")
@login_required
def projets():
    return render_template("projets.html")

@app.route("/recherche_avance")
@login_required
def recherche_avance():
    return render_template("Page_recherche_avance.html")

@app.route("/utilisateurs", methods=["GET"])
@login_required
def utilisateurs():
    recherche = request.args.get("q", "").lower() 
    utilisateurs_db = get_utilisateurs()

    if recherche:
        utilisateurs_db = [
            u for u in utilisateurs_db
            if recherche in u["nom"].lower()
            or recherche in u["prenom"].lower()
            or recherche in u["email"].lower()
        ]

    return render_template("utilisateurs.html", utilisateurs_db=utilisateurs_db, recherche=recherche)

# Ci dessous les pages du pied de page , souvent seules.
@app.route("/cgu")
def cgu():
    return render_template("./Pages_speciales/cgu.html")

@app.route("/rgpd")
@login_required
def rgpd():
    return render_template("./Pages_speciales/rgpd.html")

@app.route("/utilisateur/<int:uid>")
@login_required
def utilisateur_detail(uid):
    conn = sqlite3.connect('database/database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Utilisateurs WHERE utilisateur_id = ?", (uid,))
    utilisateur = cursor.fetchone()
    conn.close()

    if utilisateur is None:
        abort(404)

    # Appelle le bon dossier + bon fichier
    return render_template("Pages_speciales/utilisateur-template.html", utilisateur=utilisateur)

@app.route("/client/<int:client_id>")
@login_required
def client_detail(client_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM Clients WHERE client_id = ?", (client_id,))
    client = c.fetchone()
    if client is None:
        abort(404)
 
    c.execute("""
        SELECT p.* 
        FROM Projets p
        JOIN Conventions c ON p.convention_id = c.convention_id
        WHERE c.client_id = ?
    """, (client_id,))
    projets = c.fetchall()
    
    conn.close()
    
    return render_template("Pages_speciales/clients_template.html", client=client, projets=projets)

#Ici les pages d'erruer personalisé, elle ne sont pas encore toute la mais il faut que je réflechisse auquelles je met.
@app.errorhandler(404)
def page_not_found(error):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def serveur_error(error):
    return render_template("errors/500.html"), 500


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__ == "__main__":
    app.run(debug=True)

