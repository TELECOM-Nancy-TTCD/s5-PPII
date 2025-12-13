INSERT INTO Roles VALUES (NULL, "admin", 0, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true);
INSERT INTO Roles VALUES (NULL, "membre", 5, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false);
PRAGMA table_info(Roles);
SELECT role_id, nom FROM Roles;

INSERT INTO Utilisateurs(utilisateur_id, email, mot_de_passe_hashed, nom, prenom, est_intervenant, heures_dispo_semaine) VALUES (NULL, 'john@admin.tns.com','kRwuE/Vgiz4bI9yLi+jVteBHC/qxVLrD9TIvPh42iq2FRtTyyX3YdfYnVhY6WjFf412/GFiw8K/NqoxfDPVKqC65HiPT3TsxNF0iePMYRdk=', 'ADMIN', 'John TNS', false, 169);
SELECT utilisateur_id, email FROM Utilisateurs;
-- Mot de passe: superadmin

-- Contenu actuel de la DB :
-- rôles ci-dessus; utilisateurs John ci-dessus qui est admin, et Bob (email bob@tns.com, mdp bob) qui est membre