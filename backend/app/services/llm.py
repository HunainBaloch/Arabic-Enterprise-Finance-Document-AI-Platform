import json
import logging
import httpx
from app.core.config import settings
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

class LLMInvoiceResponse(BaseModel):
    vendor_name: Optional[str] = Field(None, description="The name of the vendor or supplier")
    trn: Optional[str] = Field(None, description="The Tax Registration Number (TRN) if present")
    invoice_date: Optional[str] = Field(None, description="The date of the invoice in YYYY-MM-DD format")
    total_amount: Optional[float] = Field(None, description="The grand total amount on the invoice")
    vat_amount: Optional[float] = Field(None, description="The total VAT or tax amount")
    reasoning: Optional[str] = Field(None, description="Brief explanation of how values were found")
    low_confidence_fields: List[str] = Field(default=[], description="List of exact key names that you are uncertain about due to OCR noise or missing data")

async def generate_json_validation(raw_text: str, nlp_entities: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
    """
    Sends the raw OCR text and AraBERT NER entities to a local LLM (Ollama)
    to generate a clean, normalized JSON structure. Includes retry logic for Pydantic validation.
    """
    if not settings.OLLAMA_BASE_URL:
        # Fallback if Ollama isn't configured for local fast-dev
        return {
            "validation_status": "skipped_no_llm_configured",
            "structured_data": nlp_entities
        }
        
    last_error = None
    
    for attempt in range(max_retries):
        prompt = f"""
        You are an expert Arabic Enterprise Finance Document AI.
        Your task is to take the following raw invoice text and initial NLP extractions
        and output a strictly valid JSON object representing the invoice.
        
        Raw Text:
        {raw_text}
        
        Initial Entities:
        {json.dumps(nlp_entities, ensure_ascii=False)}
        
        Output JSON MUST include these exact keys:
        - vendor_name (string)
        - trn (string)
        - invoice_date (YYYY-MM-DD)
        - total_amount (float)
        - vat_amount (float)
        - reasoning (string explaining your confidence or any missing fields)
        - low_confidence_fields (list of strings representing the data keys you are unsure about)
        
        Return ONLY JSON.
        """
        
        if last_error:
            prompt += f"\n\nERROR IN PREVIOUS OUTPUT:\n{last_error}\nPlease fix the JSON formatting or key structures."
            
        logger.info(f"Sending prompt to LLM {settings.LLM_MODEL} at {settings.OLLAMA_BASE_URL} (Attempt {attempt + 1}/{max_retries})")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.LLM_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json" # Ollama strict JSON mode
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                response_text = result.get("response", "{}")
                
                try:
                    # Validate directly with Pydantic JSON parser
                    if hasattr(LLMInvoiceResponse, "model_validate_json"):
                        validated_response = LLMInvoiceResponse.model_validate_json(response_text)
                    else:
                        validated_response = LLMInvoiceResponse.parse_raw(response_text)
                    
                    return validated_response.dict()
                    
                except ValidationError as e:
                    logger.warning(f"Pydantic Validation failed on attempt {attempt + 1}: {str(e)}")
                    last_error = f"Validation Error: {str(e)}"
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON Decode failed on attempt {attempt + 1}: {str(e)}")
                    last_error = f"JSON Decode Error: {str(e)}"
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP Error communicating with LLM: {str(e)}")
            return {
                "validation_status": "llm_failed",
                "error": str(e),
                "structured_data": nlp_entities
            }
        except Exception as e:
            logger.error(f"Unexpected error in LLM Generation: {str(e)}")
            return {
                "validation_status": "llm_failed",
                "error": str(e),
                "structured_data": nlp_entities
            }
            
    # If all retries fail, return an empty initialized structure to prevent pipeline crashes
    logger.error(f"LLM failed to produce valid Pydantic JSON after {max_retries} attempts.")
    return LLMInvoiceResponse().dict()
