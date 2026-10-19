# Cahier des Charges Initial : Module « Gestion des Tests »

Tu es un ingénieur logiciel senior. Tu travailles sur le projet "UML Architecture Analyzer" (backend FastAPI + Python, frontend Angular 17 + Tailwind CSS v3, SQLite, PaddleOCR + OpenCV, SDK google-genai pour Gemini, tests pytest). Ta mission : créer un nouveau module « Gestion des Tests » : un module de test de robustesse avec INJECTION D'ERREURS ET D'ANOMALIES dans le pipeline de l'application.

## 0. Règles du projet
- Le module « Gestion des Prompts » appartient à un autre membre de l'équipe : tu peux le LIRE pour copier les conventions (structure, nommage, schémas Pydantic, gestion d'erreurs, style Angular), mais tu ne dois PAS le modifier. Les seuls fichiers existants que tu peux toucher : main.py (enregistrer le routeur), core/database.py (ajouter mes tables sans changer les siennes), la navigation Angular (ajouter un onglet) et le README (ajouter une section).
- Travaille sur une branche : git checkout -b feature/gestion-des-tests. Ne commite jamais sur main.
- Réutilise services/llm_service.py et le modèle Gemini déjà configuré. N'ajoute aucune dépendance lourde : utilise OpenCV et numpy (déjà présents) pour dégrader les images.
- Les tests existants doivent continuer à passer.

## 1. Objectif fonctionnel
1. GÉNÉRATION (LLM) : à partir de la documentation d'une analyse UML (acteurs, cas d'utilisation, relations), Gemini génère des cas de test par cas d'utilisation, de types « nominal », « limite » et « erreur ».
2. INJECTION DE FAUTES : un moteur d'injection (fault injector) permet de perturber volontairement le pipeline pour vérifier que l'application réagit proprement (message d'erreur clair, pas de crash, mode dégradé).
3. EXÉCUTION : un runner exécute les tests (un seul, une sélection ou tous), compare le comportement observé au comportement attendu, et enregistre automatiquement le statut.
4. SUIVI : statuts « à faire », « passé », « échoué », historique des exécutions, statistiques et score de robustesse.
5. EXPORT : Markdown et Gherkin (.feature).

## 2. Catalogue d'injections (services/fault_injector.py)
Chaque injection a : id, catégorie, nom, description, paramètres, comportement attendu de l'application.
### A. Anomalies sur les fichiers uploadés (entrée de l'OCR)
- Image floue (flou gaussien), bruitée (bruit gaussien / sel et poivre), faible contraste, très sombre, rotation (5°, 90°, 180°), image tronquée, très petite et très grande résolution, image blanche, image sans diagramme.
- Fichier vide (0 octet), fichier corrompu (octets aléatoires), mauvais format (texte renommé en .png), extension non supportée, fichier trop volumineux.
Génère les images dégradées par code à partir d'une image de référence (créer un petit diagramme de test dans tests/fixtures/).
### B. Anomalies sur les données extraites (sortie de l'OCR / entrée du LLM)
- Texte vide, texte avec caractères parasites, noms d'acteurs dupliqués, cas d'utilisation sans acteur, acteur sans cas d'utilisation, relations include/extend circulaires ou incohérentes, texte extrêmement long, caractères spéciaux / unicode / tentative d'injection de prompt dans le texte.
### C. Fautes sur le service LLM (Gemini)
- Timeout, erreur 429 (quota), erreur 500, clé API absente ou invalide, réponse vide, réponse non JSON, JSON tronqué, réponse très lente, réponse en mauvaise langue.
Implémente ces fautes via un wrapper/décorateur ou un patch contrôlé autour de l'appel à llm_service, SANS modifier le code de production de manière intrusive.
### D. Anomalies sur l'API
- Payloads invalides (champs manquants, types erronés, valeurs hors énumération), requêtes concurrentes, identifiants inexistants.
### Sécurité de l'injection
- Désactivée par défaut : n'est active que si ENABLE_FAULT_INJECTION=true dans .env ; sinon les routes d'exécution renvoient 403 avec un message clair.
- L'injection est limitée au scope d'une exécution (context manager) et ne doit JAMAIS affecter les requêtes normales des autres utilisateurs.

## 3. Backend
### 3.1 Base de données (core/database.py)
Table test_cases : id, analysis_name, use_case, actor (nullable), title, test_type (nominal | limite | erreur), injection_id (nullable), preconditions, steps (JSON), expected_result, expected_behavior (ex. "erreur_4xx_message_clair" | "mode_secours" | "traitement_normal" | "rejet_propre"), priority (haute | moyenne | basse), status (a_faire | passe | echoue, défaut a_faire), generated_by_llm (BOOLEAN), created_at, updated_at.
Table test_runs : id, test_case_id (FK), started_at, duration_ms, status (passe | echoue | erreur), actual_behavior, details (JSON : code HTTP, message, trace courte), injection_id. Contraintes CHECK sur les énumérations.
### 3.2 Services
- services/test_service.py : CRUD, changement de statut, filtres, statistiques, export Markdown et Gherkin.
- services/test_generator.py : appelle Gemini pour produire une liste JSON stricte de cas de test (réponse JSON uniquement, nettoyage des balises ```json, validation Pydantic, éléments invalides ignorés). Le LLM doit aussi proposer, pour les tests de type limite/erreur, une injection_id du catalogue. FALLBACK local par gabarits si Gemini est indisponible (indicateur "fallback": true).
- services/test_runner.py : pour un test donné, applique l'injection correspondante dans un scope isolé, exécute le pipeline (OCR → LLM → documentation) en appelant directement les services, mesure la durée, capture le résultat/l'exception, compare à expected_behavior, enregistre un test_run et met à jour le statut du test. Timeout global par exécution et exécution séquentielle (pas de dégradation du serveur).
### 3.3 Routes (api/endpoints/tests.py)
- GET  /api/tests/injections                → catalogue des injections
- POST /api/tests/generate                  → génération LLM (save=true pour enregistrer)
- GET/POST/PUT/DELETE /api/tests[/{id}]     → CRUD avec filtres (use_case, type, statut, priorité, injection)
- PATCH /api/tests/{id}/status              → statut manuel
- POST /api/tests/{id}/run                  → exécuter un test
- POST /api/tests/run-all                   → exécuter une sélection ou tous les tests
- GET  /api/tests/{id}/runs                 → historique des exécutions
- GET  /api/tests/stats                     → total, répartition par statut/type/injection, taux de réussite, score de robustesse par catégorie (A, B, C, D)
- GET  /api/tests/export?format=markdown|gherkin
Schémas Pydantic, codes HTTP corrects (201, 204, 403, 404, 422), messages d'erreur en français.

## 4. Frontend (Angular 17 + Tailwind)
Crée frontend/src/app/components/test-manager/ (standalone) et frontend/src/app/services/test.service.ts. Ajoute l'onglet « Gestion des Tests ».
- Génération : coller/charger la documentation, bouton « Générer avec l'IA », indicateur de chargement, bandeau si fallback utilisé.
- Catalogue d'injections : liste filtrable par catégorie (A, B, C, D) avec description.
- Tableau des tests : filtres, badges (à faire = gris, passé = vert, échoué = rouge), badge de type, bouton « Exécuter » par ligne et « Tout exécuter » avec barre de progression, détail de la dernière exécution (comportement attendu vs observé, durée), historique.
- Formulaire modal de création/édition (étapes dynamiques, choix de l'injection).
- Tableau de bord : total, répartition par statut, taux de réussite, score de robustesse par catégorie.
- Boutons d'export Markdown et Gherkin. États vide/chargement/erreur, interface responsive. Avertissement visible si ENABLE_FAULT_INJECTION est désactivé.

## 5. Tests du module (objectif : 100 % de couverture)
- tests/test_fault_injector.py : chaque injection produit bien l'anomalie attendue (image dégradée différente de l'originale, fichier corrompu, etc.).
- tests/test_test_service.py, tests/test_test_generator.py (Gemini mocké : réponse valide, JSON invalide, JSON entouré de ```json, erreur API, clé absente → fallback), tests/test_test_runner.py (passé / échoué / erreur / timeout / injection désactivée), tests/test_tests_endpoints.py (TestClient, tous les codes de retour).
- Base SQLite temporaire pour l'isolation. Fixtures d'images dans tests/fixtures/.
- Ajoute tests/features/gestion_tests.feature (scénarios Gherkin en français : générer, injecter une image floue, simuler un timeout Gemini, vérifier le mode secours, exporter).
- Commande de couverture à fournir :
  pytest --cov=services.test_service --cov=services.test_generator --cov=services.test_runner --cov=services.fault_injector --cov=api.endpoints.tests --cov-report=term-missing

## 6. Documentation et CI
- README : section « Module Gestion des Tests » (backend, frontend, injections, variable ENABLE_FAULT_INJECTION, tests, commande de couverture).
- Crée docs/prompt-gestion-tests.md contenant ce prompt.
- Vérifie que le pipeline GitHub Actions compile toujours ; ajoute pytest au workflow si absent (avec ENABLE_FAULT_INJECTION=true uniquement pour les tests).

## 7. Qualité et livrables
- Code typé (type hints, TypeScript strict), propre, sans clé API en dur, sans modification du module prompts.
- À la fin, résume : fichiers créés/modifiés, commandes pour lancer backend, frontend et tests, limites connues.
