import os
import magic  # python-magic library
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError


def is_valid_pdf(file_path, filename):
    """
    Check if a file is a valid PDF by:
    1. Verifying the extension is .pdf
    2. Checking the file header/magic number
    3. Attempting to parse the PDF content
    """
    if not os.path.exists(file_path):
        return False, "Folder does not exist"

    # Check 1: File extension is .pdf
    if not filename.lower().endswith(".pdf"):
        return False, "File does not have .pdf extension"

    file_path = os.path.join(file_path, filename)
    # Check if file exists
    if not os.path.exists(file_path):
        return False, "File does not exist"

    try:
        # Check 2: Verify file is actually a PDF by magic number
        file_type = magic.from_file(file_path, mime=True)
        if file_type != "application/pdf":
            return False, f"File is not a PDF (detected as: {file_type})"

        # Check 3: Try to read the PDF to check for corruption
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            # Try reading some basic info
            num_pages = len(reader.pages)
            if num_pages == 0:
                return True, "PDF is valid but has no pages"
            # Try reading first page text as additional check
            try:
                _ = reader.pages[0].extract_text()
            except:
                pass  # Some PDFs might not have extractable text but are still valid

        return True, "PDF is valid"

    except PdfReadError as e:
        return False, f"PDF appears corrupted: {str(e)}"
    except Exception as e:
        return False, f"Error validating PDF: {str(e)}"


# Example usage
# file_path = "soa.pdf"
# is_valid, message = is_valid_pdf(file_path)
# print(f"File: {file_path}")
# print(f"Is valid PDF: {is_valid}")
# print(f"Message: {message}")
