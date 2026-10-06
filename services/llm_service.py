import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from the .env file.")

genai.configure(api_key=api_key.strip())

SYSTEM_PROMPT = """Tu es un Architecte Logiciel Francophone de niveau Sénior.
Ton rôle est d'analyser les textes extraits d'un diagramme de cas d'utilisation UML (UML Use Case Diagram) et de déduire l'objectif global du système.
Les textes incluent les acteurs, les cas d'utilisation, et les relations telles que <<include>> et <<extend>>.

À partir de cette liste de textes :
1. Déduis le titre/le nom global du système (ex: Système de gestion de commandes).
2. Identifie les acteurs principaux.
3. Rédige une documentation technique en Markdown qui cartographie les acteurs et leurs cas d'utilisation, tout en expliquant les dépendances (include/extend).

Ta réponse DOIT être UNIQUEMENT un objet JSON valide suivant exactement cette structure, sans aucun texte ou bloc markdown supplémentaire :
{
  "system_title": "Nom du système déduit",
  "detected_actors": ["acteur1", "acteur2"],
  "documentation_markdown": "# Documentation Technique\\n..."
}"""

def generate_documentation(ocr_texts: list[str]) -> dict:
    if not ocr_texts:
        return {
            "system_title": "Inconnu",
            "detected_actors": [],
            "documentation_markdown": "Aucun texte détecté dans le diagramme."
        }

    # MOCK: Gemini API Quota Exhausted. Returning dummy data directly.
    return {
        "system_title": "Système de Gestion de Commandes (Mock)",
        "detected_actors": ["Client", "Administrateur", "Livreur"],
        "documentation_markdown": "# Documentation Technique (Mode Hors-Ligne)\n\n"
                                  "Ceci est une documentation générée localement car le quota de l'API Gemini a été atteint.\n\n"
                                  "## Acteurs Identifiés\n"
                                  "- **Client** : Peut passer des commandes.\n"
                                  "- **Administrateur** : Gère l'inventaire et les utilisateurs.\n"
                                  "- **Livreur** : Confirme les expéditions.\n\n"
                                  "## Cas d'Utilisation (Use Cases)\n"
                                  "- Le Client interagit avec le système pour acheter un produit.\n"
                                  "- *<< include >>* : L'authentification est requise pour passer une commande.\n"
    }
