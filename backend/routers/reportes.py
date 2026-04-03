# =============================================
# ForensicShield Lite — routers/reportes.py
# Endpoints para generación y descarga de PDFs
# =============================================

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import hashlib
import os

from database        import get_db
from models          import Reporte, Escaneo, ScanResultado, Usuario
from auth            import verificar_token
from recomendaciones import generar_recomendaciones
from pdf_generator   import generar_pdf

router = APIRouter(
    prefix="/api/reportes",
    tags=["Reportes"]
)


def obtener_usuario(request: Request, db: Session) -> Usuario:
    token = request.cookies.get("fs_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido.")
    token_data = verificar_token(token)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado.")
    usuario = db.query(Usuario).filter(Usuario.id == token_data.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado.")
    return usuario


def calcular_numero(reporte_id: int, año: int) -> str:
    return f"FSL-{año}-{reporte_id:06d}"


def calcular_riesgo_maximo(puertos: list) -> str:
    orden = {"critico": 4, "alto": 3, "medio": 2, "bajo": 1, "ninguno": 0}
    maximo = "ninguno"
    for p in puertos:
        r = p.get("riesgo") or "ninguno"
        if orden.get(r, 0) > orden.get(maximo, 0):
            maximo = r
    return maximo


# ── POST /api/reportes/generar/{escaneo_id} ──────────────────────────
@router.post(
    "/generar/{escaneo_id}",
    summary="Generar reporte PDF de un escaneo"
)
async def generar_reporte(
    escaneo_id: int,
    request:    Request,
    db:         Session = Depends(get_db)
):
    usuario = obtener_usuario(request, db)

    # ── Verificar que el escaneo pertenece al usuario ────────────────
    escaneo = db.query(Escaneo).filter(
        Escaneo.id         == escaneo_id,
        Escaneo.usuario_id == usuario.id,
        Escaneo.estado     == "completado"
    ).first()

    if not escaneo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escaneo no encontrado o aún no completado."
        )

    # ── Obtener puertos del escaneo ──────────────────────────────────
    resultados = db.query(ScanResultado).filter(
        ScanResultado.escaneo_id == escaneo_id
    ).all()

    puertos = [
        {
            "puerto":    r.puerto,
            "protocolo": r.protocolo,
            "estado":    r.estado,
            "servicio":  r.servicio,
            "version":   r.version,
            "riesgo":    r.riesgo,
        }
        for r in resultados
    ]

    # ── Generar recomendaciones ──────────────────────────────────────
    rec_data    = generar_recomendaciones(puertos)
    recs        = rec_data.get("recomendaciones", [])
    riesgo_max  = calcular_riesgo_maximo(puertos)

    # ── Crear registro en BD (estado: generando) ─────────────────────
    now = datetime.now(timezone.utc)

    reporte = Reporte(
        usuario_id      = usuario.id,
        titulo          = f"Auditoría {escaneo.target_ip} — {now.strftime('%d/%m/%Y %H:%M')}",
        formato         = "pdf",
        estado          = "generando",
        escaneos_inc    = [escaneo_id],
        total_hallazgos = len([p for p in puertos if p["estado"] == "open"]),
        contenido       = {
            "target_ip":      escaneo.target_ip,
            "modo":           escaneo.target_nombre or "rapido",
            "duracion_seg":   escaneo.duracion_seg or 0,
            "puertos_abiertos": escaneo.puertos_abiertos or 0,
            "riesgo_maximo":  riesgo_max,
            "analista":       f"{usuario.nombre} {usuario.apellido}",
        }
    )
    db.add(reporte)
    db.flush()  # Obtener ID sin hacer commit

    # ── Calcular número único de reporte ────────────────────────────
    numero_reporte = calcular_numero(reporte.id, now.year)

    # ── Generar PDF ──────────────────────────────────────────────────
    try:
        datos_escaneo = {
            "target_ip":        escaneo.target_ip,
            "modo":             escaneo.target_nombre or "rapido",
            "duracion_seg":     escaneo.duracion_seg or 0,
            "puertos_abiertos": escaneo.puertos_abiertos or 0,
            "riesgo_maximo":    riesgo_max,
            "fecha_hora":       now.strftime("%d de %B de %Y, %H:%M:%S"),
        }

        ruta_pdf = generar_pdf(
            numero_reporte  = numero_reporte,
            analista        = f"{usuario.nombre} {usuario.apellido}",
            datos_escaneo   = datos_escaneo,
            puertos         = puertos,
            recomendaciones = recs,
        )

        # Hash de integridad del archivo
        with open(ruta_pdf, "rb") as f:
            hash_pdf = hashlib.sha256(f.read()).hexdigest()

        # ── Actualizar registro con datos finales ────────────────────
        reporte.estado       = "completado"
        reporte.ruta_archivo = ruta_pdf
        reporte.hash_sha256  = hash_pdf
        reporte.contenido["numero_reporte"] = numero_reporte
        reporte.titulo = f"{numero_reporte} — Auditoría {escaneo.target_ip}"
        db.commit()

        return {
            "reporte_id":     reporte.id,
            "numero_reporte": numero_reporte,
            "estado":         "completado",
            "mensaje":        "Reporte generado correctamente.",
        }

    except Exception as e:
        reporte.estado = "fallido"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el PDF: {str(e)}"
        )


# ── GET /api/reportes/lista ──────────────────────────────────────────
@router.get(
    "/lista",
    summary="Listar reportes del usuario autenticado"
)
async def listar_reportes(
    request: Request,
    db:      Session = Depends(get_db)
):
    usuario = obtener_usuario(request, db)

    reportes = db.query(Reporte).filter(
        Reporte.usuario_id == usuario.id,
        Reporte.estado     == "completado"
    ).order_by(Reporte.generado_en.desc()).limit(50).all()

    resultado = []
    for r in reportes:
        contenido = r.contenido or {}
        resultado.append({
            "reporte_id":     r.id,
            "numero_reporte": contenido.get("numero_reporte", calcular_numero(r.id, r.generado_en.year)),
            "titulo":         r.titulo,
            "target_ip":      contenido.get("target_ip", "—"),
            "riesgo_maximo":  contenido.get("riesgo_maximo", "ninguno"),
            "hallazgos":      r.total_hallazgos,
            "generado_en":    r.generado_en.strftime("%d/%m/%Y %H:%M") if r.generado_en else "—",
        })

    return {"reportes": resultado, "total": len(resultado)}


# ── GET /api/reportes/descargar/{reporte_id} ─────────────────────────
@router.get(
    "/descargar/{reporte_id}",
    summary="Descargar reporte PDF"
)
async def descargar_reporte(
    reporte_id: int,
    request:    Request,
    db:         Session = Depends(get_db)
):
    usuario = obtener_usuario(request, db)

    reporte = db.query(Reporte).filter(
        Reporte.id         == reporte_id,
        Reporte.usuario_id == usuario.id,
        Reporte.estado     == "completado"
    ).first()

    if not reporte:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reporte no encontrado.")

    if not reporte.ruta_archivo or not os.path.exists(reporte.ruta_archivo):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo PDF no disponible.")

    contenido = reporte.contenido or {}
    numero    = contenido.get("numero_reporte", calcular_numero(reporte.id, reporte.generado_en.year))

    return FileResponse(
        path         = reporte.ruta_archivo,
        media_type   = "application/pdf",
        filename     = f"{numero}.pdf",
        headers      = {"Content-Disposition": f'attachment; filename="{numero}.pdf"'}
    )
