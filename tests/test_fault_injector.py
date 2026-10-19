import pytest
import os
import cv2
import numpy as np
from services.fault_injector import (
    FaultInjector,
    fault_injector,
    FaultInjectionDisabledError,
    UnknownInjectionError,
    INJECTIONS_CATALOG
)

def test_catalog_completeness():
    catalog = fault_injector.get_catalog()
    assert len(catalog) >= 30
    
    categories = {item.category for item in catalog}
    assert categories == {"A", "B", "C", "D"}

    for item in catalog:
        assert item.id
        assert item.name
        assert item.description
        assert item.expected_behavior in ("erreur_4xx_message_clair", "mode_secours", "traitement_normal", "rejet_propre")

def test_get_injection_valid_and_unknown():
    item = fault_injector.get_injection("A_BLUR_GAUSSIAN")
    assert item.id == "A_BLUR_GAUSSIAN"
    assert item.category == "A"

    with pytest.raises(UnknownInjectionError):
        fault_injector.get_injection("NON_EXISTENT_INJECTION_XYZ")

def test_reference_image_fallback_when_file_missing():
    fi = FaultInjector(reference_image_path="path/does/not/exist/diagram.png")
    img = fi.get_reference_image()
    assert img is not None
    assert img.shape == (400, 600, 3)

def test_category_a_image_degradations():
    ref_img = fault_injector.get_reference_image()
    assert ref_img is not None
    assert ref_img.shape[0] > 0

    # 1. Blur
    blurred_bytes = fault_injector.generate_image_anomaly("A_BLUR_GAUSSIAN")
    assert len(blurred_bytes) > 0
    blurred_arr = cv2.imdecode(np.frombuffer(blurred_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert not np.array_equal(ref_img, blurred_arr)

    # 2. Gaussian Noise
    noise_bytes = fault_injector.generate_image_anomaly("A_NOISE_GAUSSIAN")
    noise_arr = cv2.imdecode(np.frombuffer(noise_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert not np.array_equal(ref_img, noise_arr)

    # 3. Salt & Pepper Noise
    sp_bytes = fault_injector.generate_image_anomaly("A_NOISE_SALT_PEPPER")
    assert len(sp_bytes) > 0

    # 4. Low Contrast
    lc_bytes = fault_injector.generate_image_anomaly("A_LOW_CONTRAST")
    lc_arr = cv2.imdecode(np.frombuffer(lc_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert not np.array_equal(ref_img, lc_arr)

    # 5. Very Dark
    dark_bytes = fault_injector.generate_image_anomaly("A_VERY_DARK")
    dark_arr = cv2.imdecode(np.frombuffer(dark_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert dark_arr.mean() < ref_img.mean()

    # 6. Rotations
    rot5_bytes = fault_injector.generate_image_anomaly("A_ROTATION_5")
    rot90_bytes = fault_injector.generate_image_anomaly("A_ROTATION_90")
    rot180_bytes = fault_injector.generate_image_anomaly("A_ROTATION_180")
    assert len(rot5_bytes) > 0
    assert len(rot90_bytes) > 0
    assert len(rot180_bytes) > 0

    # 7. Cropped
    crop_bytes = fault_injector.generate_image_anomaly("A_CROPPED")
    crop_arr = cv2.imdecode(np.frombuffer(crop_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert crop_arr.shape[0] < ref_img.shape[0]

    # 8. Resolutions Tiny & Huge
    tiny_bytes = fault_injector.generate_image_anomaly("A_RES_TINY")
    tiny_arr = cv2.imdecode(np.frombuffer(tiny_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert tiny_arr.shape[:2] == (16, 16)

    huge_bytes = fault_injector.generate_image_anomaly("A_RES_HUGE", {"width": 500, "height": 500})
    huge_arr = cv2.imdecode(np.frombuffer(huge_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert huge_arr.shape[:2] == (500, 500)

    # 9. Blank & Non-diagram
    blank_bytes = fault_injector.generate_image_anomaly("A_BLANK_IMAGE")
    blank_arr = cv2.imdecode(np.frombuffer(blank_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert (blank_arr == 255).all()

    photo_bytes = fault_injector.generate_image_anomaly("A_NON_DIAGRAM")
    assert len(photo_bytes) > 0

def test_category_a_file_anomalies():
    # Empty file
    assert fault_injector.generate_image_anomaly("A_FILE_EMPTY") == b""

    # Corrupted bytes
    corrupted = fault_injector.generate_image_anomaly("A_FILE_CORRUPTED", {"byte_count": 100})
    assert len(corrupted) == 100

    # Fake PNG
    fake_png = fault_injector.generate_image_anomaly("A_FILE_FAKE_PNG")
    assert b"Ceci est un fichier texte" in fake_png

    # Unsupported ext
    unsupp = fault_injector.generate_image_anomaly("A_FILE_UNSUPPORTED_EXT")
    assert b"%PDF" in unsupp

    # File too large
    too_large = fault_injector.generate_image_anomaly("A_FILE_TOO_LARGE", {"size_bytes": 1024})
    assert len(too_large) == 1024

def test_category_b_data_anomalies():
    sample_texts = ["Systeme Bancaire", "Client", "Authentifier", "<<include>>"]

    # Empty
    assert fault_injector.apply_data_anomaly("B_EMPTY_TEXT", sample_texts) == []

    # Noise characters
    noisy = fault_injector.apply_data_anomaly("B_NOISE_CHARS", sample_texts)
    assert any("@#$%" in t for t in noisy)

    # Duplicate actors
    dups = fault_injector.apply_data_anomaly("B_DUPLICATE_ACTORS", sample_texts)
    assert len(dups) > len(sample_texts)

    # Usecase without actor & Actor without usecase
    uc_no_act = fault_injector.apply_data_anomaly("B_USECASE_WITHOUT_ACTOR", sample_texts)
    assert any("Authentifier" in t for t in uc_no_act)

    act_no_uc = fault_injector.apply_data_anomaly("B_ACTOR_WITHOUT_USECASE", sample_texts)
    assert any("Acteur Client" in t for t in act_no_uc)

    # Circular relations
    circ = fault_injector.apply_data_anomaly("B_CIRCULAR_RELATIONS", sample_texts)
    assert any("Cas A <<include>> Cas B" in t for t in circ)

    # Extreme length
    ext = fault_injector.apply_data_anomaly("B_EXTREME_LENGTH", sample_texts)
    assert len(ext[0]) > 10000

    # Special unicode
    uni = fault_injector.apply_data_anomaly("B_UNICODE_SPECIAL", sample_texts)
    assert any("🚀" in t for t in uni)

    # Prompt injection
    pi = fault_injector.apply_data_anomaly("B_PROMPT_INJECTION", sample_texts)
    assert any("Ignore all previous instructions" in t for t in pi)

    # Default untouched
    untouched = fault_injector.apply_data_anomaly("UNKNOWN_INJ_ID", sample_texts)
    assert untouched == sample_texts

def test_context_manager_isolation(monkeypatch):
    monkeypatch.setenv("ENABLE_FAULT_INJECTION", "true")
    assert fault_injector.current_injection is None

    with fault_injector.apply("A_BLUR_GAUSSIAN", {"kernel_size": 21}) as item:
        assert item.id == "A_BLUR_GAUSSIAN"
        curr = fault_injector.current_injection
        assert curr is not None
        assert curr["id"] == "A_BLUR_GAUSSIAN"
        assert curr["params"]["kernel_size"] == 21

    # Revenu à l'état neutre
    assert fault_injector.current_injection is None

def test_security_disabled_error(monkeypatch):
    monkeypatch.setenv("ENABLE_FAULT_INJECTION", "false")
    with pytest.raises(FaultInjectionDisabledError):
        with fault_injector.apply("A_BLUR_GAUSSIAN"):
            pass
