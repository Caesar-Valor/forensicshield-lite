-- =============================================
-- ForensicShield Lite — Esquema de base de datos (PostgreSQL)
-- Refleja exactamente los modelos de backend/models.py
--
-- Uso (desde la raíz del proyecto):
--   createdb forensicshield_db
--   psql -d forensicshield_db -f backend/schema.sql
--
-- Es idempotente: puede ejecutarse varias veces sin error.
-- =============================================

-- ---------------------------------------------
-- Tipos ENUM
-- ---------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rol_usuario') THEN
        CREATE TYPE rol_usuario AS ENUM ('admin', 'analista', 'viewer');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_escaneo') THEN
        CREATE TYPE estado_escaneo AS ENUM ('pendiente', 'en_progreso', 'completado', 'fallido');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_puerto') THEN
        CREATE TYPE estado_puerto AS ENUM ('open', 'closed', 'filtered');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'severidad_evento') THEN
        CREATE TYPE severidad_evento AS ENUM ('info', 'low', 'medium', 'high', 'critical');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'fuente_log') THEN
        CREATE TYPE fuente_log AS ENUM ('apache', 'nginx', 'ssh', 'sistema', 'firewall');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'categoria_regla') THEN
        CREATE TYPE categoria_regla AS ENUM ('brute_force', 'injection', 'reconnaissance', 'malware', 'exfiltracion');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_alerta') THEN
        CREATE TYPE estado_alerta AS ENUM ('pendiente', 'en_revision', 'resuelta', 'falso_positivo');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'formato_reporte') THEN
        CREATE TYPE formato_reporte AS ENUM ('pdf', 'json', 'csv');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_reporte') THEN
        CREATE TYPE estado_reporte AS ENUM ('generando', 'completado', 'fallido');
    END IF;
END
$$;

-- ---------------------------------------------
-- usuarios
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id             SERIAL PRIMARY KEY,
    nombre         VARCHAR(100) NOT NULL,
    apellido       VARCHAR(100) NOT NULL,
    email          VARCHAR(255) NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    rol            rol_usuario  NOT NULL DEFAULT 'viewer',
    activo         BOOLEAN      NOT NULL DEFAULT TRUE,
    avatar_url     VARCHAR(500),
    ultimo_acceso  TIMESTAMP,
    creado_en      TIMESTAMP    NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMP    NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_usuarios_email ON usuarios (email);

-- ---------------------------------------------
-- sesiones_activas
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS sesiones_activas (
    id             SERIAL PRIMARY KEY,
    usuario_id     INTEGER      NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    jwt_token_hash VARCHAR(255) NOT NULL UNIQUE,
    ip_origen      VARCHAR(45),
    dispositivo    VARCHAR(255),
    activa         BOOLEAN      NOT NULL DEFAULT TRUE,
    creado_en      TIMESTAMP    NOT NULL DEFAULT now(),
    expira_en      TIMESTAMP    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sesiones_activas_usuario ON sesiones_activas (usuario_id);

-- ---------------------------------------------
-- intentos_login
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS intentos_login (
    id           SERIAL PRIMARY KEY,
    email        VARCHAR(255) NOT NULL,
    usuario_id   INTEGER      REFERENCES usuarios (id) ON DELETE SET NULL,
    ip_origen    VARCHAR(45)  NOT NULL,
    exitoso      BOOLEAN      NOT NULL,
    motivo_fallo VARCHAR(100),
    dispositivo  VARCHAR(255),
    intentado_en TIMESTAMP    NOT NULL DEFAULT now()
);
-- Usado por el bloqueo de fuerza bruta (IP + ventana de tiempo)
CREATE INDEX IF NOT EXISTS ix_intentos_login_ip_fecha ON intentos_login (ip_origen, intentado_en);

-- ---------------------------------------------
-- recuperacion_password (reservado)
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS recuperacion_password (
    id           SERIAL PRIMARY KEY,
    usuario_id   INTEGER      NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    token_hash   VARCHAR(255) NOT NULL UNIQUE,
    usado        BOOLEAN      NOT NULL DEFAULT FALSE,
    ip_solicitud VARCHAR(45),
    creado_en    TIMESTAMP    NOT NULL DEFAULT now(),
    expira_en    TIMESTAMP    NOT NULL
);

-- ---------------------------------------------
-- escaneos
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS escaneos (
    id               SERIAL PRIMARY KEY,
    usuario_id       INTEGER        NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    target_ip        VARCHAR(45)    NOT NULL,
    target_nombre    VARCHAR(255),
    estado           estado_escaneo NOT NULL DEFAULT 'pendiente',
    puertos_abiertos INTEGER        DEFAULT 0,
    puertos_cerrados INTEGER        DEFAULT 0,
    duracion_seg     INTEGER,
    notas            TEXT,
    iniciado_en      TIMESTAMP      NOT NULL DEFAULT now(),
    finalizado_en    TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_escaneos_usuario_fecha ON escaneos (usuario_id, iniciado_en DESC);

-- ---------------------------------------------
-- scan_resultados
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS scan_resultados (
    id             SERIAL PRIMARY KEY,
    escaneo_id     INTEGER       NOT NULL REFERENCES escaneos (id) ON DELETE CASCADE,
    puerto         INTEGER       NOT NULL,
    protocolo      VARCHAR(10)   NOT NULL DEFAULT 'TCP',
    estado         estado_puerto NOT NULL,
    servicio       VARCHAR(100),
    version        VARCHAR(255),
    cve_id         VARCHAR(50),
    riesgo         VARCHAR(20),
    descubierto_en TIMESTAMP     NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_scan_resultados_escaneo ON scan_resultados (escaneo_id);

-- ---------------------------------------------
-- log_eventos (reservado)
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS log_eventos (
    id           SERIAL PRIMARY KEY,
    usuario_id   INTEGER          REFERENCES usuarios (id) ON DELETE SET NULL,
    fuente       fuente_log       NOT NULL,
    tipo_evento  VARCHAR(100)     NOT NULL,
    severidad    severidad_evento NOT NULL,
    ip_origen    VARCHAR(45)      NOT NULL,
    descripcion  TEXT,
    log_raw      TEXT,
    detectado_en TIMESTAMP        NOT NULL DEFAULT now()
);

-- ---------------------------------------------
-- reglas_deteccion (reservado)
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS reglas_deteccion (
    id             SERIAL PRIMARY KEY,
    nombre         VARCHAR(255)     NOT NULL UNIQUE,
    descripcion    TEXT,
    categoria      categoria_regla  NOT NULL,
    patron_regex   TEXT             NOT NULL,
    severidad      severidad_evento NOT NULL,
    umbral_alertas INTEGER          DEFAULT 5,
    ventana_seg    INTEGER          DEFAULT 60,
    activa         BOOLEAN          NOT NULL DEFAULT TRUE,
    creado_por     INTEGER          REFERENCES usuarios (id) ON DELETE SET NULL,
    creado_en      TIMESTAMP        NOT NULL DEFAULT now()
);

-- ---------------------------------------------
-- alertas (reservado)
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS alertas (
    id                SERIAL PRIMARY KEY,
    regla_id          INTEGER          REFERENCES reglas_deteccion (id) ON DELETE SET NULL,
    log_evento_id     INTEGER          REFERENCES log_eventos (id)      ON DELETE SET NULL,
    scan_resultado_id INTEGER          REFERENCES scan_resultados (id)  ON DELETE SET NULL,
    titulo            VARCHAR(255)     NOT NULL,
    descripcion       TEXT,
    severidad         severidad_evento NOT NULL,
    estado            estado_alerta    NOT NULL DEFAULT 'pendiente',
    ip_origen         VARCHAR(45),
    asignado_a        INTEGER          REFERENCES usuarios (id) ON DELETE SET NULL,
    resuelto_por      INTEGER          REFERENCES usuarios (id) ON DELETE SET NULL,
    resuelto_en       TIMESTAMP,
    creado_en         TIMESTAMP        NOT NULL DEFAULT now()
);

-- ---------------------------------------------
-- reportes
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS reportes (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER         NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    titulo          VARCHAR(255)    NOT NULL,
    descripcion     TEXT,
    formato         formato_reporte NOT NULL DEFAULT 'pdf',
    estado          estado_reporte  NOT NULL DEFAULT 'generando',
    contenido       JSONB,
    hash_sha256     VARCHAR(64),
    escaneos_inc    INTEGER[],
    alertas_inc     INTEGER[],
    total_hallazgos INTEGER         DEFAULT 0,
    ruta_archivo    VARCHAR(500),
    generado_en     TIMESTAMP       NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_reportes_usuario_fecha ON reportes (usuario_id, generado_en DESC);

-- ---------------------------------------------
-- nombres_dispositivos
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS nombres_dispositivos (
    id             SERIAL PRIMARY KEY,
    usuario_id     INTEGER      NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    ip             VARCHAR(45)  NOT NULL,
    mac            VARCHAR(17),
    nombre         VARCHAR(255) NOT NULL,
    notas          TEXT,
    creado_en      TIMESTAMP    NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMP    NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_nombres_dispositivos_usuario_ip ON nombres_dispositivos (usuario_id, ip);
