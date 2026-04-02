# =============================================
# ForensicShield Lite — Autenticación
# Maneja bcrypt (passwords) y JWT (tokens)
# =============================================

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

from schemas import TokenData

load_dotenv()

SECRET_KEY           = os.getenv("SECRET_KEY")
ALGORITHM            = os.getenv("ALGORITHM", "HS256")
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))

# =============================================
# Validación al arrancar el servidor
# Si no hay SECRET_KEY el servidor no inicia
# =============================================
if not SECRET_KEY:
    raise RuntimeError(
        "❌ SECRET_KEY no está definida en el .env — "
        "el servidor no puede arrancar sin ella."
    )

if SECRET_KEY == "forensicshield_super_secret_key_2026_cambia_esto_en_produccion":
    import warnings
    warnings.warn(
        "⚠️  Estás usando la SECRET_KEY de desarrollo. "
        "Cámbiala antes de subir a producción.",
        stacklevel=2
    )

# =============================================
# BCRYPT — Verificación de contraseñas
# =============================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_password(password_plano: str, password_hash: str) -> bool:
    """
    Compara la contraseña del usuario contra el hash en BD.
    Nunca desencripta — solo compara con bcrypt.
    """
    try:
        return pwd_context.verify(password_plano, password_hash)
    except Exception:
        # Si el hash está corrupto no lanzamos excepción — solo retornamos False
        return False

def hashear_password(password: str) -> str:
    """
    Genera un hash bcrypt de una contraseña.
    Usado al crear o actualizar usuarios.
    """
    return pwd_context.hash(password)

# =============================================
# JWT — Generación y verificación de tokens
# =============================================

def crear_token(usuario_id: int, email: str, rol: str) -> str:
    """
    Genera un JWT firmado con los datos del usuario.
    Expira según TOKEN_EXPIRE_MINUTES del .env
    """
    expiracion = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub":   str(usuario_id),
        "email": email,
        "rol":   rol,
        "exp":   expiracion,
        "iat":   datetime.now(timezone.utc)
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token(token: str) -> Optional[TokenData]:
    """
    Verifica que el JWT sea válido y no haya expirado.
    Devuelve los datos del usuario o None si es inválido.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        usuario_id = payload.get("sub")
        email      = payload.get("email")
        rol        = payload.get("rol")

        if not usuario_id or not email:
            return None

        return TokenData(
            usuario_id = int(usuario_id),
            email      = email,
            rol        = rol
        )

    except JWTError:
        return None