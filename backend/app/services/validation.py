import logging

logger = logging.getLogger(__name__)

VAT_RATE = 0.05
TOLERANCE_GAP = 0.02 # Allow 2 cents for mathematical rounding variance

def validate_uae_vat(total_amount: float, vat_amount: float) -> dict:
    """
    Validates if the VAT amount is exactly 5% of the pre-tax amount.
    Note: 'total_amount' usually represents the final amount (inclusive of VAT).
    If total_amount is inclusive, then Pre-Tax = total_amount / 1.05.
    If total_amount is exclusive, then Pre-Tax = total_amount.
    We will assume total_amount is INCLUSIVE for standard UAE B2B invoices.
    """
    if total_amount is None or vat_amount is None:
        return {
            "is_valid": False,
            "reason": "Missing amounts for VAT calculation."
        }
        
    try:
        total = float(total_amount)
        vat = float(vat_amount)
        
        # Calculate expected VAT assuming total is inclusive
        # VAT = Total - (Total / 1.05)
        expected_vat_inclusive = total - (total / (1 + VAT_RATE))
        
        # Calculate expected VAT assuming total is exclusive
        expected_vat_exclusive = total * VAT_RATE
        
        if abs(vat - expected_vat_inclusive) <= TOLERANCE_GAP:
            return {"is_valid": True, "reason": "VAT matches inclusive total."}
            
        if abs(vat - expected_vat_exclusive) <= TOLERANCE_GAP:
            return {"is_valid": True, "reason": "VAT matches exclusive total."}
            
        return {
            "is_valid": False,
            "reason": f"VAT mismatch. Expected ~{expected_vat_inclusive:.2f} or {expected_vat_exclusive:.2f}, got {vat}"
        }
        
    except ValueError:
        return {
            "is_valid": False, 
            "reason": "Amounts could not be converted to float."
        }
