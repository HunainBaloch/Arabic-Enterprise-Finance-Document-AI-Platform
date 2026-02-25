import logging
import os
import tempfile
import numpy as np
import pytesseract
from PIL import Image
from pytesseract import Output
import fitz  # PyMuPDF — pure Python PDF renderer, no Poppler required
from app.services.preprocessing import preprocess_image
from app.core.config import settings

logger = logging.getLogger(__name__)

# Tesseract executable path configuration
if os.name == 'nt':
    tesseract_cmd = os.environ.get('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    if os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    else:
        logger.warning(f"Tesseract executable not found at {tesseract_cmd}. Ensure it is in your PATH or set TESSERACT_CMD.")

def _process_single_image(image_path: str):
    preprocessed_path = preprocess_image(image_path)
    
    blocks = []
    full_text = []
    confidences = []
    
    try:
        img = Image.open(preprocessed_path)
        # Use Arabic and English language packs. 
        # Note: 'ara' or 'ara+eng' requires the Tesseract Arabic language data installed.
        data = pytesseract.image_to_data(img, lang='ara+eng', output_type=Output.DICT)
        
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            
            # Tesseract uses -1 for layout blocks, we only want text with confidence > -1
            if conf > -1 and text:
                # bounding box: left, top, width, height
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                # Convert to PaddleOCR style polygon points: [top-left, top-right, bottom-right, bottom-left]
                box = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
                
                confidence_normalized = float(conf) / 100.0  # Normalize to 0.0 - 1.0
                blocks.append({
                    "box": box,
                    "text": text,
                    "confidence": confidence_normalized
                })
                full_text.append(text)
                confidences.append(confidence_normalized)
                
        overall_confidence = float(np.mean(confidences)) if confidences else 0.0
        return "\n".join(full_text), blocks, overall_confidence
        
    except FileNotFoundError:
        logger.error("Tesseract OCR not found. Please install tesseract-ocr system binary.")
        return "", [], 0.0
    except Exception as e:
        logger.error(f"Tesseract extraction error: {str(e)}")
        return "", [], 0.0

def extract_text(file_path: str) -> dict:
    """
    Extracts text, bounding boxes, and calculates an overall confidence score.
    Returns a dictionary with raw_text, blocks, and confidence.
    """
    logger.info(f"Running OCR on {file_path}")
    
    try:
        if file_path.lower().endswith(".pdf"):
            # Use PyMuPDF to render PDF pages
            pdf_doc = fitz.open(file_path)
            all_blocks = []
            all_confidences = []
            all_texts = []
            
            with tempfile.TemporaryDirectory() as temp_dir:
                for i, page in enumerate(pdf_doc):
                    # Higher zoom (e.g. 2.0 or 3.0) improves Tesseract OCR accuracy significantly.
                    # As Tesseract is much more memory efficient than PaddleOCR, we can safely scale up.
                    mat = fitz.Matrix(2.0, 2.0)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    img_path = os.path.join(temp_dir, f"page_{i}.jpg")
                    pix.save(img_path)
                    
                    text, blocks, conf = _process_single_image(img_path)
                    if text:
                        all_texts.append(text)
                        all_blocks.extend(blocks)
                        all_confidences.append(conf)
                        
            pdf_doc.close()
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
