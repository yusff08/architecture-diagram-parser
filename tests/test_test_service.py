import pytest
import os
import tempfile
import sqlite3
from schemas.tests import TestCaseCreate, TestCaseUpdate
from services.test_service import TestService

@pytest.fixture
def temp_service():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_service_db.sqlite")
    service = TestService(db_path=db_file)
    yield service
    if os.path.exists(db_file):
        os.remove(db_file)

def test_crud_lifecycle(temp_service):
    # 1. Create
    data = TestCaseCreate(
        analysis_name="Analyse DAB",
        use_case="Retirer Espèces",
        actor="Client",
        title="Retrait nominal de billets",
        test_type="nominal",
        injection_id=None,
        preconditions="Solde suffisant",
        steps=["Insérer carte", "Taper code", "Sélectionner montant"],
        expected_result="Billets distribués et compte débité",
        expected_behavior="traitement_normal",
        priority="haute",
        status="a_faire",
        generated_by_llm=False
    )
    created = temp_service.create_test_case(data)
    assert created.id > 0
    assert created.title == "Retrait nominal de billets"
    assert created.status == "a_faire"
    assert len(created.steps) == 3

    # 2. Get by ID
    fetched = temp_service.get_test_case_by_id(created.id)
    assert fetched is not None
    assert fetched.use_case == "Retirer Espèces"

    # 3. Update nominal
    update_data = TestCaseUpdate(
        title="Retrait nominal standard",
        priority="moyenne"
    )
    updated = temp_service.update_test_case(created.id, update_data)
    assert updated.title == "Retrait nominal standard"
    assert updated.priority == "moyenne"

    # 4. Update vide (aucun champ)
    same = temp_service.update_test_case(created.id, TestCaseUpdate())
    assert same.id == created.id

    # 5. Update inexistant
    assert temp_service.update_test_case(999999, update_data) is None

    # 6. Status update
    stat_up = temp_service.update_test_status(created.id, "passe")
    assert stat_up.status == "passe"

    # 7. Delete
    deleted = temp_service.delete_test_case(created.id)
    assert deleted is True
    assert temp_service.get_test_case_by_id(created.id) is None

    # 8. Delete inexistant
    assert temp_service.delete_test_case(999999) is False

def test_steps_and_details_invalid_json_fallback(temp_service):
    # Insère directement du texte non-JSON dans SQLite
    conn = sqlite3.connect(temp_service.db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO test_cases (
        analysis_name, use_case, title, test_type, steps,
        expected_result, expected_behavior, priority, status
    ) VALUES ('Sys', 'UC', 'Titre', 'nominal', 'TEXT_PAS_JSON', 'Res', 'traitement_normal', 'haute', 'a_faire')
    """)
    new_id = cursor.lastrowid
    cursor.execute("""
    INSERT INTO test_runs (
        test_case_id, duration_ms, status, actual_behavior, details
    ) VALUES (?, 10, 'passe', 'traitement_normal', 'DETAILS_PAS_JSON')
    """, (new_id,))
    conn.commit()
    conn.close()

    tc = temp_service.get_test_case_by_id(new_id)
    assert tc is not None
    assert tc.steps == ["TEXT_PAS_JSON"]
    assert tc.last_run["details"] == {}

    runs = temp_service.get_runs_for_test(new_id)
    assert len(runs) == 1
    assert runs[0].details == {}

def test_filters(temp_service):
    # Insère plusieurs tests pour filtrer
    t1 = temp_service.create_test_case(TestCaseCreate(
        analysis_name="Sys A",
        use_case="Authentifier",
        title="Auth nominale",
        test_type="nominal",
        expected_result="OK",
        expected_behavior="traitement_normal",
        priority="haute",
        status="passe"
    ))
    t2 = temp_service.create_test_case(TestCaseCreate(
        analysis_name="Sys A",
        use_case="Authentifier",
        title="Auth avec image floue",
        test_type="erreur",
        injection_id="A_BLUR_GAUSSIAN",
        expected_result="Erreur",
        expected_behavior="mode_secours",
        priority="basse",
        status="echoue"
    ))
    t3 = temp_service.create_test_case(TestCaseCreate(
        analysis_name="Sys B",
        use_case="Consulter Solde",
        title="Consultation solde",
        test_type="limite",
        injection_id="A_ROTATION_5",
        expected_result="OK",
        expected_behavior="traitement_normal",
        priority="moyenne",
        status="a_faire"
    ))

    # Filtre par use_case
    by_uc = temp_service.get_test_cases(use_case="Authentifier")
    assert len(by_uc) == 2

    # Filtre par test_type
    by_type = temp_service.get_test_cases(test_type="nominal")
    assert len(by_type) == 1
    assert by_type[0].id == t1.id

    # Filtre par status
    by_status = temp_service.get_test_cases(status="echoue")
    assert len(by_status) == 1
    assert by_status[0].id == t2.id

    # Filtre par priority
    by_prio = temp_service.get_test_cases(priority="moyenne")
    assert len(by_prio) == 1

    # Filtre par injection_id
    by_inj = temp_service.get_test_cases(injection_id="A_BLUR_GAUSSIAN")
    assert len(by_inj) == 1

def test_stats_and_robustness(temp_service):
    # Crée et exécute des tests pour valider les scores
    t1 = temp_service.create_test_case(TestCaseCreate(
        analysis_name="Sys Test",
        use_case="UC1",
        title="Test A1",
        test_type="erreur",
        injection_id="A_BLUR_GAUSSIAN",
        expected_result="R1",
        expected_behavior="mode_secours"
    ))
    t2 = temp_service.create_test_case(TestCaseCreate(
        analysis_name="Sys Test",
        use_case="UC2",
        title="Test B1",
        test_type="erreur",
        injection_id="B_EMPTY_TEXT",
        expected_result="R2",
        expected_behavior="mode_secours"
    ))

    # Enregistre un run réussi pour t1 et un échoué pour t2
    temp_service.record_test_run(t1.id, 120, "passe", "mode_secours", {"http": 200}, "A_BLUR_GAUSSIAN")
    temp_service.record_test_run(t2.id, 90, "echoue", "crash", {"http": 500}, "B_EMPTY_TEXT")

    stats = temp_service.get_stats()
    assert stats.total == 2
    assert stats.by_status["passe"] == 1
    assert stats.by_status["echoue"] == 1
    assert stats.success_rate == 50.0

    assert stats.category_scores["A"].total_tests == 1
    assert stats.category_scores["A"].passed_tests == 1
    assert stats.category_scores["A"].score_percentage == 100.0

    assert stats.category_scores["B"].total_tests == 1
    assert stats.category_scores["B"].passed_tests == 0
    assert stats.category_scores["B"].score_percentage == 0.0

    assert stats.global_robustness_score == 50.0

def test_exports_markdown_and_gherkin(temp_service):
    t = temp_service.create_test_case(TestCaseCreate(
        analysis_name="Export System",
        use_case="Valider Transaction",
        actor="Client",
        title="Validation transaction",
        test_type="erreur",
        injection_id="C_LLM_TIMEOUT",
        preconditions="Compte actif",
        steps=["Envoyer requête", "Attendre réponse"],
        expected_result="Message timeout",
        expected_behavior="mode_secours",
        priority="haute"
    ))
    temp_service.record_test_run(t.id, 300, "passe", "mode_secours", {}, "C_LLM_TIMEOUT")

    md = temp_service.export_markdown()
    assert "# 📋 Cahier de Recette & Tests de Robustesse" in md
    assert "Valider Transaction" in md
    assert "C_LLM_TIMEOUT" in md

    gherkin = temp_service.export_gherkin()
    assert "# language: fr" in gherkin
    assert "Fonctionnalité: Suite de tests de robustesse" in gherkin
    assert "Scénario: Validation transaction" in gherkin
    assert "@erreur" in gherkin
    assert "mode_secours" in gherkin
