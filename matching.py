

import sqlite3

from math import exp,sqrt

DATABASE = 'database/database.db'

con = sqlite3.connect(DATABASE)

cur = con.cursor()

def get_projet(id):
    query = """SELECT * FROM Projets WHERE projet_id=? """
    res = cur.execute(query,(id,))
    p = res.fetchone()
    assert p != None
    projet = {"id" : p[0], "nom" : p[2],"charge":p[5], "debut" : p[6], "fin" : p[7]}
    return projet 

def get_utilisateur(id):
    res = cur.execute("SELECT * FROM Utilisateurs WHERE utilisateur_id=?",(id,))
    u = res.fetchone()
    utilisateur = {"id":u[0],"nom":u[4],"prenom":u[5],"est_intervenant": u[8], "heures" : u[9]}
    return utilisateur

def get_competences_utilisateur(id_utilisateur):
    res = cur.execute("""SELECT * FROM Intervenant_competences 
                        JOIN Competences ON Intervenant_competences.competence_id =
                        Competences.competence_id 
                        WHERE intervenant_id=?""",(id_utilisateur,))
    competences = []
    for c in res.fetchall():
        competence = { "id":c[1], "nom" : c[4], "niveau" : c[2]}
        competences.append(competence)
    return competences

def get_competences_projet(id_projet):
    res = cur.execute("""SELECT * FROM Projet_competences
                        JOIN Competences ON Projet_competences.competence_id = Competences.competence_id 
                        WHERE projet_id=? ORDER BY projet_id """, (id_projet,) )
    competences = []
    for c in res.fetchall():
        competence = { "id":c[1], "nom" : c[4], "niveau" : c[2]}
        competences.append(competence)
    return competences

def get_nb_intervenant(id_projet):
    res = cur.execute("""SELECT Count(Distinct(utilisateur_id)) FROM Travaille_sur
                        WHERE projet_id=?""", (id_projet,) )
    return res.fetchone()[0]

def get_projets_participe_utilisateur(id_utilisateur):
    res = cur.execute("""SELECT Travaille_sur.projet_id FROM Travaille_sur
                    JOIN Projets ON Travaille_sur.projet_id = Projets.projet_id
                    WHERE est_intervenant_sur_projet == true AND
                    statut = 'En cours' AND
                     utilisateur_id=?""", (id_utilisateur, ))
    return [elt[0] for elt in res.fetchall()]

def get_all_utilisateurs():
    res = cur.execute("""SELECT utilisateur_id FROM Utilisateurs """)
    return [ elt[0] for elt in res.fetchall() ]

def get_all_pairs_utilisateurs():
    res = cur.execute("""SELECT u1.utilisateur_id,u2.utilisateur_id FROM
                        Utilisateurs AS u1 JOIN Utilisateurs AS u2 
                        ON u1.utilisateur_id < u2.utilisateur_id  """)
    return [(elt[0],elt[1]) for elt in res.fetchall()]

def get_all_triplets_utilisateurs():
    res = cur.execute("""SELECT u1.utilisateur_id,u2.utilisateur_id,u3.utilisateur_id FROM
                        Utilisateurs AS u1 JOIN Utilisateurs AS u2 
                        ON u1.utilisateur_id < u2.utilisateur_id
                        JOIN Utilisateurs AS u3 
                        ON u2.utilisateur_id < u3.utilisateur_id  """)
    return [(elt[0],elt[1],elt[2]) for elt in res.fetchall()]


def has_competence(id_utilisateur,id_competence):
    res = cur.execute(""" SELECT * FROM Intervenant_competences
                            WHERE intervenant_id =? 
                            AND competence_id =?""", (id_utilisateur,id_competence )  )
    return res.fetchone() != None 

def get_level_competence(id_utilisateur,id_competence):
    res = cur.execute(""" SELECT niveau FROM Intervenant_competences
                            WHERE intervenant_id =? 
                            AND competence_id =?""", (id_utilisateur,id_competence) )
    resultat = res.fetchone()
    assert (resultat!= None)
    return resultat[0]

def competence_commune(id_projet1,id_projet2):
    query = """
    SELECT COUNT(DISTINCT competence_id)
    FROM (
        SELECT competence_id FROM Projet_competences WHERE projet_id = ?
        INTERSECT
        SELECT competence_id FROM Projet_competences WHERE projet_id = ?
    ) AS t;
    """
    cur.execute(query, (id_projet1, id_projet2))
    return  cur.fetchone()[0]

def get_projet_experience(ids_utilisateur):
    if not ids_utilisateur:  # éviter les listes vides
        return []

    placeholders = ','.join(['?'] * len(ids_utilisateur))
    query = f"""
    SELECT p.projet_id
    FROM Travaille_sur AS t
    JOIN Projets AS p ON p.projet_id = t.projet_id
    WHERE utilisateur_id IN ({placeholders}) AND statut = 'Terminé'
    """
    res = cur.execute(query, ids_utilisateur)
    return [ elt[0] for elt in  res.fetchall()]


def charge_par_semaine(projet_id):
    projet = get_projet(projet_id)
    nb_jour = temps_projet(projet["debut"],projet["fin"])
    return projet["charge"] / (nb_jour/7)


def charge_individuelle_par_semaine(id_projet):
    nb_intervenant = get_nb_intervenant(id_projet)
    return charge_par_semaine(id_projet)/nb_intervenant

def charge_courante_utilisateur(id_utilisateur):
    return sum([charge_individuelle_par_semaine(id_projet) for id_projet in get_projets_participe_utilisateur(id_utilisateur)])

def temps_libre(id_utilisateur):
    utilisateur = get_utilisateur(id_utilisateur)
    return utilisateur["heures"] -  charge_courante_utilisateur(id_utilisateur)


def niveau_requis(competence,id_utilisateur):
    niveau_projet = competence["niveau"]
    competences_utilisateurs = get_competences_utilisateur(id_utilisateur) 
    for c in competences_utilisateurs :
        if c["id"] == competence["id"] :
            if c["niveau"] >= competence["niveau"]:
                return True 
    return False 


def temps_projet(date_debut,date_fin) :
    date_debut = date_debut.split("-")
    date_fin = date_fin.split("-")
    return int(date_fin[2])-int(date_debut[2]) + 30*( int(date_fin[1])- int(date_debut[1]) ) + 365*( int(date_fin[0])-int(date_debut[0]) )

def competences_lies_projet(competences,id_utilisateur) :
    ids_projet = [competence["id"] for competence in competences]
    competences_utilisateur_projet = [ competence for competence in get_competences_utilisateur(id_utilisateur) if competence["id"] in ids_projet ]
    return competences_utilisateur_projet


def filtrage_minimal(id_projet,ids_utilisateur):
    """ 
    input : id du projet, ids des utilisateurs dont on veut tester le matching 
    avec le projet 
    output : booleen, vrai si le groupe d'utilisateurs PEUVENT participer au projet 
    specification : le groupe peut participer au projet si :
        - ils sont tous intervenant 
        - leurs compétences recouvrent bien les compétences attendues sur le projet
        - ils ont assez de temps en semaine pour se répartir la charge du projet
        sur le temps du projet
        - il n'y a pas d'utilisateur superflu qui n'a aucune compétence en rapport avec le projet
    remarque : cette fonction ne donne pas de pourcentage de matching
    """
    for id in ids_utilisateur:
        utilisateur = get_utilisateur(id)
        if not utilisateur["est_intervenant"]:
            return False 
    charge_semaine_projet = charge_par_semaine(id_projet)
    if  sum([ temps_libre(id) for id in ids_utilisateur ] ) < charge_par_semaine(id_projet) :
            return False 
    competences_projet = get_competences_projet(id_projet)
    for competence in competences_projet :
        if not any( [niveau_requis(competence,id) for id in ids_utilisateur] ):
            return False
    for id in ids_utilisateur:
        if not any( [niveau_requis(competence,id) for competence in competences_projet] ):
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

def competence_max(id_competence,n):
    if n>3:
        return -1 
    if n==1:
        ensemble_utilisateurs = get_all_utilisateurs()
        intervenants_projet = [ id for id in ensemble_utilisateurs if filtrage_minimal(id_projet,[id]) ]
        intervenant_competence = [ id for id in intervenants_projet if has_competence(id_competence,id) ]
        if intervenant_competence == []:
            return 0
        return max( [get_level_competence(id,id_competence) for id in intervenant_competence] )

def disponibilite_max_projet(id_projet,n):
    if n>3:
        return -1 
    if n==1 :
        ensemble_utilisateurs = get_all_utilisateurs()
        intervenants_projet = [ id for id in ensemble_utilisateurs if filtrage_minimal(id_projet,[id]) ]
        if intervenants_projet == []:
            return 0
        return max( [ temps_libre(id) for id in intervenants_projet ] )
    if n==2 :
        ensemble_utilisateurs = get_all_pairs_utilisateurs()
        intervenants_projet = [ c for c in ensemble_utilisateurs if filtrage_minimal(id_projet,list(c)) ]
        if intervenants_projet == []:
            return 0
        return max( sum( [temps_libre(u) for u in ids] ) for ids in intervenants_projet )
    if n==3:
        ensemble_utilisateurs = get_all_triplets_utilisateurs()
        intervenants_projet = [ c for c in ensemble_utilisateurs if filtrage_minimal(id_projet,list(c)) ]
        if intervenants_projet == []:
            return 0
        return max( sum( [temps_libre(u) for u in ids] ) for ids in intervenants_projet )

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

def fonction1(x):
    return exp(x)

def function2(x):
    return x**2

def matching_competence(projet_id,utilisateur_ids):
    competences_projet = get_competences_projet(projet_id)
    niveau_requis = [competence["niveau"] for competence in competences_projet]
    competences_utilisateurs = recuperation_competences_utilisateurs(competences_projet,utilisateur_ids)
    return sum( [fonction1(competences_utilisateurs[i]["niveau"]) - fonction1(niveau_requis[i]) for i in range(len(niveau_requis))  ] ) / sum( [fonction1(10) - fonction1(niveau) for niveau in niveau_requis] )


def matching_disponibilite(projet_id,utilisateur_ids):
    dispo_max = disponibilite_max_projet(projet_id,len(utilisateur_ids))
    if dispo_max == 0 :
        return -1
    return sum( [temps_libre(id) for id in utilisateur_ids] ) / dispo_max

def homogeneite_utilisateurs(projet_id,utilisateur_ids):
    score = 1
    competences_commune = 0
    score_competence = []
    competences_projet = get_competences_projet(projet_id)
    for competence in competences_projet:
        dist = [ abs(get_level_competence(id_1,competence["id"]) -get_level_competence(id_2,competence["id"]) ) for id_2 in utilisateur_ids  for id_1 in utilisateur_ids if id_2 > id_1 and has_competence(id_1,competence["id"]) and has_competence(id_2,competence["id"]) ]
        if dist != []:
            competences_commune += 1
            score_competence.append(1- min(dist)/10 )
        else:
            score *= 1
    if len(score_competence) == 0:
        return competences_commune/len(competences_projet)
    return competences_commune/len(competences_projet) * ( sum(score_competence)/len(score_competence) )

def homogeneite_projet(projet_id,projet_ids):
    competences_projet = get_competences_projet(projet_id)
    res = 1
    for id in projet_ids:
        res *= 1-(competence_commune(projet_id,id)/len(competences_projet) )
    return 1  - res

def matching_experience(projet_id,utilisateur_ids):
    projet_ids = get_projet_experience(utilisateur_ids)
    return homogeneite_projet(projet_id,projet_ids)


def matching_nombre_intervenants(projet_id,utilisateur_ids):
    n = len(utilisateur_ids)
    homogeneite = homogeneite_utilisateurs(projet_id,utilisateur_ids)
    return (function2(1/n)/function2(1/1)) * (1-homogeneite)



def matching(projet_id,utilisateur_ids):
    score_competence = matching_competence(projet_id,utilisateur_ids)
    score_disponibilite = matching_disponibilite(projet_id,utilisateur_ids)
    score_nombre_intervenants = matching_nombre_intervenants(projet_id,utilisateur_ids)
    score_experience = matching_experience(projet_id,utilisateur_ids)
    print(utilisateur_ids)
    print(score_competence,score_disponibilite,score_nombre_intervenants,score_experience)
    print()
    score = score_competence*(1/4) + score_disponibilite*(1/4) + score_nombre_intervenants*(1/4)+score_experience*(1/4)
    return round(score*100)



def best_composition(projet_id):
    selection = []
    for id in get_all_utilisateurs():
        if filtrage_minimal(projet_id,[id]):
            selection.append( ([id],matching(projet_id,[id])) )
    for pair in get_all_pairs_utilisateurs():
        if filtrage_minimal(projet_id,list(pair)):
            selection.append( (list(pair),matching(projet_id,list(pair))) )
    for triplet in get_all_triplets_utilisateurs():
        if filtrage_minimal(projet_id,list(triplet)):
            selection.append( (list(triplet),matching(projet_id,list(triplet))) )
    return selection


for id in range(1,10):
    print(id,best_composition(id))


con.close()
