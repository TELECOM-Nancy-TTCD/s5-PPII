from flask import Flask, session, render_template, request, redirect, url_for, g
from flask_login import LoginManager, login_user
from flask_login import UserMixin as User
import sqlite3


DATABASE= 'database.db'

def get_db():
    db= getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)

app.secret_key = b'6031f03d38eede6a7a9c5827a0bd25e418a0d236abf4665cc7c23c7249c36867' 
# Clé pour l'encodage des cookies de session

@login_manager.user_loader
def load_user(uid):
    return User.get(uid)


def verify_credentials(form): # Vérifier les entrées de l'utilisateur
    c = get_db().cursor()
    



@app.route("/login", methods = ["GET", "POST"])
def login():
    
    if request.method == 'POST' : 
        
        username = request.form["Nom d'utilisateur"]
        mdp = request.form["username"]
        
        return redirect(url_for('index'))


    return render_template('Pages_speciales/login_page.html')


# Ici les pages du menus principales (vide) mas utile pour creer le menu 
@app.route("/")          
def accueil():
    return render_template("accueil.html")

@app.route("/contact")
def contact():
    return render_template("./Pages_speciales/contact.html")

@app.route("/clients")
def clients():
    return render_template("clients.html")

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