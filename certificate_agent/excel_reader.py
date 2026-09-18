"""Excel file reader and student data validator."""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import openpyxl

from .config import REG_NO_SYNONYMS, NAME_SYNONYMS
from .utils import build_certificate_filename, sanitize_filename


@dataclass
class StudentRecord:
    """Represents a validated student record from the Excel file."""
    reg_no: str
    name: str
    row_index: int
    safe_filename: str
    is_duplicate_regno: bool = False


class ExcelReader:
    """Reads and validates student records from Excel workbooks."""

    def __init__(self, excel_path: Path):
        self.excel_path = Path(excel_path)
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.excel_path}")

    @staticmethod
    def _normalize_header(header: Any) -> str:
        """Normalizes header string for comparison."""
        if header is None:
            return ""
        s = str(header).strip().lower()
        # Remove extra whitespace and special characters
        s = re.sub(r"[\t\r\n]+", " ", s)
        s = re.sub(r"\s+", " ", s)
        return s

    def _match_column(self, header: str, patterns: List[str]) -> bool:
        """Checks if a normalized header matches any of the synonym regexes."""
        for pat in patterns:
            if re.search(pat, header, re.IGNORECASE):
                return True
        return False

    def read_students(self) -> List[StudentRecord]:
        """Loads and parses the Excel workbook, identifying required student fields.
        
        Raises:
            ValueError: If required columns ('Reg No' or 'Name') cannot be found.
        """
        wb = openpyxl.load_workbook(self.excel_path, data_only=True)
        sheet = wb.active
        if sheet is None:
            raise ValueError(f"No active sheet found in Excel workbook: {self.excel_path.name}")

        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise ValueError(f"Excel workbook is completely empty: {self.excel_path.name}")

        # Find header row (usually row 0, but check first 5 rows in case of top banner)
        header_row_idx = -1
        reg_col_idx = -1
        name_col_idx = -1
        detected_headers: List[str] = []

        for r_idx in range(min(len(rows), 5)):
            row = rows[r_idx]
            if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                continue

            # Check if this row looks like a header
            temp_reg_idx = -1
            temp_name_idx = -1
            temp_headers = []

            for c_idx, cell in enumerate(row):
                norm_h = self._normalize_header(cell)
                temp_headers.append(norm_h)
                if temp_reg_idx == -1 and self._match_column(norm_h, REG_NO_SYNONYMS):
                    temp_reg_idx = c_idx
                elif temp_name_idx == -1 and self._match_column(norm_h, NAME_SYNONYMS):
                    temp_name_idx = c_idx

            if temp_reg_idx != -1 and temp_name_idx != -1:
                header_row_idx = r_idx
                reg_col_idx = temp_reg_idx
                name_col_idx = temp_name_idx
                detected_headers = [str(c) for c in row if c is not None]
                break

        if reg_col_idx == -1 or name_col_idx == -1:
            # Gather all columns found in first non-empty row for error message
            first_row_cols = [str(c).strip() for c in rows[0] if c is not None and str(c).strip()]
            err_msg = [
                f"Required columns 'Reg No' and 'Name' could not be found in {self.excel_path.name}.",
                f"Columns detected in file: {first_row_cols}",
                "Accepted 'Reg No' variations: Reg No, RegNo, Registration No, Roll No, Student ID",
                "Accepted 'Name' variations: Name, Student Name, Full Name, Candidate Name",
            ]
            raise ValueError("\n".join(err_msg))

        # Parse student data rows
        students: List[StudentRecord] = []
        seen_regnos: Dict[str, int] = {}

        for r_idx in range(header_row_idx + 1, len(rows)):
            row = rows[r_idx]
            if not row:
                continue

            # Extract Reg No
            reg_raw = row[reg_col_idx] if reg_col_idx < len(row) else None
            # Extract Name
            name_raw = row[name_col_idx] if name_col_idx < len(row) else None

            # Skip completely blank rows
            if (reg_raw is None or str(reg_raw).strip() == "") and \
               (name_raw is None or str(name_raw).strip() == ""):
                continue

            # Handle partially missing fields
            if reg_raw is None or str(reg_raw).strip() == "":
                # Warning: student has name but missing reg no
                continue
            if name_raw is None or str(name_raw).strip() == "":
                # Warning: student has reg no but missing name
                continue

            # Clean and format Reg No
            # Handle float representation (e.g. 202601.0 -> 202601)
            if isinstance(reg_raw, float) and reg_raw.is_integer():
                reg_str = str(int(reg_raw))
            else:
                reg_str = str(reg_raw).strip()

            # Clean and format Name
            name_str = " ".join(str(name_raw).strip().split())

            # Track duplicates
            is_dup = False
            if reg_str in seen_regnos:
                seen_regnos[reg_str] += 1
                is_dup = True
                safe_fname = build_certificate_filename(
                    f"{reg_str}_dup{seen_regnos[reg_str]}", name_str
                )
            else:
                seen_regnos[reg_str] = 1
                safe_fname = build_certificate_filename(reg_str, name_str)

            students.append(
                StudentRecord(
                    reg_no=reg_str,
                    name=name_str,
                    row_index=r_idx + 1,  # 1-indexed for user-friendly logs
                    safe_filename=safe_fname,
                    is_duplicate_regno=is_dup,
                )
            )

        wb.close()
        return students
