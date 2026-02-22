import os
from typing import Optional
from app.services.erp.base import ERPConnector

def get_erp_connector(provider: str) -> Optional[ERPConnector]:
    """
    Factory function to initialize the requested ERP connector. 
    In production, credentials should be loaded from secure secrets/env vars.
    """
    if provider == "odoo":
        from app.services.erp.odoo import OdooConnector
        url = os.getenv("ODOO_URL", "http://localhost:8069")
        db = os.getenv("ODOO_DB", "idp")
        username = os.getenv("ODOO_USERNAME", "admin")
        password = os.getenv("ODOO_PASSWORD", "admin")
        return OdooConnector(url, db, username, password)

    elif provider == "erpnext":
        from app.services.erp.erpnext import ERPNextConnector
        url = os.getenv("ERPNEXT_URL", "http://localhost:8000")
        api_key = os.getenv("ERPNEXT_API_KEY", "test")
        api_secret = os.getenv("ERPNEXT_API_SECRET", "test")
        return ERPNextConnector(url, api_key, api_secret)
        
    elif provider == "dolibarr":
        from app.services.erp.dolibarr import DolibarrConnector
        url = os.getenv("DOLIBARR_URL", "http://localhost/dolibarr/htdocs")
        api_key = os.getenv("DOLIBARR_API_KEY", "test")
        return DolibarrConnector(url, api_key)
        
    return None
