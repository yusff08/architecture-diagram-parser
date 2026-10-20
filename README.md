# 🧠 AI-powered UML Architecture Analyzer

Bienvenue dans le dépôt du projet **UML Architecture Analyzer** ! 

## 🎯 Ce que fait l'application
Cette application intelligente permet aux utilisateurs de télécharger (via glisser-déposer) des images de **diagrammes de cas d'utilisation UML**. 
1. **Extraction (OCR)** : Elle utilise la vision par ordinateur (PaddleOCR) pour lire le texte, les acteurs et les relations présents dans l'image.
2. **Analyse (LLM)** : Elle envoie ces données à l'intelligence artificielle Google Gemini (via le tout nouveau SDK `google-genai`).
3. **Génération** : Elle produit automatiquement et instantanément une documentation technique structurée, précise et prête à l'emploi (au format Markdown).

## 👥 Pour qui est-elle conçue ?
Cette application est un outil de productivité destiné aux :
- **Architectes Logiciels et Analystes Métier** : Pour transformer rapidement des schémas visuels en documentation textuelle standardisée.
- **Ingénieurs Logiciels et Développeurs** : Pour comprendre l'architecture d'un système sans avoir à décrypter un schéma complexe.
- **Étudiants en Informatique** : Pour vérifier que la logique de leurs diagrammes UML est claire et cohérente.

---

## 🧩 Architecture et Modules (Pour les contributeurs)

Pour faciliter le travail en équipe et l'ajout de nouvelles fonctionnalités, voici où trouver les modules clés :

### 🖥️ Frontend (Dossier `frontend/`)
Le frontend est développé en **Angular 17** avec **Tailwind CSS**.
- **Composant Upload (Glisser-Déposer)** : `frontend/src/app/components/diagram-uploader/` (Gère la zone de dépôt d'image et la validation).
- **Afficheur Markdown** : `frontend/src/app/components/documentation-viewer/` (Parse et stylise la réponse de l'IA en utilisant la bibliothèque `marked`).
- **Services API** : `frontend/src/app/services/` (Contient les appels HTTP vers le backend).

### ⚙️ Backend (Dossiers `/` et `services/`)
Le backend est une API REST développée avec **FastAPI (Python)**.
- **Point d'Entrée (API)** : `main.py` et les fichiers dans `api/` (Définition des routes et gestion des requêtes).
- **Service IA (Gemini)** : `services/llm_service.py` (C'est ici qu'est configuré le modèle `gemini-3.8-flash` via le SDK `google-genai`).
- **Moteur OCR** : Scripts gérant l'extraction de texte via OpenCV et PaddleOCR.

### 📝 Module « Gestion des Prompts »
Permet de gérer (CRUD) les prompts envoyés à Gemini au lieu d'un prompt codé en dur, et de choisir le prompt utilisé pour chaque analyse.
- **Backend** : `api/endpoints/prompts.py` (routes `/api/prompts`), `services/prompt_service.py` (logique métier), `core/database.py` (SQLite, fichier `prompts.db` créé au premier démarrage avec un prompt par défaut).
- **Analyse de qualité d'un prompt** : `services/prompt_analyzer.py` (Gemini + analyse locale de secours si l'API est indisponible), route `POST /api/prompts/analyze`. Spécification : `docs/specification-analyse-prompt.md`.
- **Frontend** : onglet « Gestion des Prompts » (`frontend/src/app/components/prompt-manager/`) et liste « Prompt à utiliser » dans l'analyseur.
- **Tests** : `tests/` (pytest, 100 % de couverture du module) et `tests/features/gestion_prompts.feature` (scénarios Gherkin).
  ```bash
  pip install -r requirements-dev.txt
  pytest --cov=services.prompt_service --cov=services.prompt_analyzer --cov=api.endpoints.prompts --cov=core.database --cov-report=term-missing
  ```
- **Prompts utilisés pour construire le module** : `docs/prompt-gestion-prompts.md`.

### 🔗 Module « Exigences & Traçabilité »
Extrait les exigences d'un cahier des charges avec Gemini, les associe aux cas d'utilisation de la documentation UML générée (sans relancer l'OCR) et calcule le taux de couverture.
- **Backend** : `api/endpoints/traceability.py` (routes `/api/traceability`), `services/traceability_service.py` (logique métier), `services/traceability_ai.py` (Gemini : timeout, quota, validation JSON), `services/coverage_service.py` (score), `core/traceability_db.py` (tables SQLite `tr_*` dans la même base que les prompts).
- **Frontend** : onglet « Exigences & Traçabilité » (`frontend/src/app/components/traceability/`) : tableau de bord, exigences, traçabilité, matrice (export CSV), rapport (export Markdown / PDF).
- **Tests** : `tests/test_traceability.py` (Gemini simulé) et `frontend/src/app/**/traceability*.spec.ts`.
- **Documentation détaillée** : `docs/gestion-exigences-tracabilite.md`.

---

## 🚀 Technologies Utilisées
- **Backend** : FastAPI (Python)
- **OCR Engine** : PaddleOCR + OpenCV
- **LLM** : Google Gemini 3.8 Flash (SDK `google-genai`)
- **Frontend** : Angular 17 + Tailwind CSS v3

---

## 🛠️ Prérequis

Avant de cloner le projet, assurez-vous d'avoir installé les éléments suivants sur votre machine :
1. **[Python 3.10+](https://www.python.org/downloads/)**
2. **[Node.js 20+](https://nodejs.org/en/)** (et npm)
3. **[Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-US/cpp/windows/latest-supported-vc-redist?view=msvc-170)** *(Strictement requis sur Windows pour éviter les crashs du moteur C++ sous-jacent de PaddleOCR et oneDNN)*.

---

## ⚙️ Installation & Démarrage

### 1. Configuration du Backend (Python)

Ouvrez un terminal à la racine du projet (`mini projet/`) et exécutez les commandes suivantes :

```bash
# Créer un environnement virtuel isolé
python -m venv venv

# Activer l'environnement virtuel
# Sur Windows :
venv\Scripts\activate
# Sur Mac/Linux :
source venv/bin/activate

# Installer les dépendances du backend
pip install -r requirements.txt
```

**🔐 Variables d'environnement :**
Créez un fichier `.env` à la racine du projet et ajoutez-y votre clé d'API Gemini (sans espaces ni guillemets) :
```env
GEMINI_API_KEY=votre_cle_api_ici
```

**Démarrer le serveur API :**
```bash
uvicorn main:app --reload
```
Le backend sera alors opérationnel et à l'écoute sur `http://localhost:8000`.

---

### 2. Configuration du Frontend (Angular)

Ouvrez un **nouveau terminal** (pour laisser le backend tourner) et déplacez-vous dans le répertoire front :

```bash
cd frontend

# Installer les packages Node (l'utilisation de --legacy-peer-deps est critique pour ngx-markdown)
npm install --legacy-peer-deps

# Démarrer le serveur de développement Angular
npm start
```
L'interface utilisateur sera accessible sur `http://localhost:4200`.

---

## 🌿 Workflow Git & Collaboration (Règles de l'équipe)

Pour garantir la stabilité de la branche `main` (qui est surveillée et compilée automatiquement par notre pipeline CI/CD GitHub Actions), l'équipe utilise un workflow de Feature Branching strict.

1. **Ne jamais commiter directement sur la branche `main`.**
2. Avant de commencer une nouvelle tâche, synchronisez-vous et créez une branche de fonctionnalité :
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/nom-de-la-fonctionnalite
   # Exemple : git checkout -b feature/upload-drag-and-drop
   ```
3. Développez, testez localement, et commitez vos changements avec des messages descriptifs.
4. Pushez votre branche sur GitHub :
   ```bash
   git push -u origin feature/nom-de-la-fonctionnalite
   ```
5. Allez sur GitHub et ouvrez une **Pull Request (PR)** vers `main`. 
6. Le pipeline CI va s'exécuter pour vérifier que le code compile. Demandez à un autre membre de l'équipe de faire une Code Review avant d'approuver le Merge !

---

## 🧪 Module « Gestion des Tests » (Robustesse & Injection d'Anomalies)

Le module **Gestion des Tests** est un framework complet d'assurance qualité et d'évaluation de la résilience logicielle conçu pour éprouver l'application face à des conditions réelles dégradées, des pannes d'infrastructure et des attaques d'injection.

### 🌟 Fonctionnalités Clés
1. **Génération IA (Gemini 3.8 Flash)** : Analyse la documentation textuelle UML pour produire automatiquement des cas de test (nominaux, limites et erreurs) avec association automatique d'anomalies issues du catalogue.
2. **Mode Secours Local (Fallback)** : En cas de panne ou d'indisponibilité du service Gemini (quota dépassé, absence de clé ou réseau coupé), un moteur local prend le relais de façon transparente (`fallback: true`).
3. **Moteur d'Injection de Fautes (`services/fault_injector.py`)** : Catalogue de plus de 30 anomalies classées en 4 catégories :
   - **Catégorie A (Upload & Entrée OCR)** : Images floues (flou gaussien), bruitées (bruit gaussien / sel et poivre), faible contraste, très sombres, rotations (5°, 90°, 180°), images tronquées, résolutions minuscules (16x16) ou géantes (4000x4000), images blanches ou photos hors diagramme, fichiers vides (0 octet), fichiers corrompus, extensions invalides et fichiers trop volumineux (> 10 Mo).
   - **Catégorie B (Données Extraites & Entrée LLM)** : Listes de textes vides, artefacts d'OCR parasites, doublons massifs d'acteurs, cas d'utilisation orphelins, acteurs orphelins, relations circulaires (`<<include>>` réciproques), textes extrêmement longs (> 50k caractères), caractères Unicode spéciaux/bidirectionnels, et tentatives d'injection de prompt.
   - **Catégorie C (Service LLM Gemini)** : Simulation contrôlée de Timeout, erreurs 429 (quota), erreurs 500 serveur Google, clé API manquante ou invalide, réponses vides, réponses non JSON (HTML/texte brut), JSON tronqués, forte latence et mauvaise langue.
   - **Catégorie D (API REST)** : Payloads invalides, identifiants inexistants (404) et requêtes simultanées concurrentes.
4. **Runner Séquentiel Isolé (`services/test_runner.py`)** : Exécute les tests de façon isolée (scope contextuel thread-safe), compare le comportement observé au comportement attendu (`expected_behavior`), enregistre l'historique détaillé (`duration_ms`, HTTP code, trace) et met à jour le statut du test.
5. **Tableau de Bord & Scores de Robustesse** : Suivi des statuts (À faire, Passé, Échoué), taux de réussite et scores de robustesse spécifiques par catégorie (Score A, B, C, D) et global.
6. **Détection Intelligente d'Anomalies (`services/anomaly_detector.py`)** : Analyse hybride d'une documentation UML en deux étages :
   - **Moteur de règles local** (toujours disponible) : extraction des acteurs, cas d'utilisation et relations `<<include>>`/`<<extend>>`, puis détection des acteurs et cas orphelins, relations circulaires (parcours de graphe), doublons exacts et approchés (similarité ≥ 85 %), bruit OCR, caractères Unicode invisibles/bidirectionnels, textes extrêmes, modèle vide et tentatives d'injection de prompt.
   - **Validation par Gemini** : chaque anomalie reçoit un verdict (confirmée ou faux positif probable) avec une explication et un indice de confiance ; l'IA ajoute les anomalies sémantiques invisibles aux règles (noms ambigus, responsabilités incohérentes, mauvais usage de `<<extend>>`...). En cas d'indisponibilité, le résultat des règles est renvoyé seul (`fallback_used: true`).
   - **Score de qualité** sur 100, pondéré par la gravité et la confiance, et **génération automatique des cas de test de robustesse** : chaque anomalie est reliée à une injection du catalogue (`B_CIRCULAR_RELATIONS`, `B_ACTOR_WITHOUT_USECASE`...).
7. **Exports Multi-Formats** : Export en un clic du cahier de recette complet au format **Markdown** (.md) et en spécifications BDD **Gherkin** (.feature en français).

### 🔒 Sécurité & Isolation de l'Injection
- **Désactivée par défaut en production** : L'injection n'est active que si `ENABLE_FAULT_INJECTION=true` est explicitement configuré dans le fichier `.env`. Si désactivée, les routes d'exécution renvoient immédiatement un code **HTTP 403 Forbidden** avec un message explicite.
- **Isolation stricte** : L'application des fautes est encapsulée dans un gestionnaire de contexte (`with fault_injector.apply(id):`) basé sur `threading.local()`, garantissant qu'aucune requête utilisateur concurrente n'est perturbée.

### 🌐 Endpoints de l'API (`/api/tests`)
- `GET  /api/tests/injections` : Catalogue complet des anomalies et comportements attendus.
- `POST /api/tests/generate` : Génération IA des cas de test (`save=true` pour persister).
- `POST /api/tests/anomalies/detect` : Détection intelligente d'anomalies (`use_ai`, `generate_tests`, `save`).
- `GET  /api/tests` : Liste filtrable (`use_case`, `test_type`, `status`, `priority`, `injection_id`).
- `POST /api/tests` : Création manuelle d'un cas de test.
- `GET  /api/tests/{id}` : Consultation détaillée d'un test.
- `PUT  /api/tests/{id}` : Mise à jour d'un cas de test.
- `DELETE /api/tests/{id}` : Suppression d'un cas de test.
- `PATCH /api/tests/{id}/status` : Modification manuelle du statut (`a_faire`, `passe`, `echoue`).
- `POST /api/tests/{id}/run` : Exécution unitaire d'un test sous injection.
- `POST /api/tests/run-all` : Exécution séquentielle de tout ou partie des tests.
- `GET  /api/tests/{id}/runs` : Historique des exécutions d'un test.
- `GET  /api/tests/stats` : Statistiques, taux de réussite et scores de robustesse (A, B, C, D).
- `GET  /api/tests/export?format=markdown|gherkin` : Téléchargement du cahier de test.

### 🚀 Exécution des Tests & Couverture de Code
Pour lancer la suite de tests automatisée du module avec rapport de couverture :

```bash
# Activer le mode injection pour les tests
export ENABLE_FAULT_INJECTION=true  # ou sous Windows PowerShell : $env:ENABLE_FAULT_INJECTION="true"

# Lancer la commande de couverture officielle
pytest --cov=services.test_service --cov=services.test_generator --cov=services.test_runner --cov=services.fault_injector --cov=api.endpoints.tests --cov-report=term-missing
```
