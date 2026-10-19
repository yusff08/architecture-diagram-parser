import json
from typing import List, Optional, Dict, Any
from core.database import get_db, init_db
from schemas.tests import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseResponse,
    TestRunResponse,
    TestStatsResponse,
    CategoryRobustnessScore
)
from services.fault_injector import INJECTIONS_CATALOG

class TestService:
    __test__ = False

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        init_db(self.db_path)

    def _row_to_test_case(self, row: Any, last_run: Optional[Dict[str, Any]] = None) -> TestCaseResponse:
        steps_raw = row["steps"]
        try:
            steps = json.loads(steps_raw) if steps_raw else []
        except Exception:
            steps = [steps_raw] if steps_raw else []

        return TestCaseResponse(
            id=row["id"],
            analysis_name=row["analysis_name"],
            use_case=row["use_case"],
            actor=row["actor"],
            title=row["title"],
            test_type=row["test_type"],
            injection_id=row["injection_id"],
            preconditions=row["preconditions"],
            steps=steps,
            expected_result=row["expected_result"],
            expected_behavior=row["expected_behavior"],
            priority=row["priority"],
            status=row["status"],
            generated_by_llm=bool(row["generated_by_llm"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            last_run=last_run
        )

    def get_test_cases(
        self,
        use_case: Optional[str] = None,
        test_type: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        injection_id: Optional[str] = None
    ) -> List[TestCaseResponse]:
        query = "SELECT * FROM test_cases WHERE 1=1"
        params = []

        if use_case:
            query += " AND use_case LIKE ?"
            params.append(f"%{use_case}%")
        if test_type:
            query += " AND test_type = ?"
            params.append(test_type)
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if injection_id:
            query += " AND injection_id = ?"
            params.append(injection_id)

        query += " ORDER BY id DESC"

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()
            
            results = []
            for r in rows:
                # Récupère le dernier run pour chaque test
                last_run_row = cursor.execute(
                    "SELECT * FROM test_runs WHERE test_case_id = ? ORDER BY id DESC LIMIT 1",
                    (r["id"],)
                ).fetchone()
                
                last_run = None
                if last_run_row:
                    try:
                        details = json.loads(last_run_row["details"])
                    except Exception:
                        details = {}
                    last_run = {
                        "id": last_run_row["id"],
                        "started_at": str(last_run_row["started_at"]),
                        "duration_ms": last_run_row["duration_ms"],
                        "status": last_run_row["status"],
                        "actual_behavior": last_run_row["actual_behavior"],
                        "details": details,
                        "injection_id": last_run_row["injection_id"]
                    }
                results.append(self._row_to_test_case(r, last_run))
            return results

    def get_test_case_by_id(self, test_id: int) -> Optional[TestCaseResponse]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT * FROM test_cases WHERE id = ?", (test_id,)).fetchone()
            if not row:
                return None
            
            last_run_row = cursor.execute(
                "SELECT * FROM test_runs WHERE test_case_id = ? ORDER BY id DESC LIMIT 1",
                (test_id,)
            ).fetchone()
            
            last_run = None
            if last_run_row:
                try:
                    details = json.loads(last_run_row["details"])
                except Exception:
                    details = {}
                last_run = {
                    "id": last_run_row["id"],
                    "started_at": str(last_run_row["started_at"]),
                    "duration_ms": last_run_row["duration_ms"],
                    "status": last_run_row["status"],
                    "actual_behavior": last_run_row["actual_behavior"],
                    "details": details,
                    "injection_id": last_run_row["injection_id"]
                }
            return self._row_to_test_case(row, last_run)

    def create_test_case(self, data: TestCaseCreate) -> TestCaseResponse:
        steps_json = json.dumps(data.steps, ensure_ascii=False)
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO test_cases (
                analysis_name, use_case, actor, title, test_type,
                injection_id, preconditions, steps, expected_result,
                expected_behavior, priority, status, generated_by_llm
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.analysis_name,
                data.use_case,
                data.actor,
                data.title,
                data.test_type,
                data.injection_id,
                data.preconditions,
                steps_json,
                data.expected_result,
                data.expected_behavior,
                data.priority,
                data.status,
                1 if data.generated_by_llm else 0
            ))
            new_id = cursor.lastrowid
        return self.get_test_case_by_id(new_id)

    def update_test_case(self, test_id: int, data: TestCaseUpdate) -> Optional[TestCaseResponse]:
        existing = self.get_test_case_by_id(test_id)
        if not existing:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return existing

        fields = []
        params = []
        for k, v in update_dict.items():
            if k == "steps" and v is not None:
                fields.append("steps = ?")
                params.append(json.dumps(v, ensure_ascii=False))
            else:
                fields.append(f"{k} = ?")
                params.append(v)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(test_id)

        query = f"UPDATE test_cases SET {', '.join(fields)} WHERE id = ?"
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

        return self.get_test_case_by_id(test_id)

    def update_test_status(self, test_id: int, status: str) -> Optional[TestCaseResponse]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE test_cases SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, test_id)
            )
        return self.get_test_case_by_id(test_id)

    def delete_test_case(self, test_id: int) -> bool:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM test_cases WHERE id = ?", (test_id,))
            return cursor.rowcount > 0

    def record_test_run(
        self,
        test_case_id: int,
        duration_ms: int,
        status: str,
        actual_behavior: str,
        details: Dict[str, Any],
        injection_id: Optional[str] = None
    ) -> TestRunResponse:
        details_json = json.dumps(details, ensure_ascii=False)
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO test_runs (
                test_case_id, duration_ms, status, actual_behavior, details, injection_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                test_case_id,
                duration_ms,
                status,
                actual_behavior,
                details_json,
                injection_id
            ))
            run_id = cursor.lastrowid
            
            # Mise à jour du statut du test case
            new_test_status = "passe" if status == "passe" else "echoue"
            cursor.execute(
                "UPDATE test_cases SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_test_status, test_case_id)
            )

            row = cursor.execute("SELECT * FROM test_runs WHERE id = ?", (run_id,)).fetchone()
            return TestRunResponse(
                id=row["id"],
                test_case_id=row["test_case_id"],
                started_at=str(row["started_at"]),
                duration_ms=row["duration_ms"],
                status=row["status"],
                actual_behavior=row["actual_behavior"],
                details=details,
                injection_id=row["injection_id"]
            )

    def get_runs_for_test(self, test_id: int) -> List[TestRunResponse]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            rows = cursor.execute(
                "SELECT * FROM test_runs WHERE test_case_id = ? ORDER BY id DESC",
                (test_id,)
            ).fetchall()
            
            runs = []
            for r in rows:
                try:
                    details = json.loads(r["details"])
                except Exception:
                    details = {}
                runs.append(TestRunResponse(
                    id=r["id"],
                    test_case_id=r["test_case_id"],
                    started_at=str(r["started_at"]),
                    duration_ms=r["duration_ms"],
                    status=r["status"],
                    actual_behavior=r["actual_behavior"],
                    details=details,
                    injection_id=r["injection_id"]
                ))
            return runs

    def get_stats(self) -> TestStatsResponse:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT * FROM test_cases").fetchall()

            total = len(rows)
            by_status = {"a_faire": 0, "passe": 0, "echoue": 0}
            by_type = {"nominal": 0, "limite": 0, "erreur": 0}
            by_priority = {"haute": 0, "moyenne": 0, "basse": 0}

            for r in rows:
                s = r["status"]
                t = r["test_type"]
                p = r["priority"]
                if s in by_status:
                    by_status[s] += 1
                if t in by_type:
                    by_type[t] += 1
                if p in by_priority:
                    by_priority[p] += 1

            executed = by_status["passe"] + by_status["echoue"]
            success_rate = round((by_status["passe"] / executed * 100), 1) if executed > 0 else 0.0

            # Calcul des scores de robustesse par catégorie (A, B, C, D)
            cat_names = {
                "A": "Entrée OCR (Fichiers & Images)",
                "B": "Entrée LLM (Données Extraites)",
                "C": "Service LLM (Gemini)",
                "D": "API REST"
            }
            cat_stats: Dict[str, Dict[str, int]] = {
                cat: {"total": 0, "passed": 0} for cat in ("A", "B", "C", "D")
            }

            for r in rows:
                inj_id = r["injection_id"]
                if inj_id and inj_id in INJECTIONS_CATALOG:
                    category = INJECTIONS_CATALOG[inj_id].category
                    if category in cat_stats:
                        cat_stats[category]["total"] += 1
                        if r["status"] == "passe":
                            cat_stats[category]["passed"] += 1

            category_scores: Dict[str, CategoryRobustnessScore] = {}
            for cat, data in cat_stats.items():
                pct = round((data["passed"] / data["total"] * 100), 1) if data["total"] > 0 else 100.0
                category_scores[cat] = CategoryRobustnessScore(
                    category=cat,
                    category_name=cat_names[cat],
                    total_tests=data["total"],
                    passed_tests=data["passed"],
                    score_percentage=pct
                )

            # Score global de robustesse
            tot_inj = sum(c.total_tests for c in category_scores.values())
            pass_inj = sum(c.passed_tests for c in category_scores.values())
            global_robustness = round((pass_inj / tot_inj * 100), 1) if tot_inj > 0 else 100.0

            return TestStatsResponse(
                total=total,
                by_status=by_status,
                by_type=by_type,
                by_priority=by_priority,
                success_rate=success_rate,
                category_scores=category_scores,
                global_robustness_score=global_robustness
            )

    def export_markdown(self) -> str:
        tests = self.get_test_cases()
        stats = self.get_stats()
        
        md = "# 📋 Cahier de Recette & Tests de Robustesse - UML Architecture Analyzer\n\n"
        md += f"**Total des cas de test :** {stats.total} | "
        md += f"**Taux de réussite :** {stats.success_rate}% | "
        md += f"**Score de robustesse global :** {stats.global_robustness_score}%\n\n"
        
        md += "## 📊 Scores par Catégorie de Robustesse\n\n"
        md += "| Catégorie | Description | Tests Réussis / Total | Score de Robustesse |\n"
        md += "| :--- | :--- | :---: | :---: |\n"
        for cat, sc in stats.category_scores.items():
            md += f"| **{cat}** | {sc.category_name} | {sc.passed_tests} / {sc.total_tests} | {sc.score_percentage}% |\n"
        md += "\n---\n\n"

        md += "## 🧪 Liste des Cas de Test\n\n"
        for t in tests:
            status_emoji = "✅" if t.status == "passe" else ("❌" if t.status == "echoue" else "⏳")
            md += f"### {status_emoji} [{t.test_type.upper()}] {t.title} (`ID: #{t.id}`)\n\n"
            md += f"- **Système / Analyse :** {t.analysis_name}\n"
            md += f"- **Cas d'Utilisation :** `{t.use_case}`\n"
            if t.actor:
                md += f"- **Acteur Associé :** {t.actor}\n"
            md += f"- **Priorité :** {t.priority.capitalize()} | **Statut :** {t.status}\n"
            if t.injection_id:
                md += f"- **Anomalie Injectée :** `{t.injection_id}`\n"
            if t.preconditions:
                md += f"- **Préconditions :** {t.preconditions}\n"
            
            md += "\n**Étapes de test :**\n"
            if t.steps:
                for i, step in enumerate(t.steps, 1):
                    md += f"{i}. {step}\n"
            else:
                md += "1. Exécuter le pipeline nominal ou perturbé.\n"

            md += f"\n- **Résultat Métier Attendu :** {t.expected_result}\n"
            md += f"- **Comportement Système Attendu :** `{t.expected_behavior}`\n"
            
            if t.last_run:
                lr = t.last_run
                run_badge = "Passé" if lr["status"] == "passe" else "Échoué"
                md += f"\n> **Dernière Exécution :** {run_badge} ({lr['duration_ms']} ms) — *Comportement observé :* `{lr['actual_behavior']}`\n"
            md += "\n---\n\n"

        return md

    def export_gherkin(self) -> str:
        tests = self.get_test_cases()
        gherkin = "# language: fr\n"
        gherkin += "Fonctionnalité: Suite de tests de robustesse et d'injection d'anomalies\n"
        gherkin += "  En tant qu'ingénieur qualité\n"
        gherkin += "  Je souhaite éprouver la résilience de l'analyseur UML face aux erreurs et pannes\n"
        gherkin += "  Afin de garantir une haute disponibilité et un comportement prévisible.\n\n"

        for t in tests:
            tags = [f"@{t.test_type}", f"@priorite_{t.priority}"]
            if t.injection_id:
                tags.append(f"@injection_{t.injection_id.lower()}")
            gherkin += f"  {' '.join(tags)}\n"
            gherkin += f"  Scénario: {t.title}\n"
            
            if t.preconditions:
                gherkin += f"    Étant donné que {t.preconditions}\n"
            else:
                gherkin += f"    Étant donné que l'analyseur d'architecture UML est opérationnel\n"

            if t.injection_id:
                gherkin += f"    Quand l'anomalie '{t.injection_id}' est injectée dans le flux du cas '{t.use_case}'\n"
            else:
                gherkin += f"    Quand le cas d'utilisation '{t.use_case}' est traité normalement\n"

            for step in t.steps:
                gherkin += f"    Et que l'utilisateur exécute l'étape \"{step}\"\n"

            gherkin += f"    Alors le résultat attendu est \"{t.expected_result}\"\n"
            gherkin += f"    Et le comportement système attendu est \"{t.expected_behavior}\"\n\n"

        return gherkin

test_service = TestService()
