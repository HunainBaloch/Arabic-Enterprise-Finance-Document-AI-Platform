import logging
import os
import tempfile
import numpy as np
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from app.services.preprocessing import preprocess_image

logger = logging.getLogger(__name__)

# Initialize PaddleOCR globally to avoid reloading the model per request
# We use arabic language which also supports english numbers and text
ocr_engine = PaddleOCR(use_angle_cls=True, lang='ar', show_log=False)

def _process_single_image(image_path: str):
    preprocessed_path = preprocess_image(image_path)
    results = ocr_engine.ocr(preprocessed_path, cls=True)
    
    if not results or not results[0]:
        return "", [], 0.0
        
    page_results = results[0]
    blocks = []
    confidences = []
    full_text = []
    
    for line in page_results:
        if not line:
            continue
        box = line[0]
        text_info = line[1]
        text = text_info[0]
        conf = float(text_info[1])
        
        blocks.append({
            "box": box,
            "text": text,
            "confidence": conf
        })
        full_text.append(text)
        confidences.append(conf)
        
    overall_confidence = float(np.mean(confidences)) if confidences else 0.0
    return "\n".join(full_text), blocks, overall_confidence


def extract_text(file_path: str) -> dict:
    """
    Extracts text, bounding boxes, and calculates an overall confidence score.
    Returns a dictionary with raw_text, blocks, and confidence.
    """
    logger.info(f"Running OCR on {file_path}")
    
    try:
        if file_path.lower().endswith(".pdf"):
            images = convert_from_path(file_path)
            all_blocks = []
            all_confidences = []
            all_texts = []
            
            with tempfile.TemporaryDirectory() as temp_dir:
                for i, img in enumerate(images):
                    img_path = os.path.join(temp_dir, f"page_{i}.jpg")
                    img.save(img_path, "JPEG")
                    
                    text, blocks, conf = _process_single_image(img_path)
                    if text:
                        all_texts.append(text)
                        all_blocks.extend(blocks)
                        all_confidences.append(conf)
                        
            return {
                "raw_text": "\n".join(all_texts),
                "blocks": all_blocks,
                "confidence": float(np.mean(all_confidences)) if all_confidences else 0.0
            }
        else:
            text, blocks, conf = _process_single_image(file_path)
            return {
                "raw_text": text,
                "blocks": blocks,
                "confidence": conf
            }
            
    except Exception as e:
        logger.error(f"OCR Failed for {file_path}: {str(e)}")
        raise e
