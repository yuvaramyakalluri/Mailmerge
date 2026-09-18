"""Report generation and CLI summary formatting."""
import csv
from pathlib import Path
from typing import List

from .generator import GenerationResult
from .validator import ValidationReport
from .config import DEFAULT_REPORT_FILENAME


class ReportGenerator:
    """Generates the generation report CSV and prints human-readable execution summaries."""

    def __init__(self, output_dir: Path, report_filename: str = DEFAULT_REPORT_FILENAME):
        self.output_dir = Path(output_dir)
        self.report_path = self.output_dir / report_filename

    def write_csv_report(self, results: List[GenerationResult]) -> Path:
        """Writes the required generation_report.csv file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self.report_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Reg No", "Name", "Status", "Output File"])
            for res in results:
                writer.writerow([res.reg_no, res.name, res.status, res.output_file])
        return self.report_path

    @staticmethod
    def print_summary(
        excel_path: Path,
        template_path: Path,
        total_students: int,
        results: List[GenerationResult],
        val_report: ValidationReport,
        output_dir: Path,
    ):
        """Prints a professional, clean summary to stdout matching the specification."""
        success_count = len([r for r in results if r.status == "Success"])
        failed_count = len([r for r in results if r.status != "Success"])

        print("\n" + "=" * 65)
        print("         CERTIFICATE GENERATION WORKFLOW COMPLETED")
        print("=" * 65)
        print(f"Excel Source:          {excel_path.name}")
        print(f"Certificate Template:  {template_path.name}")
        print("-" * 65)
        print(f"Students found:        {total_students}")
        print(f"Certificates created:  {success_count}")
        print(f"Failed:                {failed_count}")
        print("-" * 65)
        print(f"Quality Control (QC):  {'PASSED (All verified)' if val_report.is_valid else 'FAILED / WARNINGS'}")
        if val_report.errors:
            print("\nQC Errors:")
            for err in val_report.errors[:5]:
                print(f"  - {err}")
        print("-" * 65)
        print(f"Output directory:      {output_dir.resolve()}")
        print(f"Generation Report:     {output_dir / DEFAULT_REPORT_FILENAME}")
        if val_report.preview_images:
            print(f"Visual Previews:       {len(val_report.preview_images)} preview images saved in {output_dir / 'previews'}")
        print("=" * 65)
        if failed_count == 0 and val_report.is_valid:
            print("All certificates successfully generated and verified.\n")
        else:
            print("Generation completed with issues. Please inspect the report.\n")
