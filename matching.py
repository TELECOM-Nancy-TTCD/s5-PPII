

import sqlite3

DATABASE = 'database/database.db'

con = sqlite3.connect(DATABASE)

cur = con.cursor()

def get_projet(id):
    res = cur.execute("SELECT * FROM Projets WHERE projet_id="+str(id))
    p = res.fetchone()
    projet = {"id" : p[0], "nom" : p[2], "debut" : p[5], "fin" : p[6]}
    return projet 

def get_utilisateur(id):
    res = cur.execute("SELECT * FROM Utilisateurs WHERE utilisateur_id="+str(id))
    u = res.fetchone()
    utilisateur = {"id":u[0],"nom":u[4],"prenom":u[5],"est_intervenant": u[9], "heures" : u[10]}
    return utilisateur

def get_competences_utilisateur(id_utilisateurs):
    res = cur.execute("""SELECT * FROM Intervenant_competences 
                        JOIN Competences ON Intervenant_competences.competence_id =
                        Competences.competence_id 
                        WHERE intervenant_id="""+str(id_utilisateurs))
    competences = []
    for c in res.fetchall():
        competence = { "id":c[1], "nom" : c[4], "niveau" : c[2]}
        competences.append(competence)
    return competences

def get_competences_projet(id_projet):
    res = cur.execute("""SELECT * FROM Projet_competences
                        JOIN Competences ON Projet_competences.competence_id = Competences.competence_id 
                        WHERE projet_id="""+str(id_projet))
    competences = []
    for c in res.fetchall():
        competence = { "id":c[1], "nom" : c[4], "niveau" : c[2]}
        competences.append(competence)
    return competences

print( get_competences_utilisateur(1) )
print( get_competences_projet(3) )

def niveau_requis(competence,id_utilisateur):
    niveau_projet = competence["niveau"]
    competences_utilisateurs = get_competences_utilisateur(id_utilisateur) 
    for c in competences_utilisateurs :
        if c["id"] == competence["id"] :
            if c["niveau"] >= competence["niveau"]:
                return True 
    return False 


def filtrage_minimal(id_projet,id_utilisateurs):
    for id in id_utilisateurs:
        utilisateur = get_utilisateur(id)
        if not utilisateur["est_intervenant"]:
            return False 
    competences_projet = get_competences_projet(id_projet)
    for competence in competences_projet :
        if not any( [niveau_requis(competence,id) for id in id_utilisateurs] ):
            return False
    return True 

print(filtrage_minimal(3,[1]))

competences_3 = get_competences_projet(3)

print(competences_3)
print( niveau_requis(competences_3[0],1) )

con.close()
