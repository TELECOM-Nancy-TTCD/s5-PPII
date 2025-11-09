# Guide de contribution et workflow Git (Branches)

Ce document explique comment travailler avec le système de branches que nous avons défini pour le projet (1 branche par personne, une branche `dev`, et `main`). Il contient un tutoriel pas-à-pas, des commandes Git utiles, et des réponses aux questions courantes.

Rappel rapide du modèle de branches
- `main` : code stable, prêt pour production / version finale.
- `dev` : branche d'intégration où sont mergées les fonctionnalités terminées et testées.
- `nom_prenom` (ou `feature/<nom>` ) : branche personnelle de travail pour chaque contributeur.

Checklist avant de commencer une tâche
1. Mettre à jour `dev` localement : `git checkout dev && git pull origin dev`.
2. Créer votre branche (si elle n'existe pas) à partir de `dev` :
   - `git checkout -b <votre_nom>`
3. Travaillez localement et committez souvent en petits commits atomiques.

Bonnes pratiques de commits
- Message de commit clair et succinct : `type(scope): description` (ex : `feat(ui): add login form`).
- Commits atomiques : un changement logique par commit.
- Inclure le numéro de ticket/issue si pertinent.

Faire des Pull Requests (Merge Requests) vers `dev` ou `main`
- Quand votre travail est achevé et testé localement, poussez votre branche :
  - `git push origin <votre_nom>`
- Ouvrir une Merge Request (MR) vers `dev` :
  - Base: `dev`, Compare: `<votre_nom>`
  - Renseigner le titre et description (utilisez le template MR si disponible).
- Si la MR vise une release ou hotfix, targetez `main` (après revue et tests).

Récupérer les modifications si `dev` a été modifiée par quelqu'un d'autre
- Option 1 — Rebase (conserve un historique linéaire) :
  1. `git checkout <votre_nom>`
  2. `git fetch origin`
  3. `git rebase origin/dev`
  4. Résoudre les conflits si nécessaire (voir section conflits), puis `git rebase --continue`.
  5. Pousser en forçant si vous avez déjà poussé vos commits : `git push --force-with-lease origin <votre_nom>`.

- Option 2 — Merge (plus simple, ajoute un commit de merge) :
  1. `git checkout <votre_nom>`
  2. `git fetch origin`
  3. `git merge origin/dev`
  4. Résoudre les conflits si nécessaire, commit, puis `git push origin <votre_nom>`.

Rebase vs Merge — lequel choisir ?
- Rebase garde l'historique propre (linéaire) mais réécrit l'historique — nécessite `git push --force-with-lease` si vous avez déjà partagé la branche.
- Merge est plus sûr quand plusieurs personnes collaborent sur la même branche et évite d'écraser l'historique partagé.
- Règle d'or : pour vos branches personnelles, le rebase sur `dev` est recommandé avant de créer la MR; pour branches partagées, préférez le merge.

Que faire en cas de conflits ? (Guide pas-à-pas)
1. Git vous indiquera quels fichiers sont en conflit après un `rebase` ou `merge`.
2. Ouvrez les fichiers concernés ; recherchez les marqueurs `<<<<<<<`, `=======`, `>>>>>>>`.
3. Comprenez les deux versions :
   - La section entre `<<<<<<< HEAD` (ou votre branche) et `=======` est votre version locale.
   - La section entre `=======` et `>>>>>>>` est la version distante (ou la branche `dev` selon l'opération).
4. Choisissez la bonne version ou combinez-les manuellement.
5. Enregistrez les fichiers, puis :
   - Si vous êtes en merge : `git add <fichiers>` puis `git commit`.
   - Si vous êtes en rebase : `git add <fichiers>` puis `git rebase --continue`.
6. Testez votre code (build/tests).
7. Poussez vos modifications :
   - Après merge normal : `git push origin <votre_nom>`.
   - Après rebase : `git push --force-with-lease origin <votre_nom>`.

Conseils pour résoudre les conflits correctement
- Ne forcez pas aveuglément un push si vous n'êtes pas sûr d'avoir réglé tous les conflits.
- Lisez l'historique (`git log --graph --oneline --all`) pour comprendre comment les changements se sont produits.
- Si le conflit est complexe, discutez avec l'auteur des changements sur `dev` (commentaires MR/issue).

Processus de revue et critères d'acceptation pour une MR
- Tests unitaires passent (si présents).
- Aucune regression évidente sur les fonctionnalités liées.
- Code lisible et documenté si nécessaire.
- Les droits et données sensibles ne sont pas exposés.
- Un reviewer (1 ou 2) a approuvé la MR.

Annuler ou remettre à zéro une branche locale
- Revenir à la dernière version distante :
  - `git fetch origin`
  - `git reset --hard origin/<votre_nom>`

Créer une branche de correction depuis `main` (hotfix)
1. `git checkout main && git pull origin main`
2. `git checkout -b hotfix/<description>`
3. Faire les corrections, commit, push
4. Ouvrir MR vers `main`, puis après merge, merger `main` dans `dev`.

Bonnes pratiques additionnelles
- Garder les branches courtes (durée de vie courte). Une branche longue augmente les conflits.
- Mettre à jour souvent votre branche depuis `dev`.
- Communiquer les changements importants dans le canal d'équipe (Slack/Discord).
- Écrire des descriptions claires dans les MRs.

FAQ rapide
- Q: "Si quelqu'un a modifié la branch dev, comment puis-je la récupérer ?"
  - R: `git fetch origin && git rebase origin/dev` (ou `git merge origin/dev` si vous préférez).

- Q: "Comment faire des pull requests pour mettre ma branche sur le dev (ou main) ?"
  - R: Pousser votre branche (`git push origin <votre_nom>`), puis ouvrir une Merge Request sur GitLab en choisissant `target = dev` (ou `main` si hotfix/release).

- Q: "Comment faire en cas de conflits ? Qu'est-ce qu'il faut faire ?"
  - R: Résoudre les marqueurs `<<<<<<<` / `=======` / `>>>>>>>`, `git add` les fichiers, et finir le merge/rebase. Testez localement puis poussez.

Annexes : commandes utiles
- `git status` — voir l'état de la branche
- `git fetch origin` — récupérer les références distantes sans intégrer
- `git pull` — fetch + merge
- `git pull --rebase` — fetch + rebase
- `git rebase origin/dev` — rejouer vos commits sur la tête de `dev`
- `git merge origin/dev` — intégrer `dev` dans votre branche
- `git push --force-with-lease` — forcer le push de votre branche locale tout en évitant d'écraser involontairement les nouveaux commits distants

Merci de suivre ce guide ; si tu veux que j'ajoute une section (ex : hooks Git, CI/CD, règles de nommage plus strictes), dis-moi quoi et je l'ajoute.
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

