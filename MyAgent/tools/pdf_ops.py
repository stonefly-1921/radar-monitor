"""
PDF read tool using PyPDF2 (for text-based PDFs) or Tesseract OCR (for scanned PDFs).

PDF tools are delay-loaded to avoid triggering numpy compatibility issues
(pytesseract -> pandas -> numexpr -> numpy 2.x ABI crash).
PyPDF2 and pytesseract are only imported when the tool is actually executed.
"""
import os
import sys
from .base import Tool

# Lazy availability flags (checked on first use, not at import time)
_PYPDF2_AVAILABLE = None
_PYTESSERACT_AVAILABLE = None


def _is_pypdf2_available():
    """Check PyPDF2 availability lazily."""
    global _PYPDF2_AVAILABLE
    if _PYPDF2_AVAILABLE is None:
        try:
            from PyPDF2 import PdfReader  # noqa: F401
            _PYPDF2_AVAILABLE = True
        except Exception:
            _PYPDF2_AVAILABLE = False
    return _PYPDF2_AVAILABLE


def _is_pytesseract_available():
    """Check pytesseract availability lazily."""
    global _PYTESSERACT_AVAILABLE
    if _PYTESSERACT_AVAILABLE is None:
        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401
            from pdf2image import convert_from_path  # noqa: F401
            _PYTESSERACT_AVAILABLE = True
        except Exception:
            _PYTESSERACT_AVAILABLE = False
    return _PYTESSERACT_AVAILABLE


class PdfReadTool(Tool):
    """Read text content from PDF files."""
    name = "pdf_read"
    description = "读取 PDF 文件的文字内容（支持文字型 PDF 和扫描件 OCR）"
    parameters = [
        {
            "name": "path",
            "type": "string",
            "required": True,
            "description": "PDF 文件路径"
        },
        {
            "name": "max_chars",
            "type": "int",
            "required": False,
            "description": "最大读取字符数（默认 50000）"
        }
    ]

    def execute(self, **kwargs):
        path = kwargs.get("path", "")
        max_chars = kwargs.get("max_chars", 50000)

        if not path:
            return {"success": False, "error": "缺少 path 参数"}

        if not os.path.exists(path):
            return {"success": False, "error": f"文件不存在: {path}"}

        if not path.lower().endswith(".pdf"):
            return {"success": False, "error": "不是 PDF 文件"}

        if not _is_pypdf2_available():
            return {
                "success": False,
                "error": "PyPDF2 未安装。请运行: pip install installers/python_wheels/PyPDF2-3.0.1-py3-none-any.whl"
            }

        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            total_pages = len(reader.pages)
            all_text = []

            # First pass: try to extract text directly (fast, for text-based PDFs)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    all_text.append(f"[第{page_num+1}页]\n{text}")

            if all_text:
                # Text-based PDF - success
                full_text = "\n".join(all_text)
                if len(full_text) > max_chars:
                    full_text = full_text[:max_chars] + f"\n\n[...截断，原始长度 {len(full_text)} 字符]"
                return {
                    "success": True,
                    "text": full_text,
                    "pages": total_pages,
                    "method": "pyPdf2",
                    "length": len(full_text)
                }
            else:
                # No text extracted - likely a scanned PDF
                # Try OCR if pytesseract is available
                if _is_pytesseract_available():
                    ocr_result = self._ocr_pdf(path, max_chars)
                    return ocr_result
                else:
                    return {
                        "success": False,
                        "error": (
                            "此 PDF 为扫描件（无文字层）。"
                            "请安装 Tesseract OCR 和相关依赖：\n"
                            "1. 运行 installers/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe\n"
                            "2. 将 chi_sim.traineddata 复制到 Tesseract 安装目录的 tessdata/ 文件夹\n"
                            "3. 安装 Python 包: pip install Pillow pdf2image pytesseract"
                        )
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"读取 PDF 失败: {str(e)}"
            }

    def _ocr_pdf(self, pdf_path, max_chars):
        """
        OCR a scanned PDF using Tesseract.
        pytesseract / pdf2image imports are deferred to avoid numpy crash
        at tool registry initialization time.
        """
        try:
            import pytesseract
            from PIL import Image
            from pdf2image import convert_from_path

            pages = convert_from_path(pdf_path, dpi=200)
            text_pages = []

            for i, page_image in enumerate(pages):
                text = pytesseract.image_to_string(page_image, lang='chi_sim+eng')
                text_pages.append(text)
                if len("\n".join(text_pages)) > max_chars:
                    break

            full_text = "\n\n".join([f"[第{i+1}页]\n{t}" for i, t in enumerate(text_pages)])
            return {
                "success": True,
                "text": full_text,
                "pages": len(pages),
                "method": "ocr",
                "length": len(full_text)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"OCR 失败: {str(e)}"
            }

    def validate(self, params):
        if "path" not in params:
            return False, "缺少必需参数: path"
        return True, None


def register_tools(registry):
    """Register PDF tools with the registry."""
    registry.register(PdfReadTool())