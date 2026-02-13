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
        ("admin@tns.fr","pwd","Admin","Root",1,0,34),
        ("manager1@tns.fr","pwd","Durand","Sophie",2,0,32),
        ("manager2@tns.fr","pwd","Martin","Paul",2,0,32),
        ("chef1@tns.fr","pwd","Bernard","Luc",3,0,21),
        ("chef2@tns.fr","pwd","Petit","Emma",3,0,3),

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
        ("bob2@tns.com","bob","BobDoc","Client",6,0,12),

        ("junior6@tns.fr","pwd","Lefebvre","Marie",5,1,20),
        ("junior7@tns.fr","pwd","Dubois","Jeanne",5,1,20),
        ("junior8@tns.fr","pwd","Leroy","Jean",5,1,20),
        ("junior9@tns.fr","pwd","Roux","Pierre",5,1,21),
        ("junior10@tns.fr","pwd","Fournier","Michel",5,1,35),
        ("junior11@tns.fr","pwd","Rousseau","Catherine",5,1,20),
        ("junior12@tns.fr","pwd","Dupont","Jacques",5,1,10),
        ("junior13@tns.fr","pwd","Lambert","Louis",5,1,10),
        ("junior14@tns.fr","pwd","Muller","Nicole",5,1,31),
        ("junior15@tns.fr","pwd","Blanc","Paul",5,1,16),
        ("junior16@tns.fr","pwd","Boyer","Madelaine",5,1,20),
        ("junior17@tns.fr","pwd","Garnier","Robert",5,1,20),
        ("junior18@tns.fr","pwd","Legrand","Roger",5,1,20),
        ("client1@tns.com","client","Dupont","Claire",6,0,5),
        ("client2@tns.com","client","Lefevre","Marc",6,0,8)

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
        ("DataPlus","Marie Data","contact@dataplus.com","0202020202","Actif",1,48.6850,6.1800,"10 Rue Saint-Dizier, Nancy"),
        ("InnovX","Paul Innov","contact@innovx.com","0303030303","Prospect",1,48.6900,6.1820,"3 Rue de la Visitation, Nancy"),
        ("OldSoft","Claire Old","contact@oldsoft.com","0404040404","Ancien",1,48.6950,6.1780,"7 Rue Charles III, Nancy"),
        ("NetSecure","Julien Morel","julien@netsecure.fr","0612345678","Actif",1,48.6895,6.1820,"15 Rue Saint-Jean, Nancy"),
        ("EcoBat","Sophie Renard","contact@ecobat.fr","0699887766","Prospect",1,48.6752,6.1608,"3 Rue Jeanne d'Arc, Nancy"),
        ("BuildTech","Antoine Muller","antoine@buildtech.fr","0610101010","Actif",1,48.6880,6.1905,"27 Rue Saint-Dizier, Nancy"),
        ("NovaConsult","Laura Henry","contact@novaconsult.fr","0620202020","Prospect",1,48.6942,6.1812,"9 Rue des Quatre Églises, Nancy"),
        ("FastLog","Kevin Robert","kevin@fastlog.fr","0630303030","Actif",1,48.6765,6.1689,"18 Rue de la Colline, Nancy"),
        ("MediCare+","Nathalie Lopez","contact@medicareplus.fr","0640404040","Actif",1,48.7010,6.1654,"2 Rue Mon Désert, Nancy"),
        ("UrbanWeb","Thomas Colin","thomas@urbanweb.fr","0650505050","Prospect",1,48.6853,6.1780,"14 Rue Gambetta, Nancy"),
        ("ArtisanBois","Pierre Faure","p.faure@artisanbois.fr","0660606060","Actif",1,48.6927,6.1701,"6 Rue Charles III, Nancy"),
        ("CleanOffice","Isabelle Noël","contact@cleanoffice.fr","0670707070","Ancien",1,48.6794,6.1866,"33 Rue Jeanne d’Arc, Nancy"),
        ("RestoSaveurs","Olivier Marchal","olivier@restosaveurs.fr","0680808080","Actif",1,48.6988,6.1733,"1 Place Stanislas, Nancy"),
        ("SecureIT","Camille Perez","camille@secureit.fr","0690909090","Prospect",1,48.6825,6.1795,"12 Rue des Ponts, Nancy"),
        ("AgriNova","Julien Perrot","contact@agrinova.fr","0611112233","Actif",1,48.6870,6.1725,"20 Rue des Dominicains, Nancy")
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
        ("Convention Beta","Projet Beta pour GreenSolutions",date(2025,4,1),date(2025,6,30),2),
        ("Convention NetSecure","Sécurisation réseau",date(2025,5,1),date(2025,9,30),9),
        ("Convention EcoBat","Bâtiment durable",date(2025,6,1),date(2025,12,31),10),
        ("Convention BuildTech","Déploiement IT",date(2025,7,1),date(2025,11,30),11),
        ("Convention NovaConsult","Consulting stratégique",date(2025,3,15),date(2025,9,15),12),
        ("Convention FastLog","Optimisation logistique",date(2025,1,15),date(2025,7,15),13),
        ("Convention MediCare+","Système patient",date(2025,2,1),date(2025,8,1),14),
        ("Convention UrbanWeb","Site e-commerce",date(2025,4,15),date(2025,10,15),15),
        ("Convention ArtisanBois","ERP menuiserie",date(2025,5,1),date(2025,11,1),16),
        ("Convention CleanOffice","Gestion nettoyage",date(2025,1,20),date(2025,7,20),17),
        ("Convention RestoSaveurs","Application réservation",date(2025,3,1),date(2025,9,1),18),
        ("Convention SecureIT","Audit cybersécurité",date(2025,2,15),date(2025,8,15),19),
        ("Convention AgriNova","Système gestion ferme",date(2025,4,1),date(2025,10,1),20)
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
    projets =[
    (2, None, "BI", "Dashboard BI", 12000, 180, date(2025,5,1), date(2025,11,30), "En cours", None),
    (3, None, "Audit", "Audit technique", 5000, 80, date(2025,3,1), date(2025,4,30), "Terminé", None),
    (4, None, "API", "test", 4000, 80, date(2024,1,1), date(2024,3,1), "En cours", None),

    (1, 1, "Projet C", "programmation en C", 300, 60, date(2026,3,1), date(2026,3,29), "En cours", None),
    (1, 1, "Projet IA", "integration d'une IA", 300, 80, date(2026,3,1), date(2026,3,29), "En cours", None),
    (1, 1, "Projet Mathématique", "", 300, 60, date(2026,3,1), date(2026,3,29), "En cours", None),
    (1, 1, "Projet Embarqué", "", 300, 60, date(2026,3,1), date(2026,3,29), "En cours", None),
    (1, 1, "Projet Sécurité", "", 300, 60, date(2026,3,1), date(2026,3,29), "En cours", None),

    (1, 2, "Projet 1", "", 300, 60, date(2026,3,1), date(2026,3,29), "Terminé", None),
    (1, 2, "Projet 2", "", 300, 60, date(2026,3,1), date(2026,3,29), "Terminé", None),
    (1, 2, "Projet 3", "", 300, 60, date(2026,3,1), date(2026,3,29), "En cours", None),

    (1, 1, "ERP", "Refonte ERP", 20000, 300, date(2025,1,15), date(2025,9,30), "Terminé", None),
    (2, 1, "CRM", "CRM interne", 15000, 200, date(2025,2,1), date(2025,8,31), "Terminé", None),
    (3, 2, "BI", "Dashboard BI", 12000, 180, date(2025,5,1), date(2025,11,30), "En cours", None),
    (4, 3, "Audit", "Audit technique", 5000, 80, date(2025,3,1), date(2025,4,30), "Terminé", None),
    (5, 4, "API", "Test API interne", 4000, 80, date(2024,1,1), date(2024,3,1), "En cours", None),
    (6, 7, "Firewall", "Déploiement pare-feu", 8000, 120, date(2025,5,10), date(2025,8,10), "En cours", None),
    (7, 8, "BIM", "Maquette numérique", 10000, 150, date(2025,6,1), date(2025,12,1), "En cours", None),
    (8, 9, "IT Deployment", "Installation serveurs", 15000, 200, date(2025,7,5), date(2025,11,30), "Planifié", None),
    (9, 10, "Strat Consulting", "Analyse marché", 9000, 100, date(2025,3,20), date(2025,9,20), "En cours", None),
    (10, 11, "Logistics Optim", "Optimisation flux", 11000, 140, date(2025,1,20), date(2025,7,20), "Terminé", None),
    (11, 12, "Patient Sys", "Développement logiciel patient", 13000, 160, date(2025,2,10), date(2025,8,10), "En cours", None),
    (12, 13, "E-commerce", "Refonte site web", 7000, 90, date(2025,4,20), date(2025,10,20), "Planifié", None),
    (13, 14, "ERP Menuiserie", "Gestion production bois", 12000, 180, date(2025,5,5), date(2025,11,5), "En cours", None),
    (14, 15, "Cleaning Management", "Logiciel gestion équipes", 6000, 70, date(2025,1,25), date(2025,7,25), "Terminé", None),
    (15, 16, "Reservation App", "Application mobile", 9000, 110, date(2025,3,5), date(2025,9,5), "En cours", None),
    (16, 17, "Cyber Audit", "Audit sécurité complète", 14000, 200, date(2025,2,20), date(2025,8,20), "En cours", None),
    (17, 18, "Farm Management", "Logiciel ferme", 10000, 150, date(2025,4,5), date(2025,10,5), "Planifié", None)
    ]

    for p in projets:
        cur.execute("""
        INSERT OR IGNORE INTO Projets
        (projet_id, convention_id, nom_projet, description, budget, charge_travail, date_debut, date_fin, statut, doc_dossier)
        VALUES (?,?,?,?,?,?,?,?,?,?)
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
        (14,"HTML",8),(15,"PostgreSQL",2),
        
        (16,"Langage C",None),
        (17,"IA",None),
        (18,"Mathématiques numériques",None),
        (19,"Théorie des langages",None),
        (20,"Logiciel embarqué",None),
        (21,"Cryptographie",12),
        
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
        ("Post-Mortem", "2026-04-23", 0, 5)
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

        (19,16,5),(20,16,6),(21,16,7),
        (22,17,6),(23,17,6),
        (24,18,6),(24,19,6),
        (25,18,6),
        (26,19,6),
        (27,20,6),
        (28,20,6),
        (29,21,6),
        (30,21,6),
        (31,21,6),
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
        (5,1,7),(5,13,6),(5,15,5),

        (6,16,6),
        (7,17,6),
        (8,18,6),
        (8,19,6),
        (9,20,6),
        (10,21,6),
        (11,12,6),
        (12,21,6)
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
        (27,13,1,None),
        (30,11,1,None),
        (31,12,1,None)
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
