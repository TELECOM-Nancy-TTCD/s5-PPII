import sqlite3
import matching

path = "database/database.db"

conn = sqlite3.connect(path)
cursor = conn.cursor()

# Liste toutes les tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("=== LISTE DES TABLES ===")
for table in tables:
    print("-", table[0])

print("\n=== CONTENU DES TABLES ===\n")

# Affiche tout le contenu table par table
for table in tables:
    name = table[0]
    print(f"\n--- Table : {name} ---")

    cursor.execute(f"PRAGMA table_info({name});")
    columns = cursor.fetchall()

    col_names = [c[1] for c in columns]
    print("Colonnes :", col_names)

    cursor.execute(f"SELECT * FROM {name};")
    rows = cursor.fetchall()

    if not rows:
        print("Aucune donnée.")
    else:
        for row in rows:
            print(row)

conn.close()