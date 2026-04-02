# =============================================
# ForensicShield Lite — network_scanner.py
# Cesar Eduardo Valenzuela Mosquera · ITESPF 2026
#
# CORRECCIONES APLICADAS:
#   - Bug #1: Se añade ping_sweep() para descubrir
#             activamente la red antes de leer arp -a
#   - Bug #3: Se eliminó la definición duplicada de
#             bloquear_dominio() y desbloquear_dominio()
# =============================================

import subprocess
import socket
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


# =============================================
# UTILIDADES DE RED
# =============================================

def obtener_subred_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
        partes = ip_local.split(".")
        subred = f"{partes[0]}.{partes[1]}.{partes[2]}.0/24"
        return subred, ip_local
    except Exception:
        return "192.168.1.0/24", "desconocida"


def resolver_hostname(ip: str) -> str:
    """DNS inverso"""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None


def resolver_nombre_netbios(ip: str) -> str:
    """Nombre NetBIOS — funciona en PCs Windows de la misma red"""
    try:
        resultado = subprocess.run(
            ["nbtstat", "-A", ip],
            capture_output=True,
            text=True,
            timeout=6
        )
        for linea in resultado.stdout.splitlines():
            linea = linea.strip()
            if "<00>" in linea and "UNIQUE" in linea:
                nombre = linea.split()[0]
                if nombre and len(nombre) > 1:
                    return nombre.strip()
    except Exception:
        pass
    return None


def resolver_nombre_completo(ip: str) -> str:
    """
    Intenta resolver el nombre del dispositivo:
    1. DNS inverso
    2. NetBIOS (Windows)
    """
    nombre = resolver_hostname(ip)
    if nombre:
        return nombre
    nombre = resolver_nombre_netbios(ip)
    if nombre:
        return nombre
    return None


# =============================================
# BUG #1 CORREGIDO — Ping sweep activo
# =============================================

def _ping_host(ip: str) -> bool:
    """
    Hace ping a una IP. Retorna True si responde.
    Usa -n 1 en Windows (1 paquete, timeout 500ms).
    """
    try:
        resultado = subprocess.run(
            ["ping", "-n", "1", "-w", "500", ip],
            capture_output=True,
            text=True,
            timeout=2
        )
        return resultado.returncode == 0
    except Exception:
        return False


def ping_sweep(prefijo: str, ip_servidor: str) -> None:
    """
    Hace ping a todas las IPs del rango .1 - .254 en paralelo
    para poblar la tabla ARP del sistema operativo.
    Usa ThreadPoolExecutor para ejecutar hasta 50 pings simultáneos.
    """
    ips = [
        f"{prefijo}.{i}"
        for i in range(1, 255)
        if f"{prefijo}.{i}" != ip_servidor
    ]

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(_ping_host, ip): ip for ip in ips}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                pass


# =============================================
# ESCANEO DE RED LOCAL (con ping sweep)
# =============================================

def escanear_red_local() -> dict:
    subred, ip_servidor = obtener_subred_local()
    prefijo = ".".join(ip_servidor.split(".")[:3])

    # ── Paso 1: Ping sweep para poblar la caché ARP ──────────────────
    # Sin esto, arp -a solo muestra dispositivos con los que ya hubo
    # comunicación reciente y la tabla aparece casi vacía.
    if ip_servidor != "desconocida":
        ping_sweep(prefijo, ip_servidor)

    # ── Paso 2: Leer la caché ARP (ahora bien poblada) ───────────────
    try:
        resultado = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            timeout=10
        )
        salida = resultado.stdout
    except Exception as e:
        return {"error": f"Error al ejecutar arp: {str(e)}", "exitoso": False}

    hosts = []
    visto = set()

    for linea in salida.splitlines():
        match_ip  = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', linea)
        match_mac = re.search(
            r'([0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-]'
            r'[0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2})',
            linea
        )

        if not match_ip:
            continue

        ip = match_ip.group(1)
        ultimo_octeto = int(ip.split(".")[-1])

        if ultimo_octeto in (0, 255) or ip in visto:
            continue

        prefijo_ip = ".".join(ip.split(".")[:3])
        if prefijo_ip != prefijo:
            continue

        # Ignorar entradas de broadcast/multicast (MACs tipo ff-ff-ff o 01-...)
        if match_mac:
            mac_raw = match_mac.group(1).upper().replace("-", ":")
            if mac_raw in ("FF:FF:FF:FF:FF:FF",) or mac_raw.startswith("01:"):
                continue
        else:
            mac_raw = None

        visto.add(ip)

        nombre     = resolver_nombre_completo(ip)
        es_servidor = (ip == ip_servidor)

        hosts.append({
            "ip":                   ip,
            "nombre":               nombre,
            "mac":                  mac_raw,
            "fabricante":           None,
            "estado":               "up",
            "es_servidor":          es_servidor,
            "nombre_personalizado": None,
            "notas":                None
        })

    # Agregar el servidor si no apareció en arp
    if ip_servidor not in visto and ip_servidor != "desconocida":
        hosts.append({
            "ip":                   ip_servidor,
            "nombre":               socket.gethostname(),
            "mac":                  None,
            "fabricante":           None,
            "estado":               "up",
            "es_servidor":          True,
            "nombre_personalizado": None,
            "notas":                None
        })

    hosts.sort(key=lambda x: int(x["ip"].split(".")[-1]))

    return {
        "subred":      subred,
        "ip_servidor": ip_servidor,
        "total_hosts": len(hosts),
        "hosts":       hosts,
        "exitoso":     True
    }


# =============================================
# FIREWALL — Bloqueo por IP
# =============================================

def bloquear_ip_firewall(ip: str, nombre_regla: str = None) -> dict:
    nombre = nombre_regla or f"ForensicShield-Bloqueo-{ip}"
    try:
        cmd_in = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={nombre}-IN", "dir=in", "action=block",
            f"remoteip={ip}", "enable=yes"
        ]
        cmd_out = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={nombre}-OUT", "dir=out", "action=block",
            f"remoteip={ip}", "enable=yes"
        ]
        res_in  = subprocess.run(cmd_in,  capture_output=True, text=True, timeout=10)
        res_out = subprocess.run(cmd_out, capture_output=True, text=True, timeout=10)

        if res_in.returncode == 0 and res_out.returncode == 0:
            return {"exitoso": True, "mensaje": f"IP {ip} bloqueada en el firewall."}
        else:
            return {
                "exitoso": False,
                "error":   res_in.stderr or res_out.stderr or "Error desconocido"
            }
    except Exception as e:
        return {"exitoso": False, "error": str(e)}


def desbloquear_ip_firewall(ip: str, nombre_regla: str = None) -> dict:
    nombre = nombre_regla or f"ForensicShield-Bloqueo-{ip}"
    try:
        cmd_in  = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={nombre}-IN"]
        cmd_out = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={nombre}-OUT"]
        subprocess.run(cmd_in,  capture_output=True, text=True, timeout=10)
        subprocess.run(cmd_out, capture_output=True, text=True, timeout=10)
        return {"exitoso": True, "mensaje": f"IP {ip} desbloqueada."}
    except Exception as e:
        return {"exitoso": False, "error": str(e)}


# =============================================
# FIREWALL — Bloqueo por dominio
# BUG #3 CORREGIDO: definición única (se eliminó el duplicado)
# =============================================

def bloquear_dominio(dominio: str) -> dict:
    """
    Resuelve las IPs de un dominio y las bloquea en el firewall de Windows.
    """
    try:
        dominio = dominio.strip().lower()
        dominio = dominio.replace("https://", "").replace("http://", "").replace("www.", "")
        dominio = dominio.split("/")[0]

        resultados = socket.getaddrinfo(dominio, None)
        ips_unicas = list(set([r[4][0] for r in resultados]))

        if not ips_unicas:
            return {"exitoso": False, "error": f"No se pudieron resolver IPs para {dominio}"}

        bloqueadas = []
        fallidas   = []

        for ip in ips_unicas:
            res = bloquear_ip_firewall(ip, f"ForensicShield-DOM-{dominio}-{ip}")
            if res["exitoso"]:
                bloqueadas.append(ip)
            else:
                fallidas.append(ip)

        return {
            "exitoso":        True,
            "dominio":        dominio,
            "ips_resueltas":  ips_unicas,
            "ips_bloqueadas": bloqueadas,
            "ips_fallidas":   fallidas
        }
    except Exception as e:
        return {"exitoso": False, "error": str(e)}


def desbloquear_dominio(dominio: str) -> dict:
    """
    Elimina las reglas de firewall de un dominio.
    BUG #3 CORREGIDO: definición única (se eliminó el duplicado)
    """
    try:
        dominio = dominio.strip().lower()
        dominio = dominio.replace("https://", "").replace("http://", "").replace("www.", "")
        dominio = dominio.split("/")[0]

        resultados = socket.getaddrinfo(dominio, None)
        ips_unicas = list(set([r[4][0] for r in resultados]))

        for ip in ips_unicas:
            desbloquear_ip_firewall(ip, f"ForensicShield-DOM-{dominio}-{ip}")

        return {
            "exitoso": True,
            "dominio": dominio,
            "mensaje": f"Reglas de {dominio} eliminadas."
        }
    except Exception as e:
        return {"exitoso": False, "error": str(e)}


# =============================================
# FIREWALL — Bloqueo por puerto
# =============================================

def cerrar_puerto_firewall(puerto: int, protocolo: str = "TCP") -> dict:
    nombre = f"ForensicShield-Puerto-{puerto}-{protocolo}"
    try:
        cmd_in = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={nombre}-IN", "dir=in", "action=block",
            f"protocol={protocolo}", f"localport={puerto}", "enable=yes"
        ]
        cmd_out = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={nombre}-OUT", "dir=out", "action=block",
            f"protocol={protocolo}", f"remoteport={puerto}", "enable=yes"
        ]
        res_in  = subprocess.run(cmd_in,  capture_output=True, text=True, timeout=10)
        res_out = subprocess.run(cmd_out, capture_output=True, text=True, timeout=10)

        if res_in.returncode == 0 and res_out.returncode == 0:
            return {"exitoso": True, "mensaje": f"Puerto {puerto}/{protocolo} bloqueado en firewall."}
        else:
            return {"exitoso": False, "error": "Error al crear regla. ¿Uvicorn corre como admin?"}
    except Exception as e:
        return {"exitoso": False, "error": str(e)}


def abrir_puerto_firewall(puerto: int, protocolo: str = "TCP") -> dict:
    nombre = f"ForensicShield-Puerto-{puerto}-{protocolo}"
    try:
        for direccion in ["IN", "OUT"]:
            subprocess.run([
                "netsh", "advfirewall", "firewall", "delete", "rule",
                f"name={nombre}-{direccion}"
            ], capture_output=True, text=True, timeout=10)
        return {"exitoso": True, "mensaje": f"Reglas del puerto {puerto}/{protocolo} eliminadas."}
    except Exception as e:
        return {"exitoso": False, "error": str(e)}