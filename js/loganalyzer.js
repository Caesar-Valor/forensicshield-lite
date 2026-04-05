/* =============================================
   ForensicShield Lite — loganalyzer.js
   Módulo Log Analyzer — Threat Intelligence
   Cesar Eduardo Valenzuela Mosquera · ITESPF 2026
    Este archivo contiene la lógica principal del analizador de logs y URL/archivos, así como la gestión de la API Key de VirusTotal. Incluye:
    - Verificación de sesión y manejo de tokens
    - Animación de fondo con Three.js
    - Interacción con el backend para analizar URLs y archivos
    - Renderizado dinámico de resultados y recomendaciones
   ============================================= */

const API_URL = "http://127.0.0.1:8000";

/* ===== VERIFICAR SESIÓN ===== */
// El token JWT viaja en HttpOnly cookie — no accesible desde JS
const nombre   = sessionStorage.getItem("fs_nombre");
const apellido = sessionStorage.getItem("fs_apellido");
const rol      = sessionStorage.getItem("fs_rol");

if (!nombre) window.location.href = "login.html";

if (nombre) {
  document.getElementById("userName").textContent   = `${nombre} ${apellido || ""}`.trim();
  document.getElementById("userRol").textContent    = rol || "usuario";
  const iniciales = `${nombre[0]}${apellido ? apellido[0] : ""}`.toUpperCase();
  document.getElementById("userAvatar").textContent = iniciales;
}

/* ===== TEMA ===== */
const root      = document.documentElement;
const toggleBtn = document.getElementById("themeToggle");
toggleBtn.addEventListener("click", () => {
  const isLight = root.getAttribute("data-theme") === "light";
  isLight ? root.removeAttribute("data-theme") : root.setAttribute("data-theme", "light");
  if (typeof gsap !== "undefined") gsap.fromTo("body", { opacity: 0.8 }, { opacity: 1, duration: 0.5 });
});

/* ===== ANIMACIONES DE ENTRADA ===== */
window.addEventListener("load", () => {
  if (typeof gsap === "undefined") return;
  gsap.from(".sidebar",         { x: -30, opacity: 0, duration: 0.6, ease: "power3.out" });
  gsap.from(".scanner-header",  { y: 20,  opacity: 0, duration: 0.5, delay: 0.1, ease: "power3.out" });
  gsap.from(".la-tabs-section", { y: 16,  opacity: 0, duration: 0.4, delay: 0.2, ease: "power2.out" });
  gsap.from(".la-panel",        { y: 16,  opacity: 0, duration: 0.4, delay: 0.3, ease: "power2.out" });
});

/* ===== API KEY VIRUSTOTAL =====
   La key se guarda SOLO en memoria (variable JS), no en sessionStorage.
   Así no es accesible desde otras pestañas ni persiste tras cerrar el tab.
   El usuario debe reingresarla si recarga la página. */
let vtApiKey = "";

document.getElementById("btnConfigToggle").addEventListener("click", () => {
  const body = document.getElementById("configBody");
  body.hidden = !body.hidden;
});

document.getElementById("btnGuardarKey").addEventListener("click", () => {
  const val = document.getElementById("vtApiKey").value.trim();
  if (!val || val.length < 32) {
    mostrarApiStatus("La API Key parece inválida. Debe tener al menos 32 caracteres.", "error");
    return;
  }
  vtApiKey = val;
  mostrarApiStatus("API Key cargada en memoria. Se perderá al recargar la página.", "ok");
});

document.getElementById("btnLimpiarKey").addEventListener("click", () => {
  vtApiKey = "";
  document.getElementById("vtApiKey").value = "";
  mostrarApiStatus("API Key eliminada.", "info");
});

function mostrarApiStatus(msg, tipo) {
  const el = document.getElementById("apiStatus");
  el.textContent  = msg;
  el.className    = `la-api-status ${tipo}`;
  el.hidden       = false;
  setTimeout(() => { el.hidden = true; }, 4000);
}

/* ===== TABS URL / ARCHIVO ===== */
document.querySelectorAll(".la-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".la-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    const tipo = tab.dataset.tab;
    document.getElementById("panelUrl").hidden  = tipo !== "url";
    document.getElementById("panelFile").hidden = tipo !== "file";
  });
});

/* ===== DROPZONE ===== */
const dropzone     = document.getElementById("dropzone");
const fileInput    = document.getElementById("fileInput");
const dropzoneContent = document.getElementById("dropzoneContent");
const dropzoneFile    = document.getElementById("dropzoneFile");
let archivoSeleccionado = null;

dropzone.addEventListener("dragover",  e => { e.preventDefault(); dropzone.classList.add("drag-over"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
dropzone.addEventListener("drop", e => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) seleccionarArchivo(file);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) seleccionarArchivo(fileInput.files[0]);
});

document.getElementById("btnClearFile").addEventListener("click", e => {
  e.stopPropagation();
  limpiarArchivo();
});

function seleccionarArchivo(file) {
  if (file.size > 32 * 1024 * 1024) {
    mostrarAlert("fileAlert", "El archivo supera el límite de 32 MB.", "error");
    return;
  }
  archivoSeleccionado = file;
  document.getElementById("dropzoneFilename").textContent = file.name;
  document.getElementById("dropzoneFilesize").textContent = formatearTamano(file.size);
  dropzoneContent.hidden = true;
  dropzoneFile.hidden    = false;
  document.getElementById("btnAnalizarFile").disabled = false;
  ocultarAlert("fileAlert");
}

function limpiarArchivo() {
  archivoSeleccionado = null;
  fileInput.value     = "";
  dropzoneContent.hidden = false;
  dropzoneFile.hidden    = true;
  document.getElementById("btnAnalizarFile").disabled = true;
}

function formatearTamano(bytes) {
  if (bytes < 1024)        return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/* ===== ANALIZAR URL ===== */
document.getElementById("btnAnalizarUrl").addEventListener("click", async () => {
  const url = document.getElementById("urlInput").value.trim();
  if (!url) {
    mostrarAlert("urlAlert", "Ingresa una URL antes de analizar.", "error");
    return;
  }
  if (!/^https?:\/\/.+/.test(url)) {
    mostrarAlert("urlAlert", "La URL debe comenzar con http:// o https://", "error");
    return;
  }
  ocultarAlert("urlAlert");
  await ejecutarAnalisis("url", url);
});

/* ===== ANALIZAR ARCHIVO ===== */
document.getElementById("btnAnalizarFile").addEventListener("click", async () => {
  if (!archivoSeleccionado) return;
  ocultarAlert("fileAlert");
  await ejecutarAnalisis("file", archivoSeleccionado);
});

/* =============================================
   MOTOR PRINCIPAL DE ANÁLISIS
   ============================================= */

let ultimoResultado = null;
const historial = [];

async function ejecutarAnalisis(tipo, objetivo) {
  /* UI — estado cargando */
  const btnId   = tipo === "url" ? "btnAnalizarUrl" : "btnAnalizarFile";
  const txtId   = tipo === "url" ? "btnUrlText"     : "btnFileText";
  const btn     = document.getElementById(btnId);
  const txt     = document.getElementById(txtId);
  btn.disabled  = true;
  txt.textContent = "Analizando...";

  mostrarResultadoParcial(tipo, objetivo);

  try {
    let resultado;

    if (tipo === "url") {
      resultado = await analizarUrl(objetivo);
    } else {
      resultado = await analizarArchivo(objetivo);
    }

    ultimoResultado = resultado;
    renderizarResultado(resultado);
    agregarHistorial(resultado);

  } catch (err) {
    console.error("Error en análisis:", err);
    const alertId = tipo === "url" ? "urlAlert" : "fileAlert";
    mostrarAlert(alertId, `Error al analizar: ${err.message}`, "error");
    document.getElementById("resultadoSection").hidden = true;

  } finally {
    btn.disabled    = false;
    txt.textContent = tipo === "url" ? "Analizar URL" : "Analizar Archivo";
  }
}

/* =============================================
   ANÁLISIS DE URL
   ============================================= */

async function analizarUrl(url) {
  const inicio    = new Date();
  const heuristica = analizarUrlHeuristica(url);
  let vt          = null;

  if (vtApiKey) {
    vt = await consultarVtUrl(url);
  }

  const veredicto = calcularVeredicto(heuristica, vt);

  return {
    tipo:       "URL",
    objetivo:   url,
    hash:       await sha256Texto(url),
    heuristica,
    vt,
    veredicto,
    timestamp:  inicio.toISOString(),
    analista:   `${nombre} ${apellido || ""}`.trim()
  };
}

/* ===== HEURÍSTICAS DE URL ===== */
function analizarUrlHeuristica(url) {
  const indicadores = [];
  let puntuacion    = 0;

  let parsedUrl;
  try { parsedUrl = new URL(url); }
  catch { return { puntuacion: 100, nivel: "malicioso", indicadores: [{ nivel: "alto", titulo: "URL malformada", desc: "No se puede parsear como URL válida." }] }; }

  const hostname = parsedUrl.hostname.toLowerCase();
  const path     = parsedUrl.pathname.toLowerCase();
  const query    = parsedUrl.search.toLowerCase();
  const fullUrl  = url.toLowerCase();

  /* ── Protocolo ── */
  if (parsedUrl.protocol === "http:") {
    indicadores.push({ nivel: "medio", titulo: "Sin cifrado HTTPS", desc: "La URL usa HTTP — los datos viajan sin cifrar." });
    puntuacion += 20;
  }

  /* ── IP en lugar de dominio ── */
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(hostname)) {
    indicadores.push({ nivel: "alto", titulo: "IP directa en lugar de dominio", desc: "Los sitios legítimos usan nombres de dominio, no IPs directas." });
    puntuacion += 35;
  }

  /* ── Subdominio excesivo ── */
  const partesDominio = hostname.split(".");
  if (partesDominio.length > 4) {
    indicadores.push({ nivel: "medio", titulo: "Demasiados subdominios", desc: `"${hostname}" tiene ${partesDominio.length} niveles — técnica común en phishing.` });
    puntuacion += 20;
  }

  /* ── Marcas conocidas en subdominios (typosquatting) ── */
  const marcas = ["paypal", "google", "facebook", "amazon", "microsoft", "apple", "netflix", "bancopopular", "banreservas", "bhdleon"];
  const dominioRaiz = partesDominio.slice(-2).join(".");
  marcas.forEach(marca => {
    if (hostname.includes(marca) && !dominioRaiz.startsWith(marca)) {
      indicadores.push({ nivel: "alto", titulo: `Imitación de marca: "${marca}"`, desc: `El dominio contiene "${marca}" pero no es el dominio oficial. Posible phishing.` });
      puntuacion += 40;
    }
  });

  /* ── TLD sospechoso ── */
  const tldsSospechosos = [".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".click", ".loan", ".work", ".online", ".site"];
  tldsSospechosos.forEach(tld => {
    if (hostname.endsWith(tld)) {
      indicadores.push({ nivel: "medio", titulo: `TLD sospechoso: "${tld}"`, desc: "Este dominio de nivel superior es frecuentemente usado en dominios maliciosos gratuitos." });
      puntuacion += 20;
    }
  });

  /* ── Palabras clave de phishing en la URL ── */
  const palabrasPhishing = ["login", "signin", "verify", "update", "secure", "account", "banking", "confirm", "password", "credential", "suspend", "urgent", "wallet", "recover"];
  const encontradas = palabrasPhishing.filter(p => fullUrl.includes(p));
  if (encontradas.length >= 2) {
    indicadores.push({ nivel: "alto", titulo: "Múltiples palabras clave de phishing", desc: `La URL contiene: ${encontradas.join(", ")}. Patrón muy común en páginas de phishing.` });
    puntuacion += 30;
  } else if (encontradas.length === 1) {
    indicadores.push({ nivel: "medio", titulo: `Palabra clave sospechosa: "${encontradas[0]}"`, desc: "Presente en muchas URLs de phishing. Por sí solo no es determinante." });
    puntuacion += 10;
  }

  /* ── Extensión de archivo peligrosa en URL ── */
  const extPeligrosas = [".exe", ".bat", ".cmd", ".vbs", ".ps1", ".msi", ".jar", ".apk", ".scr", ".hta"];
  extPeligrosas.forEach(ext => {
    if (path.endsWith(ext) || query.includes(ext)) {
      indicadores.push({ nivel: "alto", titulo: `Descarga de archivo peligroso: "${ext}"`, desc: "La URL apunta directamente a un ejecutable o script." });
      puntuacion += 35;
    }
  });

  /* ── URL muy larga ── */
  if (url.length > 150) {
    indicadores.push({ nivel: "medio", titulo: "URL excesivamente larga", desc: `${url.length} caracteres. URLs largas pueden ocultar redirecciones maliciosas.` });
    puntuacion += 10;
  }

  /* ── Caracteres de codificación sospechosa ── */
  if ((url.match(/%[0-9a-f]{2}/gi) || []).length > 5) {
    indicadores.push({ nivel: "medio", titulo: "Múltiples caracteres URL-encoded", desc: "Codificación excesiva puede intentar evadir filtros de seguridad." });
    puntuacion += 15;
  }

  /* ── Puertos no estándar ── */
  if (parsedUrl.port && !["80", "443", "8080", "8443"].includes(parsedUrl.port)) {
    indicadores.push({ nivel: "medio", titulo: `Puerto no estándar: ${parsedUrl.port}`, desc: "Los servicios web legítimos raramente usan puertos no estándar." });
    puntuacion += 15;
  }

  /* ── Resultado limpio ── */
  if (indicadores.length === 0) {
    indicadores.push({ nivel: "bajo", titulo: "Sin indicadores sospechosos", desc: "El análisis heurístico no encontró patrones maliciosos en la URL." });
  }

  const nivel = puntuacion === 0 ? "limpio"
    : puntuacion < 30            ? "bajo"
    : puntuacion < 60            ? "medio"
    : "alto";

  return { puntuacion: Math.min(puntuacion, 100), nivel, indicadores };
}

/* =============================================
   ANÁLISIS DE ARCHIVO
   ============================================= */

async function analizarArchivo(file) {
  const inicio = new Date();

  /* Calcular SHA-256 del archivo */
  const hash = await sha256Archivo(file);

  const heuristica = analizarArchivoHeuristica(file);
  let vt = null;

  if (vtApiKey) {
    /* Primero buscar el hash en VT (no consume cuota de subida) */
    vt = await consultarVtHash(hash);

    /* Si no está en VT y el archivo es <= 32MB, subirlo */
    if (vt && vt.noEncontrado && file.size <= 32 * 1024 * 1024) {
      vt = await subirArchivoVt(file);
    }
  }

  const veredicto = calcularVeredicto(heuristica, vt);

  return {
    tipo:       "Archivo",
    objetivo:   file.name,
    tamano:     formatearTamano(file.size),
    hash,
    heuristica,
    vt,
    veredicto,
    timestamp:  inicio.toISOString(),
    analista:   `${nombre} ${apellido || ""}`.trim()
  };
}

/* ===== HEURÍSTICAS DE ARCHIVO ===== */
function analizarArchivoHeuristica(file) {
  const indicadores = [];
  let puntuacion    = 0;
  const nombre_lower = file.name.toLowerCase();
  const ext          = nombre_lower.split(".").pop();

  /* ── Extensiones peligrosas ── */
  const extCriticas = ["exe", "bat", "cmd", "vbs", "ps1", "msi", "jar", "scr", "hta", "pif", "com", "reg"];
  const extAltas    = ["dll", "sys", "drv", "lnk", "url", "vbe", "jse", "wsf"];
  const extMedias   = ["zip", "rar", "7z", "iso", "img", "doc", "xls", "ppt"];

  if (extCriticas.includes(ext)) {
    indicadores.push({ nivel: "alto", titulo: `Extensión ejecutable de alto riesgo: .${ext}`, desc: "Este tipo de archivo puede ejecutar código en el sistema directamente." });
    puntuacion += 40;
  } else if (extAltas.includes(ext)) {
    indicadores.push({ nivel: "alto", titulo: `Extensión potencialmente peligrosa: .${ext}`, desc: "Este tipo de archivo puede ser usado para ejecutar código malicioso." });
    puntuacion += 30;
  } else if (extMedias.includes(ext)) {
    indicadores.push({ nivel: "medio", titulo: `Archivo comprimido u Office: .${ext}`, desc: "Puede contener macros o ejecutables ocultos. Verificar con VirusTotal." });
    puntuacion += 15;
  }

  /* ── Doble extensión (técnica de engaño) ── */
  const partes = nombre_lower.split(".");
  if (partes.length > 2) {
    const penultima = partes[partes.length - 2];
    if (["pdf", "jpg", "png", "doc", "txt", "mp3", "mp4"].includes(penultima)) {
      indicadores.push({ nivel: "alto", titulo: "Doble extensión detectada", desc: `"${file.name}" — técnica clásica para engañar: el archivo parece .${penultima} pero es .${ext}.` });
      puntuacion += 45;
    }
  }

  /* ── Nombre sospechoso ── */
  const nombresSospechosos = ["invoice", "factura", "urgent", "payment", "click_here", "update", "setup", "install", "crack", "keygen", "patch", "activator"];
  nombresSospechosos.forEach(n => {
    if (nombre_lower.includes(n)) {
      indicadores.push({ nivel: "medio", titulo: `Nombre sospechoso: "${n}"`, desc: "Nombres de archivo comúnmente usados en malware y phishing." });
      puntuacion += 20;
    }
  });

  /* ── Tamaño inusual ── */
  if (file.size < 1024 && extCriticas.includes(ext)) {
    indicadores.push({ nivel: "medio", titulo: "Ejecutable demasiado pequeño", desc: "Menos de 1 KB — puede ser un dropper o stager minimalista." });
    puntuacion += 20;
  }

  if (indicadores.length === 0) {
    indicadores.push({ nivel: "bajo", titulo: "Sin indicadores sospechosos en metadatos", desc: "El nombre, extensión y tamaño del archivo no presentan patrones maliciosos conocidos." });
  }

  const nivel = puntuacion === 0 ? "limpio"
    : puntuacion < 30            ? "bajo"
    : puntuacion < 60            ? "medio"
    : "alto";

  return { puntuacion: Math.min(puntuacion, 100), nivel, indicadores };
}

/* =============================================
   VIRUSTOTAL API
   ============================================= */

async function consultarVtUrl(url) {
  try {
    /* Paso 1: enviar URL para análisis */
    const form = new FormData();
    form.append("url", url);

    const res1 = await fetch("https://www.virustotal.com/api/v3/urls", {
      method:  "POST",
      headers: { "x-apikey": vtApiKey },
      body:    form
    });

    if (res1.status === 429) return { error: "Límite de API alcanzado (4/min). Espera un momento." };
    if (!res1.ok) return { error: `Error VirusTotal: ${res1.status}` };

    const data1  = await res1.json();
    const urlId  = data1.data?.id;
    if (!urlId) return { error: "No se obtuvo ID de análisis." };

    /* Paso 2: obtener resultado (polling hasta que esté listo) */
    return await esperarResultadoVt(`https://www.virustotal.com/api/v3/analyses/${urlId}`);

  } catch (err) {
    return { error: `Error de red: ${err.message}` };
  }
}

async function consultarVtHash(hash) {
  try {
    const res = await fetch(`https://www.virustotal.com/api/v3/files/${hash}`, {
      headers: { "x-apikey": vtApiKey }
    });
    if (res.status === 404) return { noEncontrado: true };
    if (res.status === 429) return { error: "Límite de API alcanzado." };
    if (!res.ok) return { error: `Error VT: ${res.status}` };

    const data = await res.json();
    return parsearResultadoVt(data.data?.attributes);
  } catch (err) {
    return { error: err.message };
  }
}

async function subirArchivoVt(file) {
  try {
    const form = new FormData();
    form.append("file", file, file.name);

    const res = await fetch("https://www.virustotal.com/api/v3/files", {
      method:  "POST",
      headers: { "x-apikey": vtApiKey },
      body:    form
    });

    if (res.status === 429) return { error: "Límite de API alcanzado." };
    if (!res.ok) return { error: `Error al subir: ${res.status}` };

    const data   = await res.json();
    const anlId  = data.data?.id;
    if (!anlId) return { error: "Sin ID de análisis." };

    return await esperarResultadoVt(`https://www.virustotal.com/api/v3/analyses/${anlId}`);
  } catch (err) {
    return { error: err.message };
  }
}

async function esperarResultadoVt(url, intentos = 0) {
  if (intentos > 8) return { error: "Tiempo de espera agotado en VirusTotal." };

  await new Promise(r => setTimeout(r, 3000 + intentos * 1000));

  try {
    const res = await fetch(url, { headers: { "x-apikey": vtApiKey } });
    if (!res.ok) return { error: `Error VT: ${res.status}` };

    const data   = await res.json();
    const status = data.data?.attributes?.status;

    if (status === "completed" || !status) {
      return parsearResultadoVt(data.data?.attributes);
    }
    return await esperarResultadoVt(url, intentos + 1);
  } catch (err) {
    return { error: err.message };
  }
}

function parsearResultadoVt(attrs) {
  if (!attrs) return { error: "Sin atributos en respuesta VT." };

  const stats   = attrs.stats || attrs.last_analysis_stats || {};
  const results = attrs.results || attrs.last_analysis_results || {};

  const maliciosos  = (stats.malicious   || 0) + (stats.suspicious || 0);
  const total       = Object.values(stats).reduce((a, b) => a + b, 0);
  const categoria   = attrs.categories ? Object.values(attrs.categories)[0] : "—";

  const motores = Object.entries(results).map(([motor, info]) => ({
    motor,
    detectado:  info.category === "malicious" || info.category === "suspicious",
    resultado:  info.result || info.category || "clean"
  }));

  return { maliciosos, total, categoria, motores, stats };
}

/* =============================================
   CALCULAR VEREDICTO FINAL
   ============================================= */

function calcularVeredicto(heuristica, vt) {
  /* Sin VT — solo heurística */
  if (!vt || vt.error || vt.noEncontrado) {
    if (heuristica.puntuacion >= 60) return "malicioso";
    if (heuristica.puntuacion >= 25) return "sospechoso";
    return "limpio";
  }

  /* Con VT */
  const pctDeteccion = vt.total > 0 ? (vt.maliciosos / vt.total) : 0;

  if (pctDeteccion >= 0.1 || heuristica.puntuacion >= 60)  return "malicioso";
  if (pctDeteccion > 0    || heuristica.puntuacion >= 25)  return "sospechoso";
  return "limpio";
}

/* =============================================
   RENDERIZAR RESULTADOS
   ============================================= */

function mostrarResultadoParcial(tipo, objetivo) {
  document.getElementById("resultadoSection").hidden = false;
  document.getElementById("detalleHeuristica").hidden = true;
  document.getElementById("detalleVT").hidden         = true;

  const target = typeof objetivo === "string" ? objetivo : objetivo.name;
  document.getElementById("veredictoIcono").textContent  = "🔍";
  document.getElementById("veredictoLabel").textContent  = "Analizando...";
  document.getElementById("veredictoTarget").textContent = target;
  document.getElementById("verdictoBadge").textContent   = "—";
  document.getElementById("verdictoBadge").className     = "la-veredicto-badge";
  document.getElementById("veredictoCard").className     = "la-veredicto";
  document.getElementById("mDeteccionesNum").textContent = "—";
  document.getElementById("mCategoriaNum").textContent   = "—";
  document.getElementById("mHashNum").textContent        = "—";
  document.getElementById("mHeuristicaNum").textContent  = "—";

  if (typeof gsap !== "undefined") {
    gsap.from("#resultadoSection", { y: 20, opacity: 0, duration: 0.6, ease: "power3.out" });
  }
  document.getElementById("resultadoSection").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderizarResultado(r) {
  const veredictoInfo = {
    limpio:     { icono: "✅", label: "Sin amenazas detectadas", badge: "Limpio",      clase: "limpio"     },
    sospechoso: { icono: "⚠️", label: "Comportamiento sospechoso", badge: "Sospechoso", clase: "sospechoso" },
    malicioso:  { icono: "🚨", label: "¡Amenaza detectada!",       badge: "Malicioso",  clase: "malicioso"  }
  };
  const vi = veredictoInfo[r.veredicto] || veredictoInfo.limpio;

  /* Veredicto */
  document.getElementById("veredictoIcono").textContent  = vi.icono;
  document.getElementById("veredictoLabel").textContent  = vi.label;
  document.getElementById("veredictoTarget").textContent = r.objetivo;
  document.getElementById("verdictoBadge").textContent   = vi.badge;
  document.getElementById("verdictoBadge").className     = `la-veredicto-badge badge-${vi.clase}`;
  document.getElementById("veredictoCard").className     = `la-veredicto ${vi.clase}`;

  /* Métricas */
  const detNum = r.vt && !r.vt.error && !r.vt.noEncontrado
    ? `${r.vt.maliciosos}/${r.vt.total}`
    : vtApiKey ? "N/D" : "Sin key";
  document.getElementById("mDeteccionesNum").textContent = detNum;
  document.getElementById("mDeteccionesSub").textContent = r.vt?.total ? `de ${r.vt.total} motores` : "motores AV";
  document.getElementById("mCategoriaNum").textContent   = r.vt?.categoria || "—";
  document.getElementById("mHashNum").textContent        = r.hash ? r.hash.substring(0, 16) + "..." : "—";
  document.getElementById("mHeuristicaNum").textContent  = `${r.heuristica.puntuacion}/100`;

  /* Detalle heurístico */
  const detalleH = document.getElementById("detalleHeuristica");
  const lista    = document.getElementById("indicadoresList");
  lista.innerHTML = r.heuristica.indicadores.map(ind => `
    <div class="la-indicador riesgo-${ind.nivel}">
      <span class="la-indicador-icono">
        ${ind.nivel === "alto" ? "🔴" : ind.nivel === "medio" ? "🟡" : ind.nivel === "bajo" ? "🟢" : "🔵"}
      </span>
      <div class="la-indicador-texto">
        <strong>${escHtml(ind.titulo)}</strong>
        <span>${escHtml(ind.desc)}</span>
      </div>
    </div>
  `).join("");
  detalleH.hidden = false;

  /* Detalle VirusTotal */
  const detalleVT = document.getElementById("detalleVT");
  if (r.vt && !r.vt.error && !r.vt.noEncontrado && r.vt.motores) {
    const motoresOrdenados = [...r.vt.motores].sort((a, b) => b.detectado - a.detectado);
    document.getElementById("vtMotoresList").innerHTML = motoresOrdenados.map(m => `
      <div class="la-vt-motor ${m.detectado ? "detectado" : "limpio"}">
        <span class="la-vt-motor-dot"></span>
        <span class="la-vt-motor-nombre">${escHtml(m.motor)}</span>
        <span class="la-vt-motor-resultado">${escHtml(m.resultado)}</span>
      </div>
    `).join("");
    detalleVT.hidden = false;
  } else if (r.vt?.error) {
    document.getElementById("vtMotoresList").innerHTML = `
      <div class="la-indicador riesgo-info">
        <span class="la-indicador-icono">ℹ️</span>
        <div class="la-indicador-texto">
          <strong>VirusTotal no disponible</strong>
          <span>${escHtml(r.vt.error)}</span>
        </div>
      </div>`;
    detalleVT.hidden = false;
  } else if (!vtApiKey) {
    document.getElementById("vtMotoresList").innerHTML = `
      <div class="la-indicador riesgo-info">
        <span class="la-indicador-icono">🔑</span>
        <div class="la-indicador-texto">
          <strong>API Key no configurada</strong>
          <span>Configura tu API Key de VirusTotal para obtener análisis completo contra 70+ motores antivirus.</span>
        </div>
      </div>`;
    detalleVT.hidden = false;
  }

  /* Registro forense */
  const forenseGrid = document.getElementById("forenseGrid");
  const campos = [
    { label: "Analista",   value: r.analista },
    { label: "Timestamp",  value: new Date(r.timestamp).toLocaleString("es-DO") },
    { label: "Tipo",       value: r.tipo },
    { label: "Objetivo",   value: r.objetivo },
    { label: "SHA-256",    value: r.hash || "—" },
    { label: "Veredicto",  value: vi.badge },
    { label: "Heurística", value: `${r.heuristica.puntuacion}/100 (${r.heuristica.nivel})` },
    { label: "VT Detecciones", value: r.vt?.maliciosos != null ? `${r.vt.maliciosos}/${r.vt.total}` : "N/D" },
    ...(r.tamano ? [{ label: "Tamaño", value: r.tamano }] : [])
  ];
  forenseGrid.innerHTML = campos.map(c => `
    <div class="la-forense-item">
      <span class="la-forense-item-label">${escHtml(c.label)}</span>
      <span class="la-forense-item-value">${escHtml(c.value)}</span>
    </div>
  `).join("");

  if (typeof gsap !== "undefined") {
    gsap.from(".la-indicador", { y: 10, opacity: 0, duration: 0.4, stagger: 0.06, ease: "power2.out" });
    gsap.from(".la-metrica-card", { y: 10, opacity: 0, duration: 0.5, stagger: 0.08, ease: "back.out(1.2)" });
  }
}

/* ===== EXPORTAR JSON ===== */
document.getElementById("btnExportar").addEventListener("click", () => {
  if (!ultimoResultado) return;
  const json = JSON.stringify(ultimoResultado, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `forensicshield_${ultimoResultado.tipo.toLowerCase()}_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
});

/* =============================================
   HISTORIAL
   ============================================= */

function agregarHistorial(r) {
  historial.unshift(r);
  renderizarHistorial();
}

function renderizarHistorial() {
  const empty = document.getElementById("historialEmpty");
  const lista = document.getElementById("historialLista");

  if (historial.length === 0) {
    empty.style.display = "block";
    lista.hidden = true;
    return;
  }

  empty.style.display = "none";
  lista.hidden = false;

  lista.innerHTML = historial.map((r, i) => `
    <div class="la-historial-item" onclick="restaurarResultado(${i})">
      <span class="la-historial-dot ${r.veredicto}"></span>
      <span class="la-historial-tipo">${escHtml(r.tipo)}</span>
      <span class="la-historial-target">${escHtml(r.objetivo)}</span>
      <span class="la-historial-veredicto ${r.veredicto}">
        ${r.veredicto === "limpio" ? "✅ Limpio" : r.veredicto === "sospechoso" ? "⚠️ Sospechoso" : "🚨 Malicioso"}
      </span>
      <span class="la-historial-fecha">${new Date(r.timestamp).toLocaleTimeString("es-DO")}</span>
    </div>
  `).join("");
}

function restaurarResultado(i) {
  ultimoResultado = historial[i];
  mostrarResultadoParcial(ultimoResultado.tipo.toLowerCase(), ultimoResultado.objetivo);
  renderizarResultado(ultimoResultado);
}

document.getElementById("btnLimpiarHistorial").addEventListener("click", () => {
  historial.length = 0;
  renderizarHistorial();
});

/* =============================================
   UTILIDADES
   ============================================= */

function mostrarAlert(id, msg, tipo) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.className   = `la-alert ${tipo}`;
  el.hidden      = false;
}
function ocultarAlert(id) {
  document.getElementById(id).hidden = true;
}

function escHtml(str) {
  if (!str) return "—";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

async function sha256Texto(texto) {
  const buf  = new TextEncoder().encode(texto);
  const hash = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, "0")).join("");
}

async function sha256Archivo(file) {
  const buf  = await file.arrayBuffer();
  const hash = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, "0")).join("");
}

/* ===== CERRAR SESIÓN ===== */
document.getElementById("btnLogout").addEventListener("click", async () => {
  try {
    await fetch(`${API_URL}/api/auth/logout`, {
      method: "POST",
      credentials: "include"
    });
  } catch (_) {}
  sessionStorage.clear();
  window.location.href = "login.html";
});