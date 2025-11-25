"""
PDF text extraction utility for Customer Vetting Software.
Extracts text content from uploaded PDF files.
"""

import pdfplumber as pp
from io import BytesIO


def extract_text_from_pdf(pdf_file):
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_file: Uploaded PDF file object (from Streamlit file_uploader)
        
    Returns:
        str: Extracted text content from the PDF
        
    Raises:
        Exception: If PDF cannot be read or processed
    """
    try:
        # Read the PDF file content
        pdf_bytes = pdf_file.read()
        pdf_stream = BytesIO(pdf_bytes)
        
        # Extract text from all pages
        text_content = ""
        with pp.open(pdf_stream) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_content += f"\n--- Page {page_num} ---\n"
                    text_content += page_text
        
        return text_content.strip()
    
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

