import os
import re
import sys
from pathlib import Path

# Ensure console supports UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from pdf_generator import create_pdf_bytes

FONT_NAME = "TH Sarabun New"
COLOR_NAVY = RGBColor(27, 54, 93)
COLOR_BLUE = RGBColor(43, 108, 176)
COLOR_DARK = RGBColor(45, 55, 72)
COLOR_MUTED = RGBColor(113, 128, 150)
HEX_NAVY = "1B365D"
HEX_BORDER = "CBD5E0"
HEX_ALT_ROW = "F1F5F9"


def set_run_font(run, font_name=FONT_NAME, size_pt=13, bold=False, italic=False, color=COLOR_DARK):
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color

    rPr = run._r.get_or_add_rPr()
    rFonts = parse_xml(
        f'<w:rFonts {nsdecls("w")} w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/>'
    )
    rPr.append(rFonts)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def set_table_borders(table, color=HEX_BORDER, sz="4"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def add_formatted_text(paragraph, text, base_font=FONT_NAME, base_size=13, base_color=COLOR_DARK):
    tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith('**') and token.endswith('**'):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, font_name=base_font, size_pt=base_size, bold=True, color=base_color)
        elif token.startswith('*') and token.endswith('*'):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, font_name=base_font, size_pt=base_size, italic=True, color=base_color)
        else:
            run = paragraph.add_run(token)
            set_run_font(run, font_name=base_font, size_pt=base_size, bold=False, color=base_color)


def markdown_to_docx(md_path: Path, docx_path: Path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    doc = docx.Document()

    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("บันทึกการประชุมภายใน (Executive Meeting Minutes)")
        set_run_font(hrun, size_pt=10, color=COLOR_MUTED)

        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run("เอกสารสรุปการประชุม — ระบบอัตโนมัติ Meeting Summarizer")
        set_run_font(frun, size_pt=9, color=COLOR_MUTED)

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('|') and line.endswith('|'):
            t_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                t_lines.append(lines[i].strip())
                i += 1
            render_table(doc, t_lines)
            continue

        if line == '---' or line == '***':
            i += 1
            continue

        if not line:
            i += 1
            continue

        if line.startswith('# '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(12)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_formatted_text(p, line[2:].strip(), base_size=20, base_color=COLOR_NAVY)
            i += 1
            continue

        if line.startswith('## '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(16)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            add_formatted_text(p, line[3:].strip(), base_size=15, base_color=COLOR_NAVY)
            i += 1
            continue

        if line.startswith('### '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            add_formatted_text(p, line[4:].strip(), base_size=13.5, base_color=COLOR_BLUE)
            i += 1
            continue

        if lines[i].startswith('    - ') or lines[i].startswith('\t- ') or lines[i].startswith('  - '):
            p = doc.add_paragraph(style='List Bullet 2' if 'List Bullet 2' in doc.styles else 'List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            add_formatted_text(p, lines[i].strip()[2:].strip(), base_size=12.5)
            i += 1
            continue

        if line.startswith('- '):
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            add_formatted_text(p, line[2:].strip(), base_size=13)
            i += 1
            continue

        if re.match(r'^\d+\.\s', line):
            p = doc.add_paragraph(style='List Number' if 'List Number' in doc.styles else None)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            add_formatted_text(p, line, base_size=13)
            i += 1
            continue

        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        add_formatted_text(p, line, base_size=13)
        i += 1

    doc.save(str(docx_path))
    print(f"✅ สร้างเอกสาร Word สำเร็จ: {docx_path.name}")


def render_table(doc, table_lines):
    if len(table_lines) < 2:
        return

    raw_header = [c.strip() for c in table_lines[0].split('|')[1:-1]]
    rows_data = []
    for t_line in table_lines[2:]:
        cols = [c.strip() for c in t_line.split('|')[1:-1]]
        if cols:
            rows_data.append(cols)

    table = doc.add_table(rows=len(rows_data) + 1, cols=len(raw_header))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table)

    hdr_cells = table.rows[0].cells
    for col_idx, heading in enumerate(raw_header):
        cell = hdr_cells[col_idx]
        set_cell_background(cell, HEX_NAVY)
        set_cell_margins(cell, top=140, bottom=140, left=150, right=150)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx != 1 else WD_ALIGN_PARAGRAPH.LEFT
        add_formatted_text(p, heading, base_size=12.5, base_color=RGBColor(255, 255, 255))

    trPr = table.rows[0]._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

    for row_idx, data_row in enumerate(rows_data):
        row = table.rows[row_idx + 1]
        r_trPr = row._tr.get_or_add_trPr()
        r_trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))

        row_bg = HEX_ALT_ROW if row_idx % 2 == 1 else "FFFFFF"

        for col_idx in range(len(raw_header)):
            cell = row.cells[col_idx]
            if row_bg != "FFFFFF":
                set_cell_background(cell, row_bg)
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

            val = data_row[col_idx] if col_idx < len(data_row) else ""
            p = cell.paragraphs[0]
            if col_idx in [0, 2, 3]:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT

            add_formatted_text(p, val, base_size=12)

    sp_p = doc.add_paragraph()
    sp_p.paragraph_format.space_before = Pt(6)
    sp_p.paragraph_format.space_after = Pt(6)


def convert_md_to_pdf(md_path: Path, pdf_path: Path):
    """Generate PDF directly from Markdown using pure Python fpdf2 engine."""
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
    pdf_bytes = create_pdf_bytes(md_text, title=md_path.stem)
    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)
    print(f"✅ สร้างเอกสาร PDF สำเร็จ: {pdf_path.name}")


def main():
    base_dir = Path(__file__).resolve().parent
    summaries_dir = base_dir / "summaries"

    md_files = list(summaries_dir.glob("*.md"))
    if not md_files:
        print("ไม่พบไฟล์ Markdown ในโฟลเดอร์ summaries/")
        return

    for md_file in sorted(md_files):
        docx_file = md_file.with_suffix(".docx")
        pdf_file = md_file.with_suffix(".pdf")
        print(f"\n📄 กำลังประมวลผล: {md_file.name}")
        markdown_to_docx(md_file, docx_file)
        try:
            convert_md_to_pdf(md_file, pdf_file)
        except Exception as e:
            print(f"⚠️ เกิดข้อผิดพลาดในการสร้าง PDF: {e}")


if __name__ == "__main__":
    main()
