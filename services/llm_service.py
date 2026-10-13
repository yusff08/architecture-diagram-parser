import os
import json
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from the .env file.")

client = genai.Client(api_key=api_key.strip())

# The editable instructions now come from the "Gestion des Prompts" module (see core/database.py).
# This output contract is always appended and cannot be edited, so the response stays parseable.
JSON_FORMAT_INSTRUCTIONS = """Ta réponse DOIT être UNIQUEMENT un objet JSON valide suivant exactement cette structure, sans aucun texte ou bloc markdown supplémentaire :
{
  "system_title": "Nom du système déduit",
  "detected_actors": ["acteur1", "acteur2"],
  "documentation_markdown": "# Documentation Technique\\n..."
}"""

def generate_documentation(ocr_texts: list[str], prompt_instructions: str) -> dict:
    if not ocr_texts:
        return {
            "system_title": "Inconnu",
            "detected_actors": [],
            "documentation_markdown": "Aucun texte détecté dans le diagramme."
        }

    try:
        prompt = f"{prompt_instructions}\n\n{JSON_FORMAT_INSTRUCTIONS}\n\nVoici les textes extraits par OCR :\n"
        for text in ocr_texts:
            prompt += f"- {text}\n"

        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
        
    except Exception as e:
        logging.error(f"Error during Gemini generation: {e}")
        return {
            "system_title": "Erreur Génération",
            "detected_actors": [],
            "documentation_markdown": f"Une erreur s'est produite lors de la génération avec l'API Gemini : {str(e)}"
        }
