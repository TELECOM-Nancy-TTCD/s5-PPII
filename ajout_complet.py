import os
import sqlite3
import base64
from hashlib import scrypt
from datetime import date, datetime, timedelta
import random

DB_PATH = "database/database.db"

def hash_password(mdp: str):
    salt = os.urandom(16)
    h = scrypt(mdp.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.b64encode(salt + h).decode()

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # =========================================================
    # ROLES
    # =========================================================
    print("➤ Ajout des rôles...")
    roles = [
    ("Admin", 0, 1,1,1, 1,1, 1,1, 1,1,1, 1, 1,1, 1, 1,1),
    ("Manager", 1, 0,1,0, 1,1, 1,1, 1,1,1, 1, 0,1, 1, 1,1),
    ("Chef de projet", 2, 0,0,0, 1,1, 1,1, 1,1,1, 1, 0,1, 1, 0,0),
    ("Intervenant senior", 3, 0,0,0, 1,0, 0,0, 1,0,0, 0, 1,0, 1, 0,0),
    ("Intervenant junior", 4, 0,0,0, 1,0, 0,0, 1,0,0, 0, 1,0, 0, 0,0),
    ("Membre", 5, 0,0,0, 0,0, 0,0, 0,0,0, 0, 0,0, 0, 0,0),
]

    for r in roles:
        cur.execute("""
            INSERT OR IGNORE INTO Roles
            (nom, hierarchie,
            administrateur, peut_gerer_utilisateurs, peut_gerer_roles,
            peut_lire_clients, peut_gerer_clients,
            peut_creer_interactions, peut_gerer_interactions,
            peut_lire_projets, peut_gerer_projets, peut_gerer_jalons,
            peut_assigner_intervenants,
            peut_lire_utilisateurs, peut_acceder_documents,
            peut_gerer_competences, peut_lancer_matching, peut_exporter_csv)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, r)

    print("   ✔ Rôles ajoutés.\n")
    # =========================================================
    # UTILISATEURS
    # =========================================================
    print("➤ Ajout des utilisateurs...")
    users = [
        ("admin@tns.fr","pwd","Admin","Root",1,0,None),
        ("manager1@tns.fr","pwd","Durand","Sophie",2,0,None),
        ("manager2@tns.fr","pwd","Martin","Paul",2,0,None),
        ("chef1@tns.fr","pwd","Bernard","Luc",3,0,None),
        ("chef2@tns.fr","pwd","Petit","Emma",3,0,None),

        ("interv1@tns.fr","pwd","Moreau","Alice",4,1,40),
        ("interv2@tns.fr","pwd","Simon","Bob",4,1,35),
        ("interv3@tns.fr","pwd","Laurent","Chloé",4,1,30),
        ("interv4@tns.fr","pwd","Girard","Eva",4,1,40),
        ("interv5@tns.fr","pwd","Andre","Leo",4,1,35),

        ("junior1@tns.fr","pwd","Garcia","Hugo",5,1,25),
        ("junior2@tns.fr","pwd","Roux","Lina",5,1,20),
        ("junior3@tns.fr","pwd","Fournier","Noah",5,1,20),
        ("junior4@tns.fr","pwd","Mercier","Mila",5,1,25),
        ("junior5@tns.fr","pwd","Blanc","Adam",5,1,20),

        ("john@admin.tns.com","superadmin","John","TNS",1,0,169),
        ("bob@tns.com","bob","Bob","Client",6,0,0),
        ("bob2@tns.com","bob","BobDoc","Client",6,0,12)
    ]

    for u in users:
        cur.execute("""
        INSERT OR IGNORE INTO Utilisateurs
        (email,mot_de_passe_hashed,mot_de_passe_expire,nom,prenom,
         role_id,est_intervenant,heures_dispo_semaine)
        VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
        """, (u[0],hash_password(u[1]),u[2],u[3],u[4],u[5],u[6]))

    print("   ✔ Utilisateurs ajoutés.\n")
    # =========================================================
    # CLIENTS
    # =========================================================
    print("➤ Ajout des clients...")
    clients = [
        ("TechCorp","Alice Martin","alice@techcorp.com","0601020304","Actif",1,48.6921,6.1844,"12 Rue de la République, Nancy"),
        ("GreenSolutions","Bruno Petit","bruno@greensol.fr","0605060708","Actif",1,48.6738,6.1560,"8 Avenue du Général Leclerc, Nancy"),
        ("Boulangerie Dupont","Claire Dupont","contact@dupont-boulangerie.fr","0677889900","Prospect",1,48.7002,6.1740,"5 Rue des Carmes, Nancy"),
        ("AutoPlus Garage","David Leroy","david@autoplus.fr","0655443322","Actif",1,48.6930,6.2000,"23 Rue Stanislas, Nancy"),
        ("ImmoCity","Eva Lambert","eva@immocity.fr","0611223344","Ancien",1,48.6800,6.1700,"41 Boulevard d'Haussonville, Nancy"),
        ("DataPlus","Marie Data","contact@dataplus.com","0202020202","Actif",2,None,None,None),
        ("InnovX","Paul Innov","contact@innovx.com","0303030303","Prospect",3,None,None,None),
        ("OldSoft","Claire Old","contact@oldsoft.com","0404040404","Ancien",4,None,None,None)
    ]

    for c in clients:
        cur.execute("""
        INSERT OR IGNORE INTO Clients
        (nom_entreprise,contact_nom,contact_email,contact_telephone,
         type_client,interlocuteur_principal_id,localisation_lat,localisation_lng,address)
        VALUES (?,?,?,?,?,?,?,?,?)
        """, c)
    print("   ✔ Clients ajoutés.\n")
    # =========================================================
    # CONVENTIONS
    # =========================================================
    print("➤ Ajout des conventions...")
    conventions = [
        ("Convention TechCorp","Projet long terme",date(2025,1,1),date(2025,12,31),1),
        ("Convention DataPlus","Analyse données",date(2025,2,1),date(2025,10,31),2),
        ("Convention InnovX","Étude faisabilité",date(2025,3,1),date(2025,6,30),3),
        ("Convention OldSoft","Maintenance",date(2024,1,1),date(2024,12,31),4),
        ("Convention Alpha","Projet Alpha pour TechCorp",date(2025,4,1),date(2025,6,30),1),
        ("Convention Beta","Projet Beta pour GreenSolutions",date(2025,4,1),date(2025,6,30),2)
    ]

    for c in conventions:
        cur.execute("""
        INSERT OR IGNORE INTO Conventions
        (nom_convention,description,date_debut,date_fin,client_id)
        VALUES (?,?,?,?,?)
        """, c)
    print("   ✔ Convention ajoutés.\n")
    # =========================================================
    # PROJETS
    # =========================================================
    print("➤ Ajout des projets...")
    projets = [
        (1,"ERP","Refonte ERP",20000,300,date(2025,1,15),date(2025,9,30),"Terminé"),
        (1,"CRM","CRM interne",15000,200,date(2025,2,1),date(2025,8,31),"Terminé"),
        (2,"BI","Dashboard BI",12000,180,date(2025,5,1),date(2025,11,30),"En cours"),
        (3,"Audit","Audit technique",5000,80,date(2025,3,1),date(2025,4,30),"Terminé"),
        (4,"API","test",4000,80,date(2024,1,1),date(2024,3,1),"En cours")
    ]

    for p in projets:
        cur.execute("""
        INSERT OR IGNORE INTO Projets
        (convention_id,nom_projet,description,budget,charge_travail,date_debut,date_fin,statut)
        VALUES (?,?,?,?,?,?,?,?)
        """, p)
    print("   ✔ Projets ajoutés.\n")
    # =========================================================
    # COMPETENCES
    # =========================================================
    print("➤ Ajout des compétences...")
    competences = [
        (1,"Python",None),(2,"SQL",None),(3,"Java",None),
        (4,"Gestion de projet",None),(5,"Data Analysis",None),
        (6,"Machine Learning",None),(7,"Dev Backend",3),
        (8,"Dev Frontend",None),(9,"Cloud",None),
        (10,"Docker",9),(11,"Communication",None),
        (12,"Cybersécurité",None),(13,"Flask",1),
        (14,"HTML",8),(15,"PostgreSQL",2)
    ]

    for c in competences:
        cur.execute("""
        INSERT OR IGNORE INTO Competences
        (competence_id,nom,competence_parent)
        VALUES (?,?,?)
        """, c)
    print("   ✔ Compétences ajoutées.\n")

    # ==========================
    # JALONS
    # ==========================
    jalons = [
        # description, date_fin, est_complete, projet_id
        ("signature de la charte de projet", "2025-04-28", 1, 1),
        ("Implémentation de la base de données", "2025-04-29", 1, 3),
        ("Implémentation du Flask", "2025-04-29", 0, 3),
        ("Post-Mortem", None, 0, 5)
    ]

    for j in jalons:
        cur.execute("""
            INSERT OR IGNORE INTO Jalons
            (description, date_fin, est_complete, projet_id)
            VALUES (?, ?, ?, ?)
        """, j)

    print("   ✔ Jalons ajoutés.\n")

    # ==========================
    # INTERACTIONS
    # ==========================
    interaction_examples = [
        "Appel rapide pour valider l’avancement.",
        "Envoi d’un mail contenant des documents complémentaires.",
        "Discussion sur le cahier des charges.",
        "Relance client concernant la signature.",
        "Point technique sur les contraintes du projet.",
        "Retour du client au sujet du devis.",
        "Organisation d’un rendez-vous de suivi.",
        "Échange informel sur les prochaines étapes."
    ]

    # Récupération IDs existants
    cur.execute("SELECT client_id FROM Clients")
    all_clients = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT utilisateur_id FROM Utilisateurs")
    all_users = [row[0] for row in cur.fetchall()]

    for client_id in all_clients:
        for _ in range(random.randint(2, 5)):
            contenu = random.choice(interaction_examples)
            utilisateur = random.choice(all_users) if all_users else None
            date_str = (datetime.now() - timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""
                INSERT OR IGNORE INTO Interactions
                (date_time_interaction, titre, contenu, type_interaction_id, client_id, utilisateur_id)
                VALUES (?, 'Message', ?, 'other', ?, ?)
            """, (date_str, contenu, client_id, utilisateur))

    print("   ✔ Interactions ajoutées.\n")

    # ==========================
    # INTERVENANT_COMPETENCES
    # ==========================
    intervenant_competences = [
        # intervenant_id, competence_id, niveau
        (6, 1, 8), (6, 2, 7), (6, 5, 10),
        (7, 3, 7), (7, 7, 8),
        (8, 8, 7), (8, 11, 6),
        (9, 1, 5), (9, 2, 4),
        (10, 8, 6),
        (11, 9, 5),
        (12, 6, 8), (12, 10, 7),
        (13, 4, 7),
        (14, 2, 5),
        (15, 12, 4),(15,3,6),(15,7,7),
        (16,1,9),(16,13,8),(16,15,6),
        (17,1,8),(17,13,4),(17,15,7),
        (18,1,6),(18,13,5),(18,15,5),
    ]

    for ic in intervenant_competences:
        cur.execute("""
            INSERT OR IGNORE INTO Intervenant_competences
            (intervenant_id, competence_id, niveau)
            VALUES (?, ?, ?)
        """, ic)

    print("   ✔ Intervenant compétences ajoutées.\n")

    # ==========================
    # PROJET_COMPETENCES
    # ==========================
    projet_competences = [
        # projet_id, competence_id, niveau_requis
        (1, 1, 7), (1, 13, 6), (1, 4, 6),(1,5,5),
        (2, 3, 6), (2, 7, 7),
        (3, 5, 6),
        (5,1,7),(5,13,6),(5,15,5)
    ]

    for pc in projet_competences:
        cur.execute("""
            INSERT OR IGNORE INTO Projet_competences
            (projet_id, competence_id, niveau_requis)
            VALUES (?, ?, ?)
        """, pc)

    print("   ✔ Projet compétences ajoutées.\n")

    # ==========================
    # TRAVAILLE_SUR
    # ==========================
    travaille_sur = [
        # utilisateur_id, projet_id, est_intervenant_sur_projet, poste
        (4, 1, 0, None),
    ]

    for ts in travaille_sur:
        cur.execute("""
            INSERT OR IGNORE INTO Travaille_sur
            (utilisateur_id, projet_id, est_intervenant_sur_projet, poste)
            VALUES (?, ?, ?, ?)
        """, ts)

    print("   ✔ Travaille_sur ajoutés.\n")

    conn.commit()
    conn.close()
    print("✅ BASE COMPLÈTE — TOUTES LES TABLES, TOUTES LES DONNÉES")

if __name__ == "__main__":
    main()
