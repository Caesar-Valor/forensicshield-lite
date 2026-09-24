# =============================================
# ForensicShield Lite — pdf_generator.py
# Genera reportes PDF de auditoría de seguridad
# =============================================

from fpdf import FPDF
from datetime import datetime
import os

# Rutas de recursos
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "..", "img", "forense2.png")
OUT_DIR   = os.path.join(BASE_DIR, "reports")

# Paleta de colores — terminal verde ForensicShield
COLOR_DARK    = (6,   13,  8)        # #060d08
COLOR_ACCENT  = (34,  197, 94)       # #22c55e
COLOR_ACCENT2 = (22,  163, 74)       # #16a34a  (hover)
COLOR_WHITE   = (255, 255, 255)
COLOR_LIGHT   = (240, 247, 241)      # fondo alterno de filas
COLOR_MUTED   = (82,  122, 88)       # #527a58
COLOR_BORDER  = (34,  197, 94, 30)   # borde sutil verde

# Colores de riesgo
RIESGO_COLOR = {
    "critico": (239, 68,  68),
    "alto":    (249, 115, 22),
    "medio":   (234, 179,  8),
    "bajo":    ( 34, 197, 94),
    "ninguno": (100, 116, 139),
}

ESTADO_COLOR = {
    "open":     ( 34, 197, 94),
    "closed":   (100, 116, 139),
    "filtered": (234, 179,  8),
}

URGENCIA_LABEL = {
    "inmediata": "INMEDIATA",
    "alta":      "ALTA",
    "media":     "MEDIA",
    "baja":      "BAJA",
}


def asegurar_directorio():
    os.makedirs(OUT_DIR, exist_ok=True)


def _safe(text: str) -> str:
    """Convierte texto a Latin-1 seguro para las fuentes built-in de fpdf2."""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "\u2014": "-",   # em dash —
        "\u2013": "-",   # en dash –
        "\u2012": "-",   # figure dash
        "\u2011": "-",   # non-breaking hyphen
        "\u2010": "-",   # hyphen
        "\u201c": '"',   # " left double quote
        "\u201d": '"',   # " right double quote
        "\u2018": "'",   # ' left single quote
        "\u2019": "'",   # ' right single quote
        "\u2026": "...", # … ellipsis
        "\u00b7": ".",   # · middle dot
        "\u2022": "-",   # • bullet
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Eliminar cualquier otro caracter fuera de Latin-1
    return text.encode("latin-1", errors="replace").decode("latin-1")


class ForensicPDF(FPDF):
    """FPDF personalizado con header y footer de ForensicShield."""

    def __init__(self, numero_reporte: str, analista: str):
        super().__init__()
        self.numero_reporte = numero_reporte
        self.analista       = analista
        self.set_auto_page_break(auto=True, margin=18)

    # ── Header (aparece en páginas 2+) ──────────────────────────────
    def header(self):
        if self.page_no() == 1:
            return
        # Barra superior oscura
        self.set_fill_color(*COLOR_DARK)
        self.rect(0, 0, 210, 13, "F")
        # Línea de acento verde
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(0, 13, 210, 0.6, "F")
        # Texto del header
        self.set_y(2.5)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*COLOR_ACCENT)
        self.cell(0, 8, "FORENSICSHIELD LITE", align="L")
        self.set_text_color(180, 200, 182)
        self.set_font("Helvetica", "", 7)
        self.cell(0, 8, f"Reporte {self.numero_reporte}  |  Pág. {self.page_no()}", align="R")
        self.ln(14)

    # ── Footer ──────────────────────────────────────────────────────
    def footer(self):
        self.set_y(-12)
        self.set_draw_color(*COLOR_ACCENT)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_y(-10)
        self.set_font("Helvetica", "I", 6.5)
        self.set_text_color(*COLOR_MUTED)
        self.cell(0, 6, f"DOCUMENTO CONFIDENCIAL  |  {self.numero_reporte}  |  Generado por ForensicShield Lite", align="C")


# ── Helpers de dibujo ────────────────────────────────────────────────

def _section_title(pdf: ForensicPDF, texto: str):
    """Encabezado de sección con barra de acento verde."""
    pdf.set_fill_color(*COLOR_ACCENT)
    pdf.rect(10, pdf.get_y(), 3, 8, "F")
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*COLOR_DARK)
    pdf.cell(0, 8, texto, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _kv_row(pdf: ForensicPDF, clave: str, valor: str, fill: bool = False):
    """Fila clave-valor con fondo alterno."""
    if fill:
        pdf.set_fill_color(*COLOR_LIGHT)
    else:
        pdf.set_fill_color(*COLOR_WHITE)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.cell(55, 7, clave.upper(), fill=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*COLOR_DARK)
    pdf.cell(0, 7, valor, fill=True, new_x="LMARGIN", new_y="NEXT")


def _badge(pdf: ForensicPDF, texto: str, color_rgb: tuple, x: float, y: float, w: float = 28):
    """Dibuja un badge de color con texto."""
    pdf.set_xy(x, y + 1)
    pdf.set_fill_color(*color_rgb)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(w, 5.5, texto.upper(), align="C", fill=True)
    pdf.set_text_color(*COLOR_DARK)


def _info_card(pdf: ForensicPDF, etiqueta: str, valor: str, x: float, y: float, w: float = 85):
    """Tarjeta de información con etiqueta y valor."""
    pdf.set_xy(x, y)
    pdf.set_fill_color(*COLOR_LIGHT)
    pdf.rect(x, y, w, 16, "F")
    # Línea izquierda de acento
    pdf.set_fill_color(*COLOR_ACCENT)
    pdf.rect(x, y, 2, 16, "F")
    # Etiqueta
    pdf.set_xy(x + 4, y + 2)
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.cell(w - 4, 5, _safe(etiqueta.upper()))
    # Valor
    pdf.set_xy(x + 4, y + 8)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*COLOR_DARK)
    pdf.cell(w - 4, 6, _safe(valor))


# ── Construcción de páginas ──────────────────────────────────────────

def _pagina_portada(pdf: ForensicPDF, datos: dict):
    """Página 1: portada con logo, fecha, solicitud y datos del escaneo."""
    pdf.add_page()

    # ── Fondo oscuro — zona superior ────────────────────────────────
    pdf.set_fill_color(*COLOR_DARK)
    pdf.rect(0, 0, 210, 110, "F")

    # ── Logo forense2.png — centrado, no ocupa todo el ancho ─────────
    logo_w = 70   # ancho del logo en mm
    logo_x = (210 - logo_w) / 2   # centrado horizontalmente
    logo_y = 10
    if os.path.exists(LOGO_PATH):
        try:
            pdf.image(LOGO_PATH, x=logo_x, y=logo_y, w=logo_w)
        except Exception:
            # fallback: texto si la imagen falla
            pdf.set_xy(0, 20)
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(*COLOR_ACCENT)
            pdf.cell(0, 10, "FORENSICSHIELD LITE", align="C")

    # ── Línea decorativa bajo el logo ───────────────────────────────
    pdf.set_draw_color(*COLOR_ACCENT)
    pdf.set_line_width(0.8)
    pdf.line(55, 64, 155, 64)

    # ── Título del reporte ───────────────────────────────────────────
    pdf.set_xy(0, 67)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.cell(0, 9, "REPORTE DE AUDITORÍA DE SEGURIDAD", align="C", new_x="LMARGIN", new_y="NEXT")

    # ── Número de reporte ────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.cell(0, 7, _safe(datos["numero_reporte"]), align="C", new_x="LMARGIN", new_y="NEXT")

    # ── Fecha y hora de generación ───────────────────────────────────
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(180, 220, 185)
    pdf.cell(0, 6, _safe(f"Generado el  {datos['fecha_hora']}"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    # ── Analista ─────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(120, 160, 125)
    pdf.cell(0, 5, _safe(f"Analista: {datos['analista']}"), align="C", new_x="LMARGIN", new_y="NEXT")

    # ── Zona blanca — datos del escaneo ─────────────────────────────
    pdf.set_fill_color(*COLOR_WHITE)
    pdf.rect(0, 110, 210, 187, "F")
    pdf.set_y(118)

    # ── Sección: Solicitud del análisis ─────────────────────────────
    _section_title(pdf, "SOLICITUD DE ANÁLISIS")

    # Descripción de lo que el usuario pidió
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*COLOR_MUTED)
    modo_desc = {
        "rapido":        "25 puertos más comunes",
        "completo":      "Todos los puertos (1-65535)",
        "personalizado": "Puertos definidos por el analista",
    }.get(datos.get("modo", "").lower(), "Escaneo de puertos")
    pdf.multi_cell(0, 5.5, f"Se realizó un análisis de red sobre el objetivo indicado utilizando el modo seleccionado por el analista. "
                           f"A continuación se detalla la configuración de la solicitud y los resultados obtenidos.")
    pdf.ln(5)

    # Tarjetas de información en dos columnas
    card_w   = 88
    card_gap = 6
    lm       = 12
    card_y   = pdf.get_y()

    _info_card(pdf, "IP / Host objetivo",   datos["target_ip"],                  lm,              card_y, card_w)
    _info_card(pdf, "Modo de escaneo",       datos["modo"].capitalize(),          lm + card_w + card_gap, card_y, card_w)

    card_y2 = card_y + 20
    _info_card(pdf, "Duración del escaneo",  f"{datos['duracion_seg']} segundos", lm,              card_y2, card_w)
    _info_card(pdf, "Descripción del modo",  modo_desc,                           lm + card_w + card_gap, card_y2, card_w)

    pdf.set_y(card_y2 + 20)
    pdf.ln(4)

    # ── Sección: Resumen de resultados ───────────────────────────────
    _section_title(pdf, "RESUMEN DE RESULTADOS")

    card_y3 = pdf.get_y()
    card_w3 = 55
    gap3    = 4

    _info_card(pdf, "Puertos abiertos",   str(datos["puertos_abiertos"]),     lm,                        card_y3, card_w3)
    _info_card(pdf, "Total analizados",   str(datos["total_puertos"]),         lm + card_w3 + gap3,       card_y3, card_w3)
    _info_card(pdf, "Cerrados / filtrados",
               str(datos["total_puertos"] - datos["puertos_abiertos"]),
               lm + 2*(card_w3 + gap3),   card_y3, card_w3)

    pdf.set_y(card_y3 + 20)
    pdf.ln(6)

    # ── Nivel de riesgo máximo ───────────────────────────────────────
    pdf.set_x(lm)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.cell(0, 5, "NIVEL DE RIESGO MÁXIMO DETECTADO", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_x(lm)
    riesgo = datos.get("riesgo_maximo", "ninguno")
    r, g, b = RIESGO_COLOR.get(riesgo, (100, 116, 139))
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(55, 10, riesgo.upper(), fill=True, align="C")

    # Descripción del nivel de riesgo
    riesgo_desc = {
        "critico": "Se detectaron puertos con vulnerabilidades críticas conocidas. Acción inmediata requerida.",
        "alto":    "Se detectaron servicios expuestos con alto potencial de explotación. Revisar urgentemente.",
        "medio":   "Se detectaron configuraciones que pueden representar riesgo. Revisar y mitigar.",
        "bajo":    "Riesgo bajo detectado. Se recomienda revisión preventiva.",
        "ninguno": "No se detectaron puertos de alto riesgo en este escaneo.",
    }.get(riesgo, "")
    pdf.set_xy(lm + 59, pdf.get_y() - 10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.multi_cell(120, 5, riesgo_desc)

    # ── Pie de portada ───────────────────────────────────────────────
    pdf.set_y(273)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.cell(0, 5, "Este documento es confidencial y está destinado exclusivamente al analista autorizado.", align="C")


def _pagina_puertos(pdf: ForensicPDF, puertos: list):
    """Página de tabla de puertos detallada."""
    pdf.add_page()
    pdf.ln(4)
    _section_title(pdf, "DETALLE DE PUERTOS ANALIZADOS")

    if not puertos:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*COLOR_MUTED)
        pdf.cell(0, 10, "No se encontraron puertos en este escaneo.", new_x="LMARGIN", new_y="NEXT")
        return

    # Cabecera de tabla
    cols = [
        ("Puerto",    18),
        ("Proto.",    16),
        ("Estado",    27),
        ("Servicio",  37),
        ("Versión",   51),
        ("Riesgo",    27),
    ]

    def _tabla_header():
        pdf.set_fill_color(*COLOR_DARK)
        pdf.set_text_color(*COLOR_ACCENT)
        pdf.set_font("Helvetica", "B", 8)
        for label, w in cols:
            pdf.cell(w, 8, label, fill=True, align="C")
        # Línea acento bajo el header
        pdf.ln()
        pdf.set_fill_color(*COLOR_ACCENT)
        pdf.rect(10, pdf.get_y(), sum(c[1] for c in cols), 0.5, "F")
        pdf.ln(0.5)

    _tabla_header()

    # Filas
    pdf.set_font("Helvetica", "", 8)
    for i, p in enumerate(puertos):
        if pdf.get_y() > 265:
            pdf.add_page()
            pdf.ln(4)
            _tabla_header()
            pdf.set_font("Helvetica", "", 8)

        fill_bg = (i % 2 == 1)
        row_h   = 7
        y_start = pdf.get_y()

        fill_color = COLOR_LIGHT if fill_bg else COLOR_WHITE
        pdf.set_fill_color(*fill_color)

        estado = p.get("estado", "")
        riesgo = p.get("riesgo", "ninguno") or "ninguno"

        # Puerto
        pdf.set_text_color(*COLOR_DARK)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(cols[0][1], row_h, str(p.get("puerto", "")), fill=fill_bg, align="C")

        # Protocolo
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(cols[1][1], row_h, (p.get("protocolo") or "TCP").upper(), fill=fill_bg, align="C")

        # Estado (con badge de color)
        x_estado = pdf.get_x()
        pdf.cell(cols[2][1], row_h, "", fill=fill_bg, align="C")
        ec = ESTADO_COLOR.get(estado, (100, 116, 139))
        label_map = {"open": "Abierto", "closed": "Cerrado", "filtered": "Filtrado"}
        _badge(pdf, label_map.get(estado, estado), ec, x_estado + 1, y_start, cols[2][1] - 2)

        # Servicio
        pdf.set_x(10 + sum(c[1] for c in cols[:3]))
        servicio = _safe(p.get("servicio") or "-")[:16]
        pdf.set_text_color(*COLOR_DARK)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(cols[3][1], row_h, servicio, fill=fill_bg)

        # Versión
        version = _safe(p.get("version") or "-")[:22]
        pdf.cell(cols[4][1], row_h, version, fill=fill_bg)

        # Riesgo (con badge de color)
        x_riesgo = pdf.get_x()
        pdf.cell(cols[5][1], row_h, "", fill=fill_bg, align="C")
        rc = RIESGO_COLOR.get(riesgo, (100, 116, 139))
        _badge(pdf, riesgo, rc, x_riesgo + 1, y_start, cols[5][1] - 2)

        pdf.ln(row_h)

    pdf.ln(4)


def _pagina_recomendaciones(pdf: ForensicPDF, recomendaciones: list):
    """Página(s) de recomendaciones — explica por qué el puerto es un riesgo y cómo cerrarlo."""
    if not recomendaciones:
        return

    pdf.add_page()
    pdf.ln(4)
    _section_title(pdf, "ANÁLISIS DE RIESGOS Y RECOMENDACIONES")

    # Introducción
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.multi_cell(0, 5, "Para cada puerto abierto detectado se detalla: el motivo por el cual representa un riesgo, "
                         "la acción recomendada para mitigarlo y el comando específico para bloquearlo en el sistema.")
    pdf.ln(5)

    for rec in recomendaciones:
        # Calcular altura estimada para evitar corte de bloque
        if pdf.get_y() > 230:
            pdf.add_page()
            pdf.ln(4)

        riesgo = rec.get("riesgo", "ninguno")
        rc     = RIESGO_COLOR.get(riesgo, (100, 116, 139))

        # ── Encabezado del bloque ─────────────────────────────────
        y_box = pdf.get_y()
        # Barra lateral de color de riesgo
        pdf.set_fill_color(*rc)
        pdf.rect(10, y_box, 3, 9, "F")
        pdf.set_x(15)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*COLOR_DARK)
        puerto_txt = _safe(f"Puerto {rec.get('puerto')}  -  {rec.get('titulo', '')}")
        pdf.multi_cell(0, 6, puerto_txt)

        # Badges: riesgo + urgencia
        pdf.set_x(15)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_fill_color(*rc)
        pdf.set_text_color(*COLOR_WHITE)
        pdf.cell(24, 5, riesgo.upper(), fill=True, align="C")

        urgencia = rec.get("urgencia", "baja")
        pdf.set_x(pdf.get_x() + 3)
        pdf.set_fill_color(*COLOR_DARK)
        pdf.cell(42, 5, f"URGENCIA: {URGENCIA_LABEL.get(urgencia, urgencia.upper())}", fill=True, align="C")
        pdf.ln(9)

        # ── ¿Por qué es un riesgo? ───────────────────────────────
        pdf.set_x(15)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*rc)
        pdf.cell(38, 5, "POR QUE ES UN RIESGO:")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*COLOR_DARK)
        pdf.set_x(53)
        # Usar multi_cell pero alineado al margen izquierdo + offset
        y_antes = pdf.get_y()
        pdf.multi_cell(0, 5, _safe(rec.get("problema", "-")))

        # ── Acción recomendada ───────────────────────────────────
        pdf.set_x(15)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*COLOR_ACCENT2)
        pdf.cell(38, 5, "COMO CERRARLO:")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*COLOR_DARK)
        pdf.set_x(53)
        pdf.multi_cell(0, 5, _safe(rec.get("accion", "-")))

        # ── Comando ──────────────────────────────────────────────
        if rec.get("comando"):
            pdf.set_x(15)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.set_text_color(*COLOR_MUTED)
            pdf.cell(0, 5, "COMANDO:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_x(15)
            # Bloque oscuro estilo terminal
            pdf.set_fill_color(*COLOR_DARK)
            pdf.set_text_color(*COLOR_ACCENT)
            pdf.set_font("Courier", "B", 7.5)
            cmd = _safe(rec["comando"])
            # Dividir comandos largos
            if len(cmd) > 90:
                cmd = cmd[:90] + "..."
            pdf.cell(0, 7, f"  $ {cmd}  ", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*COLOR_DARK)

        # ── Referencia ───────────────────────────────────────────
        if rec.get("referencia"):
            pdf.set_x(15)
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(*COLOR_MUTED)
            pdf.cell(0, 5, _safe(f"Referencia: {rec['referencia']}"), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)
        # Línea separadora
        pdf.set_draw_color(200, 225, 202)
        pdf.set_line_width(0.2)
        pdf.line(14, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)


# ── Función principal exportada ──────────────────────────────────────

def generar_pdf(
    numero_reporte:  str,
    analista:        str,
    datos_escaneo:   dict,
    puertos:         list,
    recomendaciones: list,
) -> str:
    """
    Genera el PDF completo y lo guarda en backend/reports/.
    Retorna la ruta absoluta del archivo generado.
    """
    asegurar_directorio()

    pdf = ForensicPDF(numero_reporte=numero_reporte, analista=analista)
    pdf.set_margins(10, 16, 10)

    # Datos de portada
    datos_portada = {
        "numero_reporte":   numero_reporte,
        "fecha_hora":       datos_escaneo.get("fecha_hora", "-"),
        "target_ip":        datos_escaneo.get("target_ip", "-"),
        "modo":             datos_escaneo.get("modo", "-"),
        "duracion_seg":     datos_escaneo.get("duracion_seg", 0),
        "analista":         analista,
        "puertos_abiertos": datos_escaneo.get("puertos_abiertos", 0),
        "total_puertos":    len(puertos),
        "riesgo_maximo":    datos_escaneo.get("riesgo_maximo", "ninguno"),
    }

    _pagina_portada(pdf, datos_portada)
    _pagina_puertos(pdf, puertos)
    _pagina_recomendaciones(pdf, recomendaciones)

    nombre_archivo = f"{numero_reporte}.pdf"
    ruta           = os.path.join(OUT_DIR, nombre_archivo)
    pdf.output(ruta)
    return ruta
