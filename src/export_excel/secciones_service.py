import xlsxwriter
from io import BytesIO
from bs4 import BeautifulSoup, NavigableString
import re
import logging
from typing import Optional, List, Tuple, Dict
from . import models

FAQ_SECTION_TYPES = {"questions", "faqs", "preguntas"}

YELLOW_TITLE_SECTIONS = {
    "questions", "faqs", "reviews", "rentcompanies",
    "advicestipocarrusel", "locationscarrusel", "fleetcarrusel", "rentacar",
}

WHITE_A_SECTIONS    = {"quicksearch", "fleet", "advicestipocarrusel"}
STRUCTURAL_SECTIONS = {"benefits", "agency_logs"}
SKIP_LABELS_LOWER   = {"texto alt", "texto alt "}

HEADERS = [
    "Sección",
    "Comentarios para el equipo IT",
    "Español",
    "Inglés",
    "Portugués",
    "Tipo de formato"
]

# Column widths (0-indexed)
COLUMN_WIDTHS = {0: 14.28, 1: 19.0, 2: 67.42, 3: 67.28, 4: 67.28, 5: 38.0, 6: 14.0, 7: 14.0}

# Colors in #RRGGBB for XlsxWriter
C_HEADER_BG = "#E6484B"
C_HEADER_FG = "#FFFFFF"
C_WHITE     = "#FFFFFF"
C_YELLOW    = "#FEF2CB"
C_FAQ_Q     = "#B45F06"
C_FAQ_A     = "#202124"
C_BLACK     = "#000000"

_LABEL_MAP_BASE = {
    "h1": "section_title",
    "descripción h1": "section_content",
    "descripcion h1": "section_content",
    "h2": "section_title",
    "descripción h2": "section_content",
    "descripcion h2": "section_content",
    "descripción h2 ": "section_content",
    "ip usa": "section_content_ip-United States",
    "ip br": "section_content_ip-Brazil",
    "ip bra": "section_content_ip-Brazil",
    "h3 faq": "FAQS_question",
    "descripción h3 faq": "FAQS_answer",
    "descripcion h3 faq": "FAQS_answer",
    "disclaimer": "component_content",
    "diclaimer": "component_content",
    "disclaimer f": "section_content",
    "desclaimers f": "section_content",
}


def _get_format_type(label: str, section_type: str) -> Optional[str]:
    normalized = label.strip().lower()
    if normalized == "h3":
        return "FAQS_question" if section_type in FAQ_SECTION_TYPES else "component_title"
    if normalized in ("descripción h3", "descripcion h3"):
        return "FAQS_answer" if section_type in FAQ_SECTION_TYPES else "component_content"
    return _LABEL_MAP_BASE.get(normalized)


# ---------------------------------------------------------------------------
# HTML utilities
# ---------------------------------------------------------------------------

def _html_to_plain(html: str) -> str:
    if not html or html.strip() == "":
        return ""
    if "<" not in html:
        return html
    try:
        soup = BeautifulSoup(html, "html.parser")
        for br in soup.find_all("br"):
            br.replace_with("\n")
        for p in soup.find_all("p"):
            p.append("\n")
        return soup.get_text()
    except Exception:
        return re.sub(r"<[^>]+>", "", html)


# Each run: (text, bold, italic, color_ARGB, size_pt, font_name)
Run = Tuple[str, bool, bool, str, int, str]

_BLOCK_TAGS     = frozenset({"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"})
_CONTAINER_TAGS = frozenset({"ul", "ol", "table", "tbody", "thead", "tr"})
_SKIP_WS_PARENT = _BLOCK_TAGS | _CONTAINER_TAGS | {"li"}


def _extract_color(style: str) -> Optional[str]:
    m = re.search(r"color:\s*#([0-9a-fA-F]{6})", style, re.I)
    if m:
        return "FF" + m.group(1).upper()
    m2 = re.search(r"color:\s*rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", style, re.I)
    if m2:
        r_v, g_v, b_v = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        return f"FF{r_v:02X}{g_v:02X}{b_v:02X}"
    return None


def _parse_runs(
    html: str,
    base_bold: bool,
    base_color: str,
    base_size: int,
    base_name: str = "Calibri",
) -> List[Run]:
    """Walk the HTML tree and collect text runs preserving bold, italic, color."""
    if not html or html.strip() == "":
        return []
    if "<" not in html:
        return [(html, base_bold, False, base_color, base_size, base_name)]

    runs: List[Run] = []

    def walk(node, bold: bool, italic: bool, color: str, size: int, name: str):
        if isinstance(node, NavigableString):
            text = str(node)
            parent_tag = node.parent.name if node.parent else None
            if not text.strip() and parent_tag in _SKIP_WS_PARENT:
                return
            if text:
                runs.append((text, bold, italic, color, size, name))
            return

        tag = getattr(node, "name", None)
        if tag is None:
            return
        if tag == "br":
            runs.append(("\n", bold, italic, color, size, name))
            return

        new_bold   = bold   or (tag in ("strong", "b"))
        new_italic = italic or (tag in ("em", "i"))
        new_color  = color
        if tag == "span":
            extracted = _extract_color(node.get("style", ""))
            if extracted:
                new_color = extracted

        for child in node.children:
            walk(child, new_bold, new_italic, new_color, size, name)

        if tag in _BLOCK_TAGS:
            runs.append(("\n", new_bold, new_italic, new_color, size, name))
        elif tag == "li":
            has_block_child = any(getattr(c, "name", None) in _BLOCK_TAGS for c in node.children)
            if not has_block_child:
                runs.append(("\n", new_bold, new_italic, new_color, size, name))

    try:
        soup = BeautifulSoup(html, "html.parser")
        for child in soup.children:
            walk(child, base_bold, False, base_color, base_size, base_name)
        while runs and not runs[0][0].strip():
            runs.pop(0)
        while runs and not runs[-1][0].strip():
            runs.pop()
    except Exception as exc:
        logging.warning(f"HTML parse error: {exc}")
        runs = [(_html_to_plain(html), base_bold, False, base_color, base_size, base_name)]

    return runs


# ---------------------------------------------------------------------------
# Cell data readers
# ---------------------------------------------------------------------------

def _cell_raw(cell_data: Optional[dict], template_data: dict, row: int, col: int) -> str:
    key = f"{row}-{col}"
    source = None
    if cell_data and key in cell_data:
        source = cell_data[key]
    elif key in template_data:
        source = template_data[key]
    if source is None:
        return ""
    if hasattr(source, "value"):
        return source.value or ""
    if isinstance(source, dict):
        return source.get("value", "") or ""
    return ""


def _cell_val(cell_data: Optional[dict], template_data: dict, row: int, col: int) -> str:
    return _html_to_plain(_cell_raw(cell_data, template_data, row, col))


# ---------------------------------------------------------------------------
# XlsxWriter helpers
# ---------------------------------------------------------------------------

def _argb_to_hex(argb: str) -> str:
    """'FFB45F06' → '#B45F06'"""
    return "#" + argb[2:]


def _build_formats(wb) -> Dict:
    border       = {"border": 1}
    wrap_center  = {"text_wrap": True, "align": "center", "valign": "vcenter"}
    wrap_left_top = {"text_wrap": True, "align": "left", "valign": "top"}

    fmts = {}

    fmts["header"] = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 11,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })

    fmts["section_name"] = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, **wrap_center, **border,
    })
    fmts["section_name_structural"] = wb.add_format({
        "bold": True, "font_name": "Arial", "font_size": 10,
        "font_color": C_BLACK, **wrap_center, **border,
    })

    fmts["label"] = wb.add_format({
        "font_name": "Calibri", "font_size": 10, "font_color": C_BLACK,
        "bg_color": C_WHITE, **wrap_center, **border,
    })
    fmts["label_bold"] = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 10, "font_color": C_BLACK,
        "bg_color": C_WHITE, **wrap_center, **border,
    })

    # Cell-level formats for content columns (border + alignment + optional fill).
    # Font is controlled per-run by write_rich_string; these properties apply to
    # the cell itself (fill, borders, alignment) and serve as the default font
    # when write() is used for plain-text cells.
    fmts["content"] = wb.add_format({
        "font_name": "Calibri", "font_size": 11, "font_color": C_BLACK,
        **wrap_left_top, **border,
    })
    fmts["content_faq_q"] = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 11, "font_color": C_FAQ_Q,
        **wrap_left_top, **border,
    })
    fmts["content_faq_a"] = wb.add_format({
        "font_name": "Calibri", "font_size": 11, "font_color": C_FAQ_A,
        **wrap_left_top, **border,
    })
    fmts["content_h1"] = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 14, "font_color": C_BLACK,
        **wrap_left_top, **border,
    })
    fmts["content_h2"] = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 12, "font_color": C_BLACK,
        **wrap_left_top, **border,
    })
    fmts["content_h2_yellow"] = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 12, "font_color": C_BLACK,
        "bg_color": C_YELLOW, **wrap_left_top, **border,
    })

    fmts["format_type"] = wb.add_format({
        "font_name": "Calibri", "font_size": 10, "font_color": C_BLACK,
        **wrap_left_top, **border,
    })
    fmts["section_id"] = wb.add_format({
        "font_name": "Calibri", "font_size": 10, "font_color": C_BLACK,
        **wrap_left_top, **border,
    })
    fmts["empty"] = wb.add_format({**border})

    return fmts


def _write_content_cell(
    ws, wb, row: int, col: int,
    runs: List[Run],
    base_bold: bool, base_color: str, base_size: int,
    cell_fmt,
    run_fmt_cache: dict,
) -> None:
    """Write a content cell as plain text or rich text depending on the runs."""
    if not runs:
        ws.write_blank(row, col, None, cell_fmt)
        return

    def is_default(r: Run) -> bool:
        _, b, i, c, s, _ = r
        return b == base_bold and not i and c == base_color and s == base_size

    if all(is_default(r) for r in runs):
        ws.write(row, col, "".join(r[0] for r in runs), cell_fmt)
        return

    # Build the argument list for write_rich_string:
    # alternating run-level Format objects and text strings, with cell_fmt last.
    args: list = []
    for text, bold, italic, color, size, name in runs:
        if not text:
            continue
        cache_key = (bold, italic, color, size, name)
        if cache_key not in run_fmt_cache:
            run_fmt_cache[cache_key] = wb.add_format({
                "bold": bold,
                "italic": italic,
                "font_color": _argb_to_hex(color),
                "font_size": size,
                "font_name": name,
            })
        args.extend([run_fmt_cache[cache_key], text])

    if not args:
        ws.write_blank(row, col, None, cell_fmt)
        return

    args.append(cell_fmt)
    # write_rich_string requires at least 2 format+string pairs (5 args total).
    # With only 1 run it silently ignores the call — fall back to plain write.
    if len(args) < 5:
        ws.write(row, col, "".join(r[0] for r in runs), cell_fmt)
        return
    plain_text = "".join(r[0] for r in runs)
    try:
        result = ws.write_rich_string(row, col, *args)
        # write_rich_string returns a negative int on failure instead of raising
        if isinstance(result, int) and result < 0:
            ws.write(row, col, plain_text, cell_fmt)
    except Exception as exc:
        logging.warning(f"write_rich_string failed (row={row}, col={col}): {exc}")
        ws.write(row, col, plain_text, cell_fmt)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def generate_secciones_excel(export_request: models.ExportExcelRequest) -> BytesIO:
    buffer = BytesIO()
    wb = xlsxwriter.Workbook(buffer, {"in_memory": True})

    # LandingPage must be the first sheet
    _add_landing_page_sheet(wb, export_request)

    ws = wb.add_worksheet("Secciones")

    fmts = _build_formats(wb)
    run_fmt_cache: dict = {}

    for col_idx, width in COLUMN_WIDTHS.items():
        ws.set_column(col_idx, col_idx, width)

    # Row 0 (Excel row 1): header
    ws.set_row(0, 30)
    for col_idx, header in enumerate(HEADERS):
        ws.write(0, col_idx, header, fmts["header"])

    ws.freeze_panes(1, 0)

    blocks        = export_request.template_config.blocks_metadata
    cell_data     = export_request.cell_data
    template_data = export_request.template_config.templateData

    type_to_section_id: dict = {}
    for bm in blocks.values():
        if bm.section_id is not None:
            type_to_section_id[bm.type] = bm.section_id

    all_rows: set = set()
    for key in template_data:
        try:
            r, _ = map(int, key.split("-"))
            all_rows.add(r)
        except ValueError:
            pass
    if cell_data:
        for key in cell_data:
            try:
                r, _ = map(int, key.split("-"))
                all_rows.add(r)
            except ValueError:
                pass

    if not all_rows:
        logging.warning("No hay filas en templateData ni cell_data")
        wb.close()
        buffer.seek(0)
        return buffer

    max_row = max(all_rows)

    current_section: str = ""
    current_section_id   = None
    section_pos: int     = 0
    excel_row: int       = 1  # 0-indexed; row 0 is the header

    # Track column-A merge spans: (start_row, end_row, name, type)
    section_spans: list  = []
    span_start: int      = None
    span_name: str       = ""
    span_type: str       = ""

    # last section for which a row was actually written to Excel
    last_written_section: str = ""

    for row_idx in range(max_row + 1):
        col0 = _cell_val(cell_data, template_data, row_idx, 0).strip()
        if col0 and col0 != " ":
            current_section    = col0
            current_section_id = type_to_section_id.get(col0)
            section_pos        = 0

        section_pos += 1
        is_first_data_row = (section_pos == 1)  # first row in data for this section

        label = _cell_val(cell_data, template_data, row_idx, 2).strip()

        if label.lower().strip() in SKIP_LABELS_LOWER:
            continue

        es_html = _cell_raw(cell_data, template_data, row_idx, 3)
        en_html = _cell_raw(cell_data, template_data, row_idx, 4)
        pt_html = _cell_raw(cell_data, template_data, row_idx, 5)

        spanish    = _html_to_plain(es_html)
        english    = _html_to_plain(en_html)
        portuguese = _html_to_plain(pt_html)

        if label:
            format_type = _get_format_type(label, current_section)
            if format_type is None:
                logging.warning(
                    f"Etiqueta sin mapeo: {label!r} "
                    f"(seccion={current_section!r}, fila={row_idx}) — omitida"
                )
                continue
        elif is_first_data_row and current_section:
            format_type = "section_title"
        elif section_pos == 2 and not label and current_section:
            format_type = "section_content"
        else:
            continue

        lbl_lower = label.strip().lower()
        if lbl_lower in ("h2", "h3", "h1"):
            logging.info(
                f"[TITULO] fila={row_idx} label={label!r} seccion={current_section!r} "
                f"es_html={es_html[:80]!r} format_type={format_type}"
            )

        if not spanish and not english and not portuguese:
            if format_type not in ("section_title", "section_content"):
                continue

        # Determine base style and cell format for content columns
        is_title      = format_type in ("section_title", "component_title")
        is_faq_q      = format_type == "FAQS_question"
        is_faq_a      = format_type == "FAQS_answer"
        lbl           = label.strip().lower()
        is_h1         = is_title and lbl == "h1"
        is_h2         = is_title and lbl == "h2"
        is_disclaimer = (format_type == "component_content" and
                         lbl in ("disclaimer", "diclaimer", "disclaimer f", "desclaimers f"))

        if is_faq_q:
            base_bold, base_color, base_size = True,  "FFB45F06", 11
            content_fmt = fmts["content_faq_q"]
        elif is_faq_a:
            base_bold, base_color, base_size = False, "FF202124", 11
            content_fmt = fmts["content_faq_a"]
        elif is_disclaimer:
            base_bold, base_color, base_size = False, "FF000000", 10
            content_fmt = fmts["content"]
        elif is_h1:
            base_bold, base_color, base_size = True,  "FF000000", 14
            content_fmt = fmts["content_h1"]
        elif is_h2:
            base_bold, base_color, base_size = True,  "FF000000", 12
            content_fmt = (
                fmts["content_h2_yellow"]
                if current_section in YELLOW_TITLE_SECTIONS
                else fmts["content_h2"]
            )
        elif is_title:
            base_bold, base_color, base_size = True,  "FF000000", 11
            content_fmt = fmts["content"]
        else:
            base_bold, base_color, base_size = False, "FF000000", 11
            content_fmt = fmts["content"]

        # Detect first WRITTEN row for the current section.
        # This is intentionally checked at write time (not at data-read time) so
        # that rows skipped by earlier `continue` statements (e.g. "Texto alt"
        # labels, unmapped labels) don't prevent the section span from starting.
        is_first_written = (current_section != last_written_section)
        if is_first_written:
            last_written_section = current_section
            if span_start is not None:
                section_spans.append((span_start, excel_row - 1, span_name, span_type))
            span_start = excel_row
            span_name  = current_section
            span_type  = current_section

        # Col B: label
        label_bold = is_title or is_faq_q or is_first_written
        ws.write(excel_row, 1, label, fmts["label_bold"] if label_bold else fmts["label"])

        # Cols C (2), D (3), E (4): content with rich text
        for col_idx, raw_html in [(2, es_html), (3, en_html), (4, pt_html)]:
            runs = _parse_runs(raw_html, base_bold, base_color, base_size)
            _write_content_cell(
                ws, wb, excel_row, col_idx,
                runs, base_bold, base_color, base_size,
                content_fmt, run_fmt_cache,
            )

        # Col F: format type
        ws.write(excel_row, 5, format_type, fmts["format_type"])

        # Col G: section ID (only on first written row of each section)
        if is_first_written and current_section_id is not None:
            ws.write(excel_row, 6, current_section_id, fmts["section_id"])
        else:
            ws.write_blank(excel_row, 6, None, fmts["section_id"])

        # Col H: empty
        ws.write_blank(excel_row, 7, None, fmts["empty"])

        ws.set_row(excel_row, 60)
        excel_row += 1

    # Close last section span
    if span_start is not None:
        section_spans.append((span_start, excel_row - 1, span_name, span_type))

    # Write column A: merge rows that belong to the same section
    for start_r, end_r, sec_name, sec_type in section_spans:
        is_structural = sec_type in STRUCTURAL_SECTIONS
        sec_fmt = fmts["section_name_structural"] if is_structural else fmts["section_name"]
        if end_r > start_r:
            ws.merge_range(start_r, 0, end_r, 0, sec_name, sec_fmt)
        else:
            ws.write(start_r, 0, sec_name, sec_fmt)

    logging.info(f"Secciones generado: {excel_row - 1} filas de contenido")

    city_slug = _extract_city_slug(export_request.lp_url_slug)
    proyecto = (export_request.template_info.proyecto or "").lower()
    is_viajemos = "viajemos" in proyecto or "vjm" in proyecto

    _add_imagenes_sheet(wb, city_slug)
    _add_precios_agencias_sheet(wb, city_slug)
    _add_imagenes_secciones_sheet(wb, city_slug, is_viajemos=is_viajemos)
    _add_categoria_flota_sheet(wb)
    _add_companies_sheet(wb)
    _add_agencias_sheet(wb)
    _add_formato_contenido_sheet(wb)
    _add_fuente_textos_sheet(wb)

    wb.close()
    buffer.seek(0)
    return buffer


_CITY_EXCLUDE = {
    "proyecto", "template", "landing", "page", "car", "rental", "rent",
    "renta", "alquiler", "autos", "coches", "carros", "de", "en", "in",
    "the", "a", "an", "y", "and", "best", "top", "cheap", "affordable",
    "canada", "canadá", "usa", "mexico", "méxico", "viajemos", "vjm",
    "mcr", "can", "com", "www",
}


def _extract_city_slug(hint: Optional[str]) -> str:
    """Derive a lowercase city slug from any hint string.

    Handles:
      - URL paths: '/en/cars/can/ottawa/' → 'ottawa'
      - Hyphenated slugs: 'ottawa-vjm-can' → 'ottawa'
      - SEO titles: 'Car Rental in Ottawa | VJM' → 'ottawa'
      - Plain city names: 'Ottawa' → 'ottawa'
    Returns 'ottawa' as fallback.
    """
    if not hint:
        return "ottawa"

    text = hint.strip()

    # URL-style: take last non-empty path segment, then first hyphen word
    if "/" in text:
        segments = [s for s in text.strip("/").split("/") if s]
        if segments:
            candidate = segments[-1].lower().split("-")[0]
            if candidate and candidate not in _CITY_EXCLUDE:
                return candidate

    # Pure slug (no spaces): 'ottawa-vjm-can' → first hyphen word
    if "-" in text and " " not in text:
        candidate = text.lower().split("-")[0]
        if candidate and candidate not in _CITY_EXCLUDE:
            return candidate

    # Title-style: look for proper noun directly after "en"/"in" (location preposition)
    # e.g. 'Alquiler de autos Enterprise en Miami, Florida' → 'Miami'
    # e.g. 'Car Rental in Ottawa | VJM' → 'Ottawa'
    main = text.split("|")[0]
    m = re.search(r"\b(?:en|in)\s+([A-Z][a-záéíóúüñ]+)", main)
    if m:
        return m.group(1).lower()

    # Fallback: first capitalized proper noun not in the exclude list
    for word in re.findall(r"\b([A-Z][a-záéíóúüñ]+)\b", main):
        if word.lower() not in _CITY_EXCLUDE:
            return word.lower()

    # Last resort: first word of the hint
    first = text.lower().split()[0] if text.split() else ""
    return first if first and first not in _CITY_EXCLUDE else "ottawa"


def _add_imagenes_sheet(wb, city_slug: str = "ottawa") -> None:
    """Add ImagenesComponente sheet to the workbook with city-specific content."""
    ws = wb.add_worksheet("ImagenesComponente")

    border     = {"border": 1}
    wrap_left  = {"text_wrap": True, "align": "left",   "valign": "top"}
    wrap_center = {"text_wrap": True, "align": "center", "valign": "vcenter"}

    hdr_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 11,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    cell_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10, "font_color": C_BLACK,
        **wrap_left, **border,
    })

    headers = [
        "RELACION SECCION",
        "ORDEN DE COMPONENTE",
        "IMAGEN (webp)",
        "IMAGEN ALT(INGLES)",
        "IMAGEN TITLE(INGLES)",
        "IMAGEN ALT(ESPAÑOL)",
        "IMAGEN TITLE(ESPAÑOL)",
        "IMAGEN ALT(PORTUGUES)",
        "IMAGEN TITLE(PORTUGUES)",
        "HREF(INGLES)",
        "HREF(ESPAÑOL)",
        "HREF(PORTUGUES)",
    ]

    col_widths = [16, 18, 26, 50, 50, 55, 55, 55, 55, 28, 28, 28]
    for i, w in enumerate(col_widths):
        ws.set_column(i, i, w)

    ws.set_row(0, 30)
    for i, h in enumerate(headers):
        ws.write(0, i, h, hdr_fmt)
    ws.freeze_panes(1, 0)

    rows = [
        # agencies
        ["agencies", 1, "ottawa-vjm-agencia-1.webp",
         "We're strategic allies with the most prestigious agencies in Ottawa",
         "We work with the top car rental companies in Ottawa",
         "Somos aliados estratégicos de las agencias de alquiler de autos más prestigiosas de Ottawa",
         "Trabajamos con las compañías de renta de coches más destacadas de Ottawa",
         "Somos pareceiros estratégicos das locadoras de carros mais prestigiadas de Ottawa",
         "Trabalhamos com as locadoras de veículos mais proeminentes em Ottawa",
         "", "", ""],
        ["agencies", 2, "ottawa-vjm-agencia-2.webp",
         "We connect you with the best car rental agencies in Ottawa",
         "Discover the most competitive rates on car rentals with the best agencies in Ottawa",
         "Te conectamos con las mejores empresas de renta de coches de Ottawa",
         "Conoce las tarifas más competitivas de las agencias de alquiler de autos en Ottawa",
         "Nós conectamos você com as melhores locadoras de carros em Ottawa",
         "Conheça sobre os preços atrativos das locadoras de veículos em Ottawa",
         "", "", ""],
        # carRental
        ["carRental", 1, "economicos-vjm.webp",
         "Economy car rental in Ottawa",
         "Rent a car in Ottawa",
         "Alquiler de autos compactos en Ottawa para ahorrar al máximo",
         "Renta un auto compacto en Ottawa y ajusta tu presupuesto",
         "Alugue um carro compacto em Ottawa para economizar muito",
         "Alugue um carro compacto em Ottawa e ajuste seu orçamento",
         "/en/cars/can/economy", "/es/autos/can/economicos", "/pt/carros/can/economicos"],
        ["carRental", 2, "camionetas-vjm.webp",
         "SUV Rentals in Ottawa at the best price",
         "Rent an SUV in Ottawa and feel the power on the road",
         "Renta una SUV en Ottawa al mejor precio",
         "Alquila SUVs en Ottawa con espacio, potencia y confort",
         "Alugue um SUV em Ottawa ao melhor preço",
         "Alugue SUVs em Ottawa com espaço, potência e conforto",
         "/en/cars/can/suv", "/es/autos/can/suv", "/pt/carros/can/suv"],
        ["carRental", 3, "vans-vjm.webp",
         "Rent a van in Ottawa and embark on an adventure",
         "Book a Van in Ottawa for your family trips",
         "Alquila una van en Ottawa para viajar con amigos",
         "Renta una van y lleva maletas cómodamente en Ottawa",
         "Alugue uma van em Ottawa para viajar com amigos",
         "Alugue uma van e leve malas confortavelmente em Ottawa",
         "/en/cars/can/minivan", "/es/autos/can/minivan", "/pt/carros/can/minivan"],
        ["carRental", 4, "convertibles-vjm.webp",
         "Travel with style with a convertible rental in Ottawa",
         "Rent a convertible in Ottawa and steal the spotlight",
         "Alquila un descapotable en Ottawa y siente la brisa",
         "Renta un descapotable con estilo por las calles de Ottawa",
         "Alugue um conversível em Ottawa e sinta a brisa",
         "Alugue um conversível com estilo pelas ruas de Ottawa",
         "/en/cars/can/convertible", "/es/autos/can/convertibles", "/pt/carros/can/conversivel"],
        ["carRental", 5, "lujo-vjm.webp",
         "Discover a word of distiction with a luxury car rental in Ottawa",
         "Rent luxury car in Ottawa and add a touch of elegance to your trip",
         "Alquiler de autos de lujo en Ottawa",
         "Renta de autos premium para citas de negocio",
         "Aluguel de carros de luxo em Ottawa",
         "Locação de carros premium em Ottawa para encontros de negócios",
         "/en/cars/can/luxury", "/es/autos/can/lujo", "/pt/carros/can/luxo"],
        # favoriteCities
        ["favoriteCities", 1, "toronto-vjm-cluster.webp",
         "Car rental in Toronto",
         "Car rental in Toronto",
         "Alquiler de autos en Toronto",
         "Renta de autos en Toronto",
         "Aluguel de carro em Toronto",
         "Locação de carros em Toronto",
         "/en/cars/can/toronto/", "/es/autos/can/toronto/", "/pt/carros/can/toronto/"],
        ["favoriteCities", 2, "montreal-vjm-cluster.webp",
         "Rent a car in Montreal and enjoy the cultural fusion",
         "Rent a car with French charm in Montreal",
         "Renta un auto en Montreal y disfruta la fusión cultural",
         "Alquila coche con encanto francés en Montreal",
         "Alugue um carro em Montreal e desfrute da fusão cultural",
         "Arrenda um carro com charme francês em Montreal",
         "/en/cars/can/montreal/", "/es/autos/can/montreal/", "/pt/carros/can/montreal/"],
        ["favoriteCities", 3, "quebec-vjm-cluster.webp",
         "Affordable car rental in Quebec to explore its charm",
         "Rent a vehicle and discover Quebec's natural landscapes",
         "Alquiler de autos asequibles en Quebec para explorar su encanto",
         "Renta un vehículo y descubre los paisajes naturales de Quebec",
         "Aluguel de carros acessíveis no Quebec para explorar seu charme",
         "Alugue um veículo e descubra as paisagens naturais do Quebec",
         "/en/cars/can/quebec/", "/es/autos/can/quebec/", "/pt/carros/can/quebec/"],
        ["favoriteCities", 4, "vancouver-vjm-cluster.webp",
         "Rent a car in Vancouver to explore Lynn Canyon Park",
         "Rent a car in Vancouver and hike forest trails at Lynn Canyon",
         "Renta un auto en Vancouver para explorar Lynn Canyon Park",
         "Alquila un coche en Vancouver y recorre senderos boscosos de Lynn Canyon",
         "Alugue um carro em Vancouver para explorar o Lynn Canyon Park",
         "Alugue um veículo em Vancouver e percorra trilhas boscosas no Lynn Canyon",
         "/en/cars/can/vancouver/", "/es/autos/can/vancouver/", "/pt/carros/can/vancouver/"],
        ["favoriteCities", 5, "calgary-vjm-cluster.webp",
         "car rental in Calgary to visit the Rocky Mountains",
         "rent a car and discover the majestic Rocky Mountains",
         "alquiler de carros en Calgary para visitar las Montañas Rocosas",
         "renta un carro y descubre las majestuosas Montañas Rocosas",
         "aluguel de carros em Calgary para visitar as Montanhas Rochosas",
         "alugue um carro e descubra as majestosas Montanhas Rochosas",
         "/en/cars/can/calgary/", "/es/autos/can/calgary/", "/pt/carros/can/calgary/"],
        ["favoriteCities", 6, "edmonton-vjm-cluster.webp",
         "Rent a car in Edmonton and discover its culture",
         "Rent a car in Alberta to explore the cultural scene",
         "Alquila un auto en Edmonton y descubre su cultura",
         "Renta coche en Alberta para explorar la escena cultural",
         "Alugue um carro em Edmonton e descubra sua cultura",
         "Alugue carro na Alberta para explorar a cena cultural",
         "/en/cars/can/edmonton/", "/es/autos/can/edmonton/", "/pt/carros/can/edmonton/"],
        ["favoriteCities", 7, "halifax-vjm-cluster.webp",
         "Fast vehicle rental in Halifax",
         "Car rental with views of historic ports",
         "Alquiler rápido de vehículos en Halifax",
         "Renta de coches con vistas a puertos históricos",
         "Aluguel rápido de veículos em Halifax",
         "Aluguel de carros com vista para portos históricos",
         "/en/cars/can/halifax/", "/es/autos/can/halifax/", "/pt/carros/can/halifax/"],
    ]

    city_name = city_slug.capitalize()

    def _replace_city(val):
        if isinstance(val, str):
            return val.replace("ottawa", city_slug).replace("Ottawa", city_name)
        return val

    for r_idx, row_data in enumerate(rows, start=1):
        ws.set_row(r_idx, 45)
        for c_idx, val in enumerate(row_data):
            ws.write(r_idx, c_idx, _replace_city(val), cell_fmt)


def _add_precios_agencias_sheet(wb, city_slug: str = "ottawa") -> None:
    """Add PreciosAgencias sheet with agency pricing data, replacing city name dynamically."""
    ws = wb.add_worksheet("PreciosAgencias")

    border      = {"border": 1}
    wrap_center = {"text_wrap": True, "align": "center", "valign": "vcenter"}
    wrap_left   = {"text_wrap": True, "align": "left",   "valign": "vcenter"}

    title_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 14,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    hdr_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 11,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    agency_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_center, **border,
    })
    price_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_center, **border,
    })
    text_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_left, **border,
    })

    col_widths = [14, 8, 38, 38, 38, 24, 24, 24]
    for i, w in enumerate(col_widths):
        ws.set_column(i, i, w)

    # Row 0: big merged title
    ws.set_row(0, 30)
    ws.merge_range(0, 0, 0, 7, "PRECIOS POR AGENCIAS", title_fmt)

    # Row 1: column headers with autofilter
    ws.set_row(1, 30)
    headers = [
        "AGENCIA", "PRECIO",
        "TITULO (INGLES)", "TITULO (ESPAÑOL)", "TITULO (PORTUGUES)",
        "HREF (INGLES)", "HREF (ESPAÑOL)", "HREF (PORTUGUES)",
    ]
    for i, h in enumerate(headers):
        ws.write(1, i, h, hdr_fmt)
    ws.autofilter(1, 0, 1, 7)

    city_name = city_slug.capitalize()

    agencies = [
        ("AL_Alamo",      9,  "Alamo Rent a Car in Ottawa",      "Alamo Rent a Car en Ottawa",      "Alamo Rent a Car em Ottawa",      "/en/cars/can/alamo",      "/es/autos/can/alamo",      "/pt/carros/can/alamo"),
        ("ZI_Avis",       11, "Avis Rent a Car in Ottawa",       "Avis Rent a Car en Ottawa",       "Avis Rent a Car em Ottawa",       "/en/cars/can/avis",       "/es/autos/can/avis",       "/pt/carros/can/avis"),
        ("ZD_Budget",     8,  "Budget Rent a Car in Ottawa",     "Budget Rent a Car en Ottawa",     "Budget Rent a Car em Ottawa",     "/en/cars/can/budget",     "/es/autos/can/budget",     "/pt/carros/can/budget"),
        ("ZR_Dollar",     10, "Dollar Rent a Car in Ottawa",     "Dollar Rent a Car en Ottawa",     "Dollar Rent a Car em Ottawa",     "/en/cars/can/dollar",     "/es/autos/can/dollar",     "/pt/carros/can/dollar"),
        ("ET_Enterprise", 10, "Enterprise Rent a Car in Ottawa", "Enterprise Rent a Car en Ottawa", "Enterprise Rent a Car em Ottawa", "/en/cars/can/enterprise", "/es/autos/can/enterprise", "/pt/carros/can/enterprise"),
        ("ZE_Hertz",      10, "Hertz Rent a Car in Ottawa",      "Hertz Rent a Car en Ottawa",      "Hertz Rent a Car em Ottawa",      "/en/cars/can/hertz",      "/es/autos/can/hertz",      "/pt/carros/can/hertz"),
        ("ZL_National",   13, "National Rent a Car in Ottawa",   "National Rent a Car en Ottawa",   "National Rent a Car em Ottawa",   "/en/cars/can/national",   "/es/autos/can/national",   "/pt/carros/can/national"),
        ("ZA_Payless",    8,  "Payless Rent a Car in Ottawa",    "Payless Rent a Car en Ottawa",    "Payless Rent a Car em Ottawa",    "/en/cars/can/payless",    "/es/autos/can/payless",    "/pt/carros/can/payless"),
        ("SX_Sixt",       12, "Sixt Rent a Car in Ottawa",       "Sixt Rent a Car en Ottawa",       "Sixt Rent a Car em Ottawa",       "/en/cars/can/sixt",       "/es/autos/can/sixt",       "/pt/carros/can/sixt"),
        ("ZT_Thrifty",    10, "Thrifty Rent a Car in Ottawa",    "Thrifty Rent a Car en Ottawa",    "Thrifty Rent a Car em Ottawa",    "/en/cars/can/thrifty",    "/es/autos/can/thrifty",    "/pt/carros/can/thrifty"),
    ]

    def _rc(val):
        if isinstance(val, str):
            return val.replace("Ottawa", city_name).replace("ottawa", city_slug)
        return val

    for r_idx, (agency, precio, en, es, pt, href_en, href_es, href_pt) in enumerate(agencies, start=2):
        ws.set_row(r_idx, 20)
        ws.write(r_idx, 0, agency,          agency_fmt)
        ws.write(r_idx, 1, precio,          price_fmt)
        ws.write(r_idx, 2, _rc(en),         text_fmt)
        ws.write(r_idx, 3, _rc(es),         text_fmt)
        ws.write(r_idx, 4, _rc(pt),         text_fmt)
        ws.write(r_idx, 5, href_en,         text_fmt)
        ws.write(r_idx, 6, href_es,         text_fmt)
        ws.write(r_idx, 7, href_pt,         text_fmt)


def _add_imagenes_secciones_sheet(wb, city_slug: str = "ottawa", is_viajemos: bool = True) -> None:
    """Add ImagenesSecciones sheet with section-level hero images."""
    ws = wb.add_worksheet("ImagenesSecciones")

    border      = {"border": 1}
    wrap_center = {"text_wrap": True, "align": "center", "valign": "vcenter"}
    wrap_left   = {"text_wrap": True, "align": "left",   "valign": "vcenter"}

    title_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 14,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    hdr_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 11,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    section_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_center, **border,
    })
    text_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_left, **border,
    })

    col_widths = [18, 28, 42, 42, 42, 42, 42, 42]
    for i, w in enumerate(col_widths):
        ws.set_column(i, i, w)

    # Row 0: merged title
    ws.set_row(0, 30)
    ws.merge_range(0, 0, 0, 7, "IMÁGENES SECCION", title_fmt)

    # Row 1: column headers
    ws.set_row(1, 30)
    headers = [
        "RELACION SECCION", "IMAGEN (webp)",
        "IMAGEN ALT(INGLES)", "IMAGEN TITLE(INGLES)",
        "IMAGEN ALT(ESPAÑOL)", "IMAGEN TITLE(ESPAÑOL)",
        "IMAGEN ALT(PORTUGUES)", "IMAGEN TITLE(PORTUGUES)",
    ]
    for i, h in enumerate(headers):
        ws.write(1, i, h, hdr_fmt)
    ws.autofilter(1, 0, 1, 7)

    city_name = city_slug.capitalize()

    if is_viajemos:
        rows = [
            ("quicksearch", "ottawa-vjm.webp",
             "Car rentals in Ottawa",       "Rent a car in Ottawa",
             "Renta de carros en Ottawa",   "Alquila un auto en Ottawa",
             "Aluguel de carros em Ottawa", "Locação de veículos em Ottawa"),
        ]
    else:
        # Miles Car Rental: usa prefijo ContentLp/, sufijo -mcr y fila extra TrustPilot
        rows = [
            ("quicksearch", "ContentLp/ottawa-mcr.webp",
             "Car rentals in Ottawa",       "Car rentals in Ottawa",
             "Renta de carros en Ottawa",   "Alquiler de autos en Ottawa",
             "Aluguel de carros em Ottawa", "Locação de veículos em Ottawa"),
            ("TrustPilot", "ContentLp/ottawa-mcr-opiniones.webp",
             "Reviews about car rentals in Ottawa",
             "Customer reviews about car rentals in Ottawa",
             "Comentarios de clientes acerca del alquiler de automóviles en Ottawa",
             "Reseñas de usuarios sobre renta de carros en Ottawa",
             "Opiniões de clientes sobre aluguel de carros em Ottawa",
             "Comentários de clientes sobre locação de veículos em Ottawa"),
        ]

    def _rc(val):
        if isinstance(val, str):
            return val.replace("Ottawa", city_name).replace("ottawa", city_slug)
        return val

    for r_idx, (section, imagen, alt_en, title_en, alt_es, title_es, alt_pt, title_pt) in enumerate(rows, start=2):
        ws.set_row(r_idx, 45)
        ws.write(r_idx, 0, section,          section_fmt)
        ws.write(r_idx, 1, _rc(imagen),      text_fmt)
        ws.write(r_idx, 2, _rc(alt_en),      text_fmt)
        ws.write(r_idx, 3, _rc(title_en),    text_fmt)
        ws.write(r_idx, 4, _rc(alt_es),      text_fmt)
        ws.write(r_idx, 5, _rc(title_es),    text_fmt)
        ws.write(r_idx, 6, _rc(alt_pt),      text_fmt)
        ws.write(r_idx, 7, _rc(title_pt),    text_fmt)


def _add_categoria_flota_sheet(wb) -> None:
    """Add categoriaFlotaVehiculos sheet with predefined vehicle fleet categories."""
    ws = wb.add_worksheet("categoriaFlotaVehiculos")

    border      = {"border": 1}
    wrap_center = {"text_wrap": True, "align": "center", "valign": "vcenter"}
    wrap_left   = {"text_wrap": True, "align": "left",   "valign": "vcenter"}

    title_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 12,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    hdr_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 11,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    cell_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_left, **border,
    })

    ws.set_column(0, 0, 40)

    # Row 0: merged title
    ws.set_row(0, 40)
    ws.write(0, 0, "CATEGORIAS DE FLOTA HABILITADAS EN EL LANDINGPAGE", title_fmt)

    # Row 1: column header with autofilter
    ws.set_row(1, 25)
    ws.write(1, 0, "CATEGORIA", hdr_fmt)
    ws.autofilter(1, 0, 1, 0)

    categories = ["Pequeños y Medianos", "Camionetas"]

    for r_idx, cat in enumerate(categories, start=2):
        ws.set_row(r_idx, 20)
        ws.write(r_idx, 0, cat, cell_fmt)


def _add_companies_sheet(wb) -> None:
    """Add Companies sheet with reference lists: Sitios, Miles, Viajemos, TipoSecciones, CategoriaCarros."""
    ws = wb.add_worksheet("Companies")

    border      = {"border": 1}
    wrap_center = {"text_wrap": True, "align": "center", "valign": "vcenter"}
    wrap_left   = {"text_wrap": True, "align": "left",   "valign": "vcenter"}

    hdr_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 11,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    cell_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_left, **border,
    })
    # Columns: A(0)=Sitios, B(1)=spacer, C(2)=Miles, D(3)=spacer,
    #          E(4)=Viajemos, F(5)=spacer, G(6)=TipoSecciones, H(7)=spacer, I(8)=CategoriaCarros
    col_widths = [18, 3, 28, 3, 30, 3, 22, 3, 24]
    for i, w in enumerate(col_widths):
        ws.set_column(i, i, w)

    SITIOS        = 0
    MILES         = 2
    VIAJEMOS      = 4
    TIPO_SECCIONES = 6
    CATEGORIA_CARROS = 8

    columns = {
        SITIOS: "Sitios",
        MILES:  "Miles",
        VIAJEMOS: "Viajemos",
        TIPO_SECCIONES: "TipoSecciones",
        CATEGORIA_CARROS: "CategoriaCarros",
    }

    sitios_data = [
        "Miles",
        "Viajemos",
    ]

    miles_data = [
        "miles_alemania", "miles_espana", "miles_francia", "miles_italia",
        "miles_portugal", "miles_uk", "milescarrental_atlanta", "milescarrental_brasil",
        "milescarrental_com", "milescarrental_dallas", "milescarrental_eu",
        "milescarrental_fort_lauderdale", "milescarrental_houston",
        "milescarrental_las_vegas", "milescarrental_los_angeles",
        "milescarrental_mexico", "milescarrental_miami", "milescarrental_new_york",
        "milescarrental_orlando", "milescarrental_palm_beach", "milescarrental_san_diego",
        "milescarrental_san_francisco", "milescarrental_tampa",
    ]

    viajemos_data = [
        "viajemos", "viajemos_argentina", "viajemos_bolivia", "viajemos_brasil",
        "viajemos_canada", "viajemos_chile", "viajemos_colombia", "viajemos_costa_rica",
        "viajemos_ecuador", "viajemos_espana", "viajemos_guatemala", "viajemos_honduras",
        "viajemos_mexico", "viajemos_nicaragua", "viajemos_panama", "viajemos_paraguay",
        "viajemos_peru", "viajemos_portugal", "viajemos_puerto_rico",
        "viajemos_republica_dominicana", "viajemos_salvador", "viajemos_uk",
        "viajemos_uruguay", "viajemos_venezuela",
    ]

    tipo_secciones_data = [
        "agencies", "agencyLogos", "bestHotels", "carRental", "favoriteCities",
        "featuredCar", "hotelEuropa", "HotelPrice", "hotels", "locationscarrusel",
        "quicksearch", "rentalCarFaqs", "rentcompanies", "sectionCars", "typeCars",
        "worldCars", "worldTourism",
    ]

    categoria_carros_data = [
        "Pequeños y Medianos", "Grandes", "Lujo", "Vans",
        "Camionetas", "Deportivos", "Híbridos y Eléctricos", "Pickups",
    ]

    all_data = {
        SITIOS:           sitios_data,
        MILES:            miles_data,
        VIAJEMOS:         viajemos_data,
        TIPO_SECCIONES:   tipo_secciones_data,
        CATEGORIA_CARROS: categoria_carros_data,
    }

    # Row 0: headers + autofilter per column
    ws.set_row(0, 25)
    for col_idx, label in columns.items():
        ws.write(0, col_idx, label, hdr_fmt)
        ws.autofilter(0, col_idx, 0, col_idx)

    # Data rows
    max_rows = max(len(v) for v in all_data.values())
    for r_idx in range(max_rows):
        ws.set_row(r_idx + 1, 18)
        for col_idx, data in all_data.items():
            if r_idx < len(data):
                ws.write(r_idx + 1, col_idx, data[r_idx], cell_fmt)
            else:
                ws.write_blank(r_idx + 1, col_idx, None, cell_fmt)


def _add_agencias_sheet(wb) -> None:
    """Add Agencias sheet with the list of agency codes."""
    ws = wb.add_worksheet("Agencias")

    border     = {"border": 1}
    wrap_center = {"text_wrap": True, "align": "center", "valign": "vcenter"}
    wrap_left   = {"text_wrap": True, "align": "left",   "valign": "vcenter"}

    hdr_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 11,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    cell_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_left, **border,
    })

    ws.set_column(0, 0, 22)
    ws.set_row(0, 25)
    ws.write(0, 0, "Agency", hdr_fmt)
    ws.autofilter(0, 0, 0, 0)

    agencies = [
        "AL_Alamo", "EP_Europcar", "ET_Enterprise", "FX_Fox", "KD_Keddy",
        "MX_Mex Rent a Car", "SX_Sixt", "ZA_Payless", "ZD_Budget",
        "ZE_Hertz", "ZI_Avis", "ZL_National", "ZR_Dollar", "ZT_Thrifty",
    ]

    for r_idx, agency in enumerate(agencies, start=1):
        ws.set_row(r_idx, 18)
        ws.write(r_idx, 0, agency, cell_fmt)


def _add_formato_contenido_sheet(wb) -> None:
    """Add FormatoContenido sheet with the list of content format types."""
    ws = wb.add_worksheet("FormatoContenido")

    border      = {"border": 1}
    wrap_center = {"text_wrap": True, "align": "center", "valign": "vcenter"}
    wrap_left   = {"text_wrap": True, "align": "left",   "valign": "vcenter"}

    hdr_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 11,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    cell_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_left, **border,
    })

    ws.set_column(0, 0, 24)
    ws.set_row(0, 25)
    ws.write(0, 0, "TipoFormato", hdr_fmt)
    ws.autofilter(0, 0, 0, 0)

    formats = [
        "section_title", "section_content",
        "section_content_ip_us", "section_content_ip_br",
        "section_disclaimer",
        "component_title", "component_content",
        "FAQS_question", "FAQS_answer",
        "FAQS_question", "FAQS_answer",
        "FAQS_question", "FAQS_answer",
        "FAQS_question", "FAQS_answer",
    ]

    for r_idx, fmt in enumerate(formats, start=1):
        ws.set_row(r_idx, 18)
        ws.write(r_idx, 0, fmt, cell_fmt)


def _add_fuente_textos_sheet(wb) -> None:
    """Add FuenteTextos sheet with Viajemos brand color reference."""
    ws = wb.add_worksheet("FuenteTextos")

    border      = {"border": 1}
    wrap_center = {"text_wrap": True, "align": "center", "valign": "vcenter"}
    wrap_left   = {"text_wrap": True, "align": "left",   "valign": "vcenter"}

    hdr_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 11,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    name_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_left, **border,
    })
    hex_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_center, **border,
    })

    ws.set_column(0, 0, 20)
    ws.set_column(1, 1, 12)
    ws.set_column(2, 2, 14)

    ws.set_row(0, 25)
    ws.write(0, 0, "Viajemos", hdr_fmt)
    ws.write(0, 1, "Columna",  hdr_fmt)
    ws.write(0, 2, "Columna",  hdr_fmt)

    rows = [
        ("Azul Negrilla",   "#0583ff"),
        ("Marado Negrilla", "#8154ef"),
        ("Verde Negrilla",  "#00b000"),
    ]

    for r_idx, (label, hex_color) in enumerate(rows, start=1):
        preview_fmt = wb.add_format({
            "bold": True, "font_name": "Calibri", "font_size": 10,
            "font_color": hex_color, "bg_color": C_WHITE,
            **wrap_center, **border,
        })
        ws.set_row(r_idx, 18)
        ws.write(r_idx, 0, label,      name_fmt)
        ws.write(r_idx, 1, hex_color,  hex_fmt)
        ws.write(r_idx, 2, "Prueba",   preview_fmt)


def _add_landing_page_sheet(wb, export_request: models.ExportExcelRequest) -> None:
    """Add LandingPage sheet as the first sheet in the workbook."""
    ws = wb.add_worksheet("LandingPage")

    border      = {"border": 1}
    wrap_center = {"text_wrap": True, "align": "center", "valign": "vcenter"}
    wrap_left   = {"text_wrap": True, "align": "left",   "valign": "vcenter"}

    title_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 16,
        "font_color": C_HEADER_FG, "bg_color": C_HEADER_BG,
        **wrap_center, **border,
    })
    hdr_fmt = wb.add_format({
        "bold": True, "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_center, **border,
    })
    cell_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        **wrap_left, **border,
    })
    num_fmt = wb.add_format({
        "font_name": "Calibri", "font_size": 10,
        "font_color": C_BLACK, "bg_color": C_WHITE,
        "num_format": "#,##0.00", **wrap_center, **border,
    })

    col_widths = [18, 18, 30, 12, 12, 30, 38, 30, 38, 30, 38]
    for i, w in enumerate(col_widths):
        ws.set_column(i, i, w)

    # Row 0: merged title spanning all 11 columns
    ws.set_row(0, 35)
    ws.merge_range(0, 0, 0, 10, "LANDINGPAGE", title_fmt)

    # Row 1: column headers
    ws.set_row(1, 30)
    headers = [
        "Nombre del sitio", "Dominio", "Url LandingPage",
        "HighPrice", "LowPrice",
        "Meta titulo (Ingles)", "Meta descripción (Ingles)",
        "Meta titulo(español)", "Meta descripción(Español)",
        "Meta titulo (Portugues)", "Meta descripción (Portugues)",
    ]
    for i, h in enumerate(headers):
        ws.write(1, i, h, hdr_fmt)

    # Row 2: one data row pre-filled from the request
    info    = export_request.template_info
    proyecto = (info.proyecto or "").lower()
    is_viajemos = "viajemos" in proyecto or "vjm" in proyecto

    nombre_sitio = "Viajemos" if is_viajemos else "Miles Car Rental"
    dominio      = "viajemos" if is_viajemos else "milescarrental"
    city_slug    = _extract_city_slug(export_request.lp_url_slug)
    url_lp       = f"es/autos/can/{city_slug}/" if is_viajemos else f"/en/cars/can/{city_slug}/"

    ws.set_row(2, 22)
    ws.write(2, 0,  nombre_sitio, cell_fmt)
    ws.write(2, 1,  dominio,      cell_fmt)
    ws.write(2, 2,  url_lp,       cell_fmt)
    # HighPrice and LowPrice left empty for the user to fill
    ws.write_blank(2, 3,  None, num_fmt)
    ws.write_blank(2, 4,  None, num_fmt)
    # Meta fields left empty
    for col in range(5, 11):
        ws.write_blank(2, col, None, cell_fmt)
