from flask import Flask,render_template,send_file
from flask import g

from flask import Blueprint

import redis
from database import *

import sqlite3

conventions_bp = Blueprint('conventions',__name__,url_prefix='/conventions')

class FakeRedis:
    """Simple fake Redis-like client used for tests. Stores values in an in-memory dict.

    Methods implemented: get, setex, set, sadd, srem, smembers, expire, delete
    """
    def __init__(self):
        self.store = {}
        self.sets = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def setex(self, key, ttl, value):
        # TTL is ignored for the fake client
        self.store[key] = value

    def sadd(self, key, member):
        s = self.sets.setdefault(key, set())
        s.add(member)

    def srem(self, key, member):
        s = self.sets.get(key)
        if s:
            s.discard(member)
            if not s:
                # optionally remove empty set
                del self.sets[key]

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def expire(self, key, ttl):
        # ignore TTL in fake
        return True

    def delete(self, key):
        self.store.pop(key, None)
        self.sets.pop(key, None)


r = FakeRedis()
db = Database(r,'database/database.db')



print()

DATABASE = 'database/database.db'

def get_db():
    db = getattr(g,'_database', None)
    if db is None :
        db = g._database = sqlite3.connect(DATABASE)
    return db

def get_projets_by_convention(id_convention):
    c = get_db().cursor()
    c.execute("SELECT * FROM Projets WHERE convention_id="+str(id_convention))
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
    c.execute("SELECT * FROM Clients WHERE client_id="+str(id))
    for client in c.fetchall():
        return {"id":client[0],"nom_entreprise":client[1],
                "contact_nom":client[2],"contact_email":client[3],
                "contact_telephone":client[4],"type_client":client[5],
                "interlocuteur_principal":client[6],"localisation_lat":client[7],
                "localisation_lng":client[8],"addresse":client[9]}
    return {}

def get_convention(id):
    c = get_db().cursor()
    c.execute("SELECT * FROM Conventions WHERE convention_id="+str(id))
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
    c.execute("SELECT utilisateur_id,nom,prenom FROM Utilisateurs WHERE utilisateur_id="+str(id))
    for utilisateur in c.fetchall():
        return {"id":utilisateur[0],"nom":utilisateur[1],"prenom":utilisateur[2]}
    return {}

@conventions_bp.route('/')
def index():
    l = liste_conventions()
    return render_template('liste_conventions.html',context=l)

@conventions_bp.route('/<int:id>')
def convention(id : int) :
    conv =  get_convention(id)
    client = get_client( conv["client_id"] )
    return render_template('convention.html',context={"convention":conv, 
    "client":get_client( conv["client_id"] ) , "projets": get_projets_by_convention(id), "utilisateur" : get_utilisateur(client["interlocuteur_principal"]) } 
    )

