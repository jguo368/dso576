"""Build the Module 6 Gradescope PDF from validated cleaning evidence."""

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "module6_data_cleaning_submission.pdf"
BRANCH = "fennie-project"
BRANCH_URL = "https://github.com/jguo368/dso576/tree/fennie-project"
CLEANING_COMMIT = "794e5d6fcce8abe6a8a8fa9a0488ed71ec8ed5e3"


def paragraph(text, style):
    return Paragraph(str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style)


def table(data, widths, styles):
    rows = [[paragraph(cell, styles["small"]) for cell in row] for row in data]
    output = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    output.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2F3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FC")]),
    ]))
    return output


def heading(text, styles):
    return [Spacer(1, 8), Paragraph(text, styles["heading"]), Spacer(1, 3)]


def main():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="title2", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=17, leading=21, alignment=TA_CENTER, textColor=colors.black, spaceAfter=8))
    styles.add(ParagraphStyle(name="subtitle", parent=styles["Normal"], fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.black, spaceAfter=12))
    styles.add(ParagraphStyle(name="heading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.black, spaceBefore=6, spaceAfter=3))
    styles.add(ParagraphStyle(name="body", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=5))
    styles.add(ParagraphStyle(name="small", parent=styles["BodyText"], fontSize=7.2, leading=9))
    doc = SimpleDocTemplate(str(OUT), pagesize=letter, rightMargin=0.45*inch, leftMargin=0.45*inch, topMargin=0.45*inch, bottomMargin=0.45*inch)
    story = []
    story += [Paragraph("Module 6 Project Data Cleaning Assignment", styles["title2"]), Paragraph("Medi Cal access and provider capacity analysis", styles["subtitle"])]
    story.append(paragraph("Business vision: A Medi-Cal access strategy manager at DHCS must decide which counties and language populations should be prioritized for additional language-access capacity.", styles["body"]))
    story += heading("GitHub submission information", styles)
    story.append(table([["Branch name", "Branch URL", "Cleaning workflow commit ID"], [BRANCH, BRANCH_URL, CLEANING_COMMIT]], [1.15*inch, 3.35*inch, 2.55*inch], styles))

    story += heading("Fourteen item cleaning checklist", styles)
    checklist = [
        ["#", "Status", "Evidence"],
        ["1", "Done", "County-month-language eligible populations are a planning signal; provider capacity remains unresolved because no provider dataset is present."],
        ["2", "Done", "Grain and candidate keys are documented for all four datasets."],
        ["3", "Done", "Original CSVs are read-only; source hashes are recorded."],
        ["4", "Done", "Raw fields remain and parsed date/count/comparison fields are added; conversion failures are reported."],
        ["5", "Done", "Only outer-whitespace comparison fields are added; language categories are not combined."],
        ["6", "Done", "Exact duplicates and repeated candidate keys are reported separately."],
        ["7", "Done", "Missing counts and percentages are reported before and after; blanks stay missing."],
        ["8", "Done", "Negative values, failed parses, invalid counties, placeholders, and P records are flagged."],
        ["9", "Done", "One-to-one county-month key coverage is verified; long demographic tables are not directly merged."],
        ["10", "Done", "631,980 rows before and 631,980 rows after across the four files; no rows were dropped."],
        ["11", "Done", "Missing counts are never changed to zero; county rankings/maps filter Invalid County Code."],
        ["12", "Done", "Five difficult individual-record checks all passed."],
        ["13", "Done", "A restart/rerun produced identical non-manifest output hashes."],
        ["14", "Unresolved", "Provider capacity, F/P definitions, suppression policy, and merged-file provenance need documentation."],
    ]
    story.append(table(checklist, [0.3*inch, 0.65*inch, 6.1*inch], styles))

    story += heading("Cleaning decision log", styles)
    log = pd.read_csv(HERE / "outputs" / "cleaning_decision_log.csv")
    story.append(table([["Rule", "Reason", "Validation check"]] + log.values.tolist(), [2.1*inch, 2.45*inch, 2.5*inch], styles))

    story += heading("Five individual record checks", styles)
    checks = pd.read_csv(HERE / "outputs" / "record_checks.csv")
    check_rows = [["Case", "Original", "Expected", "Actual", "Match"]]
    for _, row in checks.iterrows():
        check_rows.append([row["case"], row["original_value"], row["expected_result"], row["actual_result"], row["matches"]])
    story.append(table(check_rows, [1.1*inch, 1.25*inch, 1.7*inch, 2.6*inch, 0.55*inch], styles))

    story += heading("Codex Suggestion Verification", styles)
    story.append(paragraph("Suggestion checked: Retain and flag Invalid County Code records instead of deleting them. The original derived county-month file contains three affected records. All three remain in the cleaned output and carry is_invalid_county_code=True, so cleaning preserves row count and audit visibility. Because Invalid County Code is not a California county, county-level rankings and maps must exclude only those flagged records. The derived-file key check matched all 11,603 non-statewide county-month keys with zero unmatched keys and no row multiplication.", styles["body"]))
    story += heading("Reproducibility and limits", styles)
    story.append(paragraph("Running python cleaning/clean_medi_cal.py loads only original CSV inputs and writes derived outputs. A second run produced identical non-manifest output hashes. Blank and suppressed counts remain missing; F and P records remain present with a P flag. Provider-capacity values and definitions are not invented because no provider dataset is in the inspected files.", styles["body"]))
    doc.build(story)


if __name__ == "__main__":
    main()
