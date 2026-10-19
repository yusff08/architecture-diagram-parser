# Gestion 4 — Exigences & Traçabilité UML

## 1. Rôle

Ce module vérifie qu'un diagramme UML de cas d'utilisation répond bien au cahier des charges d'un projet :

1. l'utilisateur crée un **projet d'analyse** et saisit ou importe son **cahier des charges** (`.txt` / `.md`) ;
2. **Gemini extrait les exigences** (référence `REQ-001`…, titre, description, type, priorité) ; l'utilisateur les **vérifie et corrige** avant de les enregistrer ;
3. l'utilisateur choisit une **documentation UML** : celle produite par l'onglet « Analyser un diagramme » (réutilisée **sans relancer l'OCR**) ou un fichier Markdown importé ;
4. les **acteurs et cas d'utilisation** explicitement écrits dans la documentation sont identifiés (Gemini et/ou saisie manuelle) ;
5. Gemini **associe chaque exigence aux cas d'utilisation** et justifie la couverture ; l'utilisateur peut **corriger** chaque association ;
6. le module calcule le **taux de couverture**, affiche la **matrice de traçabilité**, les **recommandations IA** et permet l'**export CSV / Markdown / PDF (impression)**.

Toutes les données sont enregistrées en SQLite et restent disponibles après actualisation du navigateur.

## 2. Architecture

```
Angular (onglet « Exigences & Traçabilité »)
  components/traceability/
    traceability.component.ts    sélection du projet + navigation entre les 5 pages
    tr-dashboard.component.ts    1. Tableau de bord
    tr-requirements.component.ts 2. Extraction et CRUD des exigences
    tr-analysis.component.ts     3. Documents UML, éléments, analyse IA, corrections manuelles
    tr-matrix.component.ts       4. Matrice (recherche, filtres, tri, export CSV)
    tr-report.component.ts       5. Rapport (statistiques, graphique, suggestions, export)
  services/traceability.service.ts         appels HTTP vers /api/traceability
  services/generated-documentation.store.ts mémorise les documentations générées par l'analyseur
        │ HTTP JSON
        ▼
FastAPI  api/endpoints/traceability.py   routes REST + traduction des erreurs en HTTP
         schemas/traceability.py         schémas Pydantic (API + contrats JSON de Gemini)
         services/traceability_service.py logique métier (CRUD, matrice, analyse, exports)
         services/traceability_ai.py      appels Gemini (prompts, timeout, quota, validation)
         services/coverage_service.py     calcul du score (fonctions pures)
         core/traceability_db.py          tables SQLite tr_*
```

### Réutilisation de l'existant

- **Base SQLite** : même fichier que la Gestion des Prompts (`settings.DATABASE_PATH`, `prompts.db`), même `get_connection()`. Les tables sont préfixées `tr_` ; `init_traceability_db()` est idempotent et ne touche jamais à la table `prompts`.
- **Documentation UML générée** : `DiagramService` (déjà utilisé par l'analyseur) mémorise chaque documentation générée dans le navigateur (`localStorage`, 10 dernières). La page « Traçabilité » propose de l'enregistrer dans le projet : l'OCR n'est pas relancé. Les acteurs déjà détectés (`detected_actors`) sont repris s'ils figurent dans le texte.
- **Style** : mêmes cartes, boutons dégradés, messages d'erreur et conventions Tailwind que les autres onglets.

### Modèle de données

| Table | Contenu | Contraintes |
|---|---|---|
| `tr_projects` | projet, cahier des charges, document UML actif | nom unique |
| `tr_requirements` | exigences | `UNIQUE(project_id, reference)`, `CHECK` type/priorité, cascade sur le projet |
| `tr_uml_documents` | documentations Markdown | cascade sur le projet |
| `tr_uml_elements` | acteurs / cas d'utilisation, origine `ia` / `manuel` / `generation` | `UNIQUE(document_id, kind, name)` |
| `tr_coverage` | statut + justification + recommandation par (exigence, document), origine `ia` / `manuel` | clé primaire composée, cascades |
| `tr_links` | associations exigence ↔ cas d'utilisation | `UNIQUE(requirement_id, element_id)`, cascades |
| `tr_analyses` | historique : résumé, suggestions, statistiques figées | cascade sur le projet |

Les clés étrangères sont activées (`PRAGMA foreign_keys = ON`) : supprimer une exigence supprime ses couvertures et associations ; supprimer un document remet à vide le document actif du projet.

## 3. Extraction IA et garde-fous

`services/traceability_ai.py` envoie trois types de prompts à Gemini (`response_mime_type="application/json"`, température 0,1) :

| Étape | Contrat JSON validé par Pydantic |
|---|---|
| Extraction des exigences | `{"requirements": [{"title", "description", "type", "priority"}]}` |
| Acteurs / cas d'utilisation | `{"actors": [...], "use_cases": [{"name", "actors"}]}` |
| Traçabilité | `{"mappings": [{"reference", "status", "use_cases", "justification", "recommendation"}], "summary", "suggestions"}` |

Garde-fous appliqués **côté serveur** après la réponse de Gemini :

- **Aucun élément inventé** : un acteur ou cas d'utilisation n'est conservé que s'il apparaît textuellement dans la documentation (comparaison sans accents ni casse, mot entier). Un cas cité par Gemini lors de la traçabilité mais absent du document est rejeté et signalé à l'utilisateur.
- **Exigences non fonctionnelles** : toujours « À vérifier manuellement » ; un cas d'utilisation ne prouve pas leur satisfaction.
- « Couverte » / « Partielle » sans cas d'utilisation valide ⇒ « Non couverte ».
- Exigence oubliée par Gemini ⇒ « À vérifier manuellement » (rien n'est supposé).
- **Validation humaine prioritaire** : une couverture corrigée manuellement (`origin = manuel`) n'est jamais écrasée par une nouvelle analyse IA.
- Les suggestions sont des **recommandations** ; le diagramme original n'est jamais modifié.

### Erreurs

Il n'y a **pas de résultat de secours fictif** : si Gemini échoue, l'API renvoie une erreur explicite et les données déjà saisies restent intactes.

| Cas | HTTP | Message |
|---|---|---|
| `GEMINI_API_KEY` absente, SDK absent, clé refusée | 503 | configuration à corriger |
| Quota dépassé (429 / `RESOURCE_EXHAUSTED`) | 429 | réessayer plus tard |
| Délai dépassé (`GEMINI_TIMEOUT_SECONDS`, 90 s par défaut) | 504 | réessayer |
| JSON invalide ou non conforme au schéma, réponse vide | 502 | relancer l'analyse |
| Autre erreur réseau / API | 502 | Gemini indisponible |

Variables d'environnement (fichier `.env` du backend, jamais commité) : `GEMINI_API_KEY` (obligatoire pour l'IA), `GEMINI_MODEL` (défaut `gemini-3.8-flash`, le modèle du projet), `GEMINI_TIMEOUT_SECONDS` (défaut 90). Le frontend ne contient aucun secret.

## 4. Calcul de la couverture

```
taux = (couvertes + 0,5 × partiellement couvertes) / exigences fonctionnelles analysables × 100
```

- **Dénominateur** : exigences **fonctionnelles** dont le statut est Couverte, Partielle ou Non couverte.
- Comptées **à part** (hors dénominateur) : exigences non fonctionnelles, « À vérifier manuellement » et « Non analysées ».
- Si le dénominateur vaut 0, le taux est « non calculable » (`null`), jamais 0 % ni 100 %.
- La formule et le dénominateur sont affichés dans le rapport et l'export Markdown.

Exemple : REQ-001 couverte (1) + REQ-002 partielle (0,5) + REQ-003 couverte (1) + REQ-004 non couverte (0) = 2,5 / 4 = **62,5 %** ; REQ-005 (performance) est « À vérifier » et n'entre pas dans le calcul.

## 5. Endpoints (`/api/traceability`)

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/dashboard` | statistiques globales, projets, analyses récentes |
| GET / POST | `/projects` | lister / créer un projet |
| GET / PUT / DELETE | `/projects/{id}` | consulter / modifier / supprimer (cascade) |
| POST | `/requirements/extract` | extraction Gemini (non enregistrée) |
| GET / POST | `/projects/{id}/requirements` | lister / ajouter (référence auto `REQ-NNN`) |
| POST | `/projects/{id}/requirements/bulk` | enregistrer les exigences validées (option `replace_existing`) |
| GET / PUT / DELETE | `/requirements/{id}` | consulter / modifier / supprimer (avec ses associations) |
| POST | `/files/read-text` | lire un `.txt` / `.md` (≤ 1 Mo, UTF-8, non vide) |
| GET / POST | `/projects/{id}/documents` | lister / ajouter une documentation UML Markdown |
| PUT | `/projects/{id}/documents/{doc}/active` | choisir le document analysé |
| GET / DELETE | `/documents/{id}` | consulter (avec éléments) / supprimer |
| POST | `/documents/{id}/extract-elements` | identifier acteurs et cas d'utilisation (Gemini) |
| POST | `/documents/{id}/elements` | ajouter un acteur / cas d'utilisation manuellement |
| DELETE | `/elements/{id}` | supprimer un élément |
| POST | `/projects/{id}/analyze` | analyse de traçabilité Gemini (body `{document_id}`) |
| GET | `/projects/{id}/matrix?document_id=` | matrice + statistiques |
| PUT | `/projects/{id}/coverage/{requirement_id}` | correction manuelle (statut, cas, justification) |
| GET | `/projects/{id}/matrix.csv` | export CSV (`;`, UTF-8 avec BOM pour Excel) |
| GET | `/projects/{id}/report.md` | export du rapport Markdown |
| GET | `/projects/{id}/analyses`, `/analyses/{id}` | historique des analyses |

Documentation interactive : `http://localhost:8000/docs`, section « Exigences & Traçabilité ».

## 6. Lancer et tester

```bash
# Backend (à la racine)
pip install -r requirements.txt
echo GEMINI_API_KEY=votre_cle > .env
uvicorn main:app --reload            # crée les tables tr_* au démarrage

# Frontend
cd frontend
npm install --legacy-peer-deps
npm start                            # http://localhost:4200 → onglet « Exigences & Traçabilité »

# Tests backend (Gemini toujours simulé, aucune clé nécessaire)
pip install -r requirements-dev.txt
pytest tests/test_traceability.py --cov=services.traceability_service --cov=services.traceability_ai \
       --cov=services.coverage_service --cov=api.endpoints.traceability --cov-report=term-missing

# Tests et build frontend
cd frontend
npx ng test --watch=false --browsers=ChromeHeadless
npm run build
```

## 7. Exemple complet

1. Onglet **Analyser un diagramme** : importer le diagramme de réservation → documentation « Système de réservation » générée (acteurs Client, Administrateur).
2. Onglet **Exigences & Traçabilité** → **Nouvelle analyse** → nom « Réservation en ligne », coller :
   > Le client doit pouvoir se connecter, consulter son profil et effectuer une réservation. L'administrateur doit pouvoir gérer les utilisateurs. Le système doit répondre rapidement aux requêtes.
3. **Extraire les exigences avec IA** → REQ-001 Authentification du client, REQ-002 Consultation du profil, REQ-003 Réservation, REQ-004 Gestion des utilisateurs (fonctionnelles), REQ-005 Performance du système (non fonctionnelle). Corriger si besoin → **Enregistrer les exigences**.
4. Page **Traçabilité** → « Utiliser cette documentation » (documentation générée à l'étape 1) → **Identifier avec Gemini** (ou ajouter les cas à la main) → **Lancer l'analyse avec Gemini**.
5. Résultat : REQ-001 → *Se connecter* (Couverte), REQ-005 → « À vérifier manuellement », une exigence de paiement absente du diagramme → « Non couverte » avec la recommandation « étudier l'ajout du cas d'utilisation “Effectuer un paiement” ». Corriger une ligne avec **Corriger** si nécessaire.
6. Pages **Matrice** (filtrer, **Exporter en CSV**) et **Rapport** (graphique, suggestions, **Exporter en Markdown** ou **Imprimer / PDF**).

## 8. Limites connues

- Le PDF est produit par la fonction d'impression du navigateur (aucune dépendance PDF ajoutée au projet).
- La liste des documentations générées réutilisables est propre au navigateur (`localStorage`) ; une fois enregistrée dans un projet, la documentation est en base et partagée.
- La qualité de l'extraction dépend de Gemini : l'utilisateur doit valider les exigences et associations proposées (c'est voulu).
