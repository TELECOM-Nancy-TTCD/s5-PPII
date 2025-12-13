import sqlite3

DATABASE = 'database/database.db'

db = sqlite3.connect(DATABASE)

cur = db.cursor()

cur.execute("DELETE FROM conventions")

cur.execute("DELETE FROM clients")

cur.execute("DELETE FROM projets")

cur.execute("DELETE FROM utilisateurs")


db.commit()

db.close()