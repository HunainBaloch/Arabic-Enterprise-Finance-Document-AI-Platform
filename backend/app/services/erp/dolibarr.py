import logging
import httpx
from typing import Dict, Any
from app.services.erp.base import ERPConnector

logger = logging.getLogger(__name__)

class DolibarrConnector(ERPConnector):
    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "DOLAPIKEY": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def sync_invoice(self, document_id: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pushes extracted invoice data to Dolibarr via REST API.
        """
        logger.info(f"Syncing document {document_id} to Dolibarr ERP")
        try:
            # Map standard IDP fields to Dolibarr Vendor Invoice fields
            payload = {
                "ref_supplier": f"INV-{document_id[:8]}",
                "socid": 1, # This would ideally be dynamically resolved from vendor_name
                "date": extracted_data.get("invoice_date"),
                "total_tpp": extracted_data.get("total_amount", 0.0), # Example mapping
                "tva": extracted_data.get("vat_amount", 0.0),
                "type": 0, # Standard invoice
                "note_public": f"Auto-extracted by AI Platform from Document ID: {document_id}"
            }
            
            response = httpx.post(f"{self.url}/api/index.php/supplierinvoices", headers=self.headers, json=payload, timeout=10.0)
            response.raise_for_status()
            
            result_data = response.json()
            logger.info(f"Successfully synced to Dolibarr: Invoice ID {result_data}")
            return {
                "success": True,
                "provider": "dolibarr",
                "erp_reference": str(result_data),
                "message": "Invoice created in Dolibarr"
            }

        except httpx.HTTPError as e:
            logger.error(f"Dolibarr REST API error: {str(e)}")
            raise e # Raise to allow celery retry mechanism
        except Exception as e:
            logger.error(f"Dolibarr Sync failed mysteriously: {str(e)}")
            raise e
