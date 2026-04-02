# =============================================
# ForensicShield Lite — routers/network.py
# Cesar Eduardo Valenzuela Mosquera · ITESPF 2026
#
# Este módulo define las rutas relacionadas con la gestión de la red local, incluyendo:
#   - Escaneo de hosts activos
#   - Asignación de nombres personalizados
#   - Gestión de firewall para bloquear/desbloquear IPs y dominios
#
# =============================================

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models   import NombreDispositivo
from schemas  import NombreDispositivoCreate
from auth     import verificar_token
from network_scanner import (
    escanear_red_local,
    bloquear_ip_firewall,
    desbloquear_ip_firewall,
    bloquear_dominio,
    desbloquear_dominio
)

router = APIRouter(
    prefix="/api/network",
    tags=["Red Local"]
)


def obtener_usuario_id(request: Request) -> int:
    token = request.cookies.get("fs_token")
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido.")
    token_data = verificar_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")
    return token_data.usuario_id


# ── GET /api/network/hosts ──────────────────────────────────────────
@router.get("/hosts", summary="Descubrir hosts activos en la red local")
async def obtener_hosts(request: Request, db: Session = Depends(get_db)):
    usuario_id = obtener_usuario_id(request)

    resultado = escanear_red_local()

    if not resultado.get("exitoso"):
        raise HTTPException(status_code=500, detail=resultado.get("error"))

    nombres_guardados = db.query(NombreDispositivo).filter(
        NombreDispositivo.usuario_id == usuario_id
    ).all()

    mapa_nombres = {n.ip: n.nombre for n in nombres_guardados}
    mapa_notas   = {n.ip: n.notas  for n in nombres_guardados}

    for host in resultado["hosts"]:
        if host["ip"] in mapa_nombres:
            host["nombre_personalizado"] = mapa_nombres[host["ip"]]
            host["notas"]                = mapa_notas[host["ip"]]
        else:
            host["nombre_personalizado"] = None
            host["notas"]                = None

    return resultado


# ── POST /api/network/nombre ────────────────────────────────────────
@router.post("/nombre", summary="Asignar nombre personalizado a un dispositivo")
async def guardar_nombre(
    datos:   NombreDispositivoCreate,
    request: Request,
    db:      Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    existente = db.query(NombreDispositivo).filter(
        NombreDispositivo.usuario_id == usuario_id,
        NombreDispositivo.ip         == datos.ip
    ).first()

    if existente:
        existente.nombre = datos.nombre
        existente.notas  = datos.notas
        existente.mac    = datos.mac or existente.mac
    else:
        db.add(NombreDispositivo(
            usuario_id = usuario_id,
            ip         = datos.ip,
            mac        = datos.mac,
            nombre     = datos.nombre,
            notas      = datos.notas
        ))

    db.commit()
    return {"mensaje": f"Nombre '{datos.nombre}' guardado para {datos.ip}"}


# ── GET /api/network/nombres ────────────────────────────────────────
@router.get("/nombres", summary="Listar nombres guardados")
async def listar_nombres(request: Request, db: Session = Depends(get_db)):
    usuario_id = obtener_usuario_id(request)
    nombres = db.query(NombreDispositivo).filter(
        NombreDispositivo.usuario_id == usuario_id
    ).all()
    return {
        "total": len(nombres),
        "dispositivos": [
            {"ip": n.ip, "mac": n.mac, "nombre": n.nombre, "notas": n.notas}
            for n in nombres
        ]
    }


# ── POST /api/network/bloquear ──────────────────────────────────────
# BUG #2 CORREGIDO: el frontend enviaba mac en la URL pero el backend
# solo usaba ip. Se mantiene solo ip como parámetro.
@router.post("/bloquear", summary="Bloquear IP via firewall local de Windows")
async def bloquear_dispositivo(
    ip:      str,
    request: Request,
    db:      Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    if not ip:
        raise HTTPException(status_code=400, detail="IP requerida.")

    resultado = bloquear_ip_firewall(ip)

    if resultado["exitoso"]:
        return {"mensaje": resultado["mensaje"]}
    else:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Error al bloquear: {resultado['error']}. "
                "Asegúrate de ejecutar uvicorn como Administrador."
            )
        )


# ── POST /api/network/desbloquear ───────────────────────────────────
@router.post("/desbloquear", summary="Desbloquear IP del firewall local")
async def desbloquear_dispositivo(
    ip:      str,
    request: Request,
    db:      Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    resultado = desbloquear_ip_firewall(ip)

    if resultado["exitoso"]:
        return {"mensaje": resultado["mensaje"]}
    else:
        raise HTTPException(status_code=500, detail=resultado["error"])


# ── POST /api/network/bloquear-dominio ─────────────────────────────
@router.post("/bloquear-dominio", summary="Bloquear un dominio via firewall")
async def bloquear_dom(
    dominio: str,
    request: Request,
    db:      Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    if not dominio or len(dominio) < 3:
        raise HTTPException(status_code=400, detail="Dominio inválido.")

    resultado = bloquear_dominio(dominio)

    if resultado["exitoso"]:
        return resultado
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {resultado['error']}. Ejecuta uvicorn como Administrador."
        )


# ── POST /api/network/desbloquear-dominio ──────────────────────────
@router.post("/desbloquear-dominio", summary="Desbloquear un dominio del firewall")
async def desbloquear_dom(
    dominio: str,
    request: Request,
    db:      Session = Depends(get_db)
):
    usuario_id = obtener_usuario_id(request)

    resultado = desbloquear_dominio(dominio)

    if resultado["exitoso"]:
        return resultado
    else:
        raise HTTPException(status_code=500, detail=resultado["error"])