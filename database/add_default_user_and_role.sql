INSERT INTO Roles VALUES (NULL, 'admin', 0, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true);
INSERT INTO Roles VALUES (NULL, 'membre', 5, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false);
PRAGMA table_info(Roles);
SELECT role_id, nom FROM Roles;



-- Mot de passe: superadmin

-- Contenu actuel de la DB :
-- rôles ci-dessus; utilisateurs John ci-dessus qui est admin, et Bob (email bob@tns.com, mdp bob) qui est membre