# =============================================
# ForensicShield Lite — Schemas (Pydantic)
# Define qué datos entran y salen de la API
# Cesar Eduardo Valenzuela Mosquera · ITESPF 2026
# =============================================

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import re

# =============================================
# AUTH — Login
# =============================================

class LoginRequest(BaseModel):
    """Lo que el frontend envía al hacer POST /api/auth/login"""
    email:    EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validar_email(cls, v):
        v = v.strip()
        if len(v) > 255:
            raise ValueError("El correo es demasiado largo.")
        return v

    @field_validator("password")
    @classmethod
    def validar_password(cls, v):
        if len(v) < 8:
            raise ValueError("La contraseña debe tener mínimo 8 caracteres.")
        if len(v) > 128:
            raise ValueError("La contraseña es demasiado larga.")
        patrones_peligrosos = [
            r"(\s|^)(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC)\s",
            r"--\s*$",
            r";\s*(DROP|DELETE|INSERT|UPDATE)",
            r"\/\*.*\*\/",
            r"xp_",
            r"WAITFOR\s+DELAY",
        ]
        for patron in patrones_peligrosos:
            if re.search(patron, v.upper(), re.IGNORECASE):
                raise ValueError("Contraseña no válida.")
        return v

class LoginResponse(BaseModel):
    """Lo que la API devuelve si el login es exitoso"""
    token:    str
    rol:      str
    nombre:   str
    apellido: str
    mensaje:  str = "Login exitoso"

class ErrorResponse(BaseModel):
    """Respuesta de error estándar"""
    detail: str

# =============================================
# SCANNER — Validación de IP y parámetros
# =============================================

class ScanRequest(BaseModel):
    """Lo que el frontend envía al hacer POST /api/scanner/iniciar"""
    target_ip:      str
    target_nombre:  Optional[str] = None
    modo:           str = "rapido"
    puertos_custom: Optional[str] = None

    @field_validator("target_ip")
    @classmethod
    def validar_ip(cls, v):
        v = v.strip()
        if len(v) > 253:
            raise ValueError("IP o hostname demasiado largo.")
        if re.search(r"[;&|`$<>'\"\\\n\r]", v):
            raise ValueError("La IP contiene caracteres no válidos.")
        ipv4     = r"^(\d{1,3}\.){3}\d{1,3}$"
        hostname = r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{0,251}[a-zA-Z0-9])?$"
        if not re.match(ipv4, v) and not re.match(hostname, v):
            raise ValueError("Formato de IP o hostname inválido.")
        if re.match(ipv4, v):
            if any(int(o) > 255 for o in v.split(".")):
                raise ValueError("Dirección IPv4 inválida.")
        return v

    @field_validator("modo")
    @classmethod
    def validar_modo(cls, v):
        if v not in ("rapido", "completo"):
            raise ValueError("Modo inválido. Usa 'rapido' o 'completo'.")
        return v

    @field_validator("puertos_custom")
    @classmethod
    def validar_puertos(cls, v):
        if v is None:
            return v
        if not re.match(r"^[\d,\-\s]+$", v):
            raise ValueError("Formato de puertos inválido.")
        if len(v) > 100:
            raise ValueError("Rango de puertos demasiado largo.")
        return v

    @field_validator("target_nombre")
    @classmethod
    def validar_nombre(cls, v):
        if v is None:
            return v
        if len(v) > 255:
            raise ValueError("Nombre demasiado largo.")
        v = re.sub(r"[<>\"';&|`]", "", v).strip()
        return v

class ScanResponse(BaseModel):
    """Lo que la API devuelve al iniciar un escaneo"""
    escaneo_id: int
    mensaje:    str
    estado:     str

# =============================================
# USUARIO — Datos básicos del perfil
# =============================================

class UsuarioBase(BaseModel):
    nombre:   str
    apellido: str
    email:    EmailStr
    rol:      str

class UsuarioPerfil(UsuarioBase):
    """Datos del usuario que se pueden devolver al frontend"""
    id:            int
    activo:        bool
    ultimo_acceso: Optional[datetime] = None
    creado_en:     datetime

    class Config:
        from_attributes = True

# =============================================
# TOKEN — Verificación JWT
# =============================================

class TokenData(BaseModel):
    """Datos que se guardan dentro del JWT"""
    usuario_id: int
    email:      str
    rol:        str



# =============================================
# NETWORK SCAN — Red local
# =============================================

class NombreDispositivoCreate(BaseModel):
    ip:     str
    mac:    Optional[str] = None
    nombre: str
    notas:  Optional[str] = None

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v):
        v = v.strip()
        if not v or len(v) > 255:
            raise ValueError("Nombre inválido.")
        v = re.sub(r"[<>\"';&|`]", "", v)
        return v

    @field_validator("ip")
    @classmethod
    def validar_ip(cls, v):
        v = v.strip()
        ipv4 = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(ipv4, v):
            raise ValueError("IP inválida.")
        if any(int(o) > 255 for o in v.split(".")):
            raise ValueError("IP fuera de rango.")
        return v