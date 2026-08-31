# -*- coding: utf-8 -*-
"""
intelligent_extraction_engine.py — Universal Multi-Format Extraction Coordinator
Routes PDF, XLSX, DOCX, TXT to specialized engines and applies confidence scoring.
"""

from pathlib import Path
from typing import Dict, Any
from drive_integration.pdf_extraction_engine import PDFExtractionEngine
from drive_integration.xlsx_extraction_engine import XLSXExtractionEngine

logger = __import__("logging").getLogger("nexa.extract.coordinator")


class ExtractionEngine:
    def __init__(self):
        self.pdf_engine = PDFExtractionEngine()
        self.xlsx_engine = XLSXExtractionEngine()

    def extract_from_file(self, file_path: Path) -> Dict[str, Any]:
        ext = file_path.suffix.lower()
        if ext == '.pdf':
            return self.pdf_engine.extract_text(file_path)
        elif ext in ('.xlsx', '.xls', '.csv'):
            res = self.xlsx_engine.extract_sheets_and_tables(file_path)
            return {
                "text": res.get("raw_text", ""),
                "sheets": res.get("sheets", {}),
                "confidence": res.get("confidence", 0.0),
                "success": res.get("success", False)
            }
        elif ext in ('.docx', '.doc'):
            try:
                import docx
                doc = docx.Document(str(file_path))
                text = "\\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                return {"text": text, "confidence": 92.0, "success": bool(text)}
            except Exception:
                return {"text": "", "confidence": 0.0, "success": False}
        elif ext in ('.txt', '.md', '.json'):
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
                return {"text": text, "confidence": 100.0, "success": bool(text)}
            except Exception:
                return {"text": "", "confidence": 0.0, "success": False}

        return {"text": "", "confidence": 0.0, "success": False, "message": f"Unsupported format: {ext}"}
