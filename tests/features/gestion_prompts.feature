Feature: Gestion des prompts de génération
  En tant qu'architecte logiciel qui utilise UML Architecture Analyzer
  Je veux créer, consulter, modifier et supprimer les prompts envoyés à l'IA, et choisir le prompt utilisé pour une analyse
  Afin de comparer différents prompts et obtenir la documentation la plus adaptée à mon besoin

  Background:
    Given l'application est démarrée
    And le prompt "Architecte Sénior" existe et il est le prompt par défaut
    And je suis sur l'onglet "Gestion des Prompts"

  # --- Consulter ---------------------------------------------------------------

  Scenario: Afficher la liste des prompts avec le prompt par défaut en premier
    Given le prompt "Résumé court" existe
    When j'ouvre l'onglet "Gestion des Prompts"
    Then je vois 2 prompts
    And le premier prompt est "Architecte Sénior" avec le badge "Par défaut"

  # --- Créer -------------------------------------------------------------------

  Scenario: Créer un prompt valide
    When je clique sur "+ Nouveau prompt"
    And je saisis le nom "Résumé court"
    And je saisis le contenu "Tu es un analyste. Résume le diagramme UML en 5 lignes maximum."
    And je clique sur "Enregistrer"
    Then je vois le message "Prompt créé avec succès."
    And le prompt "Résumé court" apparaît dans la liste

  Scenario: Créer un prompt avec un nom déjà utilisé
    Given le prompt "Résumé court" existe
    When je crée un prompt nommé "Résumé court" avec un contenu valide
    Then je vois le message d'erreur "Un prompt nommé 'Résumé court' existe déjà."
    And la liste contient toujours un seul prompt "Résumé court"

  Scenario Outline: Refuser un prompt avec des données invalides
    When je crée un prompt nommé "<nom>" avec le contenu "<contenu>"
    Then je vois le message d'erreur "Le nom doit faire au moins 3 caractères et le contenu au moins 20 caractères."
    And aucun nouveau prompt n'est ajouté

    Examples:
      | nom          | contenu                                         |
      | ab           | Tu es un analyste. Résume le diagramme UML.     |
      | Résumé court | Trop court                                      |
      | ab           | Court                                           |

  # --- Modifier ----------------------------------------------------------------

  Scenario: Modifier un prompt
    Given le prompt "Résumé court" existe
    When je clique sur "Modifier" pour le prompt "Résumé court"
    And je remplace le nom par "Résumé très court"
    And je clique sur "Enregistrer"
    Then je vois le message "Prompt modifié avec succès."
    And le prompt "Résumé très court" apparaît dans la liste
    And le prompt "Résumé court" n'apparaît plus dans la liste

  # --- Supprimer ---------------------------------------------------------------

  Scenario: Supprimer un prompt après confirmation
    Given le prompt "Résumé court" existe
    When je clique sur "Supprimer" pour le prompt "Résumé court"
    Then une confirmation "Supprimer « Résumé court » ?" s'affiche
    When je clique sur "Oui, supprimer"
    Then le prompt "Résumé court" n'apparaît plus dans la liste

  Scenario: Annuler la suppression d'un prompt
    Given le prompt "Résumé court" existe
    When je clique sur "Supprimer" pour le prompt "Résumé court"
    And je clique sur "Annuler"
    Then le prompt "Résumé court" est toujours dans la liste

  Scenario: Impossible de supprimer le prompt par défaut
    When je regarde le prompt "Architecte Sénior"
    Then le bouton "Supprimer" n'est pas proposé pour ce prompt
    And si la suppression est demandée directement à l'API, elle est refusée avec le message "Impossible de supprimer le prompt par défaut. Définissez d'abord un autre prompt par défaut."

  # --- Prompt par défaut -------------------------------------------------------

  Scenario: Changer le prompt par défaut
    Given le prompt "Résumé court" existe
    When je clique sur "Définir par défaut" pour le prompt "Résumé court"
    Then je vois le message "« Résumé court » est maintenant le prompt par défaut."
    And "Résumé court" est le seul prompt avec le badge "Par défaut"
    And "Résumé court" est affiché en premier dans la liste

  # --- Analyse de qualité (Atelier 4) ------------------------------------------

  Scenario: Analyser la qualité d'un prompt avec l'IA
    Given le service Gemini est disponible
    When j'ouvre le formulaire d'un prompt
    And je clique sur "Analyser la qualité"
    Then je vois un score sur 100 et un verdict
    And je vois les points forts et les suggestions d'amélioration
    And je vois le badge "Analyse IA (Gemini)"

  Scenario: Analyser la qualité quand l'IA est indisponible
    Given le service Gemini est indisponible
    When j'ouvre le formulaire d'un prompt
    And je clique sur "Analyser la qualité"
    Then je vois quand même un score sur 100 et un verdict
    And je vois le badge "Analyse locale (fallback)" avec la raison de l'indisponibilité

  # --- Utilisation dans l'analyse de diagramme ---------------------------------

  Scenario: Analyser un diagramme avec un prompt choisi
    Given le prompt "Résumé court" existe
    And je suis sur l'onglet "Analyser un diagramme"
    When je dépose l'image d'un diagramme UML
    And je choisis le prompt "Résumé court" dans la liste "Prompt à utiliser"
    And je clique sur "Generate Documentation"
    Then la documentation est générée avec le prompt "Résumé court"
    And je vois "Prompt utilisé : Résumé court" dans le résultat

  Scenario: Le prompt par défaut est présélectionné
    When je vais sur l'onglet "Analyser un diagramme"
    Then la liste "Prompt à utiliser" affiche "Architecte Sénior (par défaut)"
