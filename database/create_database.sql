CREATE TABLE Roles (
    role_id INTEGER PRIMARY KEY,
    nom VARCHAR,
    hierarchie INT, -- pour la modification de rôles, on ne peut destituer un individu d'un role plus haut

    administrateur BOOLEAN DEFAULT false,
    peut_gerer_utilisateurs BOOLEAN DEFAULT false,
    peut_gerer_roles BOOLEAN DEFAULT false,
    
    peut_lire_clients BOOLEAN DEFAULT false,
    peut_gerer_clients BOOLEAN DEFAULT false,
    peut_creer_interactions BOOLEAN DEFAULT false,
    peut_gerer_interactions BOOLEAN DEFAULT false,
    
    peut_lire_projets BOOLEAN DEFAULT false,
    peut_gerer_projets BOOLEAN DEFAULT false,
    peut_gerer_jalons BOOLEAN DEFAULT false,
    peut_assigner_intervenants BOOLEAN DEFAULT false,

    peut_lire_intervenants BOOLEAN DEFAULT false,
    peut_modifier_intervenants BOOLEAN DEFAULT false, 
    peut_acceder_documents BOOLEAN DEFAULT false,
    peut_gerer_competences BOOLEAN DEFAULT false,

    peut_lancer_matching BOOLEAN DEFAULT false,
    peut_exporter_csv BOOLEAN DEFAULT false
    
);

CREATE TABLE Utilisateurs (
    utilisateur_id INTEGER PRIMARY KEY ,
    email VARCHAR UNIQUE NOT NULL,
    mot_de_passe_hashed VARCHAR NOT NULL,
    mot_de_passe_expire TEXT NULL, -- Date d'expiration du mot de passe, NULL si jamais expiré
    nom VARCHAR,
    prenom VARCHAR,
    avatar VARCHAR, -- Lien vers l'avatar de l'utilisateur
    role_id INT,
    
    est_intervenant BOOLEAN, -- Savoir s'il est un intervenant selectable
    heures_dispo_semaine INT,
    
    doc_carte_vitale VARCHAR,
    doc_cni VARCHAR,
    doc_adhesion VARCHAR,
    doc_rib VARCHAR,

    FOREIGN KEY (role_id) REFERENCES Roles(role_id) ON UPDATE CASCADE ON DELETE RESTRICT -- Pas de suppression de rôle si un utilisateur au moins a ce rôle
);

CREATE TABLE Clients (
    client_id INTEGER PRIMARY KEY ,
    nom_entreprise VARCHAR NOT NULL,
    contact_nom VARCHAR,
    contact_email VARCHAR,
    contact_telephone VARCHAR,
    type_client TEXT NOT NULL
        CHECK (type_client IN ('Prospect', 'Actif', 'Ancien')),

    interlocuteur_principal_id INT, --La personne de TNS en contact avec l'entreprise
    localisation_lat FLOAT,
    localisation_lng FLOAT,
    address VARCHAR,

    FOREIGN KEY (interlocuteur_principal_id) REFERENCES Utilisateurs(utilisateur_id) ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE Conventions (
    convention_id INTEGER PRIMARY KEY ,
    nom_convention VARCHAR NOT NULL,
    description TEXT,
    date_debut TEXT,
    date_fin TEXT,
    doc_contrat VARCHAR,

    client_id INT,
    FOREIGN KEY (client_id) REFERENCES Clients(client_id) ON UPDATE CASCADE ON DELETE CASCADE --suppression d'un client implique suppression de ses conventions

);

CREATE TABLE Projets (
    projet_id INTEGER PRIMARY KEY ,
    convention_id INT,
    nom_projet VARCHAR NOT NULL,
    description TEXT,
    budget FLOAT,
    date_debut TEXT,
    date_fin TEXT,
    statut TEXT NOT NULL
        CHECK( statut IN ('En attente', 'En cours', 'Terminé', 'Annulé')),
    doc_dossier VARCHAR, --Lien vers un dossier contenant tous les documents du projet

    FOREIGN KEY (convention_id) REFERENCES Conventions(convention_id) ON UPDATE CASCADE ON DELETE CASCADE -- suppression d'une convention implique suppression des projets associés
);

CREATE TABLE Competences (
    competence_id INTEGER PRIMARY KEY ,
    nom VARCHAR UNIQUE NOT NULL,

    -- sous-compétence (relation réflexive)
    competence_parent INT,
    FOREIGN KEY (competence_parent) REFERENCES Competences(competence_id) ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE Jalons (
    jalon_id INTEGER PRIMARY KEY ,
    description VARCHAR NOT NULL,
    date_fin TEXT,
    est_complete BOOLEAN DEFAULT false,

    projet_id INT,
    FOREIGN KEY (projet_id) REFERENCES Projets(projet_id) ON UPDATE CASCADE ON DELETE CASCADE --Suppression d'un projet implique suppression des jalons associés
);

--Tables de relations N-M

CREATE TABLE Interactions ( -- correspond au 'communique avec' du schéma mais avec le logging
    interaction_id INTEGER PRIMARY KEY,
    date_time_interaction TEXT NOT NULL,
    titre VARCHAR NOT NULL,
    contenu TEXT NOT NULL,
    type_interaction_id TEXT NOT NULL
        CHECK( type_interaction_id IN ('email', 'phone', 'meeting', 'textmessage', 'other')),

    -- relations aux autres tables

    client_id INT,
    utilisateur_id INT,
    FOREIGN KEY (client_id) REFERENCES Clients(client_id) ON UPDATE CASCADE ON DELETE CASCADE, -- Client supprimé implique conversations supprimé
    FOREIGN KEY (utilisateur_id) REFERENCES Utilisateurs(utilisateur_id) ON UPDATE CASCADE ON DELETE SET NULL -- Interlocuteur supprimé implique conversations associées à NULL

);

CREATE TABLE Intervenant_competences (
    intervenant_id INT,
    competence_id INT,
    
    niveau INT NOT NULL
        CHECK (niveau BETWEEN 0 AND 5),
    PRIMARY KEY (intervenant_id, competence_id),
    FOREIGN KEY (intervenant_id) REFERENCES Utilisateurs(utilisateur_id) ON UPDATE CASCADE ON DELETE CASCADE, --suppression d'un intervenant implique suppression de ses compétences
    FOREIGN KEY (competence_id) REFERENCES Competences(competence_id) ON UPDATE CASCADE ON DELETE CASCADE --suppression d'une compétence implique que l'intervenant n'a plus cette compétence

);

CREATE TABLE Projet_competences (
    projet_id INT,
    competence_id INT,
    niveau_requis INT NOT NULL
        CHECK (niveau_requis BETWEEN 0 AND 5),
    FOREIGN KEY (projet_id) REFERENCES Projets(projet_id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (competence_id) REFERENCES Competences(competence_id) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (projet_id, competence_id)

);

CREATE TABLE Travaille_sur (
    utilisateur_id INT,
    projet_id INT,
    est_intervenant_sur_projet BOOLEAN,
    poste VARCHAR,
    PRIMARY KEY (utilisateur_id, projet_id),
    FOREIGN KEY (utilisateur_id) REFERENCES Utilisateurs(utilisateur_id) ON UPDATE CASCADE ON DELETE SET NULL, -- Si un utilisateur est supprimé tandis qu'il travaille sur un projet, NULL travaille sur le projet
    FOREIGN KEY (projet_id) REFERENCES Projets(projet_id) ON UPDATE CASCADE ON DELETE CASCADE -- Suppression d'un projet implique suppression de la notion de qui travaille dessus

)