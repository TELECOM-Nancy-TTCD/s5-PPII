from flask import Flask, session, render_template, request, redirect, url_for, g, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from hashlib import scrypt
import os, base64, sqlite3


DATABASE= 'database.db'

def get_db():
    db= getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

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

            if row == None:
                return None
            
            return cls(row)
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


def verify_password(mdp_entre, stored_hash):
    
    octets_decodes = base64.b64decode(stored_hash) # bytes obtenus par décodage en B64
    
    salt = octets_decodes[:16]
    mdp_hache_stocke = octets_decodes[16:]
    # Impossible de revenir au mdp depuis le hash, donc on hache l'entrée avec le même salt et on vérifie l'égalité

    mdp_hache_entre = scrypt(mdp_entre.encode(), salt, 2**14, 8, 1) # hachage du mdp avec le salt

    return mdp_hache_entre == mdp_hache_stocke



@login_manager.user_loader
def load_user(uid):
    return User.get(uid)


@app.route("/")
@app.route("/index")
@login_required
def index():


    return render_template('index.html', user=current_user)



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
                if next_page == None or next_page[0]=="/":
                    return redirect(url_for("index"))
                
                return redirect(next)
            
                
        
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
        c.execute("INSERT INTO Utilisateurs VALUES (?)", (None, email, hmdp, nom, prenom, role_id, est_intervenant, heures_dispo, doc_carte_vitale, doc_cni, doc_adhesion, doc_rib)) 
        get_db().commit()
        #Insertion de None = NULL dans la colonne primary key car elle se gère ainsi automatiquement
        user_added_successfully = True

    # Chargement de la page
    roles_possibles =["a","b","d"] #c.execute("SELECT nom FROM Roles").fetchall() #Obtention des noms de rôles possibles

    return render_template("create_user.html", context={"success":user_added_successfully, "roles_possibles": roles_possibles})



@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()