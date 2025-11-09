# Merge Request Template

## Titre
(Ex : feat(auth): ajouter connexion par token)

## Description
- **Quoi** : Décrire brièvement ce qui a été fait.
- **Pourquoi** : Pourquoi ce changement est nécessaire.
- **Comment** : Approche utilisée, décisions importantes.

## Comment tester
- Étapes à suivre pour reproduire et tester localement.
- Commandes ou scripts utiles.

## Checklist
- [ ] La branche cible est `dev` (ou `main` si besoin de production)
- [ ] Tests locaux passés
- [ ] CI verte
- [ ] Documentation mise à jour (si applicable)
- [ ] Aucun secret ajouté dans le code

## Liens
- Issue liée : #<numéro>
- Ticket externe / design : <lien>

## Notes pour le reviewer
- Points particuliers à vérifier
- Limitations connues

---

> Astuce : si `dev` a évolué depuis la création de la MR, mettez à jour votre branche via `git merge origin/dev` ou `git rebase origin/dev` avant de demander le merge final.
