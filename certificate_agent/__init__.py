"""Automated Certificate Generation Agent package.

Provides end-to-end automated mail merge between student data in Excel
and reference certificate templates (PDF or Image) with precision vector overlay,
auto-fitting typography, multi-stage field detection, and quality verification.
"""

__version__ = "1.0.0"
__author__ = "Antigravity AI"

from .detector import FileDetector
from .excel_reader import ExcelReader, StudentRecord
from .template_analyzer import TemplateAnalyzer, TemplateInfo, DynamicField
from .generator import CertificateGenerator, GenerationResult
from .validator import CertificateValidator, ValidationReport
from .report_generator import ReportGenerator

__all__ = [
    "FileDetector",
    "ExcelReader",
    "StudentRecord",
    "TemplateAnalyzer",
    "TemplateInfo",
    "DynamicField",
    "CertificateGenerator",
    "GenerationResult",
    "CertificateValidator",
    "ValidationReport",
    "ReportGenerator",
]
