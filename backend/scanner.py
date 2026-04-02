# =============================================
# ForensicShield Lite — scanner.py
# Motor de escaneo de puertos con Nmap
# Cesar Eduardo Valenzuela Mosquera · ITESPF 2026
# Este módulo contiene la lógica principal para ejecutar escaneos de puertos utilizando Nmap, procesar los resultados y generar recomendaciones de seguridad basadas en los servicios detectados. Se integra con el router de FastAPI para exponer esta funcionalidad a través de una API REST.
# =============================================

import nmap
import socket
import subprocess
import os
from datetime import datetime, timezone
from typing import Optional

# =============================================
# FIX DE ENCODING — Windows en español
# Nmap en Windows con idioma español genera
# salida en cp1252/latin-1, no UTF-8.
# Forzamos la variable de entorno antes de
# cualquier llamada a nmap para que el proceso
# hijo produzca salida UTF-8 limpia.
# =============================================
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("NMAP_PRIVILEGED", "")

def _safe_decode(data: bytes) -> str:
    """Decodifica bytes intentando UTF-8, cp1252 y latin-1."""
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")

# =============================================
# Clasificación de riesgo por puerto
# Basado en puertos conocidos peligrosos
# =============================================
PUERTOS_RIESGO = {
    # Crítico — servicios sin cifrado o muy vulnerables
    21:   "critico",   # FTP
    23:   "critico",   # Telnet
    69:   "critico",   # TFTP
    135:  "critico",   # RPC Windows
    137:  "critico",   # NetBIOS
    138:  "critico",   # NetBIOS
    139:  "critico",   # NetBIOS
    445:  "critico",   # SMB (EternalBlue)
    1433: "critico",   # SQL Server
    3389: "critico",   # RDP

    # Alto — servicios sensibles expuestos
    22:   "alto",      # SSH
    25:   "alto",      # SMTP
    110:  "alto",      # POP3
    143:  "alto",      # IMAP
    512:  "alto",      # rexec
    513:  "alto",      # rlogin
    514:  "alto",      # rsh
    3306: "alto",      # MySQL
    5432: "alto",      # PostgreSQL
    6379: "alto",      # Redis
    27017:"alto",      # MongoDB

    # Medio — servicios web o de infraestructura
    80:   "medio",     # HTTP
    8080: "medio",     # HTTP alternativo
    8443: "medio",     # HTTPS alternativo
    2049: "medio",     # NFS
    5900: "medio",     # VNC

    # Bajo — servicios cifrados o de bajo riesgo
    443:  "bajo",      # HTTPS
    465:  "bajo",      # SMTPS
    993:  "bajo",      # IMAPS
    995:  "bajo",      # POP3S
    53:   "bajo",      # DNS
}

def clasificar_riesgo(puerto: int, estado: str) -> str:
    """
    Devuelve el nivel de riesgo de un puerto.
    Solo los puertos abiertos tienen riesgo real.
    """
    if estado != "open":
        return "ninguno"
    return PUERTOS_RIESGO.get(puerto, "info")

# =============================================
# MODO RÁPIDO — Puertos más comunes (~30 seg)
# =============================================
PUERTOS_RAPIDO = (
    "21,22,23,25,53,80,110,135,139,143,443,445,"
    "465,993,995,1433,2049,3306,3389,5432,5900,"
    "6379,8080,8443,27017"
)

# =============================================
# FUNCIÓN PRINCIPAL DE ESCANEO
# =============================================
def ejecutar_escaneo(
    target_ip: str,
    modo: str = "rapido",          # "rapido" o "completo"
    puertos_custom: Optional[str] = None   # ej: "80,443,8080"
) -> dict:
    """
    Ejecuta un escaneo Nmap contra una IP objetivo.

    Parámetros:
        target_ip      : IP o hostname a escanear
        modo           : 'rapido' (puertos comunes) o 'completo' (1-65535)
        puertos_custom : rango personalizado de puertos (opcional)

    Retorna un dict con:
        - ip, hostname, estado_host
        - puertos: lista de resultados por puerto
        - resumen: contadores y duración
    """

    # ── Validar IP básica ────────────────────────────────────────────
    try:
        socket.inet_aton(target_ip)
    except socket.error:
        # Puede ser un hostname — intentar resolverlo
        try:
            socket.gethostbyname(target_ip)
        except socket.gaierror:
            return {
                "error": f"IP o hostname inválido: {target_ip}",
                "exitoso": False
            }

    # ── Configurar argumentos de Nmap ────────────────────────────────
    if puertos_custom:
        rango_puertos = puertos_custom
        descripcion_modo = "personalizado"
    elif modo == "completo":
        rango_puertos = "1-65535"
        descripcion_modo = "completo"
    else:
        rango_puertos = PUERTOS_RAPIDO
        descripcion_modo = "rapido"

    # -sV  → detectar versiones de servicios
    # -T4  → velocidad agresiva (equilibrio velocidad/precisión)
    # --open → mostrar solo puertos abiertos en el output (igual escaneamos todos)
    # -sV  → detectar versiones de servicios
    # -T4  → velocidad agresiva (equilibrio velocidad/precisión)
    # --host-timeout → evita cuelgues en hosts que no responden
    argumentos_nmap = "-sV -T4 --host-timeout 120s"

    nm = nmap.PortScanner()
    inicio = datetime.now(timezone.utc)

    try:
        nm.scan(
            hosts     = target_ip,
            ports     = rango_puertos,
            arguments = argumentos_nmap
        )
    except UnicodeDecodeError:
        # ── Fallback de encoding ──────────────────────────────────────
        # python-nmap llama internamente a subprocess con text=True
        # y falla al decodificar la salida en cp1252/latin-1.
        # Solución: invocar nmap directamente como bytes y parsear XML.
        try:
            cmd = [
                "nmap", "-sV", "-T4", "--host-timeout", "120s",
                "-oX", "-",       # XML por stdout — sin caracteres raros
                "-p", rango_puertos,
                target_ip
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,   # lee bytes, no texto
                timeout=300
            )
            if proc.returncode != 0:
                err_msg = _safe_decode(proc.stderr) if proc.stderr else "Error desconocido"
                return {"error": f"Nmap falló: {err_msg}", "exitoso": False}

            xml_str = _safe_decode(proc.stdout)
            nm = nmap.PortScanner()
            nm.analyse_nmap_xml_scan(xml_str)
        except Exception as e2:
            return {
                "error":   f"Error de encoding al procesar nmap: {str(e2)}",
                "exitoso": False
            }
    except nmap.PortScannerError as e:
        return {
            "error":   f"Error de Nmap: {str(e)}",
            "exitoso": False
        }
    except Exception as e:
        return {
            "error":   f"Error inesperado: {str(e)}",
            "exitoso": False
        }

    fin = datetime.now(timezone.utc)
    duracion_seg = int((fin - inicio).total_seconds())

    # ── Procesar resultados ──────────────────────────────────────────
    puertos_resultado = []
    contadores = {
        "open":     0,
        "closed":   0,
        "filtered": 0
    }

    # Verificar si el host respondió
    if target_ip not in nm.all_hosts():
        return {
            "ip":       target_ip,
            "hostname": target_ip,
            "estado_host": "down",
            "puertos":  [],
            "resumen": {
                "modo":           descripcion_modo,
                "puertos_open":   0,
                "puertos_closed": 0,
                "puertos_filtered": 0,
                "duracion_seg":   duracion_seg,
                "iniciado_en":    inicio.isoformat(),
                "finalizado_en":  fin.isoformat(),
            },
            "exitoso": True,
            "advertencia": "El host no respondió. Puede estar apagado o bloquear pings."
        }

    host_info = nm[target_ip]

    # Hostname
    hostnames = host_info.hostnames()
    hostname  = hostnames[0]["name"] if hostnames and hostnames[0]["name"] else target_ip

    # Estado del host
    estado_host = host_info.state()

    # Iterar protocolos (tcp, udp)
    for protocolo in host_info.all_protocols():
        puertos_lista = sorted(host_info[protocolo].keys())

        for puerto in puertos_lista:
            info_puerto = host_info[protocolo][puerto]
            estado      = info_puerto["state"]        # open / closed / filtered
            servicio    = info_puerto.get("name", "")
            version     = info_puerto.get("version", "")
            producto    = info_puerto.get("product", "")

            # Concatenar producto + versión si existen
            version_completa = " ".join(filter(None, [producto, version])).strip()

            riesgo = clasificar_riesgo(puerto, estado)

            # Contar estados
            if estado in contadores:
                contadores[estado] += 1

            puertos_resultado.append({
                "puerto":    puerto,
                "protocolo": protocolo.upper(),
                "estado":    estado,
                "servicio":  servicio  or None,
                "version":   version_completa or None,
                "riesgo":    riesgo,
            })

    # Ordenar: primero los abiertos, luego por número de puerto
    puertos_resultado.sort(key=lambda x: (x["estado"] != "open", x["puerto"]))

    return {
        "ip":          target_ip,
        "hostname":    hostname,
        "estado_host": estado_host,
        "puertos":     puertos_resultado,
        "resumen": {
            "modo":               descripcion_modo,
            "puertos_open":       contadores["open"],
            "puertos_closed":     contadores["closed"],
            "puertos_filtered":   contadores["filtered"],
            "duracion_seg":       duracion_seg,
            "iniciado_en":        inicio.isoformat(),
            "finalizado_en":      fin.isoformat(),
        },
        "exitoso": True
    }

from recomendaciones import generar_recomendaciones