# =============================================
# ForensicShield Lite — pdf_generator.py
# Genera reportes PDF de auditoría de seguridad
# =============================================

from fpdf import FPDF
from datetime import datetime
import os

# Rutas de recursos
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "..", "img", "forensicShield.jpeg.jpeg")
OUT_DIR   = os.path.join(BASE_DIR, "reports")

# Paleta de colores
COLOR_DARK    = (15, 15, 35)       # #0f0f23
COLOR_ACCENT  = (109, 93, 252)     # #6d5dfc
COLOR_WHITE   = (255, 255, 255)
COLOR_LIGHT   = (245, 245, 250)    # fondo alterno de filas
COLOR_MUTED   = (120, 120, 140)    # texto secundario
COLOR_BORDER  = (220, 220, 230)

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


def asegurar_directorio():
    os.makedirs(OUT_DIR, exist_ok=True)


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
        self.rect(0, 0, 210, 14, "F")
        # Texto del header
        self.set_y(3)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*COLOR_ACCENT)
        self.cell(0, 8, "FORENSICSHIELD LITE", align="L")
        self.set_text_color(180, 180, 200)
        self.set_font("Helvetica", "", 7)
        self.cell(0, 8, f"Reporte {self.numero_reporte}  |  Pág. {self.page_no()}", align="R")
        self.ln(14)

    # ── Footer ──────────────────────────────────────────────────────
    def footer(self):
        self.set_y(-12)
        self.set_draw_color(*COLOR_ACCENT)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_y(-10)
        self.set_font("Helvetica", "I", 6.5)
        self.set_text_color(*COLOR_MUTED)
        self.cell(0, 6, f"DOCUMENTO CONFIDENCIAL  ·  {self.numero_reporte}  ·  Generado por ForensicShield Lite", align="C")


# ── Helpers de dibujo ────────────────────────────────────────────────

def _section_title(pdf: ForensicPDF, texto: str):
    """Encabezado de sección con barra de acento."""
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


# ── Construcción de páginas ──────────────────────────────────────────

def _pagina_portada(pdf: ForensicPDF, datos: dict):
    """Página 1: portada con logo, número de reporte y datos del escaneo."""
    pdf.add_page()

    # Fondo oscuro superior (60% de la página)
    pdf.set_fill_color(*COLOR_DARK)
    pdf.rect(0, 0, 210, 140, "F")

    # Logo
    if os.path.exists(LOGO_PATH):
        try:
            pdf.image(LOGO_PATH, x=80, y=18, w=50)
        except Exception:
            pass
    pdf.ln(72)

    # Título principal
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.cell(0, 10, "REPORTE DE AUDITORÍA", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.cell(0, 8, "DE SEGURIDAD", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Línea decorativa
    pdf.set_draw_color(*COLOR_ACCENT)
    pdf.set_line_width(1.0)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(5)

    # Número de reporte destacado
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.cell(0, 8, datos["numero_reporte"], align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Fecha y hora
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(180, 180, 200)
    pdf.cell(0, 6, f"Generado el {datos['fecha_hora']}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)

    # Zona blanca de datos del escaneo
    pdf.set_fill_color(*COLOR_WHITE)
    pdf.rect(0, 140, 210, 157, "F")
    pdf.set_y(148)

    # Datos principales en dos columnas
    col_w = 85
    col_gap = 10
    lm = 15

    campos = [
        ("IP Objetivo",    datos["target_ip"]),
        ("Modo de Escaneo", datos["modo"].capitalize()),
        ("Duración",       f"{datos['duracion_seg']} segundos"),
        ("Analista",       datos["analista"]),
        ("Puertos Abiertos", str(datos["puertos_abiertos"])),
        ("Total Puertos",  str(datos["total_puertos"])),
    ]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*COLOR_MUTED)

    for i, (clave, valor) in enumerate(campos):
        col = i % 2
        if col == 0:
            if i > 0:
                pdf.ln(14)
            pdf.set_x(lm)
        else:
            pdf.set_xy(lm + col_w + col_gap, pdf.get_y() - 14)

        x_pos = lm + col * (col_w + col_gap)
        y_pos = pdf.get_y()

        # Etiqueta
        pdf.set_xy(x_pos, y_pos)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*COLOR_MUTED)
        pdf.cell(col_w, 5, clave.upper())

        # Valor
        pdf.set_xy(x_pos, y_pos + 5)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*COLOR_DARK)
        pdf.cell(col_w, 7, str(valor))

    # Riesgo máximo
    pdf.set_y(210)
    pdf.set_x(lm)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.cell(0, 5, "NIVEL DE RIESGO MÁXIMO DETECTADO")
    pdf.ln(7)
    pdf.set_x(lm)
    riesgo = datos.get("riesgo_maximo", "ninguno")
    r, g, b = RIESGO_COLOR.get(riesgo, COLOR_MUTED)
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(50, 9, riesgo.upper(), fill=True, align="C")

    # Pie de portada
    pdf.set_y(270)
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
        ("Proto.",    18),
        ("Estado",    28),
        ("Servicio",  38),
        ("Versión",   52),
        ("Riesgo",    28),
    ]
    total_w = sum(c[1] for c in cols)

    pdf.set_fill_color(*COLOR_DARK)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_font("Helvetica", "B", 8)

    for label, w in cols:
        pdf.cell(w, 8, label, fill=True, align="C")
    pdf.ln()

    # Filas
    pdf.set_font("Helvetica", "", 8)
    for i, p in enumerate(puertos):
        # Check page break manually
        if pdf.get_y() > 265:
            pdf.add_page()
            pdf.ln(4)
            # Repetir cabecera
            pdf.set_fill_color(*COLOR_DARK)
            pdf.set_text_color(*COLOR_WHITE)
            pdf.set_font("Helvetica", "B", 8)
            for label, w in cols:
                pdf.cell(w, 8, label, fill=True, align="C")
            pdf.ln()
            pdf.set_font("Helvetica", "", 8)

        fill_bg = (i % 2 == 1)
        row_h   = 7
        y_start = pdf.get_y()

        if fill_bg:
            pdf.set_fill_color(*COLOR_LIGHT)
        else:
            pdf.set_fill_color(*COLOR_WHITE)

        estado = p.get("estado", "")
        riesgo = p.get("riesgo", "ninguno") or "ninguno"

        # Puerto
        pdf.set_text_color(*COLOR_DARK)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(cols[0][1], row_h, str(p.get("puerto", "")), fill=fill_bg, align="C")

        # Protocolo
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(cols[1][1], row_h, (p.get("protocolo") or "TCP").upper(), fill=fill_bg, align="C")

        # Estado (con color)
        x_before = pdf.get_x()
        pdf.cell(cols[2][1], row_h, "", fill=fill_bg, align="C")
        ec = ESTADO_COLOR.get(estado, COLOR_MUTED)
        label_map = {"open": "Abierto", "closed": "Cerrado", "filtered": "Filtrado"}
        _badge(pdf, label_map.get(estado, estado), ec, x_before + 1, y_start, cols[2][1] - 2)

        # Servicio
        pdf.set_xy(pdf.get_x() - cols[2][1] + x_before - pdf.get_x() + sum(c[1] for c in cols[:3]) + 10, y_start)
        servicio = (p.get("servicio") or "—")[:16]
        pdf.set_text_color(*COLOR_DARK)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_x(10 + sum(c[1] for c in cols[:3]))
        pdf.cell(cols[3][1], row_h, servicio, fill=fill_bg)

        # Versión
        version = (p.get("version") or "—")[:22]
        pdf.cell(cols[4][1], row_h, version, fill=fill_bg)

        # Riesgo (con color)
        x_riesgo = pdf.get_x()
        pdf.cell(cols[5][1], row_h, "", fill=fill_bg, align="C")
        rc = RIESGO_COLOR.get(riesgo, COLOR_MUTED)
        _badge(pdf, riesgo, rc, x_riesgo + 1, y_start, cols[5][1] - 2)

        pdf.ln(row_h)

    pdf.ln(4)


def _pagina_recomendaciones(pdf: ForensicPDF, recomendaciones: list):
    """Página(s) de recomendaciones de seguridad."""
    if not recomendaciones:
        return

    pdf.add_page()
    pdf.ln(4)
    _section_title(pdf, "RECOMENDACIONES DE SEGURIDAD")

    for rec in recomendaciones:
        if pdf.get_y() > 240:
            pdf.add_page()
            pdf.ln(4)

        riesgo = rec.get("riesgo", "ninguno")
        rc     = RIESGO_COLOR.get(riesgo, COLOR_MUTED)

        # Barra izquierda de color + título
        y_box = pdf.get_y()
        pdf.set_fill_color(*rc)
        pdf.rect(10, y_box, 2, 8, "F")
        pdf.set_x(14)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*COLOR_DARK)
        puerto_txt = f"Puerto {rec.get('puerto')} — {rec.get('titulo', '')}"
        pdf.multi_cell(0, 6, puerto_txt)

        # Badge riesgo + urgencia
        pdf.set_x(14)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_fill_color(*rc)
        pdf.set_text_color(*COLOR_WHITE)
        pdf.cell(22, 5, riesgo.upper(), fill=True, align="C")
        urgencia = rec.get("urgencia", "")
        pdf.set_x(pdf.get_x() + 3)
        pdf.set_fill_color(70, 70, 90)
        pdf.cell(28, 5, f"urgencia: {urgencia}", fill=True, align="C")
        pdf.ln(8)

        # Problema
        pdf.set_x(14)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*COLOR_MUTED)
        pdf.cell(25, 5, "PROBLEMA:")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*COLOR_DARK)
        pdf.multi_cell(0, 5, rec.get("problema", ""))

        # Acción
        pdf.set_x(14)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*COLOR_MUTED)
        pdf.cell(25, 5, "ACCIÓN:")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*COLOR_DARK)
        pdf.multi_cell(0, 5, rec.get("accion", ""))

        # Comando
        if rec.get("comando"):
            pdf.set_x(14)
            pdf.set_fill_color(30, 30, 50)
            pdf.set_text_color(180, 220, 255)
            pdf.set_font("Courier", "", 7)
            cmd = rec["comando"][:95]
            pdf.cell(0, 6, f"  {cmd}", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*COLOR_DARK)

        # Referencia
        if rec.get("referencia"):
            pdf.set_x(14)
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(*COLOR_MUTED)
            pdf.cell(0, 5, f"Referencia: {rec['referencia']}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)
        # Separador
        pdf.set_draw_color(*COLOR_BORDER)
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
        "numero_reporte": numero_reporte,
        "fecha_hora":     datos_escaneo.get("fecha_hora", "—"),
        "target_ip":      datos_escaneo.get("target_ip", "—"),
        "modo":           datos_escaneo.get("modo", "—"),
        "duracion_seg":   datos_escaneo.get("duracion_seg", 0),
        "analista":       analista,
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
