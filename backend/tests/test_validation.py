import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


from app.services.validation import validate_uae_vat

def test_vat_inclusive_valid():
    # If total is 105, VAT should be 5
    result = validate_uae_vat(105.00, 5.00)
    assert result["is_valid"] is True
    assert "inclusive" in result["reason"]

def test_vat_exclusive_valid():
    # If total is 100, VAT should be 5
    result = validate_uae_vat(100.00, 5.00)
    assert result["is_valid"] is True
    assert "exclusive" in result["reason"]

def test_vat_inclusive_rounding_valid():
    # Example: Total is 100
    # Expected inclusive VAT = 100 - (100 / 1.05) = 4.7619... (approx 4.76)
    result = validate_uae_vat(100.00, 4.76)
    assert result["is_valid"] is True

def test_vat_invalid():
    # If total is 100, and VAT is 20, should fail both inclusive and exclusive
    result = validate_uae_vat(100.00, 20.00)
    assert result["is_valid"] is False
    assert "VAT mismatch" in result["reason"]

def test_vat_invalid_type():
    result = validate_uae_vat("invalid", "invalid")
    assert result["is_valid"] is False
    assert "could not be converted" in result["reason"]

def test_vat_none_values():
    result = validate_uae_vat(None, 5.00)
    assert result["is_valid"] is False
    assert "Missing amounts" in result["reason"]

if __name__ == "__main__":
    # Simple manual runner if pytest is not available
    test_vat_inclusive_valid()
    test_vat_exclusive_valid()
    test_vat_inclusive_rounding_valid()
    test_vat_invalid()
    test_vat_invalid_type()
    test_vat_none_values()
    print("All validation tests passed successfully!")
