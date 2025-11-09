# Règles de contribution (CONTRIBUTING.md)

Ce document explique comment contribuer à ce dépôt (workflow Git, conventions de branches, Merge Requests, résolution des conflits). Il est écrit pour une utilisation avec une instance GitLab auto‑hébergée.

Résumé rapide
- Branches principales : `main` (production), `dev` (intégration).
- Chaque développeur travaille sur une branche personnelle/feature nommée `feature/<initiales>-<courte-description>` ou `fix/<initiales>-<desc>`.
- Aucune modification directe sur `main` ni `dev` : utilisez des Merge Requests (MR).
- MR : description complète, reviewers, CI verte.

1) Avant de commencer
- Clonez le dépôt :

```bash
git clone <url-du-repo>
cd <nom-du-repo>
```

- Mettez-vous à jour chaque matin :

```bash
git fetch origin
git checkout dev
git pull origin dev
```

2) Conventions de nommage
- Branches de fonctionnalité : `feature/<initiales>-<desc>` (ex : `feature/ab-login-token`).
- Branches de correction : `fix/<initiales>-<desc>`.
- Commits : messages clairs, format recommandé :
  - court titre (impératif) : `feat(auth): ajouter login par token`
  - corps si besoin avec explication et lien vers issue/ticket.

3) Workflow (pas à pas)
- Créer une branche locale depuis `dev` :

```bash
git checkout dev
git pull origin dev
git checkout -b feature/<initiales>-<desc>
```

- Travailler, committer :

```bash
git add <fichiers>
git commit -m "feat(...): description courte"
```

- Pousser la branche la première fois :

```bash
git push -u origin feature/<initiales>-<desc>
```

4) Mettre à jour ta branche si `dev` a évolué
Option A — Merge (simple) :

```bash
git fetch origin
git checkout feature/<...>
git merge origin/dev
# résoudre conflits si nécessaire
git push
```

Option B — Rebase (historique linéaire) :

```bash
git fetch origin
git checkout feature/<...>
git rebase origin/dev
# résoudre conflits, puis:
git rebase --continue
# si tu as déjà poussé ta branche avant le rebase:
git push --force-with-lease
```

Remarques :
- Utilisez `rebase` pour nettoyer l'historique avant une MR s'il est convenu par l'équipe.
- Toujours préférer `--force-with-lease` plutôt que `--force` pour réduire les risques d'écrasement.

5) Ouvrir une Merge Request (MR) sur GitLab
- Pousser la branche (si pas déjà fait) :

```bash
git push -u origin feature/<...>
```

- Sur GitLab : Nouveau Merge Request -> choisir :
  - Source branch : `feature/<...>`
  - Target branch : `dev` (ou `main` si la MR doit aller en production)
  - Choisir un template (voir `.gitlab/merge_request_templates/`)
  - Remplir la description (quoi, pourquoi, comment tester)
  - Ajouter reviewers et labels

- Attendre CI verte et reviews. Corriger les commentaires en committant sur la même branche.

6) Résolution des conflits
- Git marque les fichiers en conflit avec des marqueurs `<<<<<<<`, `=======`, `>>>>>>>`.
- Procédure :
  1. Lire `git status` pour connaître les fichiers en conflit.
  2. Ouvrir les fichiers, interpréter les sections conflictuelles, fusionner manuellement.
  3. `git add <fichier>` pour chaque fichier résolu.
  4. Si merge : `git commit` terminera le merge.
     Si rebase : `git rebase --continue`.
  5. Tester localement.
  6. `git push` (ou `git push --force-with-lease` après rebase).

Commandes utiles :

```bash
# annuler un merge en cours
git merge --abort
# annuler un rebase en cours
git rebase --abort
# utiliser un outil graphique pour résoudre (si configuré)
git mergetool
```

Conseils pratiques :
- Communiquez avant de réécrire l'historique partagé.
- Pull/fetch souvent et petits changements fréquents.
- Tester localement avant de pousser.

7) Politique de merge
- Respecter la politique d'équipe : squash, merge commit ou rebase.
- S'assurer que la CI passe.
- Après merge dans `dev`, mettre à jour `dev` localement :

```bash
git checkout dev
git pull origin dev
```

8) Suppression de branches
- Supprimer la branche remote une fois mergée :

```bash
git push origin --delete feature/<...>
```

- Supprimer localement :

```bash
git branch -d feature/<...>
```

9) Issues / templates
- Utilisez les templates d'issue pour signaler un bug ou proposer une fonctionnalité. Voir `.gitlab/issue_templates/`.

10) Règles de qualité
- Respecter la CI et les tests automatisés.
- Faire une review constructive et claire.
- Ajouter tests et documentation si la fonctionnalité le nécessite.

Merci de respecter ces règles — elles facilitent la collaboration et maintiennent la qualité du projet.

