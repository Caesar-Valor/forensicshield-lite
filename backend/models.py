# =============================================
# ForensicShield Lite — Modelos de Base de Datos
# Cada clase representa una tabla en PostgreSQL
# =============================================

from sqlalchemy import (
    Column, Integer, String, Boolean, Text,
    TIMESTAMP, ForeignKey, ARRAY
)
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base





# =============================================
# ENUMs — deben coincidir exactamente con los
# que creaste en PostgreSQL
# =============================================



rol_usuario_enum = ENUM(
    'admin', 'analista', 'viewer',
    name='rol_usuario',
    create_type=False  # Ya existe en la BD
)

estado_escaneo_enum = ENUM(
    'pendiente', 'en_progreso', 'completado', 'fallido',
    name='estado_escaneo',
    create_type=False
)

estado_puerto_enum = ENUM(
    'open', 'closed', 'filtered',
    name='estado_puerto',
    create_type=False
)

severidad_evento_enum = ENUM(
    'info', 'low', 'medium', 'high', 'critical',
    name='severidad_evento',
    create_type=False
)

fuente_log_enum = ENUM(
    'apache', 'nginx', 'ssh', 'sistema', 'firewall',
    name='fuente_log',
    create_type=False
)

categoria_regla_enum = ENUM(
    'brute_force', 'injection', 'reconnaissance', 'malware', 'exfiltracion',
    name='categoria_regla',
    create_type=False
)

estado_alerta_enum = ENUM(
    'pendiente', 'en_revision', 'resuelta', 'falso_positivo',
    name='estado_alerta',
    create_type=False
)

formato_reporte_enum = ENUM(
    'pdf', 'json', 'csv',
    name='formato_reporte',
    create_type=False
)

estado_reporte_enum = ENUM(
    'generando', 'completado', 'fallido',
    name='estado_reporte',
    create_type=False
)

# =============================================
# TABLA: usuarios
# =============================================
class Usuario(Base):
    __tablename__ = "usuarios"

    id             = Column(Integer, primary_key=True, index=True)
    nombre         = Column(String(100), nullable=False)
    apellido       = Column(String(100), nullable=False)
    email          = Column(String(255), nullable=False, unique=True, index=True)
    password_hash  = Column(String(255), nullable=False)
    rol            = Column(rol_usuario_enum, nullable=False, default='viewer')
    activo         = Column(Boolean, nullable=False, default=True)
    avatar_url     = Column(String(500))
    ultimo_acceso  = Column(TIMESTAMP)
    creado_en      = Column(TIMESTAMP, nullable=False, server_default=func.now())
    actualizado_en = Column(TIMESTAMP, nullable=False, server_default=func.now())

    # Relaciones
    sesiones       = relationship("SesionActiva",       back_populates="usuario")
    intentos       = relationship("IntentoLogin",       back_populates="usuario")
    escaneos       = relationship("Escaneo",            back_populates="usuario")
    log_eventos    = relationship("LogEvento",          back_populates="usuario")
    reportes       = relationship("Reporte",            back_populates="usuario")

# =============================================
# TABLA: sesiones_activas
# =============================================
class SesionActiva(Base):
    __tablename__ = "sesiones_activas"

    id             = Column(Integer, primary_key=True, index=True)
    usuario_id     = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    jwt_token_hash = Column(String(255), nullable=False, unique=True)
    ip_origen      = Column(String(45))
    dispositivo    = Column(String(255))
    activa         = Column(Boolean, nullable=False, default=True)
    creado_en      = Column(TIMESTAMP, nullable=False, server_default=func.now())
    expira_en      = Column(TIMESTAMP, nullable=False)

    usuario        = relationship("Usuario", back_populates="sesiones")

# =============================================
# TABLA: intentos_login
# =============================================
class IntentoLogin(Base):
    __tablename__ = "intentos_login"

    id           = Column(Integer, primary_key=True, index=True)
    email        = Column(String(255), nullable=False)
    usuario_id   = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"))
    ip_origen    = Column(String(45), nullable=False)
    exitoso      = Column(Boolean, nullable=False)
    motivo_fallo = Column(String(100))
    dispositivo  = Column(String(255))
    intentado_en = Column(TIMESTAMP, nullable=False, server_default=func.now())

    usuario      = relationship("Usuario", back_populates="intentos")

# =============================================
# TABLA: recuperacion_password
# =============================================
class RecuperacionPassword(Base):
    __tablename__ = "recuperacion_password"

    id           = Column(Integer, primary_key=True, index=True)
    usuario_id   = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    token_hash   = Column(String(255), nullable=False, unique=True)
    usado        = Column(Boolean, nullable=False, default=False)
    ip_solicitud = Column(String(45))
    creado_en    = Column(TIMESTAMP, nullable=False, server_default=func.now())
    expira_en    = Column(TIMESTAMP, nullable=False)

# =============================================
# TABLA: escaneos
# =============================================
class Escaneo(Base):
    __tablename__ = "escaneos"

    id               = Column(Integer, primary_key=True, index=True)
    usuario_id       = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    target_ip        = Column(String(45), nullable=False)
    target_nombre    = Column(String(255))
    estado           = Column(estado_escaneo_enum, nullable=False, default='pendiente')
    puertos_abiertos = Column(Integer, default=0)
    puertos_cerrados = Column(Integer, default=0)
    duracion_seg     = Column(Integer)
    notas            = Column(Text)
    iniciado_en      = Column(TIMESTAMP, nullable=False, server_default=func.now())
    finalizado_en    = Column(TIMESTAMP)

    usuario          = relationship("Usuario", back_populates="escaneos")
    resultados       = relationship("ScanResultado", back_populates="escaneo")

# =============================================
# TABLA: scan_resultados
# =============================================
class ScanResultado(Base):
    __tablename__ = "scan_resultados"

    id             = Column(Integer, primary_key=True, index=True)
    escaneo_id     = Column(Integer, ForeignKey("escaneos.id", ondelete="CASCADE"), nullable=False)
    puerto         = Column(Integer, nullable=False)
    protocolo      = Column(String(10), nullable=False, default='TCP')
    estado         = Column(estado_puerto_enum, nullable=False)
    servicio       = Column(String(100))
    version        = Column(String(255))
    cve_id         = Column(String(50))
    riesgo         = Column(String(20))
    descubierto_en = Column(TIMESTAMP, nullable=False, server_default=func.now())

    escaneo        = relationship("Escaneo", back_populates="resultados")

# =============================================
# TABLA: log_eventos
# =============================================
class LogEvento(Base):
    __tablename__ = "log_eventos"

    id           = Column(Integer, primary_key=True, index=True)
    usuario_id   = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"))
    fuente       = Column(fuente_log_enum, nullable=False)
    tipo_evento  = Column(String(100), nullable=False)
    severidad    = Column(severidad_evento_enum, nullable=False)
    ip_origen    = Column(String(45), nullable=False)
    descripcion  = Column(Text)
    log_raw      = Column(Text)
    detectado_en = Column(TIMESTAMP, nullable=False, server_default=func.now())

    usuario      = relationship("Usuario", back_populates="log_eventos")

# =============================================
# TABLA: reglas_deteccion
# =============================================
class ReglaDeteccion(Base):
    __tablename__ = "reglas_deteccion"

    id             = Column(Integer, primary_key=True, index=True)
    nombre         = Column(String(255), nullable=False, unique=True)
    descripcion    = Column(Text)
    categoria      = Column(categoria_regla_enum, nullable=False)
    patron_regex   = Column(Text, nullable=False)
    severidad      = Column(severidad_evento_enum, nullable=False)
    umbral_alertas = Column(Integer, default=5)
    ventana_seg    = Column(Integer, default=60)
    activa         = Column(Boolean, nullable=False, default=True)
    creado_por     = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"))
    creado_en      = Column(TIMESTAMP, nullable=False, server_default=func.now())

# =============================================
# TABLA: alertas
# =============================================
class Alerta(Base):
    __tablename__ = "alertas"

    id                = Column(Integer, primary_key=True, index=True)
    regla_id          = Column(Integer, ForeignKey("reglas_deteccion.id", ondelete="SET NULL"))
    log_evento_id     = Column(Integer, ForeignKey("log_eventos.id", ondelete="SET NULL"))
    scan_resultado_id = Column(Integer, ForeignKey("scan_resultados.id", ondelete="SET NULL"))
    titulo            = Column(String(255), nullable=False)
    descripcion       = Column(Text)
    severidad         = Column(severidad_evento_enum, nullable=False)
    estado            = Column(estado_alerta_enum, nullable=False, default='pendiente')
    ip_origen         = Column(String(45))
    asignado_a        = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"))
    resuelto_por      = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"))
    resuelto_en       = Column(TIMESTAMP)
    creado_en         = Column(TIMESTAMP, nullable=False, server_default=func.now())

# =============================================
# TABLA: reportes
# =============================================
class Reporte(Base):
    __tablename__ = "reportes"

    id              = Column(Integer, primary_key=True, index=True)
    usuario_id      = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    titulo          = Column(String(255), nullable=False)
    descripcion     = Column(Text)
    formato         = Column(formato_reporte_enum, nullable=False, default='pdf')
    estado          = Column(estado_reporte_enum, nullable=False, default='generando')
    contenido       = Column(JSONB)
    hash_sha256     = Column(String(64))
    escaneos_inc    = Column(ARRAY(Integer))
    alertas_inc     = Column(ARRAY(Integer))
    total_hallazgos = Column(Integer, default=0)
    ruta_archivo    = Column(String(500))
    generado_en     = Column(TIMESTAMP, nullable=False, server_default=func.now())

    usuario         = relationship("Usuario", back_populates="reportes")


# =============================================
# TABLA: nombres_dispositivos
# =============================================

class NombreDispositivo(Base):
    __tablename__ = "nombres_dispositivos"

    id         = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    ip         = Column(String(45), nullable=False)
    mac        = Column(String(17))
    nombre     = Column(String(255), nullable=False)
    notas      = Column(Text)
    creado_en  = Column(TIMESTAMP, nullable=False, server_default=func.now())
    actualizado_en = Column(TIMESTAMP, nullable=False, server_default=func.now())
