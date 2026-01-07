from typing import Any

from math import exp,sqrt

from database import *
from tools import get_db

class _DBProxy:
    """Petit proxy qui délègue dynamiquement vers l'instance réelle renvoyée par `get_db()`.
    Permet de garder la syntaxe historique `db.execute(...)` sans dépendre d'une variable
    globale initialisée ailleurs.
    """
    def __getattr__(self, item):
        real = get_db()
        return getattr(real, item)

_db_instance = _DBProxy()
db: Any = _db_instance

#### Configuration base de donnée ###




### ------------------------ ###

### Fonctions liées à l'algorithme de Matching ###

def get_projet(projet_id):
    """ 
    input : id d'un projet
    output : un dictionnaire contenant les informations sur le projet 
    """
    query = """SELECT * FROM Projets WHERE projet_id=? """
    res = db.execute(query,(projet_id,))
    p = res.fetchone()
    if not p:
        # Retourner un dictionnaire sûr avec valeurs par défaut
        return {"id": projet_id, "nom": None, "charge": 0, "debut": None, "fin": None}
    projet = {"id" : p[0], "nom" : p[2],"charge":p[5], "debut" : p[6], "fin" : p[7]}
    return projet 

def get_utilisateur(utilisateur_id):
    """ 
    input : id d'un utlisateur
    output : un dictionnaire contenant les informations sur l'utilisateur 
    """
    res = db.execute("SELECT * FROM Utilisateurs WHERE utilisateur_id=?",(utilisateur_id,))
    u = res.fetchone()
    utilisateur = {"id":u[0],"nom":u[4],"prenom":u[5],"est_intervenant": u[8], "heures" : u[9]}
    return utilisateur

def get_competences_utilisateur(utilisateur_id):
    """ 
    input : id d'un utilisateur
    output : liste de toutes les compétences de l'utilisateur sous forme d'une liste de dictionnaires 
    """
    res = db.execute("""SELECT * FROM Intervenant_competences 
                        JOIN Competences ON Intervenant_competences.competence_id =
                        Competences.competence_id 
                        WHERE intervenant_id=?""",(utilisateur_id,))
    competences = []
    for c in res.fetchall():
        competence = { "id":c[1], "nom" : c[4], "niveau" : c[2]}
        competences.append(competence)
    return competences

def get_competences_projet(projet_id):
    """ 
    input : id d'un projet
    output : liste de toutes les compétences requises pour le projet sous forme d'une liste de dictionnaires 
    """
    res = db.execute("""SELECT * FROM Projet_competences
                        JOIN Competences ON Projet_competences.competence_id = Competences.competence_id 
                        WHERE projet_id=? ORDER BY projet_id """, (projet_id,) )
    competences = []
    for c in res.fetchall():
        competence = { "id":c[1], "nom" : c[4], "niveau" : c[2]}
        competences.append(competence)
    return competences

def get_nb_intervenant(projet_id):
    """ 
    input : id d'un projet
    output : entier représentant le nombre d'intervenants travaillant ou ayant travaillé sur le projet
    """
    res = db.execute("""SELECT Count(Distinct(utilisateur_id)) FROM Travaille_sur
                        WHERE projet_id=?""", (projet_id,) )
    return res.fetchone()[0]

def get_projets_participe_utilisateur(utilisateur_id):
    """ 
    input : id d'un projet
    output : liste des ids des projets sur lesquels l'utilisateur travaille actuellement sous forme d'une liste d'entiers
    """
    res = db.execute("""SELECT Travaille_sur.projet_id FROM Travaille_sur
                    JOIN Projets ON Travaille_sur.projet_id = Projets.projet_id
                    WHERE est_intervenant_sur_projet == true AND
                    statut = 'En cours' AND
                     utilisateur_id=?""", (utilisateur_id, ))
    return [elt[0] for elt in res.fetchall()]

def get_all_utilisateurs():
    """ 
    input : rien 
    output : ids de l'ensemble des utilisateurs de la base de données 
    """
    res = db.execute("""SELECT utilisateur_id FROM Utilisateurs """)
    return [ elt[0] for elt in res.fetchall() ]

def get_all_pairs_utilisateurs():
    """ 
    input : rien 
    output : ensemble des pairs  d'utilisateurs de la base de données 
    """
    res = db.execute("""SELECT u1.utilisateur_id,u2.utilisateur_id FROM
                        Utilisateurs AS u1 JOIN Utilisateurs AS u2 
                        ON u1.utilisateur_id < u2.utilisateur_id  """)
    return [(elt[0],elt[1]) for elt in res.fetchall()]

def get_all_triplets_utilisateurs():
    """ 
    input : rien 
    output : ensemble des triplets d'utilisateurs de la base de données 
    """
    res = db.execute("""SELECT u1.utilisateur_id,u2.utilisateur_id,u3.utilisateur_id FROM
                        Utilisateurs AS u1 JOIN Utilisateurs AS u2 
                        ON u1.utilisateur_id < u2.utilisateur_id
                        JOIN Utilisateurs AS u3 
                        ON u2.utilisateur_id < u3.utilisateur_id  """)
    return [(elt[0],elt[1],elt[2]) for elt in res.fetchall()]


def has_competence(utilisateur_id,competence_id):
    """ 
    input : l'id d'un utilisateur et l'id d'une competence 
    output : vrai si l'utilisateur possède la compétence (niveau 0 à 10) et faux sinon 
    """
    res = db.execute(""" SELECT * FROM Intervenant_competences
                            WHERE intervenant_id =? 
                            AND competence_id =?""", (utilisateur_id,competence_id )  )
    return res.fetchone() != None 

def get_level_competence(utilisateur_id,competence_id):
    """ 
    input : l'id d'un utilisateur et l'id d'une competence 
    output : le niveau de la compétence de l'utilisateur 
    remarque : renvoie une erreur si l'utilisateur n'a pas la compétence  
    """
    res = db.execute(""" SELECT niveau FROM Intervenant_competences
                            WHERE intervenant_id =? 
                            AND competence_id =?""", (utilisateur_id,competence_id) )
    resultat = res.fetchone()
    return resultat[0]

def competences_communes_etendu(id_projet_courant,id_projet_termine):
    """ 
    input : id d'un projet, id d'un projet termine 
    output : un nombre représentant les points communs du point de vue des compétences entre le premier projet et le projet terminé
    specification : 
        - chaque compétence commune entre les deux projets vaut 1 points 
        - chaque compétence parent du projet terminé qui est une compétence du premier vaut 3/4 points
        - idem pour les coméptences parents du premier projet qui sont des compétences du projets terminés
        - chaque compétence parent du projet terminé étant une compétence parent d'une compétence du premier vaut 1/2
        On renvoie la somme de ces valeurs 
    """
    query = """
    WITH a AS (
        SELECT DISTINCT t_a.competence_id
        FROM (
            SELECT competence_id FROM Projet_competences WHERE projet_id = ?
            INTERSECT
            SELECT competence_id FROM Projet_competences WHERE projet_id = ?
        ) AS t_a
    ),
    B AS (
        SELECT  DISTINCT t_b.competence_id 
            FROM (
                SELECT  Distinct competence_parent AS competence_id 
                FROM (
                    SELECT *    
                    FROM Competences 
                    JOIN Projet_competences 
                        ON Competences.competence_id = Projet_competences.competence_id 
                    WHERE projet_id = ? AND Competences.competence_id NOT IN (SELECT competence_id FROM A)
                ) AS C
            
            INTERSECT 
            
                SELECT DISTINCT Competences.competence_id 
                FROM Competences 
                JOIN Projet_competences
                ON Competences.competence_id = Projet_competences.competence_id 
            WHERE projet_id = ? 
        ) AS t_b
    ),
    D AS (
        SELECT DISTINCT t_d.competence_id 
            FROM (
                SELECT Distinct competence_parent AS competence_id 
                FROM (
                    SELECT * 
                    FROM Competences
                    JOIN Projet_competences
                        ON Competences.competence_id = Projet_competences.competence_id 
                    WHERE projet_id = ? AND Competences.competence_id NOT IN (SELECT competence_id FROM A)
                )

            INTERSECT 

                SELECT DISTINCT Competences.competence_id 
                FROM Competences 
                JOIN Projet_competences 
                ON Competences.competence_id = Projet_competences.competence_id 
            WHERE projet_id = ?
        ) AS t_d 
    ),
    C AS (
        SELECT  DISTINCT t_c.competence_id 
            FROM ( 
                SELECT Distinct competence_parent AS competence_id 
                FROM (
                    SELECT * 
                    FROM Competences 
                    JOIN Projet_competences 
                        ON Competences.competence_id = Projet_competences.competence_id 
                    WHERE projet_id = ? AND Competences.competence_id NOT IN 
                        ( SELECT competence_id FROM A )
                ) 
                    
                INTERSECT 
                
                SELECT Distinct competence_parent AS competence_id 
                FROM (
                    SELECT * 
                    FROM Competences 
                    JOIN Projet_competences 
                        ON Competences.competence_id = Projet_competences.competence_id 
                    WHERE projet_id = ? 
                )
                ) AS t_c
    ),
    B_only AS (
        SELECT competence_id FROM B
        WHERE NOT EXISTS (
            SELECT 1 FROM A WHERE A.competence_id = B.competence_id
        )  
    ),
    D_only AS (
        SELECT competence_id FROM D
        WHERE NOT EXISTS (
            SELECT 1 FROM A WHERE A.competence_id = D.competence_id
        ) AND NOT EXISTS (
            SELECT 1 FROM B WHERE B.competence_id = D.competence_id 
        )
    ),
    C_only AS (
        SELECT competence_id FROM C
        WHERE NOT EXISTS (
            SELECT 1 FROM A WHERE A.competence_id = C.competence_id
        ) AND NOT EXISTS (
            SELECT 1 FROM B WHERE B.competence_id = C.competence_id 
        ) AND NOT EXISTS (
            SELECT 1 FROM D WHERE D.competence_id = C.competence_id
        )
    )
    SELECT 
        (SELECT COUNT(*) FROM A) + 0.75 * (SELECT count(*) FROM B_only) + 0.75 * (SELECT count(*) FROM D_only)
        + 0.5 * (SELECT count(*) FROM C_only)
    """
    res = db.execute(query, (id_projet_courant,id_projet_termine,id_projet_termine,id_projet_courant,id_projet_courant,id_projet_termine,id_projet_termine,id_projet_courant) )
    return  res.fetchone()[0]

def get_projet_experience(utilisateur_ids):
    """ 
    input : ids d'utilisateurs 
    output : ids des projets terminés auxquels ont participé les utilisateurs 
    """
    placeholders = ','.join(['?'] * len(utilisateur_ids))
    query = f"""
    SELECT p.projet_id
    FROM Travaille_sur AS t
    JOIN Projets AS p ON p.projet_id = t.projet_id
    WHERE utilisateur_id IN ({placeholders}) AND statut = 'Terminé'
    """
    res = db.execute(query, utilisateur_ids)
    return [ elt[0] for elt in  res.fetchall()]

def get_projet_courant(utilisateur_id,projet_id):
    """ 
    input : id d'un utilisateur et id d'un projet  
    output : ids des projets en cours auxquels participent l'utilisateur mais qui n'est pas le projet passé en entrée  
    """
    query= """
    SELECT count(p.projet_id)
    FROM Travaille_sur AS t
    JOIN Projets AS p On p.projet_id = t.projet_id
    WHERE utilisateur_id = ? AND statut = 'En cours' AND p.projet_id != ?     """
    res = db.execute(query, (utilisateur_id,projet_id) )
    return res.fetchone()[0]

def temps_projet(date_debut,date_fin) :
    """ 
    input : deux dates sous la forme YYYY-MM-DD (début et fin)
    output : temps en jour séparant les deux dates

    Cette version est plus robuste : elle accepte plusieurs formats 'YYYY-MM-DD' ou
    'YYYY-MM-DD HH:MM:SS', gère None/chaînes vides, et renvoie au minimum 1 jour
    pour éviter les divisions par zéro en aval.
    """
    from datetime import datetime, date

    # Défaut minimal pour éviter division par zéro
    MIN_DAYS = 1

    # Vérifier les entrées non définies
    if not date_debut or not date_fin:
        return MIN_DAYS

    # Fonction utilitaire de parsing avec plusieurs formats possibles
    def _parse(d):
        if isinstance(d, date) and not isinstance(d, datetime):
            return d
        if isinstance(d, datetime):
            return d.date()
        if not isinstance(d, str):
            # Si ce n'est pas une chaîne, on ne peut pas parser proprement
            return None
        s = d.strip()
        if not s:
            return None
        # Try common formats
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                parsed = datetime.strptime(s, fmt)
                return parsed.date()
            except Exception:
                continue
        # Dernier recours : tenter de séparer par '-' comme avant et construire une date
        try:
            parts = s.split('-')
            if len(parts) >= 3:
                y = int(parts[0])
                m = int(parts[1])
                # parts[2] peut contenir heure -> garder la partie date
                d_part = parts[2].split(' ')[0]
                day = int(d_part)
                return date(y, m, day)
        except Exception:
            return None

    d_start = _parse(date_debut)
    d_end = _parse(date_fin)

    if d_start is None or d_end is None:
        return MIN_DAYS

    try:
        delta = (d_end - d_start).days
    except Exception:
        return MIN_DAYS

    # Si la date de fin est antérieure ou identique, on considère 1 jour minimal
    if delta <= 0:
        return MIN_DAYS
    return int(delta)


def charge_par_semaine(projet_id):
    """ 
    input : id d'un projet 
    output : temps à allouer chaque semaine au projet pour le terminer dans exactement à la date de fin  
    """
    projet = get_projet(projet_id)
    nb_jour = temps_projet(projet.get("debut"), projet.get("fin"))
    nb_jour = max(1, nb_jour)
    try:
        return projet["charge"] / (nb_jour/7)
    except Exception:
        return 0


def charge_individuelle_par_semaine(projet_id):
    """ 
    input : id d'un projet  
    output : temps par semaine que doit allouer un intervenant travaillant sur le projet pour que celui-ci soit terminé dans les temps
    """
    nb_intervenant = get_nb_intervenant(projet_id)
    if not nb_intervenant or nb_intervenant <= 0:
        return charge_par_semaine(projet_id)
    return charge_par_semaine(projet_id)/nb_intervenant

def charge_courante_utilisateur(utilisateur_id):
    """ 
    input : id d'un utilisateur 
    output : charge de travail hebdomadaire de l'utilisateur calculée par rapport au projet sur lesquels il travaille  
    """
    return sum([charge_individuelle_par_semaine(projet_id) for projet_id in get_projets_participe_utilisateur(utilisateur_id)])

def temps_libre(utilisateur_id):
    """ 
    input : id d'un utilisateur 
    output : temps hebdomaire restant à l'utilisateur  
    """
    utilisateur = get_utilisateur(utilisateur_id)
    return utilisateur["heures"] -  charge_courante_utilisateur(utilisateur_id)


def niveau_requis(competence,utilisateur_id):
    """ 
    input : competence d'un projet sous forme de dictionnaire et id d'un utilisateur 
    output : vrai si l'utilisateur possède la compétence et a un niveau suffisant pour le projet faux sinon 
    """
    competence_id = competence["id"]
    if has_competence(utilisateur_id,competence_id):
        return get_level_competence(utilisateur_id,competence_id) >= competence["niveau"] 
    return False 

def competences_utilisateurs_projet(projet_id,utilisateur_ids):
    """
    input : id d'un projet et ids d'utilisateurs 
    output : ids et niveaux maximals des competences des utilisateurs en rapport avec le projet 
    exemple : si u1 possède c1 niveau 1, u2 possède c1 niveau 2 le p1 requiere c1 alors la fonction renvoie c1,2
    """
    placeholders = ','.join(['?'] * len(utilisateur_ids))
    query = f"""
    SELECT Competences.competence_id,max(Intervenant_competences.niveau) FROM Competences
    JOIN Intervenant_competences ON Intervenant_competences.competence_id = Competences.competence_id 
    JOIN Projet_competences ON Projet_competences.competence_id = Competences.competence_id 
    WHERE projet_id = ? AND intervenant_id IN ({placeholders})
    GROUP BY Competences.competence_id 
    """
    res = db.execute(query, [projet_id]+  utilisateur_ids )
    return res.fetchall()


def competence_max_parmi_utilisateurs(competence_id,ids_utilisateur):
    """
    input : id d'une compétence et l'ids d'utilisateurs
    output : renvoie le niveau maximal (0-10) des utilisateurs sur la compétence et l'id de l'utilisateur qui a le meilleur niveau
    remarque  renvoie -1,-1 si aucun des utilisateurs ne maîtrisent la compétence 
    """
    maximum = -1
    utilisateur = -1  
    for id in ids_utilisateur:
        if has_competence(id,competence_id) and get_level_competence(id,competence_id) > maximum :
            maximum = get_level_competence(id,competence_id)
            utilisateur = id 
    return maximum,utilisateur

beta = 3


def filtrage_minimal(id_projet,ids_utilisateur):
    """ 
    input : id du projet, ids des utilisateurs dont on veut tester le matching avec le projet 
    output : booleen, vrai si le groupe d'utilisateurs PEUVENT participer au projet 
    specification : le groupe peut participer au projet si :
        - ils sont tous intervenant 
        - ils ont assez de temps en semaine pour se répartir la charge du projet
        sur le temps du projet
        - il n'y a pas d'utilisateur superflu qui n'a aucune compétence en rapport avec le projet
        - leurs compétences recouvrent bien les compétences attendues sur le projet avec un degré de liberté beta 
    remarque : cette fonction ne donne pas de pourcentage de matching
    """
    for id in ids_utilisateur:
        utilisateur = get_utilisateur(id)
        if not utilisateur["est_intervenant"]:
            return False, [] 
    charge_semaine_projet = charge_par_semaine(id_projet)
    if  sum([ temps_libre(id) for id in ids_utilisateur ] ) < charge_semaine_projet :
            return False, []
    competences_projet = get_competences_projet(id_projet)
    for id in ids_utilisateur:
        if not any( [has_competence(id,competence["id"]) for competence in competences_projet] ):
            return False, []
    formation = []
    for competence in competences_projet :
        if not any( [ has_competence(id,competence["id"]) for id in ids_utilisateur] ):
            return False,[]
        if not any( [niveau_requis(competence,id) for id in ids_utilisateur] ):
            niveau_max, utilisateur_max = competence_max_parmi_utilisateurs(competence["id"],ids_utilisateur)
            if competence["niveau"] - niveau_max <= beta :
                formation.append( (competence["id"],utilisateur_max,competence["niveau"]-niveau_max) )
            else:
                return False, []
    if len(formation) > beta :
        return False, []
    return True,formation

def competence_max(competence_id,projet_id,n,utilisateurs_filtres):
    """
    input : l'id d'une compétence, l'id d'un projet, un entier n (1-3), un ensemble de n-uplet d'utilisateurs 
    output : le niveau maximum de la compétence parmi l'ensemble des groupes de n utilisateurs 
    """
    if n>3:
        return -1 
    if n==1:
        niveaux_competence = [ get_level_competence(id,competence_id) for id in utilisateurs_filtres if has_competence(id,competence_id) ]
        if niveaux_competence == []:
            return 0
        return max( niveaux_competence )
    if n==2 :
        niveaux_competence = [ get_level_competence(id,competence_id) for c in utilisateurs_filtres for id in c if has_competence(id,competence_id) ]
        if niveaux_competence == []:
            return 0
        return max( niveaux_competence )
    if n == 3 :
        niveaux_competence = [ get_level_competence(id,competence_id) for c in utilisateurs_filtres for id in c if has_competence(id,competence_id) ]
        if niveaux_competence == []:
            return 0
        return max( niveaux_competence )

def sum(L):
    if len(L)==0:
        return 0
    else:
        return L[0] + sum(L[1:])

def fonction1(x):
    return exp(x)

def function2(x):
    return x

def matching_competence(projet_id,utilisateur_ids,s_competence):
    """
    input : id d'un projet, ids d'utilisateurs (len = 1-3), sommes du niveaux maximales des compétences du projets possibles 
    output : float entre 0 et 1 représentant le score de compétence des utilisateurs (utilisateur_ids)
    exemple : si u1 à la compétence c1 niveau 7 et u2 a c1 niveau 8 et que le projet requiere seulement c1 niveau 6 alors 
    pour (p1,[u1],f1(8)), la fonction renvoie f1(7)/f1(8)
    """
    competences_utilisateurs = competences_utilisateurs_projet(projet_id,utilisateur_ids)
    return sum( [fonction1(competences_utilisateurs[i][1])  for i in range(len(competences_utilisateurs))  ] ) / s_competence

gamma = 1/5

def matching_disponibilite(projet_id,utilisateur_ids):
    """
    input : id d'un projet, ids d'utilisateurs
    output : float entre 0 et 1 représentant le score de disponibilité des utilisateurs
    specification : plus gamma est proche de 0 plus l'exigence en terme de disponibilité est évelé 
    """
    charge_semaine_projet = charge_par_semaine(projet_id)
    temps_dispo = sum( [temps_libre(id) for id in utilisateur_ids])
    return 1 - exp(- gamma * (temps_dispo - charge_semaine_projet)  )


epsilon = 1/2

def homogeneite_utilisateurs(projet_id,utilisateur_ids):
    """
    input : id d'un projet, ids d'utilisateurs
    output : float entre 0 et 1 représentant l'homogénéité entre les compétences des utilisateurs parmi celles qui sont requises par le projet  
    specification : plus le score est proche de 1 plus il y a homogénéité, plus epsilon est proche de 0 plus il faut de compétences en commun pour augmenter l'homogénéité  
    """
    s = 0
    score_competence = []
    competences_projet = get_competences_projet(projet_id)
    for competence in competences_projet:
        dist = [ 1 - ( abs(get_level_competence(id_1,competence["id"]) -get_level_competence(id_2,competence["id"]) ) ) /10 for id_2 in utilisateur_ids  for id_1 in utilisateur_ids if id_2 > id_1 and has_competence(id_1,competence["id"]) and has_competence(id_2,competence["id"]) ]
        if dist != []:
            s += sum(dist) 
    return 1 - exp(- epsilon * s)

alpha = 0.8

def homogeneite_projet(projet_id,projet_ids):
    """ 
    input : id d'un projet, ids de projets 
    output : float entre 0 et 1 représentant l'homogénéité entre le projet et l'ensemble des projets 
    specification : chaque compétence en commun entre le projet et un projet de l'ensemble est prise en compte, plus alpha est proche de 0, plus il faut
    de compétence en commun pour augmenter l'homonenéité
    """
    competences_projet = get_competences_projet(projet_id)
    res = 0
    for id in projet_ids:
        res += (competences_communes_etendu(projet_id,id)/len(competences_projet) )
    return 1  - exp(- alpha * res)

def matching_experience(projet_id,utilisateur_ids):
    """
    input : id d'un projet, ids d'utilisateurs
    output : float entre 0 et 1 représentant le score d'expérience des utilisateurs basé sur l'homogénéité entre leur expériences passées et le projet  
    """
    projet_ids = get_projet_experience(utilisateur_ids)
    return homogeneite_projet(projet_id,projet_ids)


def matching_nombre_intervenants(projet_id,utilisateur_ids):
    """
    input : id d'un projet, ids d'utilisateurs
    output : float entre 0 et 1 représentant le score basé sur la composition du groupe 
    specification : plus le nombre d'intervenants dans le groupe est petit et plus ces derniers sont hétérogène plus le score est bon 
    """
    n = len(utilisateur_ids)
    homogeneite = homogeneite_utilisateurs(projet_id,utilisateur_ids)
    return (function2(1/n)/function2(1/1)) * (1-homogeneite)


def matching_charge_mentale(projet_id,utilisateur_ids):
    """
    input : id d'un projet, ids d'utilisateurs
    output : float entre 0 et 1 représentant le score de charge mentale 
    """
    liste_nombre_projets = [ get_projet_courant(id,projet_id) for id in utilisateur_ids ]
    if liste_nombre_projets == []:
        return 1
    return 1/(1+max(liste_nombre_projets))

delta = 0.3

def matching(projet_id,utilisateur_ids,s_competence):
    """
    input : id d'un projet, ids d'utilisateurs
    output : entier entre 0 et 100 représentant le score de matching entre le groupe d'utilisateurs et le projet  
    """
    score_competence = matching_competence(projet_id,utilisateur_ids,s_competence)
    score_disponibilite = matching_disponibilite(projet_id,utilisateur_ids)
    score_nombre_intervenants = matching_nombre_intervenants(projet_id,utilisateur_ids)
    score_charge_mentale = matching_charge_mentale(projet_id,utilisateur_ids)
    score_experience = matching_experience(projet_id,utilisateur_ids)
    score_indispensable = ( score_competence**2 * score_disponibilite * score_nombre_intervenants * score_charge_mentale )**(1/5)
    #print(utilisateur_ids,  score_competence,score_disponibilite,score_nombre_intervenants,score_charge_mentale,score_experience)
    #print("oui",score_indispensable)
    return round(  (  score_indispensable * (1 +  delta* ( score_experience - score_indispensable ) )  )* 100 )


def dichotomie(L,elt):
    d = 0
    f = len(L)-1
    while d<=f:
        m = (f-d)//2 + d
        if L[m][1] == elt[1]:
            L.insert(m,elt)
            return
        elif L[m][1] < elt[1]:
            d = m+1 
        else:
            f = m-1
    L.insert(d,elt)
    return 
    

def ajout_intervenants(L,elt,k):
    if len(L)<k:
        dichotomie(L,elt)
    else:
        if L[0][1] >= elt[1]:
            return
        else:
            L.pop(0)
            dichotomie(L,elt)
            return 

def redondance(utilisateurs_valides,utilisateur_ids):
    for id1 in utilisateur_ids:
        if [id1] in utilisateurs_valides:
            return True 
        for id2 in utilisateur_ids:
            if [id1,id2] in utilisateurs_valides:
                return True
    return False 

def best_composition(projet_id):
    """
    input : id d'un projet
    output : liste des 5 meilleurs groupes d'intervenants pour le projet 
    """
    utilisateurs_valides = []
    selection = []
    competences_projet = get_competences_projet(projet_id)
    niveau_requis = [competence["niveau"] for competence in competences_projet]
    utilisateurs = get_all_utilisateurs()
    s_competence = sum( [ max( fonction1( competence_max(competences_projet[i]["id"],projet_id,1,utilisateurs)) ,fonction1( niveau_requis[i] ) ) if i<len(niveau_requis) else 0 for i in range(len(competences_projet))] )
    for id in utilisateurs:
        valide,formation = filtrage_minimal(projet_id,[id])
        if valide:
            ajout_intervenants(selection, ([id],matching(projet_id,[id],s_competence),formation),5 )
            if formation == []:
                utilisateurs_valides.append([id])
    pairs = get_all_pairs_utilisateurs()
    s_competence = sum( [ max( fonction1( competence_max(competences_projet[i]["id"],projet_id,2,pairs)) ,fonction1( niveau_requis[i] ) ) if i<len(niveau_requis) else 0 for i in range(len(competences_projet))] )
    for pair in pairs:
        valide,formation = filtrage_minimal(projet_id,list(pair))
        if valide:
            if not redondance(utilisateurs_valides,list(pair)):
                ajout_intervenants(selection, ( list(pair), matching(projet_id,list(pair),s_competence),formation ),5 )
            if formation == []:
                utilisateurs_valides.append( list(pair) )
    triplets = get_all_triplets_utilisateurs()
    s_competence = sum( [ max( fonction1( competence_max(competences_projet[i]["id"],projet_id,3,triplets)) ,fonction1( niveau_requis[i] ) ) if i<len(niveau_requis) else 0 for i in range(len(competences_projet))] )
    for triplet in triplets:
        valide,formation = filtrage_minimal(projet_id,list(triplet))
        if valide:
            if not redondance(utilisateurs_valides,list(triplet)):
                ajout_intervenants(selection, ( list(triplet), matching(projet_id,list(triplet),s_competence),formation ),5 )
    return selection


### ------------------------ ###

### Fermeture de la connexion à la base de données ### 


### ------------------------ ###