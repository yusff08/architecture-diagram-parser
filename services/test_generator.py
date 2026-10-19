import json
import logging
import re
from typing import List, Dict, Any, Tuple
from google.genai import types
from schemas.tests import TestCaseCreate, GenerateTestsResponse, TestCaseResponse
from services.test_service import test_service
from services.fault_injector import INJECTIONS_CATALOG

SYSTEM_GENERATOR_PROMPT = """Tu es un Expert en Assurance Qualité et Ingénierie des Tests Logiciels pour systèmes UML.
Ton rôle est de concevoir une suite complète de cas de test basée sur la documentation ou les textes d'un diagramme de cas d'utilisation UML.

Pour chaque cas d'utilisation identifié dans le texte, tu dois générer 3 cas de test :
1. Un test de type "nominal" : scénario idéal (traitement_normal).
2. Un test de type "limite" : conditions aux bornes, données volumineuses ou dégradations légères.
3. Un test de type "erreur" : cas d'anomalie sévère, avec injection d'une panne ou anomalie issue du catalogue.

Pour les tests de type "limite" et "erreur", tu DOIS choisir un identifiant d'anomalie parmi la liste suivante :
- Catégorie A (OCR / Fichiers) : A_BLUR_GAUSSIAN, A_NOISE_GAUSSIAN, A_NOISE_SALT_PEPPER, A_LOW_CONTRAST, A_VERY_DARK, A_ROTATION_5, A_ROTATION_90, A_ROTATION_180, A_CROPPED, A_RES_TINY, A_RES_HUGE, A_BLANK_IMAGE, A_FILE_EMPTY, A_FILE_CORRUPTED, A_FILE_FAKE_PNG, A_FILE_UNSUPPORTED_EXT, A_FILE_TOO_LARGE
- Catégorie B (Données extraites) : B_EMPTY_TEXT, B_NOISE_CHARS, B_DUPLICATE_ACTORS, B_USECASE_WITHOUT_ACTOR, B_ACTOR_WITHOUT_USECASE, B_CIRCULAR_RELATIONS, B_EXTREME_LENGTH, B_UNICODE_SPECIAL, B_PROMPT_INJECTION
- Catégorie C (Service LLM) : C_LLM_TIMEOUT, C_LLM_ERROR_429, C_LLM_ERROR_500, C_LLM_INVALID_KEY, C_LLM_EMPTY_RESPONSE, C_LLM_NON_JSON, C_LLM_TRUNCATED_JSON, C_LLM_HIGH_LATENCY, C_LLM_WRONG_LANGUAGE
- Catégorie D (API) : D_API_INVALID_PAYLOAD, D_API_CONCURRENT_REQUESTS, D_API_NONEXISTENT_ID

Les valeurs possibles pour expected_behavior sont STRICTEMENT :
- "traitement_normal"
- "mode_secours"
- "erreur_4xx_message_clair"
- "rejet_propre"

Les valeurs possibles pour priority sont STRICTEMENT : "haute", "moyenne", "basse".
Les valeurs possibles pour test_type sont STRICTEMENT : "nominal", "limite", "erreur".

Ta réponse DOIT être UNIQUEMENT un tableau JSON strict sans aucun bloc markdown, sans texte explicatif :
[
  {
    "analysis_name": "Nom de l'analyse",
    "use_case": "Nom du cas d'utilisation",
    "actor": "Nom de l'acteur ou null",
    "title": "Titre explicite du test",
    "test_type": "nominal|limite|erreur",
    "injection_id": "IDENTIFIANT_INJECTION ou null",
    "preconditions": "Préconditions nécessaires",
    "steps": ["Étape 1", "Étape 2", "Étape 3"],
    "expected_result": "Description métier du résultat",
    "expected_behavior": "traitement_normal|mode_secours|erreur_4xx_message_clair|rejet_propre",
    "priority": "haute|moyenne|basse"
  }
]
"""

class TestGenerator:
    __test__ = False

    def __init__(self):
        pass

    def _clean_json_text(self, raw_text: str) -> str:
        """Nettoie les balises markdown ```json et ``` éventuelles."""
        text = raw_text.strip()
        text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def _fallback_generate(self, doc_text: str, analysis_name: str) -> List[TestCaseCreate]:
        """
        Générateur local par gabarits si Gemini est indisponible (offline, quota ou erreur).
        Déduit des cas d'utilisation et acteurs élémentaires du texte.
        """
        logging.warning("Basculement sur le générateur de tests local par gabarits (Fallback).")
        
        # Heuristique d'extraction des cas d'utilisation et acteurs
        lines = [line.strip("- *#:\t\r\n") for line in doc_text.splitlines() if line.strip()]
        use_cases = []
        actors = []

        for line in lines:
            lower = line.lower()
            if any(k in lower for k in ["authentifier", "login", "connexion", "authentification"]):
                use_cases.append("S'authentifier")
            elif any(k in lower for k in ["consulter", "afficher", "visualiser", "rechercher"]):
                use_cases.append(line[:40])
            elif any(k in lower for k in ["creer", "ajouter", "modifier", "supprimer", "gestion"]):
                use_cases.append(line[:40])
            elif any(k in lower for k in ["client", "utilisateur", "admin", "administrateur", "gestionnaire"]):
                actors.append(line[:30])

        if not use_cases:
            use_cases = ["Authentification Système", "Traitement des Opérations", "Consultation des Données"]
        if not actors:
            actors = ["Utilisateur Principal"]

        primary_actor = actors[0]
        generated: List[TestCaseCreate] = []

        # Génération des gabarits structurés pour chaque cas
        for uc in use_cases[:3]:
            # 1. Test Nominal
            generated.append(TestCaseCreate(
                analysis_name=analysis_name,
                use_case=uc,
                actor=primary_actor,
                title=f"Exécution nominale du cas {uc}",
                test_type="nominal",
                injection_id=None,
                preconditions=f"L'acteur '{primary_actor}' dispose des droits requis pour '{uc}'.",
                steps=[
                    f"Soumettre le diagramme UML contenant le cas '{uc}'.",
                    "Vérifier la bonne reconnaissance par l'OCR.",
                    "Vérifier la déduction correcte des relations par le LLM."
                ],
                expected_result=f"Documentation technique générée avec cartographie de l'acteur '{primary_actor}' et de '{uc}'.",
                expected_behavior="traitement_normal",
                priority="haute",
                status="a_faire",
                generated_by_llm=True
            ))

            # 2. Test Limite
            generated.append(TestCaseCreate(
                analysis_name=analysis_name,
                use_case=uc,
                actor=primary_actor,
                title=f"Résistance à une rotation légère sur {uc}",
                test_type="limite",
                injection_id="A_ROTATION_5",
                preconditions="Diagramme légèrement incliné de 5 degrés lors de la numérisation.",
                steps=[
                    "Appliquer une rotation géométrique de 5 degrés sur l'image source.",
                    "Lancer l'extraction de texte via PaddleOCR.",
                    "Transmettre les fragments au service LLM."
                ],
                expected_result="Le moteur OCR compense l'angle et le LLM documente fidèlement le cas.",
                expected_behavior="traitement_normal",
                priority="moyenne",
                status="a_faire",
                generated_by_llm=True
            ))

            # 3. Test Erreur
            generated.append(TestCaseCreate(
                analysis_name=analysis_name,
                use_case=uc,
                actor=primary_actor,
                title=f"Gestion de coupure de service LLM (Timeout) sur {uc}",
                test_type="erreur",
                injection_id="C_LLM_TIMEOUT",
                preconditions="Le service externe Gemini ne répond pas dans le délai imparti.",
                steps=[
                    f"Initier l'analyse d'architecture pour le cas '{uc}'.",
                    "Simuler un blocage réseau ou un timeout lors de l'appel LLM.",
                    "Observer la réaction de l'application."
                ],
                expected_result="L'application bascule sur un mode dégradé clair sans planter.",
                expected_behavior="mode_secours",
                priority="haute",
                status="a_faire",
                generated_by_llm=True
            ))

        return generated

    def generate_tests(
        self,
        documentation_text: str,
        analysis_name: str = "Système UML",
        save_to_db: bool = True
    ) -> GenerateTestsResponse:
        """
        Génère une liste de cas de test via Gemini.
        En cas d'échec ou d'indisponibilité, utilise le fallback local par gabarits.
        """
        fallback_used = False
        parsed_items: List[TestCaseCreate] = []

        try:
            import services.llm_service as llm_svc
            active_client = getattr(llm_svc, "client", None) or llm_svc.get_gemini_client()
            prompt = f"{SYSTEM_GENERATOR_PROMPT}\n\nDocumentation ou textes UML à analyser :\n{documentation_text}\n"

            response = active_client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            cleaned_json = self._clean_json_text(response.text)
            data = json.loads(cleaned_json)

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        try:
                            # Assure les valeurs par défaut
                            item["analysis_name"] = item.get("analysis_name") or analysis_name
                            item["generated_by_llm"] = True
                            item["status"] = "a_faire"
                            
                            # Validation Pydantic
                            validated = TestCaseCreate(**item)
                            parsed_items.append(validated)
                        except Exception as val_err:
                            logging.warning(f"Item de test invalide ignoré : {val_err}")

            if not parsed_items:
                raise ValueError("Aucun cas de test valide n'a pu être extrait de la réponse LLM.")

        except Exception as e:
            logging.error(f"Erreur lors de la génération IA avec Gemini : {e}. Utilisation du fallback.")
            fallback_used = True
            parsed_items = self._fallback_generate(documentation_text, analysis_name)

        # Sauvegarde en base si demandée
        saved_responses: List[TestCaseResponse] = []
        if save_to_db:
            for item in parsed_items:
                saved = test_service.create_test_case(item)
                saved_responses.append(saved)
        else:
            # Conversion simulée avec IDs temporaires
            for idx, item in enumerate(parsed_items, 1):
                saved_responses.append(TestCaseResponse(
                    id=idx,
                    analysis_name=item.analysis_name,
                    use_case=item.use_case,
                    actor=item.actor,
                    title=item.title,
                    test_type=item.test_type,
                    injection_id=item.injection_id,
                    preconditions=item.preconditions,
                    steps=item.steps,
                    expected_result=item.expected_result,
                    expected_behavior=item.expected_behavior,
                    priority=item.priority,
                    status=item.status,
                    generated_by_llm=True,
                    created_at="En mémoire",
                    updated_at="En mémoire",
                    last_run=None
                ))

        msg = "Génération effectuée via le mode secours local (gabarits)." if fallback_used else "Génération réussie via le modèle IA Gemini."
        return GenerateTestsResponse(
            test_cases=saved_responses,
            fallback_used=fallback_used,
            total_generated=len(saved_responses),
            message=msg
        )

test_generator = TestGenerator()
