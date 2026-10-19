# language: fr
Fonctionnalité: Gestion des tests de robustesse et injection d'anomalies
  En tant qu'ingénieur qualité et architecte logiciel
  Je souhaite injecter des fautes et anomalies dans le pipeline d'analyse UML
  Afin de mesurer la résilience du système et d'assurer une haute disponibilité sans crash.

  Contexte:
    Étant donné que le module de test de robustesse est actif
    Et que le catalogue d'injection contient les 4 catégories d'anomalies (A, B, C, D)

  @generation @ia
  Scénario: Génération automatique de cas de test par l'IA Gemini
    Étant donné que l'utilisateur fournit une documentation UML avec des cas d'utilisation et des acteurs
    Quand il demande la génération de tests avec le modèle Gemini
    Alors le système produit une liste de tests de type "nominal", "limite" et "erreur"
    Et chaque test d'erreur est automatiquement associé à une anomalie du catalogue

  @injection @categorie_a @ocr
  Scénario: Injection d'une image floue dans le pipeline OCR
    Étant donné un cas de test associé à l'anomalie "A_BLUR_GAUSSIAN"
    Quand le test est exécuté par le runner
    Alors l'image est floutée dynamiquement via OpenCV
    Et le système capture l'indisponibilité du texte sans planter
    Et le statut du test passe à "passe" avec le comportement "mode_secours"

  @injection @categorie_c @llm
  Scénario: Simulation d'un timeout sur l'API Gemini
    Étant donné un cas de test associé à l'anomalie "C_LLM_TIMEOUT"
    Quand le runner exécute l'analyse UML
    Alors l'appel au modèle Gemini déclenche un timeout contrôlé
    Et l'application bascule gracieusement en mode dégradé
    Et le temps d'exécution est enregistré avec le détail de l'erreur

  @resilience @fallback
  Scénario: Déclenchement du mode secours local par gabarits
    Étant donné que la clé API Gemini est absente ou que le quota est dépassé
    Quand l'utilisateur lance la génération de tests
    Alors le générateur active automatiquement le fallback local par gabarits
    Et la réponse indique "fallback: true"
    Et au moins 3 cas de test structurés sont enregistrés en base

  @export @documentation
  Scénario: Exportation de la suite de tests
    Étant donné une suite de tests avec des exécutions validées et échouées
    Quand l'utilisateur exporte au format "markdown"
    Alors un document complet avec les statistiques et le tableau des tests est généré
    Quand l'utilisateur exporte au format "gherkin"
    Alors un fichier de spécification .feature valide en français est produit
