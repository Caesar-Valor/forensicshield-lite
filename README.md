# ForensicShield Lite

**Plataforma web de auditoría de seguridad y análisis forense digital.**

ForensicShield Lite permite escanear puertos y dispositivos de una red local, clasificar el riesgo de los servicios expuestos, aplicar medidas correctivas directamente sobre el firewall de Windows, analizar URLs y archivos sospechosos y generar reportes PDF de auditoría con hash de integridad.

> Proyecto académico — Cesar Eduardo Valenzuela Mosquera · ITESPF 2026

---

## Índice

- [Funcionalidades](#funcionalidades)
- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Ejecución](#ejecución)
- [API REST](#api-rest)
- [Modelo de datos](#modelo-de-datos)
- [Seguridad implementada](#seguridad-implementada)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Aviso legal](#aviso-legal)

---

## Funcionalidades

### 🔐 Autenticación
- Login con email y contraseña (hash **bcrypt**).
- Token **JWT** entregado en una cookie `HttpOnly` + `SameSite=Strict` (nunca accesible desde JavaScript).
- Registro de sesiones activas (se guarda el hash SHA-256 del token). Cada petición comprueba que la sesión siga activa, así que al cerrar sesión el token queda revocado aunque no haya expirado.
- Bloqueo por IP tras _N_ intentos fallidos dentro de una ventana de tiempo y rate limit de 10 peticiones/minuto en el login.
- Registro de todos los intentos de login (exitosos y fallidos, con motivo, IP y user-agent).

### 🛰️ Port Scanner (`scanner.html`)
- Escaneo con **Nmap** (`-sV`, detección de servicio y versión) en tres modos:
  - **Rápido** — 25 puertos comunes con intensidad de versión reducida (límite de 2 min por host).
  - **Completo** — puertos 1–65535 (límite de 15 min por host).
  - **Personalizado** — lista o rango de puertos definido por el usuario.
- Ejecución en segundo plano (`BackgroundTasks`) y consulta del resultado por *polling* desde el frontend.
- Clasificación de riesgo por puerto: `critico`, `alto`, `medio`, `bajo`, `info` (p. ej. Telnet, SMB, RDP → crítico; SSH, MySQL, Redis → alto).
- **Recomendaciones de seguridad** por servicio detectado: problema, acción sugerida, comando `netsh`, nivel de urgencia y referencia (OWASP, CIS, NIST).
- Cierre/apertura de puertos creando reglas en el **Firewall de Windows** (`netsh advfirewall`).
- Aviso de puertos del sistema operativo (RPC, NetBIOS, SMB…) que no se pueden cerrar desde localhost, con pasos manuales.
- Historial de los últimos 50 escaneos del usuario.

### 🌐 Descubrimiento de red local
- Detección automática de la subred `/24` del servidor.
- *Ping sweep* paralelo (100 hilos) para poblar la caché ARP y lectura de `arp -a` (IP + MAC).
- Resolución de nombres por DNS inverso.
- Asignación de **nombres personalizados y notas** a cada dispositivo (persistidos por usuario).
- Bloqueo/desbloqueo de **IPs** y **dominios** (resuelve todas sus IPs) en el firewall.
- Lanzar un escaneo de puertos directamente desde un host descubierto.

### 🧪 Log Analyzer / Threat Intelligence (`loganalyzer.html`)
- **Análisis de URLs** con heurísticas locales: HTTP sin cifrado, IP en lugar de dominio, exceso de subdominios, imitación de marcas, TLD sospechosos, palabras clave de phishing, descarga de ejecutables, URLs muy largas o con mucho *URL-encoding*, puertos no estándar.
- **Análisis de archivos** (sin subirlos al backend): extensiones ejecutables o peligrosas, doble extensión, nombres sospechosos, ejecutables anormalmente pequeños y cálculo del **SHA-256** en el navegador.
- Integración opcional con **VirusTotal API v3** (URL, hash y subida de archivo). La API Key se guarda solo en memoria y se pierde al recargar.
- Veredicto combinado (heurística + VirusTotal), historial de la sesión y exportación del resultado a JSON.

### 📄 Reportes (`reportes.html`)
- Generación de un **reporte PDF** (fpdf2) por cada escaneo completado: portada con resumen y riesgo máximo, tabla de puertos y recomendaciones.
- Numeración única `FSL-<año>-<id>` y **hash SHA-256** del PDF guardado en BD para verificar integridad.
- Listado y descarga de los reportes del usuario.

### 🎨 Interfaz
- Dashboard, sidebar de navegación y login con fondo animado (**Three.js**) y transiciones con **GSAP**.
- Tema claro/oscuro.

---

## Arquitectura

```
┌──────────────────────────┐   fetch + cookie HttpOnly   ┌──────────────────────────────┐
│  Frontend estático       │ ──────────────────────────▶ │  Backend FastAPI (uvicorn)   │
│  HTML + CSS + JS vanilla │ ◀────────────────────────── │  :8000                       │
│  (Live Server :5500)     │            JSON / PDF       │                              │
└────────────┬─────────────┘                             │  routers/ auth · scanner ·   │
             │                                           │           network · reportes │
             │ API v3 (opcional, desde el navegador)     └───────┬───────────┬──────────┘
             ▼                                                   │           │
      ┌──────────────┐                              SQLAlchemy   │           │ subprocess
      │  VirusTotal  │                                           ▼           ▼
      └──────────────┘                                   ┌────────────┐ ┌──────────────────────┐
                                                         │ PostgreSQL │ │ nmap · ping · arp ·  │
                                                         └────────────┘ │ netsh (Firewall Win) │
                                                                        └──────────────────────┘
```

---

## Tecnologías

| Capa | Tecnologías |
|------|-------------|
| Backend | Python 3, FastAPI, Uvicorn, SQLAlchemy 2, Pydantic 2 |
| Base de datos | PostgreSQL (psycopg2), tipos `ENUM`, `JSONB` y `ARRAY` |
| Seguridad | python-jose (JWT), passlib + bcrypt, slowapi (rate limiting) |
| Escaneo | Nmap + python-nmap, utilidades de Windows (`ping`, `arp`, `netsh`) |
| Reportes | fpdf2, Pillow |
| Frontend | HTML5, CSS3, JavaScript (vanilla), GSAP, Three.js, Google Fonts |
| Externo | VirusTotal API v3 (opcional) |

---

## Estructura del proyecto

```
PROYECTO CIBERSEGURIDAD/
├── index.html              # Dashboard principal
├── login.html              # Inicio de sesión
├── scanner.html            # Port Scanner + red local
├── loganalyzer.html        # Análisis de URLs y archivos
├── reportes.html           # Generación y descarga de reportes
├── css/                    # Estilos por página
├── js/
│   ├── script.js           # Dashboard
│   ├── login.js            # Login y fondo animado
│   ├── scanner.js          # Escaneo, red local, firewall, recomendaciones
│   ├── loganalyzer.js      # Heurísticas + VirusTotal
│   └── reportes.js         # Reportes PDF
├── img/                    # Logos (también usados en el PDF)
└── backend/
    ├── main.py             # App FastAPI, CORS, headers de seguridad, routers
    ├── database.py         # Conexión a PostgreSQL
    ├── models.py           # Modelos SQLAlchemy (tablas)
    ├── schemas.py          # Validación de entrada con Pydantic
    ├── auth.py             # bcrypt + JWT
    ├── scanner.py          # Motor de escaneo con Nmap
    ├── network_scanner.py  # Descubrimiento de red y reglas de firewall
    ├── recomendaciones.py  # Base de recomendaciones por puerto
    ├── crear_usuario.py    # Script para crear usuarios / cambiar contraseñas
    ├── schema.sql          # Esquema completo de PostgreSQL
    ├── pdf_generator.py    # Generación del reporte PDF
    ├── routers/
    │   ├── auth.py
    │   ├── scanner.py
    │   ├── network.py
    │   └── reportes.py
    ├── reports/            # PDFs generados (ignorado por git)
    ├── requirements.txt
    └── .env.example
```

---

## Requisitos

- **Windows 10/11** — el descubrimiento de red y el firewall usan `ping -n`, `arp -a` y `netsh advfirewall`.
- **Python 3.10+**
- **PostgreSQL 13+**
- **[Nmap](https://nmap.org/download.html)** instalado y disponible en el `PATH`.
- Un servidor estático para el frontend en el puerto **5500 o 5501** (p. ej. la extensión *Live Server* de VS Code), ya que son los orígenes permitidos por CORS.
- *(Opcional)* Una API Key gratuita de [VirusTotal](https://www.virustotal.com/).

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Caesar-Valor/forensicshield-lite.git
cd forensicshield-lite
```

### 2. Entorno virtual y dependencias

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 3. Variables de entorno

```powershell
copy backend\.env.example backend\.env
```

Edita `backend/.env`:

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Cadena de conexión, p. ej. `postgresql://usuario:clave@localhost:5432/forensicshield_db` |
| `SECRET_KEY` | Clave para firmar los JWT. Genera una con `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM` | Algoritmo JWT (por defecto `HS256`) |
| `TOKEN_EXPIRE_MINUTES` | Duración de la sesión (por defecto `60`) |
| `COOKIE_SECURE` | `true` en producción con HTTPS |
| `MAX_INTENTOS_LOGIN` | Intentos fallidos permitidos por IP (por defecto `5`) |
| `VENTANA_BLOQUEO_MINUTOS` | Ventana de bloqueo (por defecto `15`) |

> El servidor **no arranca** si `SECRET_KEY` no está definida.

### 4. Base de datos

Crea la base de datos y carga el esquema (tipos `ENUM`, tablas e índices). El script es idempotente, así que puedes volver a ejecutarlo sin problemas:

```powershell
createdb -U postgres forensicshield_db
psql -U postgres -d forensicshield_db -f backend/schema.sql
```

> `backend/schema.sql` refleja exactamente los modelos de `backend/models.py`. Si modificas un modelo, actualiza también el script.

### 5. Crear el primer usuario

No hay endpoint de registro; los usuarios se crean con el script incluido (pide la contraseña de forma oculta):

```powershell
cd backend
python crear_usuario.py --email admin@ejemplo.com --nombre Admin --apellido Principal --rol admin
```

Si el email ya existe, el script actualiza su contraseña y reactiva la cuenta.

---

## Ejecución

### Backend

Desde `backend/`, en una terminal **ejecutada como Administrador** (necesario para Nmap `-sV` y para crear reglas de firewall):

```powershell
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- API: <http://127.0.0.1:8000>
- Documentación interactiva (Swagger): <http://127.0.0.1:8000/docs>

### Frontend

Abre la carpeta raíz con **Live Server** (VS Code) y navega a `login.html`:

```
http://127.0.0.1:5500/login.html
```

> El frontend apunta a `http://127.0.0.1:8000` (constante `API_URL` en cada archivo de `js/`). Si cambias el puerto o el host, actualiza esa constante y la lista `ALLOWED_ORIGINS` de `backend/main.py`.

---

## API REST

Todas las rutas (salvo `/`, `/docs` y el login) requieren la cookie `fs_token`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET`  | `/` | Estado del servicio |
| `POST` | `/api/auth/login` | Inicia sesión y emite la cookie JWT |
| `POST` | `/api/auth/logout` | Invalida la sesión y borra la cookie |
| `POST` | `/api/scanner/iniciar` | Lanza un escaneo (`target_ip`, `modo`, `puertos_custom`, `target_nombre`) |
| `GET`  | `/api/scanner/resultado/{id}` | Estado / resultado de un escaneo |
| `GET`  | `/api/scanner/historial` | Últimos 50 escaneos del usuario |
| `GET`  | `/api/scanner/recomendaciones/{id}` | Recomendaciones para un escaneo completado |
| `POST` | `/api/scanner/cerrar-puerto?puerto=&protocolo=` | Crea reglas de bloqueo del puerto |
| `POST` | `/api/scanner/abrir-puerto?puerto=&protocolo=` | Elimina las reglas de bloqueo del puerto |
| `GET`  | `/api/network/hosts` | Descubre los hosts activos de la red local |
| `POST` | `/api/network/nombre` | Guarda nombre/notas de un dispositivo |
| `GET`  | `/api/network/nombres` | Lista los nombres guardados |
| `POST` | `/api/network/bloquear?ip=` | Bloquea una IP (entrada y salida) |
| `POST` | `/api/network/desbloquear?ip=` | Desbloquea una IP |
| `POST` | `/api/network/bloquear-dominio?dominio=` | Bloquea todas las IPs de un dominio |
| `POST` | `/api/network/desbloquear-dominio?dominio=` | Desbloquea un dominio |
| `POST` | `/api/reportes/generar/{escaneo_id}` | Genera el PDF de un escaneo |
| `GET`  | `/api/reportes/lista` | Lista los reportes del usuario |
| `GET`  | `/api/reportes/descargar/{reporte_id}` | Descarga el PDF |

---

## Modelo de datos

| Tabla | Propósito |
|-------|-----------|
| `usuarios` | Cuentas, rol (`admin` / `analista` / `viewer`) y último acceso |
| `sesiones_activas` | Sesiones JWT (hash del token, IP, dispositivo, expiración) |
| `intentos_login` | Auditoría de intentos de inicio de sesión |
| `recuperacion_password` | Tokens de recuperación de contraseña *(reservado)* |
| `escaneos` | Cabecera de cada escaneo (objetivo, estado, contadores, duración) |
| `scan_resultados` | Puertos detectados por escaneo (servicio, versión, riesgo) |
| `nombres_dispositivos` | Nombres personalizados de hosts de la red local |
| `reportes` | Reportes generados (contenido JSONB, ruta del PDF, SHA-256) |
| `log_eventos`, `reglas_deteccion`, `alertas` | Motor de detección y alertas *(modelado, aún sin endpoints)* |

---

## Seguridad implementada

- Contraseñas con **bcrypt**; JWT firmado con expiración.
- Token en cookie **HttpOnly + SameSite=Strict** (+ `Secure` configurable).
- **Rate limiting** del login y bloqueo temporal por IP tras intentos fallidos.
- Mensaje de error genérico en el login (no revela si el usuario existe).
- Validación estricta con Pydantic: formato de IP/hostname, lista blanca de caracteres para puertos, rechazo de metacaracteres de shell (`; & | $ \` < >`) para evitar *command injection*.
- Las acciones de firewall solo aceptan IPs concretas (se rechazan palabras clave de `netsh` como `any` o `localsubnet` y los rangos CIDR), dominios con formato válido, puertos 1–65535 y protocolo TCP/UDP.
- Llamadas a procesos del sistema con listas de argumentos (sin `shell=True`).
- Cada usuario solo accede a sus propios escaneos, reportes y dispositivos.
- **CORS** restringido a orígenes locales conocidos y solo métodos `GET`/`POST`.
- Cabeceras de seguridad: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`.
- Hash **SHA-256** de cada PDF generado para verificación de integridad.
- Secretos fuera del repositorio (`.env` ignorado por git).

---

## Limitaciones conocidas

- Funciona solo en **Windows** (comandos `netsh`, `ping -n`, `arp -a`).
- Las acciones de firewall y el escaneo con detección de versiones requieren ejecutar `uvicorn` **como Administrador**.
- El descubrimiento de red asume una subred `/24`.
- El Firewall de Windows no filtra el tráfico local: los puertos cerrados con la herramienta pueden seguir apareciendo al escanear `127.0.0.1` o la propia IP del servidor.
- No hay registro de usuarios ni panel de administración; los usuarios se crean con `backend/crear_usuario.py`.
- Las tablas `log_eventos`, `reglas_deteccion`, `alertas` y `recuperacion_password` están modeladas pero todavía no se usan.
- La URL del backend está fijada en el código del frontend (`API_URL`).

---

## Aviso legal

Esta herramienta está pensada para **fines educativos y de auditoría autorizada**. Escanea únicamente equipos y redes de tu propiedad o para los que tengas permiso explícito. El uso no autorizado de escáneres de puertos puede ser ilegal en tu jurisdicción.

---

**Autor:** Cesar Eduardo Valenzuela Mosquera — [GitHub @Caesar-Valor](https://github.com/Caesar-Valor)
