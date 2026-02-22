from abc import ABC, abstractmethod
from typing import Dict, Any

class ERPConnector(ABC):
    """
    Abstract base class for all ERP external connectors.
    Enforces a standard contract for syncing extracted financial data.
    """
    
    @abstractmethod
    def authenticate(self) -> bool:
        """ Authenticate with the ERP system. Returns True if successful. """
        pass
        
    @abstractmethod
    def sync_invoice(self, document_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pushes the structured JSON payload to the ERP system as an Invoice or Bill.
        Returns a dictionary containing success status and the external ERP ID.
        """
        pass
