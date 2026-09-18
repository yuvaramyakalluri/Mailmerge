"""Main autonomous workflow orchestrator for Certificate Generation Agent."""
import argparse
import sys
from pathlib import Path
from typing import Optional

from .detector import FileDetector
from .excel_reader import ExcelReader
from .template_analyzer import TemplateAnalyzer
from .generator import CertificateGenerator
from .validator import CertificateValidator
from .report_generator import ReportGenerator
from .config import DEFAULT_OUTPUT_DIR


class CertificateAgent:
    """Production-grade certificate mail-merge agent."""

    def __init__(
        self,
        working_dir: Optional[str] = None,
        excel_path: Optional[str] = None,
        template_path: Optional[str] = None,
        output_dir: Optional[str] = None,
        preview_count: int = 3,
    ):
        self.working_dir = Path(working_dir or ".").resolve()
        self.explicit_excel = excel_path
        self.explicit_template = template_path
        self.output_dir = Path(output_dir or (self.working_dir / DEFAULT_OUTPUT_DIR)).resolve()
        self.preview_count = preview_count

    def run(self) -> bool:
        """Executes the complete autonomous 10-step certificate generation workflow."""
        print("\n" + "=" * 65)
        print("  AUTOMATED CERTIFICATE GENERATION AGENT (ANTIGRAVITY CLI)")
        print("=" * 65)
        print(f"Working Directory: {self.working_dir}")

        # Step 1 & 2: Detect input files
        print("\n[Step 1/10] Scanning working directory for input files...")
        detector = FileDetector(self.working_dir)
        try:
            excel_file, template_file = detector.detect_all(
                explicit_excel=self.explicit_excel,
                explicit_template=self.explicit_template,
            )
        except Exception as e:
            print(f"\n[ERROR] File detection failed: {e}", file=sys.stderr)
            return False

        print(f"[Step 2/10] Identified files:")
        print(f"  • Excel Student Data:   {excel_file.name}")
        print(f"  • Certificate Template: {template_file.name}")

        # Step 3 & 4: Read and validate student data
        print("\n[Step 3/10] Reading student spreadsheet...")
        try:
            reader = ExcelReader(excel_file)
            students = reader.read_students()
        except Exception as e:
            print(f"\n[ERROR] Failed to read Excel student data: {e}", file=sys.stderr)
            return False

        print(f"[Step 4/10] Validated student records: {len(students)} valid students found.")
        if not students:
            print("[ERROR] No valid student records found in the spreadsheet.", file=sys.stderr)
            return False

        dup_count = sum(1 for s in students if s.is_duplicate_regno)
        if dup_count > 0:
            print(f"  [Notice] Found {dup_count} duplicate registration numbers. Filenames disambiguated safely.")

        # Step 5 & 6: Analyze certificate template and detect fields
        print("\n[Step 5/10] Analyzing certificate template layout...")
        try:
            analyzer = TemplateAnalyzer(template_file)
            template_info = analyzer.analyze(sample_students=students)
        except Exception as e:
            print(f"\n[ERROR] Failed to analyze certificate template: {e}", file=sys.stderr)
            return False

        print(f"[Step 6/10] Dynamic fields mapped:")
        print(f"  • Page Dimensions: {template_info.width:.1f} x {template_info.height:.1f} pt")
        print(f"  • Layout Type:     {'Table Layout' if template_info.is_table_layout else 'Standard Certificate'}")
        for k, f in template_info.fields.items():
            print(f"  • Field '{k}': at (x={f.x:.1f}, y={f.y:.1f}), font={f.font_name} ({f.font_size:.1f}pt), align={f.alignment}")
        if template_info.redaction_boxes:
            print(f"  • Redaction Masks: {len(template_info.redaction_boxes)} placeholder mask(s) configured.")

        # Step 7: Generate one PDF per student
        print(f"\n[Step 7/10] Generating individual certificate PDFs in {self.output_dir.name}/...")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        generator = CertificateGenerator(template_info, self.output_dir)
        results = generator.generate_all(students)

        success_count = sum(1 for r in results if r.status == "Success")
        print(f"  Progress: {success_count}/{len(students)} certificates generated.")

        # Step 8: Quality Control validation
        print("\n[Step 8/10] Running automated Quality Control checks on generated PDFs...")
        validator = CertificateValidator(template_info, self.output_dir)
        val_report = validator.validate(students, results, max_previews=self.preview_count)
        print(f"  QC Passed: {val_report.total_passed}/{val_report.total_expected}")
        if val_report.errors:
            for err in val_report.errors[:3]:
                print(f"  [QC Error] {err}")

        # Step 9: Save generation report
        print(f"\n[Step 9/10] Writing generation report to {self.output_dir / 'generation_report.csv'}...")
        report_gen = ReportGenerator(self.output_dir)
        report_gen.write_csv_report(results)

        # Step 10: Final summary
        print("\n[Step 10/10] Finalizing generation workflow...")
        report_gen.print_summary(
            excel_path=excel_file,
            template_path=template_file,
            total_students=len(students),
            results=results,
            val_report=val_report,
            output_dir=self.output_dir,
        )

        return val_report.is_valid and success_count == len(students)


def main():
    parser = argparse.ArgumentParser(
        description="Automated Certificate Generation Agent for Antigravity (AGY) CLI."
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=".",
        help="Working directory containing Excel and Certificate template files (default: current directory).",
    )
    parser.add_argument(
        "--excel",
        type=str,
        default=None,
        help="Optional explicit path to the student Excel file.",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=None,
        help="Optional explicit path to the certificate template file.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional output directory (default: ./certificates/).",
    )
    parser.add_argument(
        "--preview-count",
        type=int,
        default=3,
        help="Number of generated certificate preview images to render (default: 3).",
    )

    args = parser.parse_args()
    agent = CertificateAgent(
        working_dir=args.dir,
        excel_path=args.excel,
        template_path=args.template,
        output_dir=args.output,
        preview_count=args.preview_count,
    )
    success = agent.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
