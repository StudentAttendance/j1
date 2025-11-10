from io import BytesIO
from typing import Optional

import os
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
try:
    import arabic_reshaper  # type: ignore
    from bidi.algorithm import get_display  # type: ignore
except Exception:
    arabic_reshaper = None
    get_display = None


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Export to Excel. Prefer XlsxWriter; fallback to OpenPyXL if unavailable."""
    output = BytesIO()
    # Try XlsxWriter first (best formatting support)
    try:
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:  # type: ignore[arg-type]
            sheet = "Attendance"
            df.to_excel(writer, index=False, sheet_name=sheet)
            workbook  = writer.book  # type: ignore[attr-defined]
            worksheet = writer.sheets[sheet]  # type: ignore[attr-defined]

            try:
                worksheet.right_to_left()
            except Exception:
                pass

            header_fmt = workbook.add_format({"bold": True, "align": "right", "font_name": "Arial"})  # type: ignore[attr-defined]
            for col_idx, col in enumerate(df.columns):
                worksheet.write(0, col_idx, str(col), header_fmt)

            body_fmt = workbook.add_format({"font_name": "Arial", "align": "right"})  # type: ignore[attr-defined]
            for idx, col in enumerate(df.columns):
                max_len = max([len(str(col))] + [len(str(x)) for x in df[col].astype(str).values])
                worksheet.set_column(idx, idx, min(max_len + 2, 50), body_fmt)
        return output.getvalue()
    except Exception:
        # Fallback to OpenPyXL path
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:  # type: ignore[arg-type]
            sheet = "Attendance"
            df.to_excel(writer, index=False, sheet_name=sheet)
            wb = writer.book  # type: ignore[attr-defined]
            ws = writer.sheets[sheet]  # type: ignore[attr-defined]
            # RTL for openpyxl
            try:
                ws.sheet_view.rightToLeft = True  # type: ignore[attr-defined]
            except Exception:
                pass
            # Set font and alignment for header and body
            from openpyxl.styles import Font, Alignment  # type: ignore
            header_font = Font(name="Arial", bold=True)
            body_font = Font(name="Arial")
            align_right = Alignment(horizontal="right")
            # Header
            for cell in ws[1]:
                cell.font = header_font
                cell.alignment = align_right
            # Body
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.font = body_font
                    cell.alignment = align_right
            # Autofit naive: set width based on max length per column
            for col_cells in ws.columns:
                max_len = 0
                col_letter = col_cells[0].column_letter
                for c in col_cells:
                    max_len = max(max_len, len(str(c.value)) if c.value is not None else 0)
                ws.column_dimensions[col_letter].width = min(max_len + 2, 50)
        return output.getvalue()


def _ensure_arabic_font() -> str:
    candidates = [
        ("Tahoma", r"C:\\Windows\\Fonts\\tahoma.ttf"),
        ("Arial", r"C:\\Windows\\Fonts\\arial.ttf"),
        ("SegoeUI", r"C:\\Windows\\Fonts\\segoeui.ttf"),
        ("DejaVuSans", "DejaVuSans.ttf"),
    ]
    for name, path in candidates:
        try:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
                return name
        except Exception:
            continue
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
        return "DejaVuSans"
    except Exception:
        return "Helvetica"


def _shape_arabic(text: str) -> str:
    if not text:
        return text
    if arabic_reshaper and get_display:
        try:
            reshaped = arabic_reshaper.reshape(str(text))
            return get_display(reshaped)
        except Exception:
            return str(text)
    return str(text)


def dataframe_to_pdf_bytes(df: pd.DataFrame, title: Optional[str] = None) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=1*cm, rightMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    elements = []

    font_name = _ensure_arabic_font()
    title_style = ParagraphStyle(name="Title", fontName=font_name, fontSize=16, leading=20, alignment=2)
    if title:
        elements.append(Paragraph(_shape_arabic(title), title_style))
        elements.append(Spacer(1, 0.3*cm))

    headers = [ _shape_arabic(str(c)) for c in df.columns ]
    rows = []
    for row in df.values.tolist():
        rows.append([ _shape_arabic(str(v)) for v in row ])
    data = [headers] + rows
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
        ])
    )
    elements.append(table)

    doc.build(elements)
    return buffer.getvalue()


