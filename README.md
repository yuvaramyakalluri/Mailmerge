# Automated Certificate Generation Agent

A production-quality, autonomous mail merge agent built for the **Antigravity (AGY) CLI**. It detects student data from Excel spreadsheets and automatically generates individual high-resolution PDF certificates matching a reference certificate template with lossless vector fidelity and precision typography.

---

## 1. Quick Start

### Installation
Ensure Python 3.10+ is installed. Install the dependencies:
```bash
pip install -r requirements.txt
```

### Autonomous Run
Place your Excel file (e.g. `students.xlsx` or `student-data.xlsx`) and your certificate template (e.g. `certificate_sample.pdf` or `template.pdf`) into the working folder, open the **Antigravity (AGY) CLI**, and run:

```bash
python main.py
```

The agent will automatically:
1. Detect your Excel spreadsheet and template.
2. Read and validate student records (`Reg No` and `Name`).
3. Inspect and map template placeholders / dynamic fields.
4. Auto-fit text and merge vector graphics losslessly.
5. Perform Quality Control (QC) verification on all generated certificates.
6. Render visual PNG previews in `certificates/previews/`.
7. Output `certificates/generation_report.csv` and a clean summary.

---

## 2. Input Files & Auto-Detection

The agent automatically discovers input files in the working directory—**no hardcoded filenames required**.

### A. Student Excel File (`.xlsx`, `.xls`)
The agent scans for Excel spreadsheets in the directory, skipping temporary Office lock files (`~$*`).
- **Required Columns**:
  - `Reg No` (or variations: `RegNo`, `REG NO`, `Registration No`, `Roll No`, `Student ID`)
  - `Name` (or variations: `Student Name`, `Full Name`, `Candidate Name`)
- **Handling Details**:
  - Blank rows are safely ignored.
  - Leading and trailing whitespace is automatically stripped.
  - Numbers formatted as floats (e.g. `202601.0`) are cleaned to `202601`.
  - Duplicate registration numbers are flagged and filenames disambiguated with `_dup2`, `_dup3`.
  - Names with accented or special characters are preserved.

### B. Certificate Template (`.pdf`, `.png`, `.jpg`)
The agent detects reference templates by prioritizing filenames containing `certificate`, `template`, `sample`, or any available PDF/image file.
- **Dynamic Field Recognition**:
  - **Explicit Placeholders**: Supports `{{NAME}}`, `{{REG_NO}}`, `[NAME]`, `[REG NO]`, `<NAME>`, `{NAME}`, `{{student_name}}`, etc.
  - **Sample Student Data**: If the template contains pre-existing sample names (e.g. `Ravi Kumar`, `202601`, or any name from the Excel sheet), the agent matches and replaces them.
  - **Labeled Fields**: Detects text following labels like `Name:`, `Student Name:`, `Reg No:`, `Registration No:`.
  - **Table / Sheet Layouts**: If the template is a sheet export (like `sample_data.pdf`), the agent isolates the student row and masks subsequent rows for single-certificate output.
  - **Image Templates**: Supported via high-resolution image rendering into PDF.

---

## 3. Template & Typography Preservation

The reference template is the **source of truth** for all visual styling:
- **Zero Loss / Pure Vector Quality**: For PDF templates, vector artwork, logos, borders, seals, and backgrounds are preserved losslessly. Text is overlaid directly using vector commands.
- **Background Color Sampling**: Background color surrounding placeholders is dynamically sampled from the bitmap so redaction rectangles blend invisibly into cream, ivory, or colored backgrounds.
- **Smart Auto-Fitting**:
  - Measures text width using PDF font metrics (`stringWidth`).
  - Standard names fit naturally at full prominent font size (e.g. 24pt - 32pt).
  - Unusually long student names scale down proportionally to avoid overflowing borders or logos.
  - Minimum font size safeguards (never shrunken below readable limits, e.g. 14pt).
  - Multi-line balanced wrapping if name exceeds width even at minimum font size.

---

## 4. Output Directory Structure

Generated files are organized cleanly in `./certificates/`:

```text
certificates/
├── 202601_Ravi_Kumar.pdf
├── 202602_Priya_Sharma.pdf
├── 202603_Arjun_Reddy.pdf
├── generation_report.csv
└── previews/
    ├── 202601_Ravi_Kumar_preview.png
    ├── 202602_Priya_Sharma_preview.png
    └── 202603_Arjun_Reddy_preview.png
```

### Generation Report (`generation_report.csv`)
```csv
Reg No,Name,Status,Output File
261FB04014,K YUVA RAMYA,Success,261FB04014_K_YUVA_RAMYA.pdf
261FB04023,M MADHU,Success,261FB04023_M_MADHU.pdf
261FB04019,K PRAGATHI,Success,261FB04019_K_PRAGATHI.pdf
261FB04017,K SRAVYA,Success,261FB04017_K_SRAVYA.pdf
261FB04016,K SUMANA SRI,Success,261FB04016_K_SUMANA_SRI.pdf
```

---

## 5. Quality Control (QC) Engine

Before completing execution, the agent runs an automated verification suite:
1. **Count Verification**: Verifies total PDFs created matches total valid students in Excel.
2. **File Health**: Verifies files open cleanly, are non-empty (>1 KB), and have 1 page.
3. **Dimensions Match**: Verifies each PDF has the exact page width and height of the template.
4. **Text Inspection**: Inspects extracted text from each generated PDF using `pdfplumber` to verify that the student's **Name** and **Reg No** are present.
5. **Visual Previews**: Renders the first 3 certificates to PNG at 150 DPI into `certificates/previews/` for quick visual auditing.

---

## 6. CLI Options & Overrides

Run with default automatic discovery:
```bash
python main.py
```

Or specify custom paths or options:
```bash
python main.py --excel my_students.xlsx --template my_template.pdf --output ./my_certs/
```

| Argument | Description | Default |
|---|---|---|
| `--dir` | Working directory to scan | Current directory (`.`) |
| `--excel` | Path to student Excel file | Auto-detected |
| `--template` | Path to certificate template | Auto-detected |
| `--output` | Destination directory | `./certificates/` |
| `--preview-count` | Number of preview PNGs to render | `3` |

---

## 7. Error Handling & Duplicate Safety

- **Missing Columns**: Provides descriptive error listing columns found and valid synonyms.
- **Duplicate Reg Numbers**: Suffixes duplicate output files (`_dup2`, `_dup3`) to prevent overwriting.
- **Re-run Safety**: Re-running the agent cleanly regenerates certificates and updates the report without creating duplicate confusion.
"# Mailmerge" 
