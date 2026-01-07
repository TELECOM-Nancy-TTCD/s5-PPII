# Groupe 07 - TTCD

Git du projet PPII-Prospector


Utiliser des inclusions de templates Jinja: une template pour la structure générale, une
 template de header, une de navbar qui s'inclut dans la template de header, une template de footer...
 Ces templates peuvent alors inclure/être incluses dans d'autres templates pour éviter de répéter du HTML partout

## Pour inclure le menu (menu et pied de page) : 
- Voir les pages vide que j'ai crée. 
OU
- inclure : 
{% extends "menu.html" %}

{% block title %}Titre de la page{% endblock %}

{% block content %}
Ici le HTML de la page 
{% endblock %}


## Pour lancer le site : 
- Lancer le venv
- python3 app.py dans la racien de la branche. 
- Aller sur : http://127.0.0.1:5000/

## Juste pour mon mémo sur la DB : 

Tables : [('Roles',), ('Utilisateurs',), ('Clients',), ('Conventions',), ('Projets',), ('Competences',), ('Jalons',), ('Interactions',), ('Intervenant_competences',), ('Projet_competences',), ('Travaille_sur',)]

Structure de la table Roles :
(0, 'role_id', 'INT', 0, None, 1)
(1, 'nom', 'VARCHAR', 0, None, 0)
(2, 'hierarchie', 'INT', 0, None, 0)
(3, 'peut_gerer_utilisateurs', 'BOOLEAN', 0, 'false', 0)
(4, 'peut_gerer_roles', 'BOOLEAN', 0, 'false', 0)
(5, 'peut_lire_clients', 'BOOLEAN', 0, 'false', 0)
(6, 'peut_gerer_clients', 'BOOLEAN', 0, 'false', 0)
(7, 'peut_gerer_interactions', 'BOOLEAN', 0, 'false', 0)
(8, 'peut_lire_projets', 'BOOLEAN', 0, 'false', 0)
(9, 'peut_gerer_projets', 'BOOLEAN', 0, 'false', 0)
(10, 'peut_gerer_jalons', 'BOOLEAN', 0, 'false', 0)
(11, 'peut_assigner_intervenants', 'BOOLEAN', 0, 'false', 0)
(12, 'peut_lire_utilisateurs', 'BOOLEAN', 0, 'false', 0)
(13, 'peut_acceder_documents', 'BOOLEAN', 0, 'false', 0)
(14, 'peut_gerer_competences', 'BOOLEAN', 0, 'false', 0)
(15, 'peut_lancer_matching', 'BOOLEAN', 0, 'false', 0)
(16, 'peut_exporter_csv', 'BOOLEAN', 0, 'false', 0)

Structure de la table Utilisateurs :
(0, 'utilisateur_id', 'INT', 0, None, 1)
(1, 'email', 'VARCHAR', 1, None, 0)
(2, 'mot_de_passe_hashed', 'VARCHAR', 1, None, 0)
(3, 'nom', 'VARCHAR', 0, None, 0)
(4, 'prenom', 'VARCHAR', 0, None, 0)
(5, 'role_id', 'INT', 0, None, 0)
(6, 'est_intervenant', 'BOOLEAN', 0, None, 0)
(7, 'heures_dispo_semaine', 'INT', 0, None, 0)
(8, 'doc_carte_vitale', 'VARCHAR', 0, None, 0)
(9, 'doc_cni', 'VARCHAR', 0, None, 0)
(10, 'doc_adhesion', 'VARCHAR', 0, None, 0)
(11, 'doc_rib', 'VARCHAR', 0, None, 0)

Structure de la table Clients :
(0, 'client_id', 'INT', 0, None, 1)
(1, 'nom_entreprise', 'VARCHAR', 1, None, 0)
(2, 'contact_nom', 'VARCHAR', 0, None, 0)
(3, 'contact_email', 'VARCHAR', 0, None, 0)
(4, 'contact_telephone', 'VARCHAR', 0, None, 0)
(5, 'type_client', 'TEXT', 1, None, 0)
(6, 'interlocuteur_principal', 'VARCHAR', 0, None, 0)
(7, 'localisation_lat', 'FLOAT', 0, None, 0)
(8, 'localisation_lng', 'FLOAT', 0, None, 0)
(9, 'address', 'VARCHAR', 0, None, 0)

Structure de la table Conventions :
(0, 'convention_id', 'INT', 0, None, 1)
(1, 'nom_convention', 'VARCHAR', 1, None, 0)
(2, 'description', 'TEXT', 0, None, 0)
(3, 'date_debut', 'DATE', 0, None, 0)
(4, 'date_fin', 'DATE', 0, None, 0)
(5, 'doc_contrat', 'VARCHAR', 0, None, 0)
(6, 'client_id', 'INT', 0, None, 0)

Structure de la table Projets :
(0, 'projet_id', 'INT', 0, None, 1)
(1, 'convention_id', 'INT', 0, None, 0)
(2, 'nom_projet', 'VARCHAR', 1, None, 0)
(3, 'description', 'TEXT', 0, None, 0)
(4, 'budget', 'FLOAT', 0, None, 0)
(5, 'date_debut', 'DATE', 0, None, 0)
(6, 'date_fin', 'DATE', 0, None, 0)
(7, 'statut', 'TEXT', 1, None, 0)
(8, 'doc_dossier', 'VARCHAR', 0, None, 0)

Structure de la table Competences :
(0, 'competence_id', 'INT', 0, None, 1)
(1, 'nom', 'VARCHAR', 1, None, 0)
(2, 'competence_parent', 'INT', 0, None, 0)

Structure de la table Jalons :
(0, 'jalon_id', 'INT', 0, None, 1)
(1, 'description', 'VARCHAR', 1, None, 0)
(2, 'date_fin', 'DATE', 0, None, 0)
(3, 'est_complete', 'BOOLEAN', 0, 'false', 0)
(4, 'projet_id', 'INT', 0, None, 0)

Structure de la table Interactions :
(0, 'interaction_id', 'INT', 0, None, 1)
(1, 'date_time_interaction', 'DATETIME', 1, None, 0)
(2, 'contenu', 'TEXT', 1, None, 0)
(3, 'client_id', 'INT', 0, None, 0)
(4, 'utilisateur_id', 'INT', 0, None, 0)

Structure de la table Intervenant_competences :
(0, 'intervenant_id', 'INT', 0, None, 1)
(1, 'competence_id', 'INT', 0, None, 2)
(2, 'niveau', 'INT', 1, None, 0)

Structure de la table Projet_competences :
(0, 'projet_id', 'INT', 0, None, 1)
(1, 'competence_id', 'INT', 0, None, 2)
(2, 'niveau_requis', 'INT', 1, None, 0)

Structure de la table Travaille_sur :
(0, 'utilisateur_id', 'INT', 0, None, 1)
(1, 'projet_id', 'INT', 0, None, 2)
(2, 'est_intervenant_sur_projet', 'BOOLEAN', 0, None, 0)