"""Template analysis and intelligent dynamic field detection."""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pdfplumber
import pypdf
import pypdfium2 as pdfium
from PIL import Image

from .config import (
    PLACEHOLDER_PATTERNS,
    SAMPLE_NAME_PATTERNS,
    SAMPLE_REGNO_PATTERNS,
    IMAGE_EXTENSIONS,
    PDF_EXTENSIONS,
)
from .excel_reader import StudentRecord
from .utils import hex_to_rgb


@dataclass
class RedactionBox:
    """A rectangular area on the page that should be masked/cleared."""
    x: float
    y: float
    width: float
    height: float
    bg_color: str = "#FFFFFF"


@dataclass
class DynamicField:
    """Describes where and how a dynamic field should be rendered."""
    key: str  # 'name', 'reg_no', etc.
    x: float  # In PDF bottom-up points
    y: float  # Baseline y in PDF points
    width: float
    height: float
    alignment: str  # 'center', 'left', 'right'
    font_name: str
    font_size: float
    font_color: str  # Hex string
    bg_color: str  # Hex string
    max_width: float
    redact_box: Optional[RedactionBox] = None


@dataclass
class TemplateInfo:
    """Complete metadata and detected field locations for a certificate template."""
    file_path: Path
    template_type: str  # 'pdf' or 'image'
    width: float
    height: float
    fields: Dict[str, DynamicField] = field(default_factory=dict)
    redaction_boxes: List[RedactionBox] = field(default_factory=list)
    secondary_fields: List[DynamicField] = field(default_factory=list)
    is_table_layout: bool = False


class TemplateAnalyzer:
    """Analyzes a certificate template to detect dynamic field positions, typography, and background."""

    def __init__(self, template_path: Path):
        self.template_path = Path(template_path)
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_path}")
        self.ext = self.template_path.suffix.lower()

    def analyze(self, sample_students: Optional[List[StudentRecord]] = None) -> TemplateInfo:
        """Performs full template inspection and returns TemplateInfo."""
        if self.ext in PDF_EXTENSIONS:
            return self._analyze_pdf(sample_students)
        elif self.ext in IMAGE_EXTENSIONS:
            return self._analyze_image(sample_students)
        else:
            raise ValueError(f"Unsupported template format: {self.ext}")

    def _sample_bg_color(self, x: float, y_top: float, width: float, height: float, doc_w: float, doc_h: float) -> str:
        """Samples background color around a bounding box using pypdfium2 bitmap."""
        try:
            doc = pdfium.PdfDocument(str(self.template_path))
            # Render at 1.0 scale
            pil_img = doc[0].render(scale=1).to_pil().convert("RGB")
            
            # Sample 4 points just outside the bounding box (clamped)
            sample_points = [
                (max(0, int(x - 4)), min(pil_img.height - 1, int(y_top + height / 2.0))),
                (min(pil_img.width - 1, int(x + width + 4)), min(pil_img.height - 1, int(y_top + height / 2.0))),
                (min(pil_img.width - 1, int(x + width / 2.0)), max(0, int(y_top - 4))),
                (min(pil_img.width - 1, int(x + width / 2.0)), min(pil_img.height - 1, int(y_top + height + 4))),
            ]
            
            colors = [pil_img.getpixel(pt) for pt in sample_points]
            # Average color
            r_avg = sum(c[0] for c in colors) // len(colors)
            g_avg = sum(c[1] for c in colors) // len(colors)
            b_avg = sum(c[2] for c in colors) // len(colors)
            return f"#{r_avg:02X}{g_avg:02X}{b_avg:02X}"
        except Exception:
            return "#FFFFFF"

    def _analyze_pdf(self, sample_students: Optional[List[StudentRecord]] = None) -> TemplateInfo:
        """Analyzes vector and text layout of a PDF template."""
        with pdfplumber.open(self.template_path) as pdf:
            if not pdf.pages:
                raise ValueError(f"PDF template has no pages: {self.template_path.name}")
            page = pdf.pages[0]
            width = float(page.width)
            height = float(page.height)
            words = page.extract_words(extra_attrs=["fontname", "size"])

        # Check for Table-like layout (e.g. sample_data.pdf)
        table_layout = self._check_table_layout(words, width, height, sample_students)
        if table_layout:
            return table_layout

        # Stage 1: Explicit Placeholders (e.g. {{NAME}}, {{REG_NO}})
        fields: Dict[str, DynamicField] = {}
        redactions: List[RedactionBox] = []
        secondary: List[DynamicField] = []

        detected_name_words = []
        detected_reg_words = []

        for w in words:
            text = w["text"]
            # Check Name placeholders
            for pat in PLACEHOLDER_PATTERNS["name"]:
                if pat.search(text):
                    detected_name_words.append(w)
                    break

            # Check RegNo placeholders
            for pat in PLACEHOLDER_PATTERNS["reg_no"]:
                if pat.search(text):
                    if "verify" in text.lower() or "id=" in text.lower():
                        # Secondary verification ID placeholder
                        sec_field = self._build_field(
                            key="reg_no_verify",
                            word=w,
                            doc_w=width,
                            doc_h=height,
                            is_centered=False,
                            default_font="Helvetica",
                            default_size=w.get("size", 9.0),
                            default_color="#666666",
                        )
                        secondary.append(sec_field)
                    else:
                        detected_reg_words.append(w)
                    break

        # Stage 2: If no explicit placeholder for name/regno, check against sample students
        if sample_students and (not detected_name_words or not detected_reg_words):
            first_student = sample_students[0]
            for w in words:
                text_clean = w["text"].strip().upper()
                if not detected_reg_words and first_student.reg_no.upper() == text_clean:
                    detected_reg_words.append(w)
                if not detected_name_words:
                    # Match name tokens
                    name_tokens = [t.upper() for t in first_student.name.split() if len(t) > 1]
                    if text_clean in name_tokens:
                        detected_name_words.append(w)

        # Stage 3: Match against generic sample names
        if not detected_name_words:
            for w in words:
                for pat in SAMPLE_NAME_PATTERNS:
                    if pat.search(w["text"]):
                        detected_name_words.append(w)
                        break

        # Stage 4: Check labeled fields ("Name:", "Reg No:")
        if not detected_name_words or not detected_reg_words:
            for i, w in enumerate(words):
                w_text = w["text"].lower()
                if not detected_name_words and ("name:" in w_text or w_text == "name"):
                    if i + 1 < len(words):
                        detected_name_words.append(words[i + 1])
                if not detected_reg_words and ("reg" in w_text and ("no:" in w_text or "no" in w_text)):
                    if i + 1 < len(words):
                        detected_reg_words.append(words[i + 1])

        # Stage 5: Fallback layout heuristic (prominent area on certificate)
        if not detected_name_words:
            # Synthetic Name field in upper middle band (y = 55% from bottom)
            bg_col = self._sample_bg_color(width * 0.2, height * 0.4, width * 0.6, 40, width, height)
            fields["name"] = DynamicField(
                key="name",
                x=width / 2.0,
                y=height * 0.58,
                width=width * 0.6,
                height=35.0,
                alignment="center",
                font_name="Helvetica-Bold",
                font_size=28.0,
                font_color="#1A2B4C",
                bg_color=bg_col,
                max_width=width * 0.7,
            )
        else:
            # Combine detected name words
            w_first = detected_name_words[0]
            w_last = detected_name_words[-1]
            comb_x0 = min(w["x0"] for w in detected_name_words)
            comb_x1 = max(w["x1"] for w in detected_name_words)
            comb_top = min(w["top"] for w in detected_name_words)
            comb_bot = max(w["bottom"] for w in detected_name_words)

            font_sz = float(w_first.get("size", 28.0))
            # Determine alignment
            mid_x = (comb_x0 + comb_x1) / 2.0
            is_centered = abs(mid_x - width / 2.0) < (width * 0.15)
            align = "center" if is_centered else "left"
            target_x = (width / 2.0) if is_centered else comb_x0

            # Redaction box
            bg_col = self._sample_bg_color(comb_x0, comb_top, comb_x1 - comb_x0, comb_bot - comb_top, width, height)
            redact = RedactionBox(
                x=comb_x0 - 4,
                y=height - comb_bot - 2,
                width=(comb_x1 - comb_x0) + 8,
                height=(comb_bot - comb_top) + 4,
                bg_color=bg_col,
            )
            redactions.append(redact)

            fields["name"] = DynamicField(
                key="name",
                x=target_x,
                y=height - comb_bot + 2.0,
                width=comb_x1 - comb_x0,
                height=comb_bot - comb_top,
                alignment=align,
                font_name="Helvetica-Bold",
                font_size=max(font_sz, 22.0),
                font_color="#1A2B4C",
                bg_color=bg_col,
                max_width=width * 0.7,
                redact_box=redact,
            )

        if not detected_reg_words:
            # Synthetic RegNo field below name (y = 48% from bottom)
            bg_col = self._sample_bg_color(width * 0.25, height * 0.5, width * 0.5, 25, width, height)
            fields["reg_no"] = DynamicField(
                key="reg_no",
                x=width / 2.0,
                y=height * 0.50,
                width=width * 0.4,
                height=20.0,
                alignment="center",
                font_name="Helvetica",
                font_size=14.0,
                font_color="#333333",
                bg_color=bg_col,
                max_width=width * 0.5,
            )
        else:
            w_first = detected_reg_words[0]
            comb_x0 = min(w["x0"] for w in detected_reg_words)
            comb_x1 = max(w["x1"] for w in detected_reg_words)
            comb_top = min(w["top"] for w in detected_reg_words)
            comb_bot = max(w["bottom"] for w in detected_reg_words)

            font_sz = float(w_first.get("size", 14.0))
            mid_x = (comb_x0 + comb_x1) / 2.0
            is_centered = abs(mid_x - width / 2.0) < (width * 0.15)
            align = "center" if is_centered else "left"
            target_x = (width / 2.0) if is_centered else comb_x0

            bg_col = self._sample_bg_color(comb_x0, comb_top, comb_x1 - comb_x0, comb_bot - comb_top, width, height)
            redact = RedactionBox(
                x=comb_x0 - 4,
                y=height - comb_bot - 2,
                width=(comb_x1 - comb_x0) + 8,
                height=(comb_bot - comb_top) + 4,
                bg_color=bg_col,
            )
            redactions.append(redact)

            fields["reg_no"] = DynamicField(
                key="reg_no",
                x=target_x,
                y=height - comb_bot + 2.0,
                width=comb_x1 - comb_x0,
                height=comb_bot - comb_top,
                alignment=align,
                font_name="Helvetica",
                font_size=max(font_sz, 12.0),
                font_color="#333333",
                bg_color=bg_col,
                max_width=width * 0.5,
                redact_box=redact,
            )

        return TemplateInfo(
            file_path=self.template_path,
            template_type="pdf",
            width=width,
            height=height,
            fields=fields,
            redaction_boxes=redactions,
            secondary_fields=secondary,
            is_table_layout=False,
        )

    def _check_table_layout(
        self,
        words: List[Dict[str, Any]],
        width: float,
        height: float,
        sample_students: Optional[List[StudentRecord]],
    ) -> Optional[TemplateInfo]:
        """Detects if the template is a table export (e.g. sample_data.pdf) with REG NO and NAME columns."""
        reg_header = None
        name_header = None

        for i, w in enumerate(words):
            t = w["text"].upper()
            if t == "REG" and i + 1 < len(words) and words[i + 1]["text"].upper() == "NO":
                reg_header = (w["x0"], w["top"], words[i + 1]["x1"], words[i + 1]["bottom"])
            elif t == "REG NO" or t == "REG_NO" or t == "REGNO":
                reg_header = (w["x0"], w["top"], w["x1"], w["bottom"])
            elif t == "NAME" or t == "STUDENT NAME":
                name_header = (w["x0"], w["top"], w["x1"], w["bottom"])

        if not (reg_header and name_header):
            return None

        # Table headers detected!
        # Find row 1 and subsequent rows to redact
        # Sample Reg No row 1
        data_words = [w for w in words if w["top"] > reg_header[3]]
        if not data_words:
            return None

        min_data_top = min(w["top"] for w in data_words)
        max_data_bot = max(w["bottom"] for w in data_words)
        max_data_x1 = max(w["x1"] for w in data_words)

        # Reg No column X is around reg_header[0]
        # Name column X is around name_header[0]
        # Row 1 baseline:
        row1_words = [w for w in data_words if abs(w["top"] - min_data_top) < 6.0]
        row1_bot = max(w["bottom"] for w in row1_words)

        # Create a redaction box that covers all rows from row 1 down to the last row
        redaction = RedactionBox(
            x=reg_header[0] - 5,
            y=height - max_data_bot - 5,
            width=(max_data_x1 - reg_header[0]) + 20,
            height=(max_data_bot - min_data_top) + 10,
            bg_color="#FFFFFF",
        )

        fields: Dict[str, DynamicField] = {
            "reg_no": DynamicField(
                key="reg_no",
                x=reg_header[0],
                y=height - row1_bot + 2.5,
                width=reg_header[2] - reg_header[0],
                height=15.0,
                alignment="left",
                font_name="Helvetica",
                font_size=11.0,
                font_color="#000000",
                bg_color="#FFFFFF",
                max_width=name_header[0] - reg_header[0] - 10,
            ),
            "name": DynamicField(
                key="name",
                x=name_header[0],
                y=height - row1_bot + 2.5,
                width=150.0,
                height=15.0,
                alignment="left",
                font_name="Helvetica",
                font_size=11.0,
                font_color="#000000",
                bg_color="#FFFFFF",
                max_width=width - name_header[0] - 50,
            ),
        }

        return TemplateInfo(
            file_path=self.template_path,
            template_type="pdf",
            width=width,
            height=height,
            fields=fields,
            redaction_boxes=[redaction],
            secondary_fields=[],
            is_table_layout=True,
        )

    def _build_field(
        self,
        key: str,
        word: Dict[str, Any],
        doc_w: float,
        doc_h: float,
        is_centered: bool,
        default_font: str,
        default_size: float,
        default_color: str,
    ) -> DynamicField:
        """Helper to build DynamicField from a word dictionary."""
        w_x0 = word["x0"]
        w_x1 = word["x1"]
        w_top = word["top"]
        w_bot = word["bottom"]

        mid_x = (w_x0 + w_x1) / 2.0
        target_x = (doc_w / 2.0) if is_centered else w_x0
        align = "center" if is_centered else "left"

        bg_col = self._sample_bg_color(w_x0, w_top, w_x1 - w_x0, w_bot - w_top, doc_w, doc_h)
        redact = RedactionBox(
            x=w_x0 - 2,
            y=doc_h - w_bot - 2,
            width=(w_x1 - w_x0) + 4,
            height=(w_bot - w_top) + 4,
            bg_color=bg_col,
        )

        return DynamicField(
            key=key,
            x=target_x,
            y=doc_h - w_bot + 2.0,
            width=w_x1 - w_x0,
            height=w_bot - w_top,
            alignment=align,
            font_name=default_font,
            font_size=default_size,
            font_color=default_color,
            bg_color=bg_col,
            max_width=doc_w * 0.6,
            redact_box=redact,
        )

    def _analyze_image(self, sample_students: Optional[List[StudentRecord]] = None) -> TemplateInfo:
        """Analyzes an image template (.png, .jpg)."""
        with Image.open(self.template_path) as img:
            width, height = img.size

        # Default certificate layout for image
        fields: Dict[str, DynamicField] = {
            "name": DynamicField(
                key="name",
                x=width / 2.0,
                y=height * 0.55,
                width=width * 0.7,
                height=height * 0.08,
                alignment="center",
                font_name="Helvetica-Bold",
                font_size=height * 0.05,
                font_color="#1A2B4C",
                bg_color="#FFFFFF",
                max_width=width * 0.8,
            ),
            "reg_no": DynamicField(
                key="reg_no",
                x=width / 2.0,
                y=height * 0.45,
                width=width * 0.5,
                height=height * 0.05,
                alignment="center",
                font_name="Helvetica",
                font_size=height * 0.03,
                font_color="#333333",
                bg_color="#FFFFFF",
                max_width=width * 0.6,
            ),
        }

        return TemplateInfo(
            file_path=self.template_path,
            template_type="image",
            width=float(width),
            height=float(height),
            fields=fields,
            redaction_boxes=[],
            secondary_fields=[],
            is_table_layout=False,
        )
