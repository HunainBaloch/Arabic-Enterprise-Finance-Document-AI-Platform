import logging
import httpx
from typing import Dict, Any
from app.services.erp.base import ERPConnector

logger = logging.getLogger(__name__)

class ERPNextConnector(ERPConnector):
    def __init__(self, url: str, api_key: str, api_secret: str):
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.headers = {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }

    def authenticate(self) -> bool:
        # ERPNext uses token auth per request usually, so we can verify by fetching a known endpoint
        try:
            with httpx.Client(base_url=self.url, headers=self.headers) as client:
                response = client.get("/api/method/frappe.auth.get_logged_user")
                if response.status_code == 200:
                    logger.info("Successfully verified ERPNext Token.")
                    return True
                logger.error(f"ERPNext Auth Failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"ERPNext auth exception: {str(e)}")
            return False

    def sync_invoice(self, document_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """ Create a Purchase Invoice in ERPNext """
        try:
            # Note: Fields must match ERPNext 'Purchase Invoice' DocType
            
            # Step 1: Prepare the ERPNext payload
            supplier_name = payload.get("vendor_name", "Unknown Supplier")
            
            erpnext_payload = {
                "supplier": supplier_name,
                "bill_no": f"IDP-{document_id}",
                "bill_date": payload.get("invoice_date"),
                "grand_total": payload.get("total_amount"),
                "total_taxes_and_charges": payload.get("vat_amount"),
                # Items array usually required for Purchase Invoice
                "items": [{
                    "item_code": "IDP-EXTRACTED-SERVICE",
                    "qty": 1,
                    "rate": payload.get("total_amount", 0) - payload.get("vat_amount", 0)
                }]
            }
            
            with httpx.Client(base_url=self.url, headers=self.headers) as client:
                response = client.post("/api/resource/Purchase Invoice", json=erpnext_payload)
                response.raise_for_status()
                result = response.json()
                
                doc_name = result.get("data", {}).get("name")
                logger.info(f"ERPNext Sync Success. Invoice ID: {doc_name}")
                return {"success": True, "erp_id": str(doc_name), "provider": "erpnext"}
                
        except Exception as e:
            logger.error(f"ERPNext Sync failed for {document_id}: {str(e)}")
            raise e
