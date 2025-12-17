

import sqlite3

DATABASE = 'database/database.db'

con = sqlite3.connect(DATABASE)

cur = con.cursor()

def get_projet(id):
    res = cur.execute("SELECT * FROM Projets WHERE projet_id="+str(id))
    p = res.fetchone()
    projet = {"id" : p[0], "nom" : p[2],"charge":p[5], "debut" : p[6], "fin" : p[7]}
    return projet 

def get_utilisateur(id):
    res = cur.execute("SELECT * FROM Utilisateurs WHERE utilisateur_id="+str(id))
    u = res.fetchone()
    utilisateur = {"id":u[0],"nom":u[4],"prenom":u[5],"est_intervenant": u[8], "heures" : u[9]}
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
                        WHERE projet_id="""+str(id_projet)+ """ ORDER BY projet_id """)
    competences = []
    for c in res.fetchall():
        competence = { "id":c[1], "nom" : c[4], "niveau" : c[2]}
        competences.append(competence)
    return competences

def get_nb_intervenant(id_projet):
    res = cur.execute("""SELECT Count(Distinct(utilisateur_id)) FROM Travaille_sur
                        WHERE projet_id="""+str(id_projet))
    return res.fetchone()[0]

def get_projets_participe_utilisateur(id_utilisateur):
    res = cur.execute("""SELECT Travaille_sur.projet_id FROM Travaille_sur
                    JOIN Projets ON Travaille_sur.projet_id = Projets.projet_id
                    WHERE est_intervenant_sur_projet == true AND
                    statut = 'En cours' AND
                     utilisateur_id="""+str(id_utilisateur))
    return [elt[0] for elt in res.fetchall()]

def charge_par_semaine(projet_id):
    projet = get_projet(projet_id)
    nb_jour = temps_projet(projet["debut"],projet["fin"])
    return projet["charge"] / (nb_jour/7)


def charge_individuelle_par_semaine(id_projet):
    nb_intervenant = get_nb_intervenant(id_projet)
    return charge_par_semaine(id_projet)/nb_intervenant

def charge_courante_utilisateur(id_utilisateur):
    return sum([charge_individuelle_par_semaine(id_projet) for id_projet in get_projets_participe_utilisateur(id_utilisateur)])

def niveau_requis(competence,id_utilisateur):
    niveau_projet = competence["niveau"]
    competences_utilisateurs = get_competences_utilisateur(id_utilisateur) 
    for c in competences_utilisateurs :
        if c["id"] == competence["id"] :
            if c["niveau"] >= competence["niveau"]:
                return True 
    return False 


def temps_projet(date_debut,date_fin) :
    date_debut = date_debut.split("/")
    date_fin = date_fin.split("/")
    return int(date_fin[0])-int(date_debut[0]) + 30*( int(date_fin[1])- int(date_debut[1]) ) + 365*( int(date_fin[2])-int(date_debut[2]) )

def competences_lies_projet(competences,id_utilisateur) :
    ids_projet = [competence["id"] for competence in competences]
    competences_utilisateur_projet = [ competence for competence in get_competences_utilisateur(id_utilisateur) if competence["id"] in ids_projet ]
    return competences_utilisateur_projet


def filtrage_minimal(id_projet,id_utilisateurs):
    for id in id_utilisateurs:
        utilisateur = get_utilisateur(id)
        if not utilisateur["est_intervenant"]:
            return False 
    charge_semaine_projet = charge_par_semaine(id_projet)
    for id in id_utilisateurs:
        print(charge_par_semaine(id_projet)/len(id_utilisateurs))
        if  get_utilisateur(id)["heures"] -  charge_courante_utilisateur(id) < (charge_par_semaine(id_projet)/len(id_utilisateurs)) :
            return False 
    competences_projet = get_competences_projet(id_projet)
    for competence in competences_projet :
        if not any( [niveau_requis(competence,id) for id in id_utilisateurs] ):
            return False
    return True 

def add_replace(liste_competences,competence):
    i = 0 
    while i < len(liste_competences):
        if liste_competences[i]["id"] == competence["id"] : 
            if liste_competences[i]["niveau"] < competence["niveau"]:
                liste_competences[i]["niveau"] = competence["niveau"]
            break
        i+=1
    if i==len(liste_competences):
        liste_competences.append(competence)

def recuperation_competences_utilisateurs(competences_projet,utilisateur_ids):
    liste_competences = []
    for id in utilisateur_ids:
        competences_u = competences_lies_projet(competences_projet,id)
        for competence in competences_u:
            add_replace(liste_competences,competence)
    return liste_competences

def sum(L):
    if len(L)==0:
        return 0
    else:
        return L[0] + sum(L[1:])

def matching_competence(projet_id,utilisateur_ids):
    competences_projet = get_competences_projet(projet_id)
    niveau_requis = [competence["niveau"] for competence in competences_projet]
    competences_utilisateurs = recuperation_competences_utilisateurs(competences_projet,utilisateur_ids)
    return sum( [competences_utilisateurs[i]["niveau"] - niveau_requis[i] for i in range(len(niveau_requis))  ] ) / sum( [10 - niveau for niveau in niveau_requis] )


print(  get_utilisateur(1)["heures"] - charge_courante_utilisateur(1))

print(filtrage_minimal( 3,[1] ))

con.close()
