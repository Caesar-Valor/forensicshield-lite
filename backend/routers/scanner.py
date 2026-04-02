# =============================================
# ForensicShield Lite — routers/scanner.py
# Cesar Eduardo Valenzuela Mosquera · ITESPF 2026
#
# Este módulo define las rutas relacionadas con el escaneo de puertos, incluyendo:
#   - Iniciar escaneo de puertos en un host objetivo
# =============================================

from fastapi import APIRouter, Depends, Request, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
import os

from database        import get_db
from models          import Escaneo, ScanResultado
from scanner         import ejecutar_escaneo
from auth            import verificar_token
from schemas         import ScanRequest
from recomendaciones import generar_recomendaciones
from network_scanner import cerrar_puerto_firewall, abrir_puerto_firewall

router = APIRouter(
    prefix="/api/scanner",
    tags=["Port Scanner"]
)


# =============================================
# Schema de respuesta
# =============================================
class ScanResponse(BaseModel):
    escaneo_id: int
    mensaje:    str
    estado:     str


# =============================================
# Función auxiliar — obtener usuario del token
# =============================================
def obtener_usuario_id(request: Request) -> int:
    token = request.cookies.get("fs_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requerido."
        )
    token_data = verificar_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado."
        )
    return token_data.usuario_id


# =============================================
# Función que corre el escaneo en segundo plano
# =============================================
def procesar_escaneo(
    escaneo_id:     int,
    target_ip:      str,
    modo:           str,
    puertos_custom: Optional[str],
    db:             Session
):
    try:
        escaneo = db.query(Escaneo).filter(Escaneo.id == escaneo_id).first()
        if not escaneo:
            return

        escaneo.estado = "en_progreso"
        db.commit()

        resultado = ejecutar_escaneo(target_ip, modo, puertos_custom)

        if not resultado.get("exitoso"):
            escaneo.estado = "fallido"
            escaneo.notas  = resultado.get("error", "Error desconocido")
            db.commit()
            return

        puertos_open   = 0
        puertos_closed = 0

        for p in resultado["puertos"]:
            scan_res = ScanResultado(
                escaneo_id = escaneo_id,
                puerto     = p["puerto"],
                protocolo  = p["protocolo"],
                estado     = p["estado"],
                servicio   = p.get("servicio"),
                version    = p.get("version"),
                riesgo     = p.get("riesgo"),
            )
            db.add(scan_res)

            if p["estado"] == "open":
                puertos_open += 1
            elif p["estado"] == "closed":
                puertos_closed += 1

        escaneo.estado           = "completado"
        escaneo.puertos_abiertos = puertos_open
        escaneo.puertos_cerrados = puertos_closed
        escaneo.duracion_seg     = resultado["resumen"]["duracion_seg"]
        escaneo.finalizado_en    = datetime.now(timezone.utc)
        escaneo.target_nombre    = escaneo.target_nombre or resultado.get("hostname")

        db.commit()

    except Exception as e:
        try:
            escaneo = db.query(Escaneo).filter(Escaneo.id == escaneo_id).first()
            if escaneo:
                escaneo.estado = "fallido"
                escaneo.notas  = str(e)
                db.commit()
        except Exception:
            pass


# =============================================
# POST /api/scanner/iniciar
# =============================================
@router.post(
    "/iniciar",
    response_model=ScanResponse,
    summary="Iniciar un nuevo escaneo de puertos"
)
async def iniciar_escaneo(
    datos:            ScanRequest,
    request:          Request,
    background_tasks: BackgroundTasks,
    db:               Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    if datos.modo not in ("rapido", "completo"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modo inválido. Usa 'rapido' o 'completo'."
        )

    nuevo_escaneo = Escaneo(
        usuario_id    = usuario_id,
        target_ip     = datos.target_ip,
        target_nombre = datos.target_nombre,
        estado        = "pendiente",
        notas         = f"Modo: {datos.modo}"
    )
    db.add(nuevo_escaneo)
    db.commit()
    db.refresh(nuevo_escaneo)

    background_tasks.add_task(
        procesar_escaneo,
        escaneo_id     = nuevo_escaneo.id,
        target_ip      = datos.target_ip,
        modo           = datos.modo,
        puertos_custom = datos.puertos_custom,
        db             = db
    )

    return ScanResponse(
        escaneo_id=nuevo_escaneo.id,
        mensaje=(
            f"Escaneo iniciado en modo '{datos.modo}'. "
            f"Consulta el resultado en /api/scanner/resultado/{nuevo_escaneo.id}"
        ),
        estado="pendiente"
    )


# =============================================
# GET /api/scanner/resultado/{escaneo_id}
# =============================================
@router.get(
    "/resultado/{escaneo_id}",
    summary="Obtener resultados de un escaneo"
)
async def obtener_resultado(
    escaneo_id: int,
    request:    Request,
    db:         Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    if escaneo_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de escaneo inválido."
        )

    escaneo = db.query(Escaneo).filter(
        Escaneo.id         == escaneo_id,
        Escaneo.usuario_id == usuario_id
    ).first()

    if not escaneo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escaneo no encontrado."
        )

    if escaneo.estado in ("pendiente", "en_progreso"):
        return {
            "escaneo_id": escaneo.id,
            "estado":     escaneo.estado,
            "target_ip":  escaneo.target_ip,
            "mensaje":    "El escaneo aún está en progreso. Vuelve a consultar en unos segundos."
        }

    resultados = db.query(ScanResultado).filter(
        ScanResultado.escaneo_id == escaneo_id
    ).order_by(ScanResultado.puerto).all()

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

    return {
        "escaneo_id":       escaneo.id,
        "target_ip":        escaneo.target_ip,
        "target_nombre":    escaneo.target_nombre,
        "estado":           escaneo.estado,
        "puertos_abiertos": escaneo.puertos_abiertos,
        "puertos_cerrados": escaneo.puertos_cerrados,
        "duracion_seg":     escaneo.duracion_seg,
        "iniciado_en":      escaneo.iniciado_en.isoformat() if escaneo.iniciado_en else None,
        "finalizado_en":    escaneo.finalizado_en.isoformat() if escaneo.finalizado_en else None,
        "puertos":          puertos,
        "notas":            escaneo.notas,
    }


# =============================================
# GET /api/scanner/historial
# =============================================
@router.get(
    "/historial",
    summary="Ver historial de escaneos del usuario"
)
async def historial_escaneos(
    request: Request,
    db:      Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    escaneos = db.query(Escaneo).filter(
        Escaneo.usuario_id == usuario_id
    ).order_by(Escaneo.iniciado_en.desc()).limit(50).all()

    return {
        "total": len(escaneos),
        "escaneos": [
            {
                "id":               e.id,
                "target_ip":        e.target_ip,
                "target_nombre":    e.target_nombre,
                "estado":           e.estado,
                "puertos_abiertos": e.puertos_abiertos,
                "duracion_seg":     e.duracion_seg,
                "iniciado_en":      e.iniciado_en.isoformat() if e.iniciado_en else None,
            }
            for e in escaneos
        ]
    }


# =============================================
# GET /api/scanner/recomendaciones/{escaneo_id}
# =============================================
@router.get(
    "/recomendaciones/{escaneo_id}",
    summary="Obtener recomendaciones de seguridad de un escaneo"
)
async def obtener_recomendaciones(
    escaneo_id: int,
    request:    Request,
    db:         Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    escaneo = db.query(Escaneo).filter(
        Escaneo.id         == escaneo_id,
        Escaneo.usuario_id == usuario_id
    ).first()

    if not escaneo:
        raise HTTPException(status_code=404, detail="Escaneo no encontrado.")

    if escaneo.estado != "completado":
        raise HTTPException(status_code=400, detail="El escaneo aún no está completado.")

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

    return generar_recomendaciones(puertos)


# =============================================
# POST /api/scanner/cerrar-puerto
# =============================================
@router.post(
    "/cerrar-puerto",
    summary="Cerrar un puerto via firewall de Windows"
)
async def cerrar_puerto(
    puerto:    int,
    protocolo: str     = "TCP",
    request:   Request = None,
    db:        Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    resultado = cerrar_puerto_firewall(puerto, protocolo)

    if resultado["exitoso"]:
        return {"mensaje": resultado["mensaje"]}
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {resultado['error']}. Ejecuta uvicorn como Administrador."
        )


# =============================================
# POST /api/scanner/abrir-puerto
# =============================================
@router.post(
    "/abrir-puerto",
    summary="Eliminar regla de bloqueo de un puerto"
)
async def abrir_puerto(
    puerto:    int,
    protocolo: str     = "TCP",
    request:   Request = None,
    db:        Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    resultado = abrir_puerto_firewall(puerto, protocolo)

    if resultado["exitoso"]:
        return {"mensaje": resultado["mensaje"]}
    else:
        raise HTTPException(status_code=500, detail=resultado["error"])