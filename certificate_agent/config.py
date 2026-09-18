"""Configuration settings, constants, and column synonym mappings for Certificate Agent."""
import re
from pathlib import Path

# Supported file extensions
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
TEMPLATE_EXTENSIONS = PDF_EXTENSIONS | IMAGE_EXTENSIONS

# Default folder names
DEFAULT_OUTPUT_DIR = "certificates"
DEFAULT_REPORT_FILENAME = "generation_report.csv"
DEFAULT_PREVIEWS_DIR = "previews"

# Column name synonyms (lowercased, stripped, punctuation-agnostic)
REG_NO_SYNONYMS = [
    r"^reg(\.?\s*no\.?)?$",
    r"^regno$",
    r"^reg_no$",
    r"^registration(\s*no\.?|\s*number)?$",
    r"^roll(\.?\s*no\.?)?$",
    r"^rollno$",
    r"^roll_number$",
    r"^student\s*id$",
    r"^id$",
    r"^regd(\.?\s*no\.?)?$",
    r"^regdno$",
    r"^ht\s*no$",
    r"^hall\s*ticket\s*(no)?$",
]

NAME_SYNONYMS = [
    r"^name$",
    r"^student\s*name$",
    r"^student_name$",
    r"^candidate\s*name$",
    r"^full\s*name$",
    r"^name\s*of\s*the\s*student$",
    r"^name\s*of\s*candidate$",
    r"^participant\s*name$",
]

# Dynamic field placeholder regex patterns
PLACEHOLDER_PATTERNS = {
    "name": [
        re.compile(r"\{\{\s*name\s*\}\}", re.IGNORECASE),
        re.compile(r"\{\{\s*student_name\s*\}\}", re.IGNORECASE),
        re.compile(r"\{\{\s*full_name\s*\}\}", re.IGNORECASE),
        re.compile(r"\[\s*name\s*\]", re.IGNORECASE),
        re.compile(r"\[\s*student\s*name\s*\]", re.IGNORECASE),
        re.compile(r"<\s*name\s*>", re.IGNORECASE),
        re.compile(r"<\s*student_name\s*>", re.IGNORECASE),
        re.compile(r"\{\s*name\s*\}", re.IGNORECASE),
        re.compile(r"\{\s*student_name\s*\}", re.IGNORECASE),
    ],
    "reg_no": [
        re.compile(r"\{\{\s*reg_?no\s*\}\}", re.IGNORECASE),
        re.compile(r"\{\{\s*reg\s+no\s*\}\}", re.IGNORECASE),
        re.compile(r"\{\{\s*registration_?no\s*\}\}", re.IGNORECASE),
        re.compile(r"\{\{\s*roll_?no\s*\}\}", re.IGNORECASE),
        re.compile(r"\[\s*reg_?no\s*\]", re.IGNORECASE),
        re.compile(r"\[\s*reg\s+no\s*\]", re.IGNORECASE),
        re.compile(r"\[\s*registration\s*no\s*\]", re.IGNORECASE),
        re.compile(r"<\s*reg_?no\s*>", re.IGNORECASE),
        re.compile(r"<\s*registration_?no\s*>", re.IGNORECASE),
        re.compile(r"\{\s*reg_?no\s*\}", re.IGNORECASE),
        re.compile(r"\{\s*reg\s+no\s*\}", re.IGNORECASE),
    ]
}

# Generic sample names used in templates
SAMPLE_NAME_PATTERNS = [
    re.compile(r"\bravi\s+kumar\b", re.IGNORECASE),
    re.compile(r"\bpriya\s+sharma\b", re.IGNORECASE),
    re.compile(r"\barjun\s+reddy\b", re.IGNORECASE),
    re.compile(r"\bjohn\s+doe\b", re.IGNORECASE),
    re.compile(r"\bjane\s+doe\b", re.IGNORECASE),
    re.compile(r"\bstudent\s+name\b", re.IGNORECASE),
    re.compile(r"\bcandidate\s+name\b", re.IGNORECASE),
]

SAMPLE_REGNO_PATTERNS = [
    re.compile(r"\b2026\d{2,6}\b"),
    re.compile(r"\b2025\d{2,6}\b"),
    re.compile(r"\b2024\d{2,6}\b"),
    re.compile(r"\b123456\b"),
]

# Windows invalid filename characters: \ / : * ? " < > |
WINDOWS_INVALID_CHARS_REGEX = re.compile(r'[\\/:*?"<>|]')

# Font sizing constraints
MIN_NAME_FONT_SIZE = 14.0  # Never shrink below 14pt for names
MIN_REGNO_FONT_SIZE = 10.0
MAX_TEXT_WIDTH_RATIO = 0.85  # Maximum portion of page width text may occupy
