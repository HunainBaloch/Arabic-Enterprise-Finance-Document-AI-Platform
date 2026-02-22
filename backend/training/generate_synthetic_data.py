"""
generate_synthetic_data.py
──────────────────────────
Generates anonymised synthetic UAE Arabic/English invoice training data
in CoNLL-2003 BIO NER format suitable for fine-tuning AraBERT.

Entities targeted:
  B-VENDOR / I-VENDOR  →  Vendor / Supplier company name
  B-TRN    / I-TRN     →  Tax Registration Number
  B-DATE   / I-DATE    →  Invoice date
  B-TOTAL  / I-TOTAL   →  Grand total amount
  B-VAT    / I-VAT     →  VAT amount (5%)
  O                    →  Tokens outside any entity

Usage:
    cd backend
    python training/generate_synthetic_data.py
    # Writes: training/data/train.conll  (200 samples)
    #         training/data/dev.conll    (30 samples)
    #         training/data/test.conll   (20 samples)
"""

import os
import random
import re
from dataclasses import dataclass, field
from typing import List, Tuple

random.seed(42)

# ─── Entity Value Pools ────────────────────────────────────────────────────────

VENDORS_AR = [
    "شركة الخليج للتجارة", "مؤسسة الإمارات التقنية", "شركة دبي للحلول الذكية",
    "مجموعة أبوظبي للأعمال", "شركة الفجيرة للمقاولات", "مؤسسة الشارقة للخدمات",
    "شركة العين للتوريدات", "مجموعة رأس الخيمة التجارية", "شركة أم القيوين للتجهيزات",
    "مؤسسة عجمان للتقنية", "شركة الشرق الأوسط للتجارة", "مجموعة الخليج المتحد",
    "شركة النخيل للخدمات اللوجستية", "مؤسسة الصقر للمقاولات", "شركة الاتحاد للطاقة",
    "مجموعة ماسدر للتقنية", "شركة إيمار للتطوير العقاري", "مؤسسة الدانة للتوريدات",
    "شركة الوطني للمعدات", "مؤسسة بريق للتجارة العامة",
]

VENDORS_EN = [
    "Gulf Trade Solutions LLC", "Emirates Tech Partners FZE", "Dubai Smart Systems Co.",
    "Abu Dhabi Business Group", "Fujairah Contracting Est.", "Sharjah Services Corp",
    "Al Ain Supply Chain LLC", "RAK Commercial Holdings", "Umm Al Quwain Equipment LLC",
    "Ajman Technology Solutions", "MENAP Trading Corporation", "United Gulf Group PJSC",
    "Al Nakheel Logistics LLC", "Al Saqr Contracting WLL", "Etihad Energy Services Co.",
    "Masdar Technology LLC", "Emaar Properties PJSC", "Al Dana Supplies & Trading",
    "Al Watani Equipment Corp", "Bariq General Trading LLC",
]

VENDORS_BILINGUAL = [v_ar + " / " + v_en for v_ar, v_en in zip(VENDORS_AR, VENDORS_EN)]

# UAE TRNs are 15-digit numbers
def random_trn() -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(15)])

# Dates — various common formats
def random_date() -> str:
    year = random.choice([2023, 2024, 2025])
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    fmt = random.choice([
        f"{day:02d}/{month:02d}/{year}",
        f"{year}-{month:02d}-{day:02d}",
        f"{day:02d}-{month:02d}-{year}",
        f"{day} {'يناير فبراير مارس أبريل مايو يونيو يوليو أغسطس سبتمبر أكتوبر نوفمبر ديسمبر'.split()[month-1]} {year}",
    ])
    return fmt

def random_amounts() -> Tuple[float, float]:
    """Returns (total_inclusive, vat) where vat = total * 5/105."""
    base = round(random.uniform(500, 250000), 2)
    vat = round(base * 5 / 105, 2)
    total = round(base + vat - vat, 2)  # inclusive total
    # Occasionally introduce rounding noise (tests tolerance)
    if random.random() < 0.15:
        vat = round(vat + random.uniform(-0.01, 0.01), 2)
    return total, vat

# ─── BIO Tagging Helper ────────────────────────────────────────────────────────

def tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r"[\u0600-\u06FF]+|[A-Za-z]+|[0-9]+(?:[.,/\-][0-9]+)*|[^\w\s]", text)


def bio_tag_tokens(tokens: List[str], entity_tokens: List[str], entity_type: str) -> List[str]:
    """Assigns BIO tags for entity_tokens within tokens list."""
    tags = ["O"] * len(tokens)
    n = len(entity_tokens)
    for i in range(len(tokens) - n + 1):
        if tokens[i:i + n] == entity_tokens:
            tags[i] = f"B-{entity_type}"
            for j in range(1, n):
                tags[i + j] = f"I-{entity_type}"
            break
    return tags


@dataclass
class InvoiceSample:
    vendor: str
    trn: str
    date: str
    total: float
    vat: float

    def to_conll(self) -> str:
        """Builds a CoNLL-2003 formatted invoice sentence and returns the block."""
        vendor_pool = random.choice([VENDORS_AR, VENDORS_EN, VENDORS_BILINGUAL])
        vendor = random.choice(vendor_pool)
        trn = self.trn
        date = self.date
        total_str = f"{self.total:.2f}"
        vat_str = f"{self.vat:.2f}"

        # Build a natural-language invoice snippet with mixed Arabic/English structure
        templates = [
            # ── Template A: Arabic-primary ───
            f"اسم المورد : {vendor} الرقم الضريبي : {trn} تاريخ الفاتورة : {date} الإجمالي الشامل : {total_str} AED ضريبة القيمة المضافة : {vat_str} AED",
            # ── Template B: English-primary ──
            f"Vendor : {vendor} TRN : {trn} Invoice Date : {date} Grand Total : AED {total_str} VAT Amount : AED {vat_str}",
            # ── Template C: Bilingual table-like ─
            f"المورد Vendor : {vendor}\nرقم الضريبي TRN : {trn}\nالتاريخ Date : {date}\nالإجمالي Total : {total_str}\nالضريبة VAT : {vat_str}",
            # ── Template D: Document header style ─
            f"فاتورة ضريبية - Tax Invoice\nمن / From : {vendor}\nTRN : {trn}\nDate : {date}\nAmount : {total_str} AED\nVAT (5%) : {vat_str} AED",
        ]
        sentence = random.choice(templates)

        # Flatten multi-line to a single token stream
        flat = sentence.replace("\n", " ")
        tokens = tokenize(flat)

        # Build per-entity tags
        tags = ["O"] * len(tokens)

        def tag_entity(value: str, label: str):
            nonlocal tags
            v_tokens = tokenize(value)
            new_tags = bio_tag_tokens(tokens, v_tokens, label)
            for i, t in enumerate(new_tags):
                if t != "O":
                    tags[i] = t

        tag_entity(vendor, "VENDOR")
        tag_entity(trn, "TRN")
        tag_entity(date, "DATE")
        tag_entity(total_str, "TOTAL")
        tag_entity(vat_str, "VAT")

        lines = [f"{tok}\t{tag}" for tok, tag in zip(tokens, tags)]
        return "\n".join(lines) + "\n"


# ─── Generation ───────────────────────────────────────────────────────────────

def generate_samples(n: int) -> List[str]:
    samples = []
    for _ in range(n):
        total, vat = random_amounts()
        sample = InvoiceSample(
            vendor=random.choice(VENDORS_AR + VENDORS_EN + VENDORS_BILINGUAL),
            trn=random_trn(),
            date=random_date(),
            total=total,
            vat=vat,
        )
        samples.append(sample.to_conll())
    return samples


def write_split(samples: List[str], path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(s)
            f.write("\n")  # blank line = sentence boundary
    print(f"  Written {len(samples)} samples → {path}")


if __name__ == "__main__":
    BASE = os.path.join(os.path.dirname(__file__), "data")

    all_samples = generate_samples(250)
    random.shuffle(all_samples)

    train = all_samples[:200]
    dev = all_samples[200:230]
    test = all_samples[230:]

    print("Generating synthetic UAE invoice NER dataset …")
    write_split(train, os.path.join(BASE, "train.conll"))
    write_split(dev,   os.path.join(BASE, "dev.conll"))
    write_split(test,  os.path.join(BASE, "test.conll"))
    print(f"\nDone. Splits: train={len(train)}, dev={len(dev)}, test={len(test)}")
