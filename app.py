from flask import Flask, session, render_template, request, redirect, url_for, g
from flask_login import LoginManager, UserMixin, login_user
from hashlib import scrypt
import os, base64, sqlite3

class User(UserMixin):
    def __init__(self, id):
        self.id=id

DATABASE= 'database.db'

def get_db():
    db= getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def get_clients():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Clients")
    clients = cursor.fetchall()
    conn.close()
    return clients

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)

app.secret_key = b'6031f03d38eede6a7a9c5827a0bd25e418a0d236abf4665cc7c23c7249c36867' 
# Clé pour l'encodage des cookies de session

def hash_password(mdp):
    salt = os.urandom(16) # Génération d'un salt

    mdp_hache = scrypt(mdp.encode(), salt, 2**14, 8, 1) # hachage du mdp avec le salt

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



@app.route("/login", methods = ["GET", "POST"])
def login():
    has_failed_login = False

    if request.method == 'POST' : 
        
        c = get_db().cursor()

        adressemail = request.form["Adresse e-mail"]
        mdp = request.form["Mot de passe"]
        c.execute("SELECT utilisateur_id, mot_de_passe_hashed FROM Utilisateurs WHERE email = ?", (adressemail,))
        
        corresp = c.fetchall()
        if corresp != []: # Si on trouve un utilisateur avec cet email
            if verify_password(mdp, corresp[0][1]):
                to_login = corresp[0][0]
                login_user(User(int(to_login))) # On login l'utilisateur correspondant, identifié par son user id
            
                return redirect(url_for('index')) # TODO: Signaler à l'utilisateur que son login est réussi
        
        has_failed_login = True # Si pas d'utilisateur avec ce mail ou que le mdp est faux, on a raté le login
        # Pour un login échouant, on ré-affiche la page avec un message supplémentaire (à implémenter dans la template Jinja)
        # Pour le premier affichage, has_failed_login est à False.
    return render_template('Pages_speciales/login_page.html', has_failed_login=has_failed_login)


# Ici les pages du menus principales (vide) mas utile pour creer le menu 
@app.route("/")          
def accueil():
    return render_template("accueil.html")

@app.route("/contact")
def contact():
    return render_template("./Pages_speciales/contact.html")

@app.route("/clients")
def clients():
    clients_db = get_clients()
    return render_template("clients.html", clients_db=clients_db)

@app.route("/projets")
def projets():
    return render_template("projets.html")

@app.route("/recherche_avance")
def recherche_avance():
    return render_template("Page_recherche_avance.html")



# Ci dessous les pages du pied de page , souvent seules.
@app.route("/cgu")
def cgu():
    return render_template("./Pages_speciales/cgu.html")

@app.route("/rgpd")
def rgpd():
    return render_template("./Pages_speciales/rgpd.html")

#Ici les pages d'erruer personalisé, elle ne sont pas encore toute la mais il faut que je réflechisse auquelles je met.
@app.errorhandler(404)
def page_not_found(error):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def serveur_error(error):
    return render_template("errors/500.html"), 500



if __name__ == "__main__":
    app.run(debug=True)

