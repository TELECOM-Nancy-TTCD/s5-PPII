# Algorithme de Matching - Affectation des Intervenants aux Missions

## 📋 Contexte

Dans le cadre de TNS (Telecom Nancy Services), nous devons affecter des **intervenants** (étudiants déjà inscrits à TNS) à des **études**(missions) client. L'objectif est de trouver la meilleure combinaison d'intervenants en fonction de :
- Leurs compétences techniques
- Leur disponibilité (heures/semaine)
- Les exigences de l'étude
- La charge de travail estimée
- La deadline du projet

Le système doit **minimiser le nombre d'intervenants** par mission pour réduire les coûts (charges sociales par intervenant) tout en garantissant que toutes les compétences requises sont couvertes.

---

## 🎯 Objectifs du Matching

### Objectif principal
Trouver la **meilleure équipe d'intervenants** pour une étude donnée.

### Critères de sélection
1. **Couverture des compétences** : Tous les skills requis doivent être couverts
2. **Disponibilité suffisante** : La charge de travail doit être réalisable avant la deadline
3. **Minimisation du nombre d'intervenants** : Privilégier un seul intervenant polyvalent plutôt qu'une équipe
4. **Qualité du match** : Privilégier les experts dans les domaines requis

---

## 📊 Modèle de Données (exemple)

### Intervenant

```python
{
    "id": 1,
    "nom": "Alice Martin",
    "competences": {
        "Python": 9,      # Niveau d'expertise sur 10
        "Flask": 8,
        "React": 7,
        "PostgreSQL": 6
    },
    "disponibilite": 15,  # heures par semaine
    "projets_realises": [
        "API REST e-commerce",
        "Dashboard analytics",
        "Application mobile"
    ],
    "portfolio": "https://github.com/alice-martin"
}
```

### Mission

```python
{
    "id": 42,
    "titre": "Refonte site web e-commerce",
    "client": "Boutique XYZ",
    "competences_requises": {
        "Python": 7,      # Niveau minimum requis
        "Flask": 6,
        "React": 8,
        "PostgreSQL": 5
    },
    "charge_estimee": 120,  # heures totales
    "deadline": "2025-12-15"
}
```

---

## 🧮 Algorithme de Matching

### Phase 1 : Filtrage initial

```mermaid
graph TD
    A[Mission à pourvoir] --> B{Filtrage des intervenants}
    B --> C[Compétences pertinentes ?]
    C -->|Non| D[Rejeter]
    C -->|Oui| E[Disponibilité suffisante ?]
    E -->|Non| D
    E -->|Oui| F[Pool d'intervenants éligibles]
    F --> G[Calcul des scores]
```

#### Critères de filtrage
- **Compétences** : L'intervenant possède au moins une compétence requise
- **Disponibilité** : L'intervenant a une disponibilité > 0 h/semaine
- **Niveau minimum** : Pour chaque compétence qu'il possède, son niveau ≥ niveau requis

### Phase 2 : Calcul du score de matching

Pour chaque intervenant, on calcule un **score de matching** : *à déterminer par vos soins*.

#### Score de Compétences

TODO

#### Score de Disponibilité

TODO

#### Score d'Expérience

TODO

### Phase 3 : Recherche de la meilleure combinaison

#### Cas 1 : Un seul intervenant (préféré)

```mermaid
graph LR
    A[Intervenants triés par score] --> B{Intervenant couvre<br/>toutes les compétences ?}
    B -->|Oui| C[✅ Solution optimale<br/>1 intervenant]
    B -->|Non| D[Passer aux combinaisons]
```

#### Cas 2 : Combinaison d'intervenants

```mermaid
graph TD
    A[Générer combinaisons<br/>de 2 intervenants] --> B{Toutes compétences<br/>couvertes ?}
    B -->|Oui| C[Calculer score combiné]
    B -->|Non| D[Essayer combinaison suivante]
    C --> E{Meilleur score<br/>actuel ?}
    E -->|Oui| F[Garder cette combinaison]
    E -->|Non| D
    D --> G{Plus de combinaisons<br/>à tester ?}
    G -->|Oui| A
    G -->|Non| H[Si aucune solution:<br/>essayer 3 intervenants]
```

---

## 💡 Exemples Concrets

### Exemple 1 : Match parfait avec un seul intervenant

#### Mission
```
Titre: "Développement API REST"
Compétences requises:
  - Python: 7
  - Flask: 6
  - PostgreSQL: 5
Charge: 80 heures
Deadline: 8 semaines
```

#### Intervenants disponibles

| Nom | Python | Flask | PostgreSQL | Dispo (h/sem) | Score |
|-----|--------|-------|------------|---------------|-------|
| **Alice** | 9 | 8 | 6 | 15 | **0.95** ✅ |
| Bob | 8 | 4 | 7 | 10 | 0.72 |
| Charlie | 6 | 5 | 5 | 12 | 0.68 |

**Résultat** : Alice est choisie (score 0.95, toutes compétences couvertes, 1 seul intervenant)

---

### Exemple 2 : Combinaison nécessaire

#### Mission
```
Titre: "Application web full-stack"
Compétences requises:
  - Python: 8
  - Flask: 7
  - React: 9
  - PostgreSQL: 6
  - Docker: 7
Charge: 200 heures
Deadline: 12 semaines
```

#### Intervenants disponibles

| Nom | Python | Flask | React | PostgreSQL | Docker | Dispo |
|-----|--------|-------|-------|------------|--------|-------|
| Alice | 9 | 8 | 7 | 6 | 5 | 15 h/sem |
| David | 7 | 6 | 9 | 5 | 8 | 18 h/sem |
| Emma | 8 | 7 | 4 | 8 | 9 | 12 h/sem |

#### Analyse

**Alice seule** : ❌ React (7 < 9) et Docker (5 < 7) insuffisants
**David seul** : ❌ Manque Python (7 < 8)
**Emma seule** : ❌ React (4 < 9) très insuffisant

**Alice + David** : ✅
- Python: max(9, 7) = 9 ≥ 8 ✅
- Flask: max(8, 6) = 8 ≥ 7 ✅
- React: max(7, 9) = 9 ≥ 9 ✅
- PostgreSQL: max(6, 5) = 6 ≥ 6 ✅
- Docker: max(5, 8) = 8 ≥ 7 ✅
- Disponibilité: (15 + 18) × 12 = 396 heures ≥ 200 ✅

**Résultat** : Équipe de 2 (Alice + David)

---

### Exemple 3 : Aucun match possible

#### Mission
```
Titre: "Application Machine Learning"
Compétences requises:
  - Python: 9
  - TensorFlow: 8
  - AWS: 7
Charge: 150 heures
Deadline: 4 semaines
```

#### Intervenants disponibles

| Nom | Python | TensorFlow | AWS | Dispo |
|-----|--------|------------|-----|-------|
| Alice | 9 | 6 | 5 | 15 h/sem |
| Bob | 8 | 5 | 6 | 10 h/sem |

**Problème** : Aucun intervenant n'a TensorFlow ≥ 8

```mermaid
graph TD
    A[Aucun match trouvé] --> B{Options}
    B --> C[Revoir les exigences<br/>de la mission]
    B --> D[Former un intervenant<br/>sur TensorFlow]
    B --> E[Recruter un nouvel<br/>intervenant]
    B --> F[Refuser la mission]
```

---

## 🔄 Flux Complet du Matching

```mermaid
sequenceDiagram
    participant Client
    participant System
    participant BDD
    participant Algo
    participant Chef
    
    Client->>System: Nouvelle mission
    System->>BDD: Récupérer intervenants disponibles
    BDD-->>System: Liste intervenants
    System->>Algo: Lancer matching
    
    Algo->>Algo: Phase 1: Filtrage
    Algo->>Algo: Phase 2: Calcul scores
    Algo->>Algo: Phase 3: Recherche combinaison
    
    alt Solution trouvée
        Algo-->>System: Équipe recommandée + score
        System->>Chef: Notification + suggestions
        Chef->>System: Validation
        System->>BDD: Affecter intervenants
        System-->>Client: Mission acceptée
    else Aucune solution
        Algo-->>System: Aucun match possible
        System->>Chef: Alerte + options
        Chef->>Client: Négociation (délai/budget/scope)
    end
```

---

## 📈 Interface Utilisateur

### Vue Chef de Projet

```mermaid
graph TD
    A[Nouvelle Mission] --> B[Formulaire<br/>compétences requises]
    B --> C[Lancer Matching]
    C --> D{Résultats}
    D --> E[Top 3 recommandations]
    E --> F1[Option 1: Alice<br/>Score: 95%<br/>1 intervenant]
    E --> F2[Option 2: Bob + Charlie<br/>Score: 88%<br/>2 intervenants]
    E --> F3[Option 3: David + Emma<br/>Score: 82%<br/>2 intervenants]
    F1 --> G[Détails & Validation]
    F2 --> G
    F3 --> G
```

### Affichage d'une recommandation

```
╔══════════════════════════════════════════════════════════╗
║  Option 1 - Score: 95% ⭐⭐⭐⭐⭐                         ║
╠══════════════════════════════════════════════════════════╣
║  👤 Alice Martin                                         ║
║  📧 alice.martin@telecomnancy.eu                         ║
║  ⏱️  Disponibilité: 15h/semaine                          ║
║                                                          ║
║  Compétences:                                            ║
║    ✅ Python: 9/10 (requis: 7)                           ║
║    ✅ Flask: 8/10 (requis: 6)                            ║
║    ✅ PostgreSQL: 6/10 (requis: 5)                       ║
║                                                          ║
║  Portfolio: 12 projets réalisés                          ║
║  📂 https://github.com/alice-martin                      ║
║                                                          ║
║  Estimation: Livraison en 5.3 semaines                   ║
║                                                          ║
║  [Valider]  [Voir profil]  [Comparer]                   ║
╚══════════════════════════════════════════════════════════╝
```

---

## 🚀 Améliorations Futures

### Phase 1 (Base)
- ✅ Matching basique sur compétences
- ✅ Filtrage par disponibilité
- ✅ Interface de recommandation

### Phase 2 (Avancé)
- 🔄 Prise en compte de la charge mentale (max projets simultanés)
- 🔄 Historique de collaboration (privilégier les équipes qui ont déjà travaillé ensemble)
- 🔄 Préférences des intervenants (domaines d'intérêt)
- 🔄 Prédire quel intervenant devrait être formé

### Phase 3 (Expert)
- 🎯 Machine Learning pour prédire le succès d'une affectation
- 🎯 Optimisation multi-missions (répartir plusieurs missions simultanément)
- 🎯 Système de recommandation proactif (suggérer des missions aux intervenants)

---

##  Questions Fréquentes

**Q: Que faire si aucun intervenant n'est disponible ?**
R: Le système doit alerter le chef de projet avec des options : reporter la deadline, recruter un nouvel intervenant, ou sous-traiter.

**Q: Comment éviter qu'un intervenant soit sur-sollicité ?**
R: Ajouter une vérification de la charge totale actuelle de l'intervenant avant de l'affecter.

**Q: Peut-on proposer plusieurs options au chef de projet ?**
R: Oui ! L'algorithme devrait retourner le top 3-5 des meilleures combinaisons pour laisser le choix.

---
