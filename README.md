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

