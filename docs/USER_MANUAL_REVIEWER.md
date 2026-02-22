# Human-in-the-Loop (HITL) Dashboard: Reviewer Manual

Welcome to the Arabic Enterprise Finance Document AI Platform. Your role as a **Reviewer** is critical. You are the final human safety net that ensures the AI models correctly extracted financial data before it is synced to the downstream core ERP systems (Odoo, ERPNext, Dolibarr).

## 1. Navigating the Dashboard

1. **Upload an Invoice:** Use the home screen to drag-and-drop or browse for an Arabic or English PDF Invoice.
2. **Status Tracking:** The dashboard will show real-time processing states:
   - `UPLOADED`: Sent to server.
   - `PREPROCESSING`: De-skewing and optimizing image clarity.
   - `OCR_EXTRACTION`: PaddleOCR reading all text.
   - `NLP_EXTRACTION`: AraBERT finding specific entities (Names, Dates).
   - `LLM_VALIDATION`: Instruct-Tuned LLM structuring the messy data into an exact JSON format.

## 2. Reviewing Invoices (`HITL_REVIEW`)
If the invoice confidence score falls below **95%**, or if the mathematical VAT calculation (5%) fails the tolerance check, the document enters `HITL_REVIEW`. You must manually verify it.

### The Split-View Interface
- **Left Column (Document Viewer):** Displays the original scanned invoice. You can zoom and scroll.
- **Right Column (Editable Fields):** Displays the AI-extracted fields:
   - Vendor Name
   - TRN
   - Invoice Date
   - Total Amount
   - VAT Amount (5%)

### Low Confidence Flags (Red Border)
If the open-source LLM is uncertain about a specific extraction (e.g., a blurry date, or a vendor name spanning multiple lines), it will explicitly flag it.
- **Fields marked with a thick red border and "(Low Confidence)"** should be reviewed first.
- The AI's explicitly written **Reasoning Alert** will appear in a blue box below the inputs explaining *why* it got confused.

## 3. Approving & Syncing

Once you have visually compared the original invoice to the right-hand column and made necessary typological fixes:
1. Click the green **Approve & Save** button.
2. The AI Platform saves an immutable **Audit Log** associating your reviewer ID with the exact changes made.
3. The server immediately transitions the Document State to `COMPLETED`. 

*(Authorized Admins only can subsequently push the completed batch out to the ERP APIs).*
