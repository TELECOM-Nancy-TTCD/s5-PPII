import sqlite3

DB_PATH = "database/database.db"

def reset_table(cur, table):
    cur.execute(f"DELETE FROM {table};")
    try:
        cur.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}';")
    except sqlite3.OperationalError:
        pass

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Liste des tables connues
    tables = [
        "Roles",
        "Utilisateurs",
        "Clients",
        "Conventions",
        "Projets",
        "Competences",
        "Jalons",
        "Interactions",
        "Intervenant_competences",
        "Projet_competences",
        "Travaille_sur"
    ]

    print("=== RESET DATABASE ===")

    for table in tables:
        reset_table(cur, table)

    conn.commit()
    conn.close()

    print("\n✔ Toutes les tables ont été vidées.")
    print("Les IDs repartiront à 1 au prochain insert.")

if __name__ == "__main__":
    main()
