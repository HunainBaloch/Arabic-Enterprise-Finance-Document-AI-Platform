"""
nlp.py
──────
Loads the fine-tuned AraBERT NER model and extracts structured financial
entities from OCR-extracted invoice text.

Entity types produced:
    vendor_name   → B-VENDOR / I-VENDOR
    trn           → B-TRN    / I-TRN
    invoice_date  → B-DATE   / I-DATE
    total_amount  → B-TOTAL  / I-TOTAL
    vat_amount    → B-VAT    / I-VAT
"""

import logging
import os
from transformers import pipeline

logger = logging.getLogger(__name__)

# ── Model path resolution ──────────────────────────────────────────────────────
# Priority:
#   1. Fine-tuned UAE model at training/models/arabert_ner_uae  (production)
#   2. Base AraBERT  (fallback during initial dev / before training completes)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # → backend/
_FINETUNED_PATH = os.path.join(_REPO_ROOT, "training", "models", "arabert_ner_uae")
_BASE_MODEL = "aubmindlab/bert-base-arabertv02"

_MODEL_PATH = _FINETUNED_PATH if os.path.isdir(_FINETUNED_PATH) else _BASE_MODEL
_IS_FINETUNED = _MODEL_PATH == _FINETUNED_PATH

ner_pipeline = None


def get_ner_pipeline():
    global ner_pipeline
    if ner_pipeline is None:
        try:
            import torch
            device = 0 if torch.cuda.is_available() else -1
            logger.info(f"Loading NER pipeline from: {_MODEL_PATH} (fine-tuned={_IS_FINETUNED}) on device={device}")
            
            # Use FP16 if on GPU to speed up processing + reduce VRAM
            pipeline_kwargs = {
                "task": "ner",
                "model": _MODEL_PATH,
                "tokenizer": _MODEL_PATH,
                "aggregation_strategy": "simple",
                "device": device,
            }
            if device == 0:
                pipeline_kwargs["torch_dtype"] = torch.float16
                
            ner_pipeline = pipeline(**pipeline_kwargs)
            logger.info("NER pipeline loaded successfully.")
        except Exception as e:
            logger.warning(
                f"Failed to load NER pipeline ({e}). "
                "Running with empty-extraction fallback."
            )
            return None
    return ner_pipeline


# ── Label → field mapping ──────────────────────────────────────────────────────
# These keys MUST match the output labels of the fine-tuned model.
_ENTITY_MAP = {
    "VENDOR": "vendor_name",
    "TRN":    "trn",
    "DATE":   "invoice_date",
    "TOTAL":  "total_amount",
    "VAT":    "vat_amount",
}


def extract_financial_entities(text: str) -> dict:
    """
    Runs AraBERT NER on the OCR text to extract structured financial entities.
    Returns a dict with keys: vendor_name, trn, invoice_date, total_amount, vat_amount.
    All values are strings (or None if not found).
    """
    logger.info("Running AraBERT NER extraction")

    extracted: dict = {field: None for field in _ENTITY_MAP.values()}

    pipe = get_ner_pipeline()
    if pipe is None:
        return extracted  # graceful empty fallback

    try:
        # Handle very long texts by chunking to 512-token windows
        max_chars = 1800  # ≈ 512 BERT sub-word tokens for Arabic
        chunks = [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

        all_entities = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            chunk_entities = pipe(chunk)
            all_entities.extend(chunk_entities)

        # Aggregate entities into the target fields
        buffers: dict = {field: [] for field in _ENTITY_MAP.values()}

        for ent in all_entities:
            # entity_group from aggregation_strategy="simple" will be e.g. "VENDOR"
            raw_label = ent.get("entity_group", ent.get("entity", ""))
            # Strip BIO prefix if not already aggregated
            for prefix in ("B-", "I-"):
                if raw_label.startswith(prefix):
                    raw_label = raw_label[2:]

            field = _ENTITY_MAP.get(raw_label.upper())
            if field:
                word = ent.get("word", "").replace("##", "").strip()
                if word:
                    buffers[field].append(word)

        # Join multi-token entities
        for field, words in buffers.items():
            if words:
                extracted[field] = " ".join(words).strip()

    except Exception as e:
        logger.error(f"NER extraction failed: {e}")

    return extracted
