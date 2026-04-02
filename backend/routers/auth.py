# =============================================
# ForensicShield Lite — Router de Autenticación
# Endpoint: POST /api/auth/login
# =============================================

from fastapi import APIRouter, Depends, Request, HTTPException, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
import hashlib
import os

from database import get_db
from models   import Usuario, IntentoLogin, SesionActiva
from schemas  import LoginRequest, LoginResponse
from auth     import verificar_password, crear_token

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticación"]
)

MAX_INTENTOS    = int(os.getenv("MAX_INTENTOS_LOGIN", "5"))
VENTANA_MINUTOS = int(os.getenv("VENTANA_BLOQUEO_MINUTOS", "15"))

@router.post(
    "/login",
    response_model = LoginResponse,
    summary        = "Iniciar sesión en ForensicShield Lite"
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    datos:   LoginRequest,
    db:      Session = Depends(get_db)
):
    ip_origen   = request.client.host
    dispositivo = request.headers.get("user-agent", "desconocido")[:255]

    # ─── 1. Bloqueo por IP ────────────────────────────────────────────
    ventana_desde = datetime.now(timezone.utc) - timedelta(minutes=VENTANA_MINUTOS)

    intentos_recientes = db.query(IntentoLogin).filter(
        IntentoLogin.ip_origen    == ip_origen,
        IntentoLogin.exitoso      == False,
        IntentoLogin.intentado_en >= ventana_desde
    ).count()

    if intentos_recientes >= MAX_INTENTOS:
        raise HTTPException(
            status_code = status.HTTP_429_TOO_MANY_REQUESTS,
            detail      = f"Demasiados intentos fallidos. Intenta en {VENTANA_MINUTOS} minutos."
        )

    # ─── 2. Buscar usuario ────────────────────────────────────────────
    usuario = db.query(Usuario).filter(
        Usuario.email == datos.email
    ).first()

    # ─── 3. Verificar contraseña ──────────────────────────────────────
    password_valida = False
    if usuario:
        password_valida = verificar_password(datos.password, usuario.password_hash)

    if not usuario or not usuario.activo or not password_valida:
        if not usuario:
            motivo = "usuario no existe"
        elif not usuario.activo:
            motivo = "cuenta desactivada"
        else:
            motivo = "contraseña incorrecta"

        db.add(IntentoLogin(
            email        = datos.email,
            usuario_id   = usuario.id if usuario else None,
            ip_origen    = ip_origen,
            exitoso      = False,
            motivo_fallo = motivo,
            dispositivo  = dispositivo
        ))
        db.commit()

        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Credenciales incorrectas."
        )

    # ─── 4. Generar JWT ───────────────────────────────────────────────
    token = crear_token(
        usuario_id = usuario.id,
        email      = usuario.email,
        rol        = usuario.rol
    )

    # ─── 5. Guardar sesión ────────────────────────────────────────────
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expira_en  = datetime.now(timezone.utc) + timedelta(
        minutes=int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))
    )

    db.add(SesionActiva(
        usuario_id     = usuario.id,
        jwt_token_hash = token_hash,
        ip_origen      = ip_origen,
        dispositivo    = dispositivo,
        activa         = True,
        expira_en      = expira_en
    ))

    # ─── 6. Actualizar último acceso ──────────────────────────────────
    usuario.ultimo_acceso = datetime.now(timezone.utc)

    # ─── 7. Registrar intento exitoso ─────────────────────────────────
    db.add(IntentoLogin(
        email       = datos.email,
        usuario_id  = usuario.id,
        ip_origen   = ip_origen,
        exitoso     = True,
        dispositivo = dispositivo
    ))

    db.commit()

    # ─── 8. Devolver datos del usuario con JWT en HttpOnly cookie ─────
    token_expire_seconds = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60")) * 60
    response = JSONResponse(content={
        "rol":      usuario.rol,
        "nombre":   usuario.nombre,
        "apellido": usuario.apellido,
        "mensaje":  f"Bienvenido, {usuario.nombre}!"
    })
    response.set_cookie(
        key      = "fs_token",
        value    = token,
        httponly = True,
        samesite = "strict",
        secure   = os.getenv("COOKIE_SECURE", "false").lower() == "true",
        max_age  = token_expire_seconds,
        path     = "/"
    )
    return response


@router.post("/logout", summary="Cerrar sesión")
async def logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("fs_token")
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        sesion = db.query(SesionActiva).filter(
            SesionActiva.jwt_token_hash == token_hash,
            SesionActiva.activa         == True
        ).first()
        if sesion:
            sesion.activa = False
            db.commit()

    response = JSONResponse(content={"mensaje": "Sesión cerrada correctamente."})
    response.delete_cookie(key="fs_token", path="/")
    return response