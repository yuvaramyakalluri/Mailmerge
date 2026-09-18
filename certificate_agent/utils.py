"""Utility functions for filename sanitization, font metrics, and color calculations."""
import re
from pathlib import Path
from typing import Tuple, Optional
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

from .config import (
    WINDOWS_INVALID_CHARS_REGEX,
    MIN_NAME_FONT_SIZE,
    MIN_REGNO_FONT_SIZE,
)

# Reserved Windows file names
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_filename(name: str, max_length: int = 120) -> str:
    """Sanitizes a string to make it safe for Windows and Unix file systems.
    
    Replaces illegal characters (\\ / : * ? \" < > |) with underscores,
    collapses multiple spaces/underscores, strips trailing dots, and ensures
    reserved names are not used.
    """
    if not name:
        return "unnamed"
        
    # Replace illegal characters with underscore
    cleaned = WINDOWS_INVALID_CHARS_REGEX.sub("_", name)
    
    # Replace whitespace characters with underscore
    cleaned = re.sub(r"\s+", "_", cleaned)
    
    # Collapse multiple consecutive underscores
    cleaned = re.sub(r"_+", "_", cleaned)
    
    # Strip leading/trailing dots and underscores
    cleaned = cleaned.strip(" ._")
    
    # Check reserved Windows names
    base = cleaned.upper()
    if base in WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}_"
        
    if not cleaned:
        cleaned = "unnamed"
        
    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(" ._")
        
    return cleaned


def build_certificate_filename(reg_no: str, student_name: str) -> str:
    """Constructs a clean filename: <RegNo>_<StudentName>.pdf."""
    safe_reg = sanitize_filename(reg_no)
    safe_name = sanitize_filename(student_name)
    return f"{safe_reg}_{safe_name}.pdf"


def get_fitted_font_size(
    text: str,
    font_name: str,
    target_size: float,
    max_width: float,
    min_size: float = MIN_NAME_FONT_SIZE,
) -> Tuple[float, bool]:
    """Calculates fitted font size for text to fit within max_width.
    
    Returns:
        (font_size, needs_wrapping)
    """
    try:
        current_width = stringWidth(text, font_name, target_size)
    except Exception:
        # Default font width approximation if font not registered
        current_width = len(text) * target_size * 0.55

    if current_width <= max_width:
        return target_size, False

    # Scale down proportionally
    scale = max_width / current_width
    scaled_size = target_size * scale

    if scaled_size >= min_size:
        return round(scaled_size, 1), False

    # If even min_size exceeds width, indicates wrapping is recommended
    return min_size, True


def wrap_text_into_lines(text: str, max_words_per_line: int = 4) -> list[str]:
    """Wraps text into 2 balanced lines for names if needed."""
    words = text.split()
    if len(words) <= 2:
        return [text]
    mid = (len(words) + 1) // 2
    return [" ".join(words[:mid]), " ".join(words[mid:])]


def hex_to_rgb(hex_str: str) -> Tuple[float, float, float]:
    """Converts hex string like '#FCFAF5' to normalized RGB tuple (0.0 - 1.0)."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return r, g, b
