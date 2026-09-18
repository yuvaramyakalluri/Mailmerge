"""Automatic file detection for student data and certificate templates."""
import os
import re
from pathlib import Path
from typing import Optional, List, Tuple

from .config import (
    EXCEL_EXTENSIONS,
    PDF_EXTENSIONS,
    IMAGE_EXTENSIONS,
    TEMPLATE_EXTENSIONS,
    DEFAULT_OUTPUT_DIR,
)


class FileDetector:
    """Detects student Excel files and certificate templates from a working directory."""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir).resolve()

    def detect_excel_file(self, explicit_path: Optional[str] = None) -> Path:
        """Finds the student Excel spreadsheet.
        
        If explicit_path is provided and exists, uses it.
        Otherwise scans root_dir for *.xlsx and *.xls files (ignoring ~$ temporary files).
        """
        if explicit_path:
            p = Path(explicit_path)
            if not p.is_absolute():
                p = self.root_dir / p
            if p.exists() and p.is_file():
                return p
            raise FileNotFoundError(f"Specified Excel file not found: {explicit_path}")

        candidates: List[Path] = []
        for f in self.root_dir.iterdir():
            if f.is_file() and f.suffix.lower() in EXCEL_EXTENSIONS:
                if not f.name.startswith("~$"):  # Ignore Office lock files
                    candidates.append(f)

        if not candidates:
            raise FileNotFoundError(
                f"No Excel file (.xlsx, .xls) found in directory: {self.root_dir}\n"
                "Please ensure your student spreadsheet is placed in this folder."
            )

        if len(candidates) == 1:
            return candidates[0]

        # Prioritize files containing 'student' or 'data' or 'candidate'
        scored = []
        for c in candidates:
            score = 0
            name_lower = c.name.lower()
            if "student" in name_lower:
                score += 10
            if "data" in name_lower:
                score += 5
            if "reg" in name_lower:
                score += 3
            # Prefer newer file if scores equal
            mtime = c.stat().st_mtime
            scored.append((score, mtime, c))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return scored[0][2]

    def detect_template_file(
        self,
        explicit_path: Optional[str] = None,
        excel_path: Optional[Path] = None,
    ) -> Path:
        """Finds the certificate template file (PDF or Image).
        
        Excludes the output directory (certificates/), previews, report files,
        and intermediate rendered test files.
        Prioritizes files matching 'certificate', 'template', 'sample'.
        """
        if explicit_path:
            p = Path(explicit_path)
            if not p.is_absolute():
                p = self.root_dir / p
            if p.exists() and p.is_file():
                return p
            raise FileNotFoundError(f"Specified template file not found: {explicit_path}")

        candidates: List[Path] = []
        output_dir_name = Path(DEFAULT_OUTPUT_DIR).name.lower()

        for f in self.root_dir.iterdir():
            if not f.is_file():
                continue
            # Ignore files in output or preview directory
            if output_dir_name in str(f.parent).lower():
                continue
            ext = f.suffix.lower()
            if ext not in TEMPLATE_EXTENSIONS:
                continue

            name_lower = f.name.lower()
            # Ignore test / preview scripts and images
            if any(ign in name_lower for ign in ["preview", "_rendered", "test_"]):
                continue
            if name_lower.endswith("_report.csv"):
                continue

            candidates.append(f)

        if not candidates:
            raise FileNotFoundError(
                f"No certificate template (.pdf, .png, .jpg) found in directory: {self.root_dir}\n"
                "Please place a certificate sample or template file in this folder."
            )

        if len(candidates) == 1:
            return candidates[0]

        # Score candidates intelligently:
        # Highest priority: contains 'certificate'
        # Second priority: contains 'template'
        # Third priority: contains 'sample'
        # Format priority: PDF > PNG > JPG
        scored = []
        for c in candidates:
            score = 0
            name_lower = c.name.lower()
            if "cert" in name_lower or "certificate" in name_lower:
                score += 50
            if "template" in name_lower:
                score += 30
            if "sample" in name_lower:
                score += 15
            if c.suffix.lower() == ".pdf":
                score += 10
            elif c.suffix.lower() in IMAGE_EXTENSIONS:
                score += 5

            mtime = c.stat().st_mtime
            scored.append((score, mtime, c))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return scored[0][2]

    def detect_all(
        self,
        explicit_excel: Optional[str] = None,
        explicit_template: Optional[str] = None,
    ) -> Tuple[Path, Path]:
        """Detects both Excel and Template files, returning (excel_path, template_path)."""
        excel_path = self.detect_excel_file(explicit_excel)
        template_path = self.detect_template_file(explicit_template, excel_path=excel_path)
        return excel_path, template_path
