import asyncio
import time
import os
import torch
from app.services.nlp import extract_financial_entities
from app.services.llm import generate_json_validation

# Forcing CPU only for Paddle OCR due to missing DLLs locally
from paddleocr import PaddleOCR
ocr_engine = PaddleOCR(use_angle_cls=True, lang='ar', device='cpu')

def extract_text_cpu(file_path: "str"):
    results = ocr_engine.ocr(file_path)
    if not results or not results[0]:
         return ""
    texts = [line[1][0] for line in results[0] if line]
    return "\n".join(texts)

async def benchmark():
    pdf_path = "uploads/invoice-report-format-8-standard-invoice-arabic.pdf"
    
    print(f"--- Starting Preprocessing Benchmark (GPU NLP + CPU OCR) on {pdf_path} ---")
    
    # 1. OCR Stage
    start_time = time.time()
    try:
        from app.services.ocr import extract_text
        # extract_text now acts as a wrapper. Since paddle OCR isn't working with GPU due to DLLs,
        # we'll use the CPU version we instantiate here instead to mimic the full pipeline
        # Actually to keep it simple and accurate to the worker flow, we use the real function 
        # but we already modified ocr.py to use `device=cpu`!
        text_data = extract_text(pdf_path)
        text = text_data.get('raw_text', '')
        ocr_time = time.time() - start_time
        print(f"OCR/Text Extraction (CPU from Real PDF): {ocr_time:.2f}s")
    except Exception as e:
        print(f"OCR Stage Failed: {e}")
        text = "Sample"
        ocr_time = time.time() - start_time

    # 2. NLP Stage
    start_time = time.time()
    num_threads = torch.get_num_threads()
    cuda_avail = torch.cuda.is_available()
    print(f"NLP Configuration - CUDA Available: {cuda_avail}, CPU Threads: {num_threads}")
    entities = extract_financial_entities(text)
    nlp_time = time.time() - start_time
    print(f"NLP (NER) Extraction ({'GPU' if cuda_avail else 'CPU'}): {nlp_time:.2f}s")

    # 3. LLM Stage
    start_time = time.time()
    llm_data = await generate_json_validation(text, entities)
    llm_time = time.time() - start_time
    print(f"LLM Validation (Ollama GPU): {llm_time:.2f}s")

    total_time = ocr_time + nlp_time + llm_time
    print(f"\n--- Total Preprocessing Time: {total_time:.2f}s ---")

if __name__ == "__main__":
    asyncio.run(benchmark())
