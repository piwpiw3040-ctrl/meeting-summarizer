# -*- coding: utf-8 -*-
"""
pdf_generator.py
Pure Python in-memory PDF generation with fpdf2 & uharfbuzz for Thai script support.
Optimized for clean, compact Thai document typography (tight spacing, hanging indents, and styled tables).
"""

import io
import re
from pathlib import Path
from fpdf import FPDF
from fpdf.fonts import FontFace
from fpdf.enums import Align, VAlign, WrapMode


def strip_schedule_section(markdown_text: str) -> str:
    """
    Remove any schedule, follow-up, or next appointment sections from markdown.
    """
    if not markdown_text:
        return ""
    # Pattern to match ## 📅 การติดตามงาน... or ## กำหนดการ... and its content until next ## or end
    pat = r'\n##\s*📅?\s*(?:การติดตามงานและนัดหมายครั้งถัดไป|การติดตามงาน|กำหนดการ|นัดหมายครั้งถัดไป|Next Steps)[^\n]*\n(?:(?!## )[\s\S])*'
    cleaned = re.sub(pat, '', markdown_text, flags=re.MULTILINE).strip()
    return cleaned


class MeetingPDF(FPDF):
    def __init__(self, doc_title: str = "บันทึกการประชุม", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title = doc_title

    def header(self):
        if self.page_no() > 1:
            self.set_font("Thai", "", 9)
            self.set_text_color(130, 140, 150)
            avail_w = self.w - self.l_margin - self.r_margin
            half_w = avail_w / 2

            # Truncate title if it exceeds half width
            display_title = self.doc_title
            max_title_w = half_w - 6
            if self.get_string_width(display_title) > max_title_w:
                while len(display_title) > 3 and self.get_string_width(display_title + "...") > max_title_w:
                    display_title = display_title[:-1]
                display_title += "..."

            self.cell(half_w, 7, display_title, align=Align.L)
            self.cell(half_w, 7, "บันทึกการประชุม AI", align=Align.R, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(225, 230, 235)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Thai", "", 8.5)
        self.set_text_color(145, 155, 165)
        self.set_draw_color(230, 235, 240)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y() - 1.5, self.w - self.r_margin, self.get_y() - 1.5)
        page_str = f"หน้า {self.page_no()} / {{nb}}"
        self.cell(0, 7, page_str, align=Align.C)


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
    # Clean schedule/appointment sections
    clean_markdown = strip_schedule_section(markdown_text)

    font_reg, font_bold = get_font_paths()

    pdf = MeetingPDF(doc_title=title, orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(left=16, top=14, right=16)
    
    # Enable text shaping if uharfbuzz is available; otherwise fallback to standard TTF rendering
    try:
        import uharfbuzz
        pdf.set_text_shaping(True)
    except Exception:
        pass

    pdf.add_font("Thai", "", font_reg)
    pdf.add_font("Thai", "B", font_bold)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Thai", "", 10)

    lines = clean_markdown.splitlines()
    i = 0
    total_lines = len(lines)
    avail_width = pdf.w - pdf.l_margin - pdf.r_margin

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

                # Smart column width allocation
                if col_count == 3:
                    col_widths = (16, avail_width - 64, 48)
                elif col_count == 4:
                    col_widths = (14, avail_width - 92, 44, 34)
                elif col_count == 5:
                    col_widths = (12, avail_width - 108, 36, 30, 30)
                else:
                    col_widths = tuple(avail_width / col_count for _ in range(col_count))

                hdr_style = FontFace(family="Thai", size_pt=9.5, emphasis="BOLD", color=(255, 255, 255), fill_color=(27, 54, 93))
                even_style = FontFace(family="Thai", size_pt=9, color=(28, 28, 30), fill_color=(247, 249, 252))
                odd_style = FontFace(family="Thai", size_pt=9, color=(28, 28, 30), fill_color=(255, 255, 255))

                pdf.ln(1.5)
                with pdf.table(col_widths=col_widths, text_align=Align.L) as table:
                    # Header
                    h_row = table.row()
                    for idx, h_text in enumerate(raw_headers):
                        h_align = Align.C if idx in [0, col_count - 1] else Align.L
                        clean_h = h_text.replace("**", "").strip()
                        h_row.cell(clean_h, align=h_align, style=hdr_style)

                    # Data rows
                    for r_idx, r_data in enumerate(raw_rows):
                        d_row = table.row()
                        row_style = even_style if r_idx % 2 == 1 else odd_style
                        for c_idx in range(col_count):
                            val = r_data[c_idx] if c_idx < len(r_data) else ""
                            clean_val = val.replace("**", "").strip()
                            c_align = Align.C if c_idx in [0, col_count - 1] else Align.L
                            d_row.cell(clean_val, align=c_align, style=row_style)
                pdf.ln(2.5)
            continue

        # Heading 1 (#)
        if line.startswith("# "):
            h_text = line[2:].strip().replace("**", "")
            pdf.ln(2)
            pdf.set_font("Thai", "B", 16)
            pdf.set_text_color(27, 54, 93)  # iOS Navy #1B365D
            pdf.multi_cell(0, 7.5, h_text, new_x="LMARGIN", new_y="NEXT", wrapmode=WrapMode.CHAR)
            pdf.set_draw_color(0, 122, 255)  # iOS Blue accent line
            pdf.set_line_width(0.7)
            pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
            pdf.ln(3.5)
            i += 1
            continue

        # Heading 2 (##)
        if line.startswith("## "):
            h_text = line[3:].strip().replace("**", "")
            pdf.ln(3)
            pdf.set_font("Thai", "B", 12.5)
            pdf.set_text_color(27, 54, 93)
            pdf.multi_cell(0, 6.5, h_text, new_x="LMARGIN", new_y="NEXT", wrapmode=WrapMode.CHAR)
            pdf.ln(0.5)
            i += 1
            continue

        # Heading 3 (###)
        if line.startswith("### "):
            h_text = line[4:].strip().replace("**", "")
            pdf.ln(1.5)
            pdf.set_font("Thai", "B", 11)
            pdf.set_text_color(43, 108, 176)  # Accent blue
            pdf.multi_cell(0, 5.8, h_text, new_x="LMARGIN", new_y="NEXT", wrapmode=WrapMode.CHAR)
            pdf.ln(0.5)
            i += 1
            continue

        # Bullet items (- or *)
        if line.startswith("- ") or line.startswith("* "):
            bullet_text = line[2:].strip()
            clean_text = bullet_text.replace("**", "").strip()

            saved_l = pdf.l_margin
            pdf.set_x(saved_l + 1)
            pdf.set_font("Thai", "B", 10)
            pdf.set_text_color(0, 122, 255)  # Apple Blue bullet
            pdf.cell(5, 5.2, "•", align=Align.C)
            pdf.set_font("Thai", "", 10)
            pdf.set_text_color(40, 45, 55)

            # Hanging indent: all subsequent lines align neatly
            pdf.l_margin = saved_l + 6
            pdf.set_x(saved_l + 6)
            pdf.multi_cell(0, 5.2, clean_text, new_x="LMARGIN", new_y="NEXT", wrapmode=WrapMode.CHAR)
            pdf.l_margin = saved_l
            pdf.ln(0.8)
            i += 1
            continue

        # Normal text paragraph
        clean_line = line.replace("**", "").strip()
        pdf.set_font("Thai", "", 10)
        pdf.set_text_color(40, 45, 55)
        pdf.multi_cell(0, 5.2, clean_line, new_x="LMARGIN", new_y="NEXT", wrapmode=WrapMode.CHAR)
        pdf.ln(1.2)
        i += 1

    return bytes(pdf.output())
