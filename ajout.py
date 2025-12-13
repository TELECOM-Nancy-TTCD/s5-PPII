
import sqlite3

DATABASE = 'database/database.db'

db = sqlite3.connect(DATABASE)

cur = db.cursor()

print("oui")

cur.execute("""INSERT INTO conventions VALUES(1,'projets algorithmiques',
            'ensemble de projets consistant à implémenter des algorithmes',
            '01/01/2025','01/01/2026','https://google.com',1)""")

cur.execute("""INSERT INTO conventions VALUES(2,'oneshot : site web',
            'commande pour un site web',
            '01/01/2025','01/01/2026','https://google.com',2)""")

cur.execute("""INSERT INTO Clients VALUES(1,'Université de Lorraine','Monsieur Martin',
            'martin@email.com','0301052124','Prospect',1,11,10.5,'7 chemin du bois, Nancy')""")

cur.execute("""INSERT INTO Clients VALUES(2,'Mairie de Nancy','Monsieur Dupont',
            'dupont@email.com','0157485963','Actif',1,10,10,'10 rue de la Mairie, Nancy')""")

cur.execute("""INSERT INTO Projets VALUES(1,1,'Dijkstra',"implementation de l'algorithme susnommé",
            100,'01/01/2025','01/01/2026','En cours','https://google.com')""")

cur.execute("""INSERT INTO Projets VALUES(2,1,'A*','implementation de lalgorithme susnommé',
            150,'01/06/2025','01/01/2026','Terminé','https://google.com')""")

cur.execute("""INSERT INTO Projets VALUES(3,2,'Site Mairie','Création dun site pour la mairie de Nancy',
            250,'01/09/2025','01/08/2026','Annulé','https://google.com')""")

cur.execute("""INSERT INTO Utilisateurs VALUES(1,'email@email.com','1',NULL,
            'Oui','Oscar','https://google.com','1',true,10,'','')""")

cur.execute(""" INSERT INTO Competences VALUES(1,'Python',1)  """)

cur.execute(""" INSERT INTO Competences VALUES(2,'Flask',1)  """)

cur.execute(""" INSERT INTO Competences VALUES(3,'PostgreSQL',3)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(1,1,5)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(1,2,3)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(1,3,5)  """)

cur.execute(""" INSERT INTO Projet_competences VALUES(3,1,4)  """)

cur.execute(""" INSERT INTO Projet_competences VALUES(3,2,4)  """)

cur.execute(""" INSERT INTO Projet_competences VALUES(3,3,4)  """)


db.commit()


db.close()