INSERT INTO Projets(convention_id,
    nom_projet,
    description,
    budget,
    date_debut,
    date_fin,
    statut, doc_dossier) VALUES (0,'projet test', 'ceci est vraiment un beau test, moi je dis bravo', 1.5, '2025-04-28','2025-04-29', 'Annulé', 'https://example.org');

INSERT INTO Jalons(description, est_complete, date_fin, projet_id) VALUES ('signature de la charte de projet', 1, '2025-04-28', 1);
INSERT INTO Jalons(description, est_complete, date_fin, projet_id) VALUES ('Implémentation de la base de données', 1, '2025-04-29', 1);
INSERT INTO Jalons(description, est_complete, date_fin, projet_id) VALUES ('Implémentation du Flask', 0, '2025-04-29', 1);
INSERT INTO Jalons(description, est_complete, projet_id) VALUES ('Post-Mortem', 0, 1);
