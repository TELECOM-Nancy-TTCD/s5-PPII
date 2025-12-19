
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
            100,60,'01/01/2025','01/02/2025','En cours','https://google.com')""")

cur.execute("""INSERT INTO Projets VALUES(2,1,'A*','implementation de lalgorithme susnommé',
            150,80,'01/01/2025','01/02/2025','En cours','https://google.com')""")

cur.execute("""INSERT INTO Projets VALUES(3,2,'Site Mairie','Création dun site pour la mairie de Nancy',
            250,100,'01/09/2025','01/12/2025','Annulé','https://google.com')""")

cur.execute("""INSERT INTO Projets VALUES(4,2,'API REST','',
            80,80,'01/09/2025','01/11/2025','En cours','https://google.com')""")

cur.execute("""INSERT INTO Utilisateurs VALUES(1,'email@email.com','1',NULL,
            'Dupont','Oscar','https://google.com','1',true,50,'','','','')""")

cur.execute("""INSERT INTO Utilisateurs VALUES(2,'yoyo@email.com','1',NULL,
            'Dupont','Louis','https://google.com','1',true,20,'','','','')""")

cur.execute("""INSERT INTO Utilisateurs VALUES(3,'ouais@email.com','1',NULL,
            'Dupont','Léo','https://google.com','1',true,50,'','','','')""")

cur.execute("""INSERT INTO Utilisateurs VALUES(4,'alice@email.com','1',NULL,
            'Dupont','Alice','https://google.com','1',true,15,'','','','')""")

cur.execute("""INSERT INTO Utilisateurs VALUES(5,'bob@email.com','1',NULL,
            'Dupont','Bob','https://google.com','1',true,10,'','','','')""")

cur.execute("""INSERT INTO Utilisateurs VALUES(6,'charlie@email.com','1',NULL,
            'Dupont','Charlie','https://google.com','1',true,12,'','','','')""")

cur.execute(""" INSERT INTO Competences VALUES(1,'Python',1)  """)

cur.execute(""" INSERT INTO Competences VALUES(2,'Flask',1)  """)

cur.execute(""" INSERT INTO Competences VALUES(3,'PostgreSQL',3)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(1,1,4)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(1,2,5)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(1,3,5)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(2,1,7)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(2,3,4)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(4,1,9)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(4,2,8)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(4,3,6)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(5,1,8)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(5,2,4)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(6,1,6)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(6,2,5)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(6,3,5)  """)

cur.execute(""" INSERT INTO Intervenant_competences VALUES(5,3,7)  """)

cur.execute(""" INSERT INTO Projet_competences VALUES(3,1,6)  """)

cur.execute(""" INSERT INTO Projet_competences VALUES(3,2,4)  """)

cur.execute(""" INSERT INTO Projet_competences VALUES(3,3,4)  """)

cur.execute(""" INSERT INTO Projet_competences VALUES(4,1,6)  """)

cur.execute(""" INSERT INTO Projet_competences VALUES(4,2,4)  """)

cur.execute(""" INSERT INTO Projet_competences VALUES(4,3,5)  """)

cur.execute(""" INSERT INTO Travaille_sur VALUES(1,1,true)  """)

cur.execute(""" INSERT INTO Travaille_sur VALUES(1,2,true)  """)

cur.execute(""" INSERT INTO Travaille_sur VALUES(2,1,true)  """)

db.commit()


db.close()