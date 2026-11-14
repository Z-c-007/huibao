"""Word and PDF exporters using the exact saved version, never another LLM call."""
import io
import re
import os
from pathlib import Path
from html import escape


def plain(text):
    text = re.sub(r'\\([\\`*_{}\[\]()#+.!|<>])', r'\1', text)
    return text.replace('**', '').replace('`', '').replace('—', '-')


def blocks(markdown):
    lines, index = markdown.splitlines(), 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith('|'):
            rows = []
            while index < len(lines) and lines[index].strip().startswith('|'):
                cells = [plain(cell.strip()) for cell in re.split(r'(?<!\\)\|', lines[index].strip())[1:-1]]
                if not all(re.fullmatch(r'[-: ]+', cell) for cell in cells):
                    rows.append(cells)
                index += 1
            # Keep one complete table with a wider identity column for Chinese names.
            if rows and len(rows[0]) == 8:
                rows = [[row[0] + ('\n' + row[1] + ' · ' + row[2] if n else '及行业区县'), *row[3:]] for n, row in enumerate(rows)]
            yield 'table', rows
            continue
        match = re.match(r'^(#{1,3})\s+(.+)', line)
        if match:
            yield 'h' + str(len(match[1])), plain(match[2])
        else:
            yield 'p', plain(line)
        index += 1


def export_docx(draft):
    from docx import Document
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = Inches(.75)
    section.left_margin = section.right_margin = Inches(.75)
    for name, size in [('Normal', 11), ('Title', 20), ('Heading 1', 14), ('Heading 2', 12)]:
        style = doc.styles[name]
        style.font.name = 'SimSun'
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), '宋体')
        style.paragraph_format.space_after = Pt(7)
        style.paragraph_format.line_spacing = 1.25
    doc.core_properties.title, doc.core_properties.author = draft['title'], '用水预算监管平台'
    for kind, content in blocks(draft['markdown']):
        if kind == 'table':
            table = doc.add_table(rows=0, cols=len(content[0]))
            table.autofit = False
            proportions = [.30, .16, .15, .15, .12, .12] if len(content[0]) == 6 else [1 / len(content[0])] * len(content[0])
            for col, proportion in zip(table.columns, proportions):
                col.width = Inches(7 * proportion)
            borders = OxmlElement('w:tblBorders')
            for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
                item = OxmlElement('w:' + edge)
                for key, value in [('val', 'single'), ('sz', '4'), ('color', 'D9D9D9')]:
                    item.set(qn('w:' + key), value)
                borders.append(item)
            table._tbl.tblPr.append(borders)
            for n, row in enumerate(content):
                cells = table.add_row().cells
                props = table.rows[-1]._tr.get_or_add_trPr()
                props.append(OxmlElement('w:cantSplit'))
                if n == 0:
                    props.append(OxmlElement('w:tblHeader'))
                for col, (cell, value) in enumerate(zip(cells, row)):
                    cell.width = Inches(7 * proportions[col])
                    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    tcpr = cell._tc.get_or_add_tcPr()
                    margin = OxmlElement('w:tcMar')
                    for edge in ('top', 'bottom', 'left', 'right'):
                        item = OxmlElement('w:' + edge)
                        item.set(qn('w:w'), '85')
                        item.set(qn('w:type'), 'dxa')
                        margin.append(item)
                    tcpr.append(margin)
                    if n == 0:
                        shade = OxmlElement('w:shd')
                        shade.set(qn('w:fill'), 'F1F3F5')
                        tcpr.append(shade)
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_after = Pt(0)
                    p.paragraph_format.line_spacing = 1.15
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if col == 0 else WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run(value)
                    run.font.size = Pt(9)
                    run.bold = n == 0
            doc.add_paragraph().paragraph_format.space_after = Pt(0)
        else:
            style = {'h1': 'Title', 'h2': 'Heading 1', 'h3': 'Heading 2'}.get(kind)
            p = doc.add_paragraph(content, style)
            if kind != 'p':
                p.paragraph_format.keep_with_next = True
            if content.startswith('https://'):
                for run in p.runs:
                    run.font.size = Pt(8)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def export_pdf(draft):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    font_path = Path(os.environ.get('REPORT_FONT_PATH', 'C:/Windows/Fonts/simsun.ttc'))
    font = 'ReportChinese' if font_path.is_file() else 'STSong-Light'
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, str(font_path), subfontIndex=0) if font_path.is_file() else UnicodeCIDFont(font))
    body = ParagraphStyle('body', fontName=font, fontSize=11, leading=16, spaceAfter=5, wordWrap='CJK')
    headings = {kind: ParagraphStyle(kind, parent=body, fontSize=size, leading=size * 1.4, spaceBefore=12 if kind != 'h1' else 0, spaceAfter=9, keepWithNext=True) for kind, size in [('h1', 20), ('h2', 14), ('h3', 12)]}
    cell_style = ParagraphStyle('cell', parent=body, fontSize=9, leading=13, spaceAfter=0)
    centered = ParagraphStyle('number', parent=cell_style, alignment=TA_CENTER)
    flow = []
    for kind, content in blocks(draft['markdown']):
        if kind == 'table':
            if flow and isinstance(flow[-1], Paragraph):
                flow[-1].keepWithNext = False
            rows = [[Paragraph(escape(cell).replace('\n', '<br/>'), cell_style if i == 0 else centered) for i, cell in enumerate(row)] for row in content]
            proportions = [.30, .16, .15, .15, .12, .12] if len(content[0]) == 6 else [1 / len(content[0])] * len(content[0])
            table = Table(rows, colWidths=[504 * proportion for proportion in proportions], repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F3F5')), ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#D9D9D9')), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
            flow.extend([table, Spacer(1, 10)])
        else:
            style = headings.get(kind, body)
            if content.startswith('https://') or content.startswith(('生成时间', '检查范围', '数据快照', '报告版本')):
                style = ParagraphStyle('metadata', parent=body, fontSize=9, leading=13)
            flow.append(Paragraph(escape(content), style))
    output = io.BytesIO()
    def footer(canvas, doc):
        canvas.setFont(font, 9)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawRightString(558, 30, f"V{draft['version']}  ·  第 {doc.page} 页")
    SimpleDocTemplate(output, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=48, bottomMargin=48,
                      title=draft['title'], author='用水预算监管平台').build(flow, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
