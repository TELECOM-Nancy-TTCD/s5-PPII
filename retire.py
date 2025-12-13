import sqlite3

DATABASE = 'database/database.db'

db = sqlite3.connect(DATABASE)

cur = db.cursor()

cur.execute("DELETE FROM conventions")

cur.execute("DELETE FROM clients")

cur.execute("DELETE FROM projets")

cur.execute("DELETE FROM utilisateurs")

cur.execute("DELETE FROM competences")

cur.execute("DELETE FROM Intervenant_competences ")

cur.execute("DELETE FROM Projet_competences")


db.commit()

db.close()