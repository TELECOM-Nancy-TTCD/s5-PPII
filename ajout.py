import os
import sqlite3
import base64
from hashlib import scrypt

DB_PATH = "database/database.db"


def hash_password(mdp: str):
    salt = os.urandom(16)  # Génération d'un salt

    mdp_hache = scrypt(mdp.encode(), salt=salt, n=2 ** 14, r=8, p=1)  # hachage du mdp avec le salt

    return base64.b64encode(salt + mdp_hache).decode()
    # encodage en B64, et remise en forme texte pour stockage.
    # Les 16 premiers octets sont le salt, le reste le mdp.


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ==========================
    #   AJOUT DES RÔLES
    # ==========================
    print("➤ Ajout des rôles...")

    cur.execute("""
                INSERT INTO Roles
                VALUES (NULL, 'Admin', 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1);
                """)
    cur.execute("""
                INSERT INTO Roles
                VALUES (NULL, 'Membre', 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
                """)
    print("   ✔ Rôles ajoutés.\n")

    # ==========================
    #   AJOUT UTILISATEURS
    # ==========================
    print("➤ Ajout des utilisateurs...")

    users = [
        ("john@admin.tns.com", "superadmin", "ADMIN", "John TNS", 1, 0, 169, None, None, None, None),
        ("bob@tns.com", "bob", "Bob", "Client", 2, 0, 0, None, None, None, None),
        ("bob2@tns.com", "bob", "BobDoc", "Client", 2, 0, 12,
         "https://drive.google.com/file/d/1PzE1K6lxY1Yiqr1kLwApwygojMHcDOgK/view?usp=sharing",
         None, None, None)
    ]

    for u in users:
        cur.execute("""
                    INSERT INTO Utilisateurs(utilisateur_id, email, mot_de_passe_hashed,
                                             nom, prenom, role_id, est_intervenant, heures_dispo_semaine,
                                             doc_carte_vitale, doc_cni, doc_adhesion, doc_rib)
                    VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        u[0], hash_password(u[1]), u[2], u[3], u[4], u[5], u[6], u[7], u[8], u[9], u[10]
                    ))
    print("   ✔ Utilisateurs ajoutés.\n")

    # ==========================
    #   AJOUT CLIENTS
    # ==========================
    print("➤ Ajout des clients...")

    clients = [
        ("TechCorp", "Alice Martin", "alice@techcorp.com", "0601020304", "Actif", 1, 48.6921, 6.1844,
         "12 Rue de la République, Nancy"),
        ("GreenSolutions", "Bruno Petit", "bruno@greensol.fr", "0605060708", "Actif", 1, 48.6738, 6.1560,
         "8 Avenue du Général Leclerc, Nancy"),
        ("Boulangerie Dupont", "Claire Dupont", "contact@dupont-boulangerie.fr", "0677889900", "Prospect", 1, 48.7002,
         6.1740, "5 Rue des Carmes, Nancy"),
        ("AutoPlus Garage", "David Leroy", "david@autoplus.fr", "0655443322", "Actif", 1, 48.6930, 6.2000,
         "23 Rue Stanislas, Nancy"),
        ("ImmoCity", "Eva Lambert", "eva@immocity.fr", "0611223344", "Ancien", 1, 48.6800, 6.1700,
         "41 Boulevard d'Haussonville, Nancy")
    ]

    for c in clients:
        cur.execute("""
                    INSERT INTO Clients (client_id, nom_entreprise, contact_nom, contact_email, contact_telephone,
                                         type_client, interlocuteur_principal_id, localisation_lat, localisation_lng,
                                         address)
                    VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, c)
    print("   ✔ Clients ajoutés.\n")

    # ==========================
    #   AJOUT CONVENTIONS ET PROJETS
    # ==========================
    print("➤ Ajout de conventions et projets...")

    # Liste de conventions à créer
    conventions = [
        {"nom": "Convention Alpha", "description": "Projet Alpha pour TechCorp", "client_email": "alice@techcorp.com"},
        {"nom": "Convention Beta", "description": "Projet Beta pour GreenSolutions",
         "client_email": "bruno@greensol.fr"},
        {"nom": "Convention Gamma", "description": "Projet Gamma pour Boulangerie Dupont",
         "client_email": "contact@dupont-boulangerie.fr"},
        {"nom": "Convention Delta", "description": "Projet Delta pour AutoPlus Garage",
         "client_email": "david@autoplus.fr"},
    ]

    for conv in conventions:
        # Récupération de l'ID du client
        cur.execute("SELECT client_id FROM Clients WHERE contact_email = ?", (conv["client_email"],))
        result = cur.fetchone()
        if result is None:
            print(f"Client avec email {conv['client_email']} introuvable, convention ignorée !")
            continue
        client_id = result[0]

        # Dates réalistes pour la convention
        if conv["nom"] in ["Convention Alpha", "Convention Beta"]:
            date_debut = "2025-04-01"
            date_fin = "2025-06-30"
        else:
            date_debut = "2025-06-01"
            date_fin = "2025-12-31"

        # Insertion de la convention
        cur.execute("""
                    INSERT INTO Conventions (convention_id, nom_convention, description, date_debut, date_fin,
                                             doc_contrat, client_id)
                    VALUES (NULL, ?, ?, ?, ?, NULL, ?)
                    """, (conv["nom"], conv["description"], date_debut, date_fin, client_id))
        convention_id = cur.lastrowid

        # Création de 2 projets pour chaque convention
        for i in range(1, 3):
            projet_nom = f"Projet {conv['nom'].split()[1]} {i}"
            projet_desc = f"Description du projet {i} pour {conv['nom']}"
            if conv["nom"] in ["Convention Alpha", "Convention Beta"]:
                date_debut_proj = f"2025-04-{10 + i:02d}"
                date_fin_proj = f"2025-05-{10 + i:02d}"
            else:
                date_debut_proj = f"2025-06-{10 + i:02d}"
                date_fin_proj = f"2025-11-{10 + i:02d}"

            cur.execute("""
                        INSERT INTO Projets (projet_id, convention_id, nom_projet, description, budget, date_debut,
                                             date_fin, statut, doc_dossier)
                        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, NULL)
                        """, (
                            convention_id,
                            projet_nom,
                            projet_desc,
                            10000 * i,
                            date_debut_proj,
                            date_fin_proj,
                            "En cours"
                        ))

    print("   ✔ Conventions et projets ajoutés.\n")

    # ==========================
    #   AJOUT JALONS
    # ==========================

    cur.execute(""" INSERT INTO Jalons(description, est_complete, date_fin, projet_id)
                    VALUES ('signature de la charte de projet', 1, '2025-04-28', 1);""")
    cur.execute(""" INSERT INTO Jalons(description, est_complete, date_fin, projet_id)
                    VALUES ('Implémentation de la base de données', 1, '2025-04-29', 1);""")
    cur.execute(""" INSERT INTO Jalons(description, est_complete, date_fin, projet_id)
                    VALUES ('Implémentation du Flask', 0, '2025-04-29', 1);""")
    cur.execute(""" INSERT INTO Jalons(description, est_complete, projet_id)
                    VALUES ('Post-Mortem', 0, 1);""")

    print("   ✔ jalons ajoutés.\n")
    # ==========================
    #   AJOUT INTERACTIONS
    # ==========================
    print("➤ Ajout des interactions...")

    # Récupération de tous les clients
    cur.execute("SELECT client_id FROM Clients")
    all_clients = [row[0] for row in cur.fetchall()]

    # Récupération des utilisateurs pour attribuer les interactions
    cur.execute("SELECT utilisateur_id FROM Utilisateurs")
    all_users = [row[0] for row in cur.fetchall()]

    # Types et mapping demandés
    types_names = {
        "email": "Email",
        "phone": "Appel téléphonique",
        "meeting": "Réunion",
        "textmessage": "Message texte",
        "other": "Autre",
        "Email": "email",
        "Appel téléphonique": "phone",
        "Réunion": "meeting",
        "Message texte": "textmessage",
        "Autre": "other"
    }
    interactions_types = ['email', 'phone', 'meeting', 'textmessage', 'other']

    interactions_examples = [
        "Appel rapide pour valider l’avancement.nf jsdfizjbdfijzbdfijbdviohbjqdiovbjifvbbvzpiubzpiubpiuzrbgpiuzbgpijabfpijbpiuvzUDHzouhvpjbefpivuhrpuvbqifjbvpiubfvpiuzbivpbifugbzpirubgipubfvipjbfivubipufn liehshqifhbid",
        "Envoi d’un mail contenant des documents complémentaires.",
        "Discussion sur le cahier des charges.",
        "Relance client concernant la signature.",
        "Point technique sur les contraintes du projet.",
        "Retour du client au sujet du devis.",
        "Organisation d’un rendez-vous de suivi.",
        "Échange informel sur les prochaines étapes."
    ]

    import random
    from datetime import datetime, timedelta

    for client_id in all_clients:
        # Ajouter entre 2 et 5 interactions par client
        for _ in range(random.randint(2, 5)):
            contenu = random.choice(interactions_examples)
            utilisateur = random.choice(all_users) if all_users else None

            # Date aléatoire dans les 60 derniers jours
            date = datetime.now() - timedelta(days=random.randint(0, 60))
            date_str = date.strftime("%Y-%m-%d %H:%M:%S")

            # Type et titre conformes au schéma
            type_interaction = random.choice(interactions_types)
            titre = types_names.get(type_interaction, type_interaction)

            cur.execute("""
                        INSERT INTO Interactions (interaction_id, date_time_interaction, type_interaction_id, titre,
                                                  contenu, client_id, utilisateur_id)
                        VALUES (NULL, ?, ?, ?, ?, ?, ?)
                        """, (
                            date_str,
                            type_interaction,
                            titre,
                            contenu,
                            client_id,
                            utilisateur
                        ))

    print("   ✔ Interactions ajoutées.")

    # ==========================
    #   FIN
    # ==========================
    conn.commit()
    conn.close()

    print("\n🎉 Import terminé !")

    print("Données disponibles :")
    print("  - Admin John : john@admin.tns.com / superadmin")
    print("  - Membre Bob : bob@tns.com / bob")
    print("  - BobDoc : bob2@tns.com / bob (avec doc GDrive)")
    print("  - 5 clients ajoutés")
    print("  - Conventions et projets ajoutés")


if __name__ == "__main__":
    main()
