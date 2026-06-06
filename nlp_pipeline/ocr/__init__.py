# ocr/__init__.py
from .pdf_extractor import extract_text_from_pdf
from .image_ocr import extract_text_from_image

__all__ = ["extract_text_from_pdf", "extract_text_from_image"]
