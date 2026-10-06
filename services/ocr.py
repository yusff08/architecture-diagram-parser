import numpy as np
import cv2
from paddleocr import PaddleOCR
from typing import List, Dict, Any
import logging

# Initialize PaddleOCR globally to avoid reloading the model on every request
# lang='en' specifies English. use_textline_orientation=True helps with rotated text.
try:
    ocr = PaddleOCR(use_textline_orientation=True, lang='en', enable_mkldnn=False)
except Exception as e:
    logging.error(f"Failed to initialize PaddleOCR: {e}")
    ocr = None

def extract_text_from_image(image_bytes: bytes, confidence_threshold: float = 0.40) -> List[Dict[str, Any]]:
    if not ocr:
        raise RuntimeError("PaddleOCR is not initialized or failed to load.")

    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    
    # Decode image using OpenCV
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Failed to decode image from bytes.")

    # Perform OCR (cls=True removed for v3.x compatibility)
    result = ocr.ocr(img)
    print("DEBUG OCR RAW OUTPUT:", result)
    
    extracted_text = []
    
    if result and isinstance(result, list) and len(result) > 0:
        res_obj = result[0]
        if isinstance(res_obj, dict) and 'rec_texts' in res_obj:
            texts = res_obj.get('rec_texts', [])
            scores = res_obj.get('rec_scores', [])
            for text, score in zip(texts, scores):
                if score >= confidence_threshold:
                    extracted_text.append({
                        "text": str(text),
                        "confidence": float(score)
                    })
                    
    return extracted_text
