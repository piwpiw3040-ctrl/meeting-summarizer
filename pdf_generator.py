# -*- coding: utf-8 -*-
"""
pdf_generator.py
Pure Python in-memory PDF generation with fpdf2 & uharfbuzz for Thai script support.
"""

import io
import re
from pathlib import Path
from fpdf import FPDF
from fpdf.fonts import FontFace
from fpdf.enums import Align, VAlign


class MeetingPDF(FPDF):
    def __init__(self, doc_title: str = "บันทึกการประชุม", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title = doc_title

    def header(self):
        if self.page_no() > 1:
            self.set_font("Thai", "", 9)
            self.set_text_color(120, 130, 140)
            self.cell(0, 8, self.doc_title, align=Align.L)
            self.cell(0, 8, "เอกสารสรุปการประชุม AI", align=Align.R, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(220, 225, 230)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("Thai", "", 9)
        self.set_text_color(140, 150, 160)
        self.set_draw_color(230, 235, 240)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y() - 2, self.w - self.r_margin, self.get_y() - 2)
        page_str = f"หน้า {self.page_no()} / {{nb}}"
        self.cell(0, 8, page_str, align=Align.C)


def get_font_paths():
    base_dir = Path(__file__).resolve().parent
    local_regular = base_dir / "fonts" / "Thai-Regular.ttf"
    local_bold = base_dir / "fonts" / "Thai-Bold.ttf"

    if local_regular.exists() and local_bold.exists():
        return str(local_regular), str(local_bold)

    win_regular = Path("C:/Windows/Fonts/LeelawUI.ttf")
    win_bold = Path("C:/Windows/Fonts/LeelaUIb.ttf")
    if win_regular.exists() and win_bold.exists():
        return str(win_regular), str(win_bold)

    win_tahoma = Path("C:/Windows/Fonts/tahoma.ttf")
    win_tahomabd = Path("C:/Windows/Fonts/tahomabd.ttf")
    if win_tahoma.exists():
        bold_p = str(win_tahomabd) if win_tahomabd.exists() else str(win_tahoma)
        return str(win_tahoma), bold_p

    raise FileNotFoundError("Thai TrueType fonts not found. Ensure fonts/Thai-Regular.ttf exists.")


def create_pdf_bytes(markdown_text: str, title: str = "บันทึกการประชุม") -> bytes:
    """
    Generate native Thai PDF bytes from markdown text using fpdf2 and uharfbuzz.
    """
    font_reg, font_bold = get_font_paths()

    pdf = MeetingPDF(doc_title=title, orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(left=18, top=16, right=18)
    pdf.set_text_shaping(True)

    pdf.add_font("Thai", "", font_reg)
    pdf.add_font("Thai", "B", font_bold)
    pdf.alias_nb_pages()
    pdf.add_page()

    lines = markdown_text.splitlines()
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        raw_line = lines[i]
        line = raw_line.strip()

        if not line or line in ["---", "***", "___"]:
            i += 1
            continue

        # Markdown Table
        if line.startswith("|") and line.endswith("|"):
            table_lines = [line]
            i += 1
            while i < total_lines and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) >= 3:
                # Row 0: Headers, Row 1: Separators, Row 2+: Data
                raw_headers = [c.strip() for c in table_lines[0].split("|")[1:-1]]
                raw_rows = [[c.strip() for c in row_str.split("|")[1:-1]] for row_str in table_lines[2:]]

                col_count = len(raw_headers)
                avail_width = pdf.w - pdf.l_margin - pdf.r_margin

                # Smart column width allocation
                if col_count == 4:
                    col_widths = (16, avail_width - 80, 36, 28)
                elif col_count == 5:
                    col_widths = (14, avail_width - 100, 32, 26, 28)
                else:
                    col_widths = tuple(avail_width / col_count for _ in range(col_count))

                hdr_style = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=(27, 54, 93))
                even_style = FontFace(color=(28, 28, 30), fill_color=(245, 248, 252))
                odd_style = FontFace(color=(28, 28, 30), fill_color=(255, 255, 255))

                pdf.ln(2)
                with pdf.table(col_widths=col_widths, text_align=Align.L) as table:
                    # Header
                    h_row = table.row()
                    for idx, h_text in enumerate(raw_headers):
                        h_align = Align.C if idx in [0, col_count - 1] else Align.L
                        h_row.cell(h_text, align=h_align, style=hdr_style)

                    # Data rows
                    for r_idx, r_data in enumerate(raw_rows):
                        d_row = table.row()
                        row_style = even_style if r_idx % 2 == 1 else odd_style
                        for c_idx in range(col_count):
                            val = r_data[c_idx] if c_idx < len(r_data) else ""
                            c_align = Align.C if c_idx in [0, col_count - 1] else Align.L
                            d_row.cell(val, align=c_align, style=row_style)
                pdf.ln(3)
            continue

        # Heading 1 (#)
        if line.startswith("# "):
            h_text = line[2:].strip()
            pdf.ln(3)
            pdf.set_font("Thai", "B", 18)
            pdf.set_text_color(27, 54, 93)  # iOS Navy #1B365D
            pdf.multi_cell(0, 9, h_text, new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(0, 122, 255)  # iOS Blue accent line
            pdf.set_line_width(0.8)
            pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
            pdf.ln(5)
            i += 1
            continue

        # Heading 2 (##)
        if line.startswith("## "):
            h_text = line[3:].strip()
            pdf.ln(4)
            pdf.set_font("Thai", "B", 14)
            pdf.set_text_color(27, 54, 93)
            pdf.multi_cell(0, 8, h_text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
            i += 1
            continue

        # Heading 3 (###)
        if line.startswith("### "):
            h_text = line[4:].strip()
            pdf.ln(2)
            pdf.set_font("Thai", "B", 12)
            pdf.set_text_color(43, 108, 176)  # Accent blue
            pdf.multi_cell(0, 7, h_text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
            i += 1
            continue

        # Bullet items (- or *)
        if line.startswith("- ") or line.startswith("* "):
            bullet_text = line[2:].strip()
            pdf.set_font("Thai", "", 10.5)
            pdf.set_text_color(35, 40, 48)

            # Clean bold markers for bullet
            clean_text = bullet_text.replace("**", "")
            indent = 5
            pdf.set_x(pdf.l_margin + indent)
            pdf.set_font("Thai", "B", 10.5)
            pdf.cell(4, 6, "• ", align=Align.L)
            pdf.set_font("Thai", "", 10.5)
            pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - indent - 4, 6, clean_text, new_x="LMARGIN", new_y="NEXT")
            i += 1
            continue

        # Normal text paragraph
        clean_line = line.replace("**", "")
        pdf.set_font("Thai", "", 10.5)
        pdf.set_text_color(35, 40, 48)
        pdf.multi_cell(0, 6, clean_line, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        i += 1

    return bytes(pdf.output())
