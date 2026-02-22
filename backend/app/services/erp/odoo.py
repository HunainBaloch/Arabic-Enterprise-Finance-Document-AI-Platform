import logging
import xmlrpc.client
from typing import Dict, Any
from app.services.erp.base import ERPConnector

logger = logging.getLogger(__name__)

class OdooConnector(ERPConnector):
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        self.uid = None

    def authenticate(self) -> bool:
        try:
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                logger.info("Successfully authenticated with Odoo ERP.")
                return True
            logger.error("Odoo authentication failed: Invalid credentials.")
            return False
        except Exception as e:
            logger.error(f"Odoo authentication exception: {str(e)}")
            return False

    def sync_invoice(self, document_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.uid and not self.authenticate():
            raise Exception("Odoo Authentication failed. Cannot sync invoice.")

        try:
            # Note: Fields mapped here must match Odoo's 'account.move' model requirements.
            # We are assuming it's a Vendor Bill (in_invoice)
            
            # Step 1: Attempt to find or create the Vendor (Partner)
            vendor_name = payload.get("vendor_name")
            partner_id = False
            
            if vendor_name:
                partner_search = self.models.execute_kw(self.db, self.uid, self.password,
                    'res.partner', 'search', [[['name', '=', vendor_name]]])
                if partner_search:
                    partner_id = partner_search[0]
                else:
                     partner_id = self.models.execute_kw(self.db, self.uid, self.password,
                        'res.partner', 'create', [{'name': vendor_name, 'vat': payload.get("trn")}])

            # Step 2: Create the Invoice Record
            invoice_vals = {
                'move_type': 'in_invoice', # Vendor Bill
                'partner_id': partner_id,
                'invoice_date': payload.get("invoice_date"),
                'ref': f"IDP-{document_id}",
                # Additional line items would be mapped here based on actual DB payload structure
            }
            
            invoice_id = self.models.execute_kw(self.db, self.uid, self.password,
                'account.move', 'create', [invoice_vals])
            
            logger.info(f"Odoo Sync Success. Invoice ID: {invoice_id}")
            return {"success": True, "erp_id": str(invoice_id), "provider": "odoo"}

        except Exception as e:
            logger.error(f"Odoo Sync failed for {document_id}: {str(e)}")
            raise e
