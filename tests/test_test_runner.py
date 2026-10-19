import pytest
import os
from unittest.mock import patch, MagicMock
from schemas.tests import TestCaseCreate
from services.test_service import test_service
from services.test_runner import test_runner
from services.fault_injector import FaultInjectionDisabledError

@pytest.fixture(autouse=True)
def enable_fault_injection(monkeypatch):
    monkeypatch.setenv("ENABLE_FAULT_INJECTION", "true")

def test_run_disabled_raises_error(monkeypatch):
    monkeypatch.setenv("ENABLE_FAULT_INJECTION", "false")
    with pytest.raises(FaultInjectionDisabledError):
        test_runner.run_test(1)

def test_run_nonexistent_test():
    with pytest.raises(ValueError):
        test_runner.run_test(999999)

def test_run_nominal_test_success_and_fallback():
    # 1. Nominal succès
    tc = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys Bancaire",
        use_case="Authentifier",
        title="Test Nominal Auth",
        test_type="nominal",
        expected_result="Succès",
        expected_behavior="traitement_normal",
        priority="haute"
    ))
    
    with patch("services.llm_service.generate_documentation", return_value={"system_title": "Sys Bancaire"}):
        result = test_runner.run_test(tc.id)
        assert result.passed is True
        assert result.new_status == "passe"
        assert result.test_run.duration_ms > 0
        assert result.test_run.actual_behavior == "traitement_normal"

    # 2. Nominal avec réponse mode secours
    tc_fallback = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="UC Fallback",
        title="Nominal secours",
        test_type="nominal",
        expected_result="Mode secours",
        expected_behavior="mode_secours"
    ))
    with patch("services.llm_service.generate_documentation", return_value={"system_title": "Erreur Génération"}):
        res_fb = test_runner.run_test(tc_fallback.id)
        assert res_fb.passed is True
        assert res_fb.test_run.actual_behavior == "mode_secours"

def test_run_category_a_image_and_files():
    # 1. Image Floue sans texte
    tc_blur = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="OCR Flow",
        title="Flou Gaussien",
        test_type="erreur",
        injection_id="A_BLUR_GAUSSIAN",
        expected_result="Mode secours",
        expected_behavior="mode_secours"
    ))
    with patch("services.ocr.extract_text_from_image", return_value=[]):
        res_blur = test_runner.run_test(tc_blur.id)
        assert res_blur.passed is True
        assert res_blur.new_status == "passe"

    # 2. Image dégradée mais texte extrait
    tc_deg = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="OCR Flow 2",
        title="Bruit Gaussien Détecté",
        test_type="limite",
        injection_id="A_NOISE_GAUSSIAN",
        expected_result="Traitement normal",
        expected_behavior="traitement_normal"
    ))
    with patch("services.ocr.extract_text_from_image", return_value=[{"text": "Login", "confidence": 0.9}]):
        with patch("services.llm_service.generate_documentation", return_value={"system_title": "Doc"}):
            res_deg = test_runner.run_test(tc_deg.id)
            assert res_deg.passed is True
            assert res_deg.test_run.actual_behavior == "traitement_normal"

    # 3. Exception OCR
    tc_ocr_err = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="OCR Crash",
        title="Crash OCR Décodage",
        test_type="erreur",
        injection_id="A_CROPPED",
        expected_result="Mode secours",
        expected_behavior="mode_secours"
    ))
    with patch("services.ocr.extract_text_from_image", side_effect=ValueError("Corrupted image format")):
        res_ocr_err = test_runner.run_test(tc_ocr_err.id)
        assert res_ocr_err.passed is True
        assert res_ocr_err.test_run.actual_behavior == "mode_secours"

    # 4. Fichiers corrompus et limites
    for inj, exp, beh in [
        ("A_FILE_EMPTY", 400, "erreur_4xx_message_clair"),
        ("A_FILE_UNSUPPORTED_EXT", 415, "erreur_4xx_message_clair"),
        ("A_FILE_TOO_LARGE", 413, "erreur_4xx_message_clair"),
        ("A_FILE_CORRUPTED", 422, "erreur_4xx_message_clair"),
        ("A_FILE_FAKE_PNG", 422, "erreur_4xx_message_clair"),
    ]:
        tc_f = test_service.create_test_case(TestCaseCreate(
            analysis_name="Sys",
            use_case="Upload",
            title=f"Test {inj}",
            test_type="erreur",
            injection_id=inj,
            expected_result="Erreur HTTP",
            expected_behavior=beh
        ))
        res_f = test_runner.run_test(tc_f.id)
        assert res_f.passed is True
        assert res_f.test_run.details["http_code"] == exp

def test_run_category_b_data():
    # 1. B_EXTREME_LENGTH
    tc_b = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="Cas B",
        title="Texte extrêmement long",
        test_type="limite",
        injection_id="B_EXTREME_LENGTH",
        expected_result="Rejet",
        expected_behavior="rejet_propre"
    ))
    res_b = test_runner.run_test(tc_b.id)
    assert res_b.passed is True
    assert res_b.test_run.actual_behavior == "rejet_propre"

    # 2. B_EMPTY_TEXT
    tc_empty = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="Cas B Empty",
        title="Texte Vide",
        test_type="erreur",
        injection_id="B_EMPTY_TEXT",
        expected_result="Mode secours",
        expected_behavior="mode_secours"
    ))
    res_empty = test_runner.run_test(tc_empty.id)
    assert res_empty.passed is True
    assert res_empty.test_run.actual_behavior == "mode_secours"

    # 3. B_DUPLICATE_ACTORS nominal
    tc_dup = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="Cas B Dup",
        title="Acteurs dupliqués",
        test_type="limite",
        injection_id="B_DUPLICATE_ACTORS",
        expected_result="Traitement nominal",
        expected_behavior="traitement_normal"
    ))
    with patch("services.llm_service.generate_documentation", return_value={"system_title": "OK"}):
        res_dup = test_runner.run_test(tc_dup.id)
        assert res_dup.passed is True
        assert res_dup.test_run.actual_behavior == "traitement_normal"

def test_run_category_c_all_llm_faults():
    faults = [
        ("C_LLM_TIMEOUT", "mode_secours"),
        ("C_LLM_ERROR_429", "mode_secours"),
        ("C_LLM_ERROR_500", "mode_secours"),
        ("C_LLM_INVALID_KEY", "mode_secours"),
        ("C_LLM_EMPTY_RESPONSE", "mode_secours"),
        ("C_LLM_NON_JSON", "mode_secours"),
        ("C_LLM_TRUNCATED_JSON", "mode_secours"),
        ("C_LLM_HIGH_LATENCY", "traitement_normal"),
        ("C_LLM_WRONG_LANGUAGE", "traitement_normal"),
    ]
    for inj, beh in faults:
        tc = test_service.create_test_case(TestCaseCreate(
            analysis_name="Sys",
            use_case="Fault LLM",
            title=f"Test {inj}",
            test_type="erreur" if beh == "mode_secours" else "limite",
            injection_id=inj,
            expected_result="Attendu",
            expected_behavior=beh
        ))
        res = test_runner.run_test(tc.id)
        assert res.passed is True
        assert res.test_run.actual_behavior == beh

def test_run_category_d_api_anomalies():
    for inj, beh in [
        ("D_API_INVALID_PAYLOAD", "erreur_4xx_message_clair"),
        ("D_API_NONEXISTENT_ID", "erreur_4xx_message_clair"),
        ("D_API_CONCURRENT_REQUESTS", "traitement_normal"),
    ]:
        tc = test_service.create_test_case(TestCaseCreate(
            analysis_name="Sys",
            use_case="API check",
            title=f"Test {inj}",
            test_type="erreur" if "erreur" in beh else "nominal",
            injection_id=inj,
            expected_result="Result",
            expected_behavior=beh
        ))
        res = test_runner.run_test(tc.id)
        assert res.passed is True
        assert res.test_run.actual_behavior == beh

def test_run_test_failure_and_crash_handling():
    # 1. Échec attendu (comportement observé ne correspond pas au comportement attendu)
    tc_fail = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="Fail Case",
        title="Ce test doit échouer",
        test_type="nominal",
        expected_result="Normal",
        expected_behavior="traitement_normal"
    ))
    with patch("services.llm_service.generate_documentation", return_value={"system_title": "Erreur Génération"}):
        res_fail = test_runner.run_test(tc_fail.id)
        assert res_fail.passed is False
        assert res_fail.new_status == "echoue"
        assert res_fail.test_run.status == "echoue"

    # 2. Crash / Exception inattendue
    tc_crash = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="Crash Case",
        title="Crash inattendu",
        test_type="nominal",
        expected_result="Normal",
        expected_behavior="traitement_normal"
    ))
    with patch.object(test_runner, "_dispatch_execution", side_effect=ZeroDivisionError("Division par zéro inattendue")):
        res_crash = test_runner.run_test(tc_crash.id)
        assert res_crash.passed is False
        assert res_crash.test_run.status == "erreur"
        assert res_crash.test_run.actual_behavior == "crash_serveur_ou_exception"
        assert res_crash.test_run.details["error_type"] == "ZeroDivisionError"

def test_run_all_with_selection_and_all():
    t1 = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="U1",
        title="RunAll Pass",
        test_type="erreur",
        injection_id="D_API_NONEXISTENT_ID",
        expected_result="404",
        expected_behavior="erreur_4xx_message_clair"
    ))
    t2 = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="U2",
        title="RunAll Fail",
        test_type="nominal",
        expected_result="415",
        expected_behavior="traitement_normal" # will fail because we mock return error
    ))

    with patch("services.llm_service.generate_documentation", return_value={"system_title": "Erreur Génération"}):
        summary = test_runner.run_all(test_ids=[t1.id, t2.id])
        assert summary.total_executed == 2
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.duration_total_ms > 0

    # Exécution de tous sans spécifier de liste
    summary_all = test_runner.run_all()
    assert summary_all.total_executed >= 2

def test_run_all_with_error_status():
    t_err = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="UErr",
        title="RunAll Crash",
        test_type="nominal",
        expected_result="Crash",
        expected_behavior="traitement_normal"
    ))
    with patch.object(test_runner, "run_test") as mock_run:
        from schemas.tests import RunResultResponse, TestRunResponse
        mock_run.return_value = RunResultResponse(
            test_case_id=t_err.id,
            test_run=TestRunResponse(
                id=1,
                test_case_id=t_err.id,
                started_at="2026-10-13",
                duration_ms=5,
                status="erreur",
                actual_behavior="crash_serveur_ou_exception",
                details={}
            ),
            new_status="echoue",
            passed=False
        )
        res = test_runner.run_all(test_ids=[t_err.id])
        assert res.errors == 1
        assert res.passed == 0

def test_dispatch_unknown_category():
    tc = test_service.create_test_case(TestCaseCreate(
        analysis_name="Sys",
        use_case="UUnknown",
        title="Unknown Category",
        test_type="nominal",
        expected_result="Nominal",
        expected_behavior="traitement_normal"
    ))
    beh, details = test_runner._dispatch_execution(tc, "Z_UNKNOWN_CAT")
    assert beh in ("traitement_normal", "mode_secours")
