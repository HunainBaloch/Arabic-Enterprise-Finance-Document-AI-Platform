import sys
import traceback

with open("import_error.txt", "w") as f:
    f.write("Attempting to import app.worker...\n")
    try:
        from app.worker import process_document
        f.write("app.worker imported successfully\n")
    except Exception:
        traceback.print_exc(file=f)
