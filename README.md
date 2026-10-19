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
