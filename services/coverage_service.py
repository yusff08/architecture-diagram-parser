"""Calcul du score de couverture (Gestion 4) — fonctions pures, sans base ni IA.

Règle : taux = (couvertes + 0,5 × partielles) / fonctionnelles analysables × 100
où « fonctionnelles analysables » = exigences fonctionnelles couvertes, partielles ou non couvertes.
Les exigences « à vérifier », non analysées et non fonctionnelles sont comptées à part.
"""
import unicodedata
import re

FORMULA = "(couvertes + 0,5 × partiellement couvertes) / exigences fonctionnelles analysables × 100"
STATUS_WEIGHTS = {"couverte": 1.0, "partielle": 0.5, "non_couverte": 0.0}


def compute_stats(rows: list[dict]) -> dict:
    """rows : dicts avec au moins les clés "type" et "status"."""
    count = lambda pred: sum(1 for r in rows if pred(r))
    functional = [r for r in rows if r["type"] == "fonctionnelle"]
    analyzable = [r for r in functional if r["status"] in STATUS_WEIGHTS]
    earned = sum(STATUS_WEIGHTS[r["status"]] for r in analyzable)
    rate = round(earned / len(analyzable) * 100, 1) if analyzable else None

    return {
        "total": len(rows),
        "functional": len(functional),
        "non_functional": len(rows) - len(functional),
        "covered": count(lambda r: r["status"] == "couverte"),
        "partial": count(lambda r: r["status"] == "partielle"),
        "uncovered": count(lambda r: r["status"] == "non_couverte"),
        "to_verify": count(lambda r: r["status"] == "a_verifier"),
        "not_analyzed": count(lambda r: r["status"] == "non_analysee"),
        "analyzable_functional": len(analyzable),
        "coverage_rate": rate,
        "formula": FORMULA,
    }


def normalize(text: str) -> str:
    """Minuscules, sans accents ni ponctuation : sert à vérifier qu'un nom existe dans le document."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def appears_in(name: str, document_text: str) -> bool:
    """Vrai si le nom figure explicitement dans le texte (comparaison normalisée)."""
    needle = normalize(name)
    return bool(needle) and f" {needle} " in f" {normalize(document_text)} "
