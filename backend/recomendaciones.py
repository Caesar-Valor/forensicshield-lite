# =============================================
# ForensicShield Lite — recomendaciones.py
# Genera recomendaciones de seguridad basadas
# en los puertos abiertos detectados
# =============================================

RECOMENDACIONES = {
    21: {
        "servicio":       "FTP",
        "riesgo":         "critico",
        "titulo":         "FTP sin cifrado detectado",
        "problema":       "FTP transmite usuarios, contraseñas y archivos en texto plano. Cualquier persona en la red puede interceptarlos.",
        "accion":         "Deshabilita FTP inmediatamente y migra a SFTP (puerto 22) o FTPS (puerto 990).",
        "comando":        "netsh advfirewall firewall add rule name=BloquearFTP dir=in action=block protocol=TCP localport=21",
        "urgencia":       "inmediata",
        "referencia":     "OWASP A02:2021 — Cryptographic Failures"
    },
    22: {
        "servicio":       "SSH",
        "riesgo":         "alto",
        "titulo":         "SSH expuesto públicamente",
        "problema":       "SSH expuesto permite ataques de fuerza bruta. Si usa contraseñas débiles, es vulnerable.",
        "accion":         "Restringe el acceso SSH solo a IPs autorizadas. Configura autenticación por clave pública y deshabilita login por contraseña.",
        "comando":        "netsh advfirewall firewall add rule name=RestringirSSH dir=in action=block protocol=TCP localport=22",
        "urgencia":       "alta",
        "referencia":     "CIS Control 4 — Secure Configuration"
    },
    23: {
        "servicio":       "Telnet",
        "riesgo":         "critico",
        "titulo":         "Telnet activo — protocolo obsoleto e inseguro",
        "problema":       "Telnet transmite todo en texto plano incluyendo contraseñas. Fue reemplazado por SSH en 1995.",
        "accion":         "Deshabilita el servicio Telnet inmediatamente. No existe justificación para tener Telnet activo en 2026.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearTelnet dir=in action=block protocol=TCP localport=23",
        "urgencia":       "inmediata",
        "referencia":     "NIST SP 800-115 — Technical Guide to Information Security Testing"
    },
    25: {
        "servicio":       "SMTP",
        "riesgo":         "alto",
        "titulo":         "Servidor SMTP expuesto",
        "problema":       "SMTP sin autenticación puede ser usado como relay abierto para enviar spam o phishing.",
        "accion":         "Requiere autenticación SMTP. Restringe el acceso al puerto 25 solo a servidores de correo autorizados.",
        "comando":        "netsh advfirewall firewall add rule name=RestringirSMTP dir=in action=block protocol=TCP localport=25",
        "urgencia":       "alta",
        "referencia":     "OWASP A07:2021 — Identification and Authentication Failures"
    },
    53: {
        "servicio":       "DNS",
        "riesgo":         "medio",
        "titulo":         "Servidor DNS expuesto",
        "problema":       "Un servidor DNS mal configurado puede ser usado para amplificación de ataques DDoS o envenenamiento de caché.",
        "accion":         "Restringe las consultas DNS recursivas solo a clientes internos. Deshabilita la recursión para IPs externas.",
        "comando":        "netsh advfirewall firewall add rule name=RestringirDNS dir=in action=block protocol=UDP localport=53",
        "urgencia":       "media",
        "referencia":     "CIS Control 9 — Email and Web Browser Protections"
    },
    80: {
        "servicio":       "HTTP",
        "riesgo":         "medio",
        "titulo":         "Servidor web HTTP sin cifrado",
        "problema":       "HTTP transmite datos sin cifrar. Los usuarios son vulnerables a ataques man-in-the-middle.",
        "accion":         "Implementa HTTPS con certificado SSL/TLS. Configura redirección automática de HTTP a HTTPS.",
        "comando":        None,
        "urgencia":       "media",
        "referencia":     "OWASP A02:2021 — Cryptographic Failures"
    },
    110: {
        "servicio":       "POP3",
        "riesgo":         "alto",
        "titulo":         "POP3 sin cifrado expuesto",
        "problema":       "POP3 transmite credenciales de correo en texto plano.",
        "accion":         "Migra a POP3S (puerto 995) que usa cifrado SSL/TLS.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearPOP3 dir=in action=block protocol=TCP localport=110",
        "urgencia":       "alta",
        "referencia":     "OWASP A02:2021 — Cryptographic Failures"
    },
    135: {
        "servicio":       "RPC",
        "riesgo":         "critico",
        "titulo":         "RPC de Windows expuesto",
        "problema":       "El puerto RPC ha sido explotado históricamente por gusanos como Blaster y Sasser. Expuesto externamente es extremadamente peligroso.",
        "accion":         "Bloquea inmediatamente el acceso externo al puerto 135. Este servicio solo debe ser accesible localmente.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearRPC dir=in action=block protocol=TCP localport=135",
        "urgencia":       "inmediata",
        "referencia":     "CVE-2003-0352 — MS03-026 RPC Buffer Overflow"
    },
    139: {
        "servicio":       "NetBIOS",
        "riesgo":         "critico",
        "titulo":         "NetBIOS expuesto",
        "problema":       "NetBIOS expuesto permite enumeración de usuarios, grupos y recursos compartidos de la red.",
        "accion":         "Deshabilita NetBIOS sobre TCP/IP si no es necesario. Bloquea el acceso externo inmediatamente.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearNetBIOS dir=in action=block protocol=TCP localport=139",
        "urgencia":       "inmediata",
        "referencia":     "CIS Control 4 — Secure Configuration"
    },
    143: {
        "servicio":       "IMAP",
        "riesgo":         "alto",
        "titulo":         "IMAP sin cifrado expuesto",
        "problema":       "IMAP transmite credenciales de correo en texto plano.",
        "accion":         "Migra a IMAPS (puerto 993) que usa cifrado SSL/TLS.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearIMAP dir=in action=block protocol=TCP localport=143",
        "urgencia":       "alta",
        "referencia":     "OWASP A02:2021 — Cryptographic Failures"
    },
    443: {
        "servicio":       "HTTPS",
        "riesgo":         "bajo",
        "titulo":         "HTTPS activo — verificar configuración SSL",
        "problema":       "HTTPS está bien, pero versiones antiguas de TLS (1.0, 1.1) o cifrados débiles pueden ser vulnerables.",
        "accion":         "Verifica que uses TLS 1.2 o superior. Usa herramientas como SSL Labs para auditar la configuración.",
        "comando":        None,
        "urgencia":       "baja",
        "referencia":     "NIST SP 800-52 — TLS Guidelines"
    },
    445: {
        "servicio":       "SMB",
        "riesgo":         "critico",
        "titulo":         "SMB expuesto — vulnerabilidad EternalBlue",
        "problema":       "SMB expuesto fue el vector de WannaCry (2017) y NotPetya. Es uno de los puertos más peligrosos que puedes tener abierto.",
        "accion":         "Bloquea SMB externamente de inmediato. Aplica parche MS17-010. Deshabilita SMBv1.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearSMB dir=in action=block protocol=TCP localport=445",
        "urgencia":       "inmediata",
        "referencia":     "CVE-2017-0144 — EternalBlue / MS17-010"
    },
    1433: {
        "servicio":       "SQL Server",
        "riesgo":         "critico",
        "titulo":         "SQL Server expuesto a la red",
        "problema":       "Una base de datos expuesta directamente a internet es un objetivo de alto valor. Ataques de inyección SQL o fuerza bruta pueden comprometer todos los datos.",
        "accion":         "Restringe el acceso al puerto 1433 solo a la aplicación que lo necesita. Nunca exponer bases de datos directamente a internet.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearSQLServer dir=in action=block protocol=TCP localport=1433",
        "urgencia":       "inmediata",
        "referencia":     "OWASP A03:2021 — Injection"
    },
    3306: {
        "servicio":       "MySQL",
        "riesgo":         "alto",
        "titulo":         "MySQL expuesto a la red",
        "problema":       "MySQL expuesto permite ataques directos a la base de datos. Credenciales por defecto son frecuentemente explotadas.",
        "accion":         "Configura MySQL para escuchar solo en localhost (bind-address = 127.0.0.1). Bloquea el puerto externamente.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearMySQL dir=in action=block protocol=TCP localport=3306",
        "urgencia":       "alta",
        "referencia":     "OWASP A03:2021 — Injection"
    },
    3389: {
        "servicio":       "RDP",
        "riesgo":         "critico",
        "titulo":         "RDP expuesto — BlueKeep y fuerza bruta",
        "problema":       "RDP expuesto es uno de los vectores más usados en ransomware. BlueKeep (CVE-2019-0708) permite ejecución remota sin autenticación.",
        "accion":         "Deshabilita RDP si no es necesario. Si lo necesitas, usa VPN + RDP nunca directo a internet. Aplica parches de seguridad.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearRDP dir=in action=block protocol=TCP localport=3389",
        "urgencia":       "inmediata",
        "referencia":     "CVE-2019-0708 — BlueKeep RDP"
    },
    5432: {
        "servicio":       "PostgreSQL",
        "riesgo":         "alto",
        "titulo":         "PostgreSQL expuesto a la red",
        "problema":       "Base de datos expuesta directamente. Credenciales por defecto o débiles pueden comprometer todos los datos.",
        "accion":         "Configura PostgreSQL para escuchar solo en localhost. Bloquea el puerto 5432 externamente.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearPostgres dir=in action=block protocol=TCP localport=5432",
        "urgencia":       "alta",
        "referencia":     "OWASP A03:2021 — Injection"
    },
    5900: {
        "servicio":       "VNC",
        "riesgo":         "medio",
        "titulo":         "VNC expuesto",
        "problema":       "VNC sin autenticación o con contraseñas débiles permite acceso remoto al escritorio.",
        "accion":         "Requiere contraseña fuerte en VNC. Considera usar VPN en lugar de exponer VNC directamente.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearVNC dir=in action=block protocol=TCP localport=5900",
        "urgencia":       "media",
        "referencia":     "CIS Control 4 — Secure Configuration"
    },
    6379: {
        "servicio":       "Redis",
        "riesgo":         "alto",
        "titulo":         "Redis expuesto sin autenticación",
        "problema":       "Redis por defecto no requiere contraseña. Expuesto en red permite leer/escribir todos los datos en memoria.",
        "accion":         "Configura requirepass en Redis. Vincula Redis a localhost únicamente.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearRedis dir=in action=block protocol=TCP localport=6379",
        "urgencia":       "alta",
        "referencia":     "CVE-2022-0543 — Redis RCE"
    },
    8080: {
        "servicio":       "HTTP Alternativo",
        "riesgo":         "medio",
        "titulo":         "Puerto HTTP alternativo expuesto",
        "problema":       "Puertos HTTP alternativos frecuentemente alojan paneles de administración o APIs sin cifrar.",
        "accion":         "Verifica qué servicio corre en el puerto 8080. Si es un panel de admin, protégelo con autenticación y HTTPS.",
        "comando":        None,
        "urgencia":       "media",
        "referencia":     "OWASP A05:2021 — Security Misconfiguration"
    },
    27017: {
        "servicio":       "MongoDB",
        "riesgo":         "alto",
        "titulo":         "MongoDB expuesto sin autenticación",
        "problema":       "MongoDB por defecto no requiere autenticación. Miles de bases de datos han sido robadas por este motivo.",
        "accion":         "Habilita autenticación en MongoDB. Vincula a localhost. Nunca exponer MongoDB a internet.",
        "comando":        "netsh advfirewall firewall add rule name=BloquearMongoDB dir=in action=block protocol=TCP localport=27017",
        "urgencia":       "alta",
        "referencia":     "CVE-2017-2672 — MongoDB Unauthorized Access"
    },
}

NIVEL_URGENCIA = {
    "inmediata": 4,
    "alta":      3,
    "media":     2,
    "baja":      1
}

def generar_recomendaciones(puertos: list) -> dict:
    """
    Recibe la lista de puertos del escaneo y genera
    recomendaciones de seguridad para los puertos abiertos.
    """
    recomendaciones = []
    puertos_sin_rec = []
    resumen = {
        "inmediata": 0,
        "alta":      0,
        "media":     0,
        "baja":      0,
        "total":     0
    }

    for p in puertos:
        if p.get("estado") != "open":
            continue

        puerto_num = p.get("puerto")
        rec        = RECOMENDACIONES.get(puerto_num)

        if rec:
            recomendaciones.append({
                "puerto":     puerto_num,
                "protocolo":  p.get("protocolo", "TCP"),
                "servicio":   rec["servicio"],
                "riesgo":     rec["riesgo"],
                "titulo":     rec["titulo"],
                "problema":   rec["problema"],
                "accion":     rec["accion"],
                "comando":    rec["comando"],
                "urgencia":   rec["urgencia"],
                "referencia": rec["referencia"],
                "version":    p.get("version")
            })
            resumen[rec["urgencia"]] += 1
            resumen["total"]         += 1
        else:
            if p.get("riesgo") not in ("ninguno", "info", None):
                puertos_sin_rec.append({
                    "puerto":    puerto_num,
                    "protocolo": p.get("protocolo", "TCP"),
                    "servicio":  p.get("servicio"),
                    "riesgo":    p.get("riesgo"),
                    "version":   p.get("version")
                })

    # Ordenar por urgencia (inmediata primero)
    recomendaciones.sort(
        key=lambda x: NIVEL_URGENCIA.get(x["urgencia"], 0),
        reverse=True
    )

    return {
        "recomendaciones": recomendaciones,
        "puertos_sin_rec": puertos_sin_rec,
        "resumen":         resumen
    }