"""Quality control and automated PDF verification engine."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pdfplumber
import pypdf
import pypdfium2 as pdfium

from .excel_reader import StudentRecord
from .generator import GenerationResult
from .template_analyzer import TemplateInfo
from .config import DEFAULT_PREVIEWS_DIR


@dataclass
class ValidationReport:
    """Detailed summary of the quality control verification."""
    total_expected: int
    total_generated: int
    total_passed: int
    total_failed: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    preview_images: List[Path] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.total_failed == 0 and self.total_passed == self.total_expected


class CertificateValidator:
    """Validates generated certificate PDFs against quality control criteria."""

    def __init__(self, template_info: TemplateInfo, output_dir: Path):
        self.template_info = template_info
        self.output_dir = Path(output_dir)
        self.previews_dir = self.output_dir / DEFAULT_PREVIEWS_DIR

    def validate(
        self,
        students: List[StudentRecord],
        results: List[GenerationResult],
        max_previews: int = 3,
    ) -> ValidationReport:
        """Runs automated verification on all generated certificates."""
        report = ValidationReport(
            total_expected=len(students),
            total_generated=len([r for r in results if r.status == "Success"]),
            total_passed=0,
            total_failed=0,
        )

        # Index students by reg_no
        student_map = {s.reg_no: s for s in students}

        # Check count match
        if report.total_generated != report.total_expected:
            report.errors.append(
                f"Generated certificate count ({report.total_generated}) does not match "
                f"expected student count ({report.total_expected})."
            )

        for res in results:
            if res.status != "Success" or not res.file_path or not res.file_path.exists():
                report.total_failed += 1
                report.errors.append(f"Failed generation for {res.reg_no}: {res.error_message or 'File missing'}")
                continue

            student = student_map.get(res.reg_no)
            if not student:
                report.total_failed += 1
                report.errors.append(f"Unknown student record in results: {res.reg_no}")
                continue

            # Verify file integrity and size
            try:
                sz = res.file_path.stat().st_size
                if sz < 1024:
                    report.total_failed += 1
                    report.errors.append(f"Certificate file is unusually small or empty: {res.output_file} ({sz} bytes)")
                    continue
            except Exception as e:
                report.total_failed += 1
                report.errors.append(f"Cannot read file {res.output_file}: {e}")
                continue

            # Inspect PDF structure and content
            try:
                with pdfplumber.open(res.file_path) as pdf:
                    if len(pdf.pages) != 1:
                        report.total_failed += 1
                        report.errors.append(f"{res.output_file} has {len(pdf.pages)} pages, expected exactly 1.")
                        continue

                    page = pdf.pages[0]
                    # Verify page dimensions match template
                    w_diff = abs(float(page.width) - self.template_info.width)
                    h_diff = abs(float(page.height) - self.template_info.height)
                    if w_diff > 3.0 or h_diff > 3.0:
                        report.total_failed += 1
                        report.errors.append(
                            f"{res.output_file} dimensions ({page.width}x{page.height}) do not match "
                            f"template ({self.template_info.width}x{self.template_info.height})."
                        )
                        continue

                    # Text verification
                    page_text = page.extract_text() or ""
                    # Check Reg No
                    if student.reg_no not in page_text:
                        report.total_failed += 1
                        report.errors.append(
                            f"{res.output_file} does not contain student Reg No '{student.reg_no}'."
                        )
                        continue

                    # Check Name: either full name or major tokens
                    name_tokens = [t.lower() for t in student.name.split() if len(t) > 1]
                    page_text_lower = page_text.lower()
                    if not all(tok in page_text_lower for tok in name_tokens):
                        # Warning / error
                        report.total_failed += 1
                        report.errors.append(
                            f"{res.output_file} does not contain student Name '{student.name}'."
                        )
                        continue

            except Exception as e:
                report.total_failed += 1
                report.errors.append(f"PDF validation error in {res.output_file}: {e}")
                continue

            # Passed all checks
            report.total_passed += 1

        # Render preview images for the first N successful certificates
        if max_previews > 0:
            self.previews_dir.mkdir(parents=True, exist_ok=True)
            successful = [r for r in results if r.status == "Success" and r.file_path]
            for r in successful[:max_previews]:
                try:
                    doc = pdfium.PdfDocument(str(r.file_path))
                    img = doc[0].render(scale=2).to_pil()
                    prev_path = self.previews_dir / f"{r.file_path.stem}_preview.png"
                    img.save(prev_path)
                    report.preview_images.append(prev_path)
                except Exception as e:
                    report.warnings.append(f"Failed to render preview for {r.output_file}: {e}")

        return report
