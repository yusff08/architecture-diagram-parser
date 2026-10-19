# Spécification : Analyse de la qualité d'un prompt (Atelier 4)

## Objectif
Aider l'utilisateur de la Gestion des Prompts à écrire un **bon prompt** : l'IA évalue le texte du prompt, donne un score et propose des améliorations. Si l'API IA n'est pas disponible, une **analyse locale** prend le relais.

## Entrée (input)
| Champ | Type | Règle |
|---|---|---|
| `content` | texte | Le contenu du prompt à analyser, minimum 20 caractères |

Endpoint : `POST /api/prompts/analyze` avec le corps `{ "content": "..." }`.

## Sortie (output)
```json
{
  "score": 85,
  "verdict": "Excellent",
  "strengths": ["Rôle défini", "Tâche claire"],
  "suggestions": ["Précisez le format de sortie attendu (Markdown, tableau, sections...)."],
  "source": "ia",
  "fallback_reason": null
}
```
- `score` : entier de 0 à 100
- `verdict` : `Excellent` (≥ 80), `Correct` (≥ 50), `À améliorer` (< 50)
- `source` : `ia` (Gemini) ou `local` (fallback)
- `fallback_reason` : pourquoi le fallback a été utilisé (`null` si l'IA a répondu)

## Comportement normal
Le prompt est envoyé à **Google Gemini** avec un méta-prompt qui demande une évaluation au format JSON. La réponse est validée (champs présents, score borné entre 0 et 100).

## Comportements d'erreur (fallback local)
| Situation | Comportement |
|---|---|
| Clé `GEMINI_API_KEY` absente | Analyse locale, `fallback_reason = "Clé GEMINI_API_KEY absente."` |
| SDK `google-genai` non installé | Analyse locale, raison = erreur d'import |
| API indisponible / erreur réseau / quota | Analyse locale, raison = message de l'erreur |
| Réponse de Gemini invalide (pas du JSON, champs manquants) | Analyse locale, raison = réponse invalide |
| `content` < 20 caractères | Erreur `422` (validation), pas d'analyse |

L'application **ne plante jamais** : l'utilisateur obtient toujours un résultat.

## Règles de l'analyse locale (100 points)
| Critère | Points | Détecté par (mots-clés / forme) |
|---|---|---|
| Rôle défini | 15 | « tu es », « vous êtes », « en tant que », « agis comme », « you are », « act as » |
| Tâche claire | 20 | verbes d'action : analyse, rédige, génère, identifie, déduis, résume, explique, liste… |
| Contexte | 15 | UML, diagramme, cas d'utilisation, acteur, OCR, système… |
| Structure | 15 | liste numérotée ou à puces (au moins 2 lignes) |
| Contraintes | 15 | doit, ne pas, jamais, uniquement, maximum, au moins, sans… |
| Format de sortie | 10 | Markdown, tableau, section, titre, format, liste… |
| Longueur suffisante | 10 | au moins 30 mots |
