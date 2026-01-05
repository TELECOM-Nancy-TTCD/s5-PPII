import sqlite3
from datetime import date

conn = sqlite3.connect("database/database.db")
cursor = conn.cursor()

# =====================
# 1. ROLES
# =====================
roles = [
    (1, "Admin", 10, 1, 1),
    (2, "Manager", 7, 1, 0),
    (3, "Chef de projet", 5, 0, 0),
    (4, "Intervenant senior", 3, 0, 0),
    (5, "Intervenant junior", 1, 0, 0)
]

for r in roles:
    cursor.execute("""
        INSERT OR IGNORE INTO Roles
        (role_id, nom, hierarchie, peut_gerer_utilisateurs, peut_gerer_roles)
        VALUES (?, ?, ?, ?, ?)
    """, r)

# =====================
# 2. UTILISATEURS (15)
# =====================
utilisateurs = [
    (1, "admin@tns.fr", "pwd", "Admin", "Root", 1, 0, None),
    (2, "manager1@tns.fr", "pwd", "Durand", "Sophie", 2, 0, None),
    (3, "manager2@tns.fr", "pwd", "Martin", "Paul", 2, 0, None),

    (4, "chef1@tns.fr", "pwd", "Bernard", "Luc", 3, 0, None),
    (5, "chef2@tns.fr", "pwd", "Petit", "Emma", 3, 0, None),

    (6, "interv1@tns.fr", "pwd", "Moreau", "Alice", 4, 1, 40),
    (7, "interv2@tns.fr", "pwd", "Simon", "Bob", 4, 1, 35),
    (8, "interv3@tns.fr", "pwd", "Laurent", "Chloé", 4, 1, 30),

    (9, "junior1@tns.fr", "pwd", "Garcia", "Hugo", 5, 1, 25),
    (10, "junior2@tns.fr", "pwd", "Roux", "Lina", 5, 1, 20),
    (11, "junior3@tns.fr", "pwd", "Fournier", "Noah", 5, 1, 20),

    (12, "interv4@tns.fr", "pwd", "Girard", "Eva", 4, 1, 40),
    (13, "interv5@tns.fr", "pwd", "Andre", "Leo", 4, 1, 35),
    (14, "junior4@tns.fr", "pwd", "Mercier", "Mila", 5, 1, 25),
    (15, "junior5@tns.fr", "pwd", "Blanc", "Adam", 5, 1, 20),

    (16, "junior6@tns.fr", "pwd", "", "Sophie", 5, 1, 15),
    (17, "junior7@tns.fr", "pwd", "", "Bob", 5, 1, 10),
    (18, "junior8@tns.fr", "pwd", "", "Charlie", 5, 1, 12),
]

for u in utilisateurs:
    cursor.execute("""
        INSERT OR IGNORE INTO Utilisateurs
        (utilisateur_id, email, mot_de_passe_hashed, nom, prenom,
         role_id, est_intervenant, heures_dispo_semaine)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, u)

# =====================
# 3. CLIENTS (4)
# =====================
clients = [
    (1, "TechCorp", "Jean Tech", "contact@techcorp.com", "0101010101", "Actif", 2),
    (2, "DataPlus", "Marie Data", "contact@dataplus.com", "0202020202", "Actif", 3),
    (3, "InnovX", "Paul Innov", "contact@innovx.com", "0303030303", "Prospect", 4),
    (4, "OldSoft", "Claire Old", "contact@oldsoft.com", "0404040404", "Ancien", 5)
]

for c in clients:
    cursor.execute("""
        INSERT OR IGNORE INTO Clients
        (client_id, nom_entreprise, contact_nom, contact_email,
         contact_telephone, type_client, interlocuteur_principal_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, c)

# =====================
# 4. CONVENTIONS (4)
# =====================
conventions = [
    (1, "Convention TechCorp", "Projet long terme", date(2025,1,1), date(2025,12,31), 1),
    (2, "Convention DataPlus", "Analyse données", date(2025,2,1), date(2025,10,31), 2),
    (3, "Convention InnovX", "Étude faisabilité", date(2025,3,1), date(2025,6,30), 3),
    (4, "Convention OldSoft", "Maintenance", date(2024,1,1), date(2024,12,31), 4)
]

for conv in conventions:
    cursor.execute("""
        INSERT OR IGNORE INTO Conventions
        (convention_id, nom_convention, description,
         date_debut, date_fin, client_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, conv)

# =====================
# 5. PROJETS (10) AVEC DATES
# =====================
projets = [
    # convention 1 – TechCorp (2025)
    (1, 1, "ERP", "Refonte ERP",
     20000, 300,
     date(2025, 1, 15), date(2025, 9, 30),
     "Terminé"),

    (2, 1, "CRM", "CRM interne",
     15000, 200,
     date(2025, 2, 1), date(2025, 8, 31),
     "Terminé"),

    (8, 1, "Mobile", "Application mobile",
     10000, 150,
     date(2025, 3, 1), date(2025, 7, 31),
     "Terminé"),

    (10, 1, "API", "API partenaires",
     9000, 140,
     date(2025, 4, 1), date(2025, 10, 31),
     "Terminé"),

    (11,1,"WEB","Site WEB 2.0",8000,100,date(2025,4,1),date(2025,10,31),"Terminé" ),

    # convention 2 – DataPlus
    (3, 2, "BI", "Dashboard BI",
     12000, 180,
     date(2025, 5, 1), date(2025, 11, 30),
     "Terminé"),

    (4, 2, "ML", "Prédictions ventes",
     18000, 250,
     date(2025, 6, 1), date(2025, 12, 31),
     "Terminé"),

    (9, 2, "Migration", "Migration cloud",
     22000, 320,
     date(2025, 1, 1), date(2025, 6, 30),
     "Terminé"),

    # convention 3 – InnovX (court)
    (5, 3, "Audit", "Audit technique",
     5000, 80,
     date(2025, 3, 1), date(2025, 4, 30),
     "Terminé"),

    (6, 3, "POC", "Prototype IA",
     7000, 100,
     date(2025, 4, 1), date(2025, 6, 30),
     "Terminé"),

    # convention 4 – OldSoft (passé)
    (7, 4, "Support", "Support applicatif",
     4000, 120,
     date(2024, 1, 1), date(2024, 12, 31),
     "Terminé"),

     (12,4,"API","",4000,80,date(2024,1,1),date(2024,3,1),"En cours")
]

for p in projets:
    cursor.execute("""
        INSERT OR IGNORE INTO Projets
        (projet_id, convention_id, nom_projet, description,
         budget, charge_travail,
         date_debut, date_fin,
         statut)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, p)

# =====================
# 6. COMPÉTENCES (12)
# =====================
competences = [
    (1, "Python", None),
    (2, "SQL", None),
    (3, "Java", None),
    (4, "Gestion de projet", None),
    (5, "Data Analysis", None),
    (6, "Machine Learning", None),
    (7, "Dev Backend", 3),
    (8, "Dev Frontend", None),
    (9, "Cloud", None),
    (10, "Docker", 9),
    (11, "Communication", None),
    (12, "Cybersécurité", None),
    (13,"Flask",1),
    (14,"HTML",8),
    (15,"PostgreSQL",2)
]

for comp in competences:
    cursor.execute("""
        INSERT OR IGNORE INTO Competences
        (competence_id, nom, competence_parent)
        VALUES (?, ?, ?)
    """, comp)

# =====================
# 7. INTERVENANT ↔ COMPÉTENCES
# =====================
intervenant_competences = [
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
    cursor.execute("""
        INSERT OR IGNORE INTO Intervenant_competences
        (intervenant_id, competence_id, niveau)
        VALUES (?, ?, ?)
    """, ic)

# =====================
# 8. PROJET ↔ COMPÉTENCES
# =====================
projet_competences = [
    (1, 1, 7), (1, 13, 6), (1, 4, 6),(1,5,5),
    (2, 3, 6), (2, 7, 7),
    (3, 5, 6),
    (4, 6, 7),
    (5, 11, 5),
    (6, 6, 6),
    (7, 12, 4),
    (8, 8, 8),
    (9, 9, 7), (9, 10, 6),
    (10, 1, 6),(10,3,5),
    (11,13,5),
    (12,1,7),(12,13,6),(12,15,5)
]

for pc in projet_competences:
    cursor.execute("""
        INSERT OR IGNORE INTO Projet_competences
        (projet_id, competence_id, niveau_requis)
        VALUES (?, ?, ?)
    """, pc)

# =====================
# 9. UTILISATEURS ↔ PROJETS
# =====================
travaille_sur = [
    (6, 1, 1), (7, 1, 1), (4, 1, 0),
    (8, 2, 1), (5, 2, 0),
    (9, 3, 1),
    (12, 4, 1),
    (6, 6, 1),
    (13, 8, 1),
    (10, 7, 1),
    (14, 9, 1),
    (15, 10, 1)
]

for ts in travaille_sur:
    cursor.execute("""
        INSERT INTO Travaille_sur
        (utilisateur_id, projet_id, est_intervenant_sur_projet)
        VALUES (?, ?, ?)
    """, ts)


conn.commit()
conn.close()

print("Base de données enrichie avec un dataset large et déterministe.")
