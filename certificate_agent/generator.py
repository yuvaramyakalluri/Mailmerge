"""PDF generation engine with vector overlay, auto-fitting typography, and design preservation."""
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from PIL import Image, ImageDraw, ImageFont
import pypdf
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from .excel_reader import StudentRecord
from .template_analyzer import TemplateInfo, DynamicField, RedactionBox
from .utils import get_fitted_font_size, wrap_text_into_lines, hex_to_rgb


@dataclass
class GenerationResult:
    """Outcome of generating a single student certificate."""
    reg_no: str
    name: str
    status: str  # 'Success', 'Failed'
    output_file: str
    file_path: Optional[Path] = None
    error_message: Optional[str] = None


class CertificateGenerator:
    """Generates individual PDF certificates from student records and template metadata."""

    def __init__(self, template_info: TemplateInfo, output_dir: Path):
        self.template_info = template_info
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self, students: List[StudentRecord]) -> List[GenerationResult]:
        """Generates certificates for all provided student records."""
        results: List[GenerationResult] = []
        for student in students:
            res = self.generate_single(student)
            results.append(res)
        return results

    def generate_single(self, student: StudentRecord) -> GenerationResult:
        """Generates an individual certificate PDF for one student."""
        out_path = self.output_dir / student.safe_filename

        try:
            if self.template_info.template_type == "pdf":
                self._generate_pdf_overlay(student, out_path)
            else:
                self._generate_image_overlay(student, out_path)

            return GenerationResult(
                reg_no=student.reg_no,
                name=student.name,
                status="Success",
                output_file=student.safe_filename,
                file_path=out_path,
            )
        except Exception as e:
            return GenerationResult(
                reg_no=student.reg_no,
                name=student.name,
                status="Failed",
                output_file=student.safe_filename,
                error_message=str(e),
            )

    def _clean_content_stream(self, page: pypdf.PageObject, student: StudentRecord) -> bool:
        """Cleans placeholder text and updates embedded RegNo in the PDF content stream.
        
        Returns True if content stream was modified.
        """
        try:
            contents = page.get_contents()
            if contents is None:
                return False

            if hasattr(contents, "get_data"):
                raw_bytes = contents.get_data()
            elif isinstance(contents, list) and contents:
                raw_bytes = contents[0].get_data()
            else:
                return False

            content_str = raw_bytes.decode("latin1", errors="ignore")
            modified = False

            # Replace standalone Name placeholders with empty string
            # e.g. ({{NAME}}) Tj -> () Tj
            name_pats = [
                r"\(\{\{\s*NAME\s*\}\}\)",
                r"\(\[\s*NAME\s*\]\)",
                r"\(\<\s*NAME\s*\>\)",
                r"\(\{\s*NAME\s*\}\)",
                r"\(\{\{\s*student_name\s*\}\}\)",
            ]
            for np in name_pats:
                if re.search(np, content_str, re.IGNORECASE):
                    content_str = re.sub(np, "()", content_str, flags=re.IGNORECASE)
                    modified = True

            # If Reg No is embedded inside a string (e.g. "Registration No: {{REG_NO}}")
            # Replace the placeholder directly with student.reg_no
            reg_embedded_pats = [
                r"\{\{\s*REG_?NO\s*\}\}",
                r"\{\{\s*REG\s+NO\s*\}\}",
                r"\[\s*REG_?NO\s*\]",
                r"\[\s*REG\s+NO\s*\]",
                r"\{\s*REG_?NO\s*\}",
            ]
            for rp in reg_embedded_pats:
                if re.search(rp, content_str, re.IGNORECASE):
                    content_str = re.sub(rp, student.reg_no, content_str, flags=re.IGNORECASE)
                    modified = True

            # For table layouts (e.g. sample_data.pdf), remove sample data rows from stream
            if self.template_info.is_table_layout:
                def replace_table_data(m):
                    txt = m.group(0)
                    if "REG" in txt or "NAME" in txt:
                        return txt
                    return "() TJ" if "TJ" in txt else "() Tj"

                content_str = re.sub(r"\[\([^)]+\)[^]]*\]\s*TJ", replace_table_data, content_str)
                content_str = re.sub(r"\([^)]+\)\s*Tj", replace_table_data, content_str)
                modified = True

            if modified:
                new_obj = pypdf.generic.DecodedStreamObject()
                new_obj.set_data(content_str.encode("latin1"))
                page[pypdf.generic.NameObject("/Contents")] = new_obj
                return True

        except Exception:
            pass

        return False

    def _generate_pdf_overlay(self, student: StudentRecord, out_path: Path):
        """Generates a lossless vector overlay PDF and merges with original template."""
        width = self.template_info.width
        height = self.template_info.height

        template_reader = pypdf.PdfReader(str(self.template_info.file_path))
        template_page = template_reader.pages[0]

        # Clean placeholders from content stream so text doesn't clash
        stream_modified = self._clean_content_stream(template_page, student)

        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(width, height))

        # Render redaction boxes (only if not cleanly replaced in content stream or if table layout)
        if self.template_info.is_table_layout or not stream_modified:
            for rbox in self.template_info.redaction_boxes:
                r, g, b = hex_to_rgb(rbox.bg_color)
                can.setFillColor(colors.Color(r, g, b))
                can.rect(rbox.x, rbox.y, rbox.width, rbox.height, fill=1, stroke=0)

        # Render Reg No if it wasn't already handled directly by stream replacement
        # (Or if it is a table layout)
        reg_field = self.template_info.fields.get("reg_no")
        if reg_field:
            # If not modified in stream or if table layout
            if self.template_info.is_table_layout or not stream_modified:
                r, g, b = hex_to_rgb(reg_field.font_color)
                can.setFillColor(colors.Color(r, g, b))
                font_sz, _ = get_fitted_font_size(
                    student.reg_no,
                    reg_field.font_name,
                    reg_field.font_size,
                    reg_field.max_width,
                    min_size=10.0,
                )
                can.setFont(reg_field.font_name, font_sz)

                if reg_field.alignment == "center":
                    can.drawCentredString(reg_field.x, reg_field.y, student.reg_no)
                else:
                    can.drawString(reg_field.x, reg_field.y, student.reg_no)

        # Render Student Name with auto-fit and wrapping protection
        name_field = self.template_info.fields.get("name")
        if name_field:
            r, g, b = hex_to_rgb(name_field.font_color)
            can.setFillColor(colors.Color(r, g, b))

            fitted_size, needs_wrap = get_fitted_font_size(
                student.name,
                name_field.font_name,
                name_field.font_size,
                name_field.max_width,
                min_size=14.0,
            )

            if not needs_wrap:
                can.setFont(name_field.font_name, fitted_size)
                if name_field.alignment == "center":
                    can.drawCentredString(name_field.x, name_field.y, student.name)
                else:
                    can.drawString(name_field.x, name_field.y, student.name)
            else:
                # Wrap into 2 balanced lines
                lines = wrap_text_into_lines(student.name)
                line_spacing = fitted_size * 1.15
                can.setFont(name_field.font_name, fitted_size)
                start_y = name_field.y + (line_spacing / 2.0)
                for i, line in enumerate(lines):
                    curr_y = start_y - (i * line_spacing)
                    if name_field.alignment == "center":
                        can.drawCentredString(name_field.x, curr_y, line)
                    else:
                        can.drawString(name_field.x, curr_y, line)

        # Render Secondary Fields if not modified in stream
        if not stream_modified:
            for sec in self.template_info.secondary_fields:
                if sec.redact_box:
                    r, g, b = hex_to_rgb(sec.redact_box.bg_color)
                    can.setFillColor(colors.Color(r, g, b))
                    can.rect(sec.redact_box.x, sec.redact_box.y, sec.redact_box.width, sec.redact_box.height, fill=1, stroke=0)

                r, g, b = hex_to_rgb(sec.font_color)
                can.setFillColor(colors.Color(r, g, b))
                can.setFont(sec.font_name, sec.font_size)
                can.drawRightString(width - 55, 55, f"Verify: cert-verify.org/id={student.reg_no}")

        can.save()
        packet.seek(0)

        # Merge overlay onto template page losslessly
        overlay_reader = pypdf.PdfReader(packet)
        overlay_page = overlay_reader.pages[0]
        template_page.merge_page(overlay_page)

        writer = pypdf.PdfWriter()
        writer.add_page(template_page)

        with open(out_path, "wb") as f:
            writer.write(f)

    def _generate_image_overlay(self, student: StudentRecord, out_path: Path):
        """Renders student information onto an image template and saves as PDF."""
        img = Image.open(self.template_info.file_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        try:
            name_font = ImageFont.truetype("arial.ttf", int(img.height * 0.045))
            reg_font = ImageFont.truetype("arial.ttf", int(img.height * 0.025))
        except Exception:
            name_font = ImageFont.load_default()
            reg_font = ImageFont.load_default()

        # Name
        name_field = self.template_info.fields.get("name")
        if name_field:
            draw.text(
                (int(name_field.x), int(img.height - name_field.y)),
                student.name,
                fill=(26, 43, 76),
                font=name_font,
                anchor="mm" if name_field.alignment == "center" else "la",
            )

        # Reg No
        reg_field = self.template_info.fields.get("reg_no")
        if reg_field:
            draw.text(
                (int(reg_field.x), int(img.height - reg_field.y)),
                student.reg_no,
                fill=(51, 51, 51),
                font=reg_font,
                anchor="mm" if reg_field.alignment == "center" else "la",
            )

        img.save(out_path, "PDF", resolution=150.0)
