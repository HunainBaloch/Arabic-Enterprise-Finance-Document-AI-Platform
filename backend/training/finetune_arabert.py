"""
finetune_arabert.py
───────────────────
Fine-tunes aubmindlab/bert-base-arabertv02 on synthetic UAE invoice data
for Financial Named Entity Recognition (NER).

Target labels:
  B-VENDOR / I-VENDOR  →  Vendor company name
  B-TRN    / I-TRN     →  Tax Registration Number
  B-DATE   / I-DATE    →  Invoice date
  B-TOTAL  / I-TOTAL   →  Grand total
  B-VAT    / I-VAT     →  VAT amount

Usage:
    cd backend
    python training/finetune_arabert.py \
        --train_file training/data/train.conll \
        --dev_file   training/data/dev.conll \
        --test_file  training/data/test.conll \
        --output_dir training/models/arabert_ner_uae \
        --epochs 5 \
        --batch_size 16

Output:
    training/models/arabert_ner_uae/   ← HuggingFace model directory
    training/eval_results.json         ← Per-class precision / recall / F1
"""

import argparse
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
    set_seed,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Label Schema ──────────────────────────────────────────────────────────────
LABEL_LIST = [
    "O",
    "B-VENDOR", "I-VENDOR",
    "B-TRN",    "I-TRN",
    "B-DATE",   "I-DATE",
    "B-TOTAL",  "I-TOTAL",
    "B-VAT",    "I-VAT",
]
LABEL2ID: Dict[str, int] = {l: i for i, l in enumerate(LABEL_LIST)}
ID2LABEL: Dict[int, str] = {i: l for l, i in LABEL2ID.items()}


# ─── CoNLL Dataset Reader ──────────────────────────────────────────────────────

def read_conll(path: str) -> Tuple[List[List[str]], List[List[str]]]:
    """Parses CoNLL-2003 format. Returns (list_of_token_seqs, list_of_tag_seqs)."""
    sentences_tokens, sentences_tags = [], []
    tokens, tags = [], []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                if tokens:
                    sentences_tokens.append(tokens)
                    sentences_tags.append(tags)
                    tokens, tags = [], []
            else:
                parts = line.split("\t")
                if len(parts) == 2:
                    tokens.append(parts[0])
                    tags.append(parts[1])

    if tokens:
        sentences_tokens.append(tokens)
        sentences_tags.append(tags)

    logger.info(f"Loaded {len(sentences_tokens)} sentences from {path}")
    return sentences_tokens, sentences_tags


# ─── Tokenized NER Dataset ────────────────────────────────────────────────────

class NERDataset(Dataset):
    def __init__(
        self,
        token_seqs: List[List[str]],
        tag_seqs: List[List[str]],
        tokenizer,
        max_length: int = 256,
        label_all_tokens: bool = False,
    ):
        self.features = []
        for tokens, tags in zip(token_seqs, tag_seqs):
            encoding = tokenizer(
                tokens,
                is_split_into_words=True,
                truncation=True,
                max_length=max_length,
                padding="max_length",
                return_offsets_mapping=False,
            )
            word_ids = encoding.word_ids()
            label_ids = []
            prev_word_idx: Optional[int] = None
            for word_idx in word_ids:
                if word_idx is None:
                    label_ids.append(-100)
                elif word_idx != prev_word_idx:
                    label_ids.append(LABEL2ID.get(tags[word_idx], 0))
                else:
                    if label_all_tokens:
                        label_ids.append(LABEL2ID.get(tags[word_idx], 0))
                    else:
                        label_ids.append(-100)
                prev_word_idx = word_idx
            encoding["labels"] = label_ids
            self.features.append(encoding)

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        item = {k: torch.tensor(v) for k, v in self.features[idx].items() if k != "offset_mapping"}
        return item


# ─── Evaluation Metrics (Seqeval-style) ───────────────────────────────────────

def compute_metrics(eval_preds) -> Dict[str, float]:
    """Computes entity-level precision, recall, F1 from predictions."""
    logits, labels = eval_preds
    predictions = np.argmax(logits, axis=2)

    true_labels_all, pred_labels_all = [], []
    for pred_seq, label_seq in zip(predictions, labels):
        true_sent, pred_sent = [], []
        for pred, label in zip(pred_seq, label_seq):
            if label == -100:
                continue
            true_sent.append(ID2LABEL[label])
            pred_sent.append(ID2LABEL[pred])
        true_labels_all.append(true_sent)
        pred_labels_all.append(pred_sent)

    # Span-level F1 per entity type
    entity_types = set(l[2:] for l in LABEL_LIST if l != "O")
    metrics: Dict[str, float] = {}
    tp_total = fp_total = fn_total = 0

    for etype in entity_types:
        tp = fp = fn = 0
        for true_seq, pred_seq in zip(true_labels_all, pred_labels_all):
            true_spans = _get_spans(true_seq, etype)
            pred_spans = _get_spans(pred_seq, etype)
            for span in pred_spans:
                if span in true_spans:
                    tp += 1
                else:
                    fp += 1
            for span in true_spans:
                if span not in pred_spans:
                    fn += 1
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec  = tp / (tp + fn) if (tp + fn) else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        metrics[f"precision_{etype}"] = round(prec, 4)
        metrics[f"recall_{etype}"]    = round(rec, 4)
        metrics[f"f1_{etype}"]        = round(f1, 4)
        tp_total += tp; fp_total += fp; fn_total += fn

    overall_prec = tp_total / (tp_total + fp_total) if (tp_total + fp_total) else 0.0
    overall_rec  = tp_total / (tp_total + fn_total) if (tp_total + fn_total) else 0.0
    overall_f1   = 2 * overall_prec * overall_rec / (overall_prec + overall_rec) if (overall_prec + overall_rec) else 0.0

    metrics["precision_overall"] = round(overall_prec, 4)
    metrics["recall_overall"]    = round(overall_rec, 4)
    metrics["f1_overall"]        = round(overall_f1, 4)

    logger.info(f"\n{'─'*50}\nOverall NER F1: {overall_f1:.4f}\n{'─'*50}")
    return metrics


def _get_spans(seq: List[str], entity_type: str) -> List[Tuple[int, int, str]]:
    spans = []
    i = 0
    while i < len(seq):
        if seq[i] == f"B-{entity_type}":
            start = i
            i += 1
            while i < len(seq) and seq[i] == f"I-{entity_type}":
                i += 1
            spans.append((start, i - 1, entity_type))
        else:
            i += 1
    return spans


# ─── Main Training Function ───────────────────────────────────────────────────

def main():
    # ── Resolve paths relative to this script file ─────────────────────────────
    _HERE   = os.path.dirname(os.path.abspath(__file__))
    _DATA   = os.path.join(_HERE, "data")
    _MODELS = os.path.join(_HERE, "models")

    # ── GPU detection ───────────────────────────────────────────────────────────
    _cuda_available = torch.cuda.is_available()
    _gpu_name       = torch.cuda.get_device_name(0) if _cuda_available else "N/A"
    _gpu_vram_gb    = (
        torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
        if _cuda_available else 0
    )
    logger.info("=" * 60)
    logger.info(f"  GPU available : {_cuda_available}")
    logger.info(f"  GPU name      : {_gpu_name}")
    logger.info(f"  GPU VRAM      : {_gpu_vram_gb:.1f} GB")
    logger.info("=" * 60)

    if not _cuda_available:
        logger.warning(
            "No CUDA GPU detected! Training will fall back to CPU.\n"
            "Ensure NVIDIA drivers + CUDA toolkit are installed and "
            "torch was installed with CUDA support:\n"
            "  pip install torch --index-url https://download.pytorch.org/whl/cu121"
        )

    # ── Argument defaults tuned for RTX 4060 (8 GB VRAM) ──────────────────────
    # AraBERT-base (~440 MB) + batch_size 32 + sequence_length 256 ≈ 5–6 GB VRAM
    # Headroom kept for gradient computation.
    _default_batch  = 32 if _cuda_available else 8
    _default_epochs = 8   # more epochs gives higher F1 on a small dataset

    parser = argparse.ArgumentParser(
        description="Fine-tune AraBERT for UAE Invoice NER (RTX 4060 optimised)"
    )
    parser.add_argument("--train_file",         default=os.path.join(_DATA,   "train.conll"))
    parser.add_argument("--dev_file",           default=os.path.join(_DATA,   "dev.conll"))
    parser.add_argument("--test_file",          default=os.path.join(_DATA,   "test.conll"))
    parser.add_argument("--output_dir",         default=os.path.join(_MODELS, "arabert_ner_uae"))
    parser.add_argument("--model_name",         default="aubmindlab/bert-base-arabertv02")
    parser.add_argument("--epochs",             type=int,   default=_default_epochs)
    parser.add_argument("--batch_size",         type=int,   default=_default_batch)
    parser.add_argument("--grad_accum_steps",   type=int,   default=1)
    parser.add_argument("--lr",                 type=float, default=3e-5)
    parser.add_argument("--max_length",         type=int,   default=256)
    parser.add_argument("--seed",               type=int,   default=42)
    parser.add_argument("--dataloader_workers", type=int,   default=4 if _cuda_available else 0)
    args = parser.parse_args()

    set_seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    logger.info(f"  Script dir    : {_HERE}")
    logger.info(f"  Train file    : {args.train_file}")
    logger.info(f"  Output dir    : {args.output_dir}")
    logger.info(f"  Epochs        : {args.epochs}")
    logger.info(f"  Batch size    : {args.batch_size}  (×{args.grad_accum_steps} grad_accum)")
    logger.info(f"  DL workers    : {args.dataloader_workers}")

    # ── Precision: prefer bf16 on Ampere (RTX 30xx / 40xx), else fp16 ─────────
    # RTX 4060 is Ada Lovelace (CUDA compute 8.9) — bf16 is fully supported.
    # bf16 is numerically more stable than fp16 for NLP fine-tuning.
    _compute_cap = (
        torch.cuda.get_device_capability(0) if _cuda_available else (0, 0)
    )
    _use_bf16 = _cuda_available and _compute_cap[0] >= 8   # Ampere+
    _use_fp16 = _cuda_available and not _use_bf16
    logger.info(
        f"  Precision     : {'bf16' if _use_bf16 else 'fp16' if _use_fp16 else 'fp32 (CPU)'}"
    )

    # ── Load tokenizer & datasets ────────────────────────────────────────────
    logger.info(f"\nLoading tokenizer: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    logger.info("Reading CoNLL datasets …")
    train_tokens, train_tags = read_conll(args.train_file)
    dev_tokens,   dev_tags   = read_conll(args.dev_file)
    test_tokens,  test_tags  = read_conll(args.test_file)

    train_dataset = NERDataset(train_tokens, train_tags, tokenizer, args.max_length)
    dev_dataset   = NERDataset(dev_tokens,   dev_tags,   tokenizer, args.max_length)
    test_dataset  = NERDataset(test_tokens,  test_tags,  tokenizer, args.max_length)

    logger.info(
        f"  Dataset sizes → train: {len(train_dataset)}  "
        f"dev: {len(dev_dataset)}  test: {len(test_dataset)}"
    )

    # ── Load model ───────────────────────────────────────────────────────────
    logger.info(f"\nLoading model: {args.model_name}")
    model = AutoModelForTokenClassification.from_pretrained(
        args.model_name,
        num_labels=len(LABEL_LIST),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )

    # ── TrainingArguments — RTX 4060 tuned ──────────────────────────────────
    training_args = TrainingArguments(
        output_dir=args.output_dir,

        # ─ Evaluation / checkpointing
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1_overall",
        greater_is_better=True,
        save_total_limit=2,

        # ─ Optimisation
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum_steps,
        num_train_epochs=args.epochs,
        weight_decay=0.01,
        warmup_steps=3,
        lr_scheduler_type="cosine",

        # ─ Precision
        bf16=_use_bf16,
        fp16=_use_fp16,

        # ─ Data loading
        dataloader_num_workers=args.dataloader_workers,
        dataloader_pin_memory=_cuda_available,

        # ─ Logging
        logging_steps=5,
        report_to="none",
        seed=args.seed,
    )

    data_collator = DataCollatorForTokenClassification(tokenizer, pad_to_multiple_of=8)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=dev_dataset,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    # ── Train ────────────────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("  Starting fine-tuning …")
    logger.info("=" * 60)
    trainer.train()

    # ── Evaluate on held-out test set ────────────────────────────────────────
    logger.info("\nEvaluating on test set …")
    test_results = trainer.evaluate(test_dataset, metric_key_prefix="test")

    results_path = os.path.join(_HERE, "eval_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    logger.info(f"Evaluation results saved → {results_path}")

    # ── Save fine-tuned model ─────────────────────────────────────────────────
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    logger.info(f"Model saved → {args.output_dir}")

    # ── Final report ─────────────────────────────────────────────────────────
    f1_total   = test_results.get("test_f1_overall", 0)
    f1_vendor  = test_results.get("test_f1_VENDOR", 0)
    f1_trn     = test_results.get("test_f1_TRN",    0)
    f1_date    = test_results.get("test_f1_DATE",   0)
    f1_total_e = test_results.get("test_f1_TOTAL",  0)
    f1_vat     = test_results.get("test_f1_VAT",    0)

    logger.info("\n" + "=" * 60)
    logger.info("  FINAL NER F1 SCORES (test set)")
    logger.info("=" * 60)
    logger.info(f"  VENDOR  : {f1_vendor:.4f}")
    logger.info(f"  TRN     : {f1_trn:.4f}")
    logger.info(f"  DATE    : {f1_date:.4f}")
    logger.info(f"  TOTAL   : {f1_total_e:.4f}")
    logger.info(f"  VAT     : {f1_vat:.4f}")
    logger.info("─" * 60)
    logger.info(f"  OVERALL : {f1_total:.4f}   (target ≥ 0.85)")
    logger.info("=" * 60)

    if f1_total >= 0.85:
        logger.info("  ✅  TARGET MET: Overall F1 ≥ 0.85")
        logger.info(f"  Fine-tuned model ready at: {args.output_dir}")
        logger.info("  nlp.py will auto-load it on next backend restart.")
    else:
        logger.warning(
            f"  ⚠️  F1 = {f1_total:.4f} < 0.85 target.\n"
            "  Try: --epochs 12, or run generate_synthetic_data.py with n=500 first."
        )


if __name__ == "__main__":
    main()
