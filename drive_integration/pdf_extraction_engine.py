# -*- coding: utf-8 -*-
"""
pdf_extraction_engine.py — High-Fidelity Hybrid PDF Text & Table Extractor
"""

import io
import contextlib
from pathlib import Path
from typing import Dict, Any, List

logger = __import__("logging").getLogger("nexa.extract.pdf")


class PDFExtractionEngine:
    def extract_text(self, pdf_path: Path) -> Dict[str, Any]:
        """Extracts text, page count, and estimates extraction confidence."""
        if not pdf_path.exists():
            return {"text": "", "page_count": 0, "confidence": 0.0, "success": False}

        pages_text = []
        try:
            import PyPDF2
            with contextlib.redirect_stderr(io.StringIO()):
                reader = PyPDF2.PdfReader(str(pdf_path))
                page_count = len(reader.pages)
                for pg in reader.pages:
                    txt = pg.extract_text() or ""
                    if txt.strip():
                        pages_text.append(txt.strip())

            full_text = "\\n\\n".join(pages_text)
            confidence = 95.0 if len(full_text) > 200 else (70.0 if full_text else 0.0)
            return {
                "text": full_text,
                "page_count": page_count,
                "confidence": confidence,
                "success": bool(full_text)
            }
        except Exception as e:
            logger.warning("PDF extraction error (%s): %s", pdf_path.name, e)
            return {"text": "", "page_count": 0, "confidence": 0.0, "success": False, "error": str(e)}
