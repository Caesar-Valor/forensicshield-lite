/* =============================================
   ForensicShield Lite — script.js
   Dashboard principal
   Cesar Eduardo Valenzuela Mosquera · ITESPF 2026
   ============================================= */

const API_URL = "http://127.0.0.1:8000";

/* ===== VERIFICAR SESIÓN ===== */
// El token JWT viaja en HttpOnly cookie — no accesible desde JS
// Verificamos sesión por datos de UI en sessionStorage; la cookie autentica las APIs
const nombre   = sessionStorage.getItem("fs_nombre");
const apellido = sessionStorage.getItem("fs_apellido");
const rol      = sessionStorage.getItem("fs_rol");

if (!nombre) {
  window.location.href = "login.html";
}

/* ===== UTILIDAD — ESCAPE HTML ===== */
function escaparHTML(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g,  "&amp;")
    .replace(/</g,  "&lt;")
    .replace(/>/g,  "&gt;")
    .replace(/"/g,  "&quot;")
    .replace(/'/g,  "&#39;");
}

// Mostrar datos del usuario
if (nombre) {
  document.getElementById("userName").textContent  = `${nombre} ${apellido || ""}`.trim();
  document.getElementById("userRol").textContent   = rol || "usuario";
  const iniciales = `${nombre[0]}${apellido ? apellido[0] : ""}`.toUpperCase();
  document.getElementById("userAvatar").textContent = iniciales;
}

/* ===== TEMA CLARO/OSCURO ===== */
const root      = document.documentElement;
const toggleBtn = document.getElementById("themeToggle");

toggleBtn.addEventListener("click", () => {
  const isLight = root.getAttribute("data-theme") === "light";
  if (isLight) {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", "light");
  }
  if (typeof gsap !== "undefined") {
    gsap.fromTo("body", { opacity: 0.8 }, { opacity: 1, duration: 0.5 });
  }
});

/* ===== ANIMACIONES DE ENTRADA ===== */
window.addEventListener("load", () => {
  if (typeof gsap === "undefined") return;
  gsap.from(".sidebar",      { x: -30, opacity: 0, duration: 0.6, ease: "power3.out" });
  gsap.from(".hero-section", { y: 20,  opacity: 0, duration: 0.5, delay: 0.1, ease: "power3.out" });
  gsap.from(".metric-card",  { y: 16,  opacity: 0, duration: 0.4, stagger: 0.06, delay: 0.2, ease: "power2.out" });
  gsap.from(".dash-panel",   { y: 20,  opacity: 0, duration: 0.5, stagger: 0.08, delay: 0.3, ease: "power3.out" });
  gsap.from(".bento-card",   { y: 24,  opacity: 0, duration: 0.5, stagger: 0.07, delay: 0.35, ease: "power3.out" });
});

/* ===== NAVEGACIÓN ACTIVA AL HACER SCROLL ===== */
const sections = document.querySelectorAll("header[id], section[id]");
const navLinks  = document.querySelectorAll(".nav-link");

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      navLinks.forEach(link => {
        link.classList.remove("active");
        link.removeAttribute("aria-current");
      });
      const activeLink = document.querySelector(`.nav-link[href="#${entry.target.id}"]`);
      if (activeLink) {
        activeLink.classList.add("active");
        activeLink.setAttribute("aria-current", "page");
      }
    }
  });
}, { threshold: 0.4 });

sections.forEach(section => observer.observe(section));

/* ===== CARGAR MÉTRICAS Y HISTORIAL ===== */
async function cargarDashboard() {
  try {
    const res  = await fetch(`${API_URL}/api/scanner/historial`, {
      credentials: "include"
    });

    if (res.status === 401) {
      sessionStorage.clear();
      window.location.href = "login.html";
      return;
    }

    if (!res.ok) return;

    const data = await res.json();
    const escaneos = data.escaneos || [];

    actualizarMetricas(escaneos);
    renderizarHistorial(escaneos);

  } catch (err) {
    console.error("Error cargando dashboard:", err);
  }
}

/* ===== ACTUALIZAR MÉTRICAS ===== */
function actualizarMetricas(escaneos) {
  const total       = escaneos.length;
  const abiertos    = escaneos.reduce((sum, e) => sum + (e.puertos_abiertos || 0), 0);
  const completados = escaneos.filter(e => e.estado === "completado");

  // Contar críticos — escaneos con riesgo alto detectado
  // (aproximación basada en puertos_abiertos > 0)
  const criticos = completados.filter(e => (e.puertos_abiertos || 0) > 0).length;

  document.getElementById("mEscaneos").textContent = total;
  document.getElementById("mCriticos").textContent = criticos;
  document.getElementById("mAbiertos").textContent = abiertos;

  // Último escaneo
  if (escaneos.length > 0) {
    const ultimo = escaneos[0];
    const fecha  = ultimo.iniciado_en ? tiempoRelativo(ultimo.iniciado_en) : "—";
    document.getElementById("mUltimo").textContent = `${ultimo.target_ip} · ${fecha}`;
  } else {
    document.getElementById("mUltimo").textContent = "Ninguno aún";
  }
}

/* ===== RENDERIZAR HISTORIAL ===== */
function renderizarHistorial(escaneos) {
  const histEmpty = document.getElementById("histEmpty");
  const histTable = document.getElementById("histTable");
  const tbody     = document.getElementById("histTableBody");

  if (!escaneos || escaneos.length === 0) {
    histEmpty.hidden = false;
    histTable.hidden = true;
    return;
  }

  histEmpty.hidden = true;
  histTable.hidden = false;

  // Mostrar los últimos 8 escaneos
  const recientes = escaneos.slice(0, 8);

  tbody.innerHTML = recientes.map(e => {
    const estadoClass = `estado-${e.estado}`;
    const estadoLabel = {
      completado: "Completado",
      pendiente:  "Pendiente",
      en_progreso:"En progreso",
      fallido:    "Fallido"
    }[e.estado] || e.estado;

    // Determinar riesgo máximo basado en puertos abiertos
    let riesgoLabel = "Ninguno";
    let riesgoClass = "riesgo-ninguno-sm";
    if (e.puertos_abiertos > 0) {
      riesgoLabel = "Detectado";
      riesgoClass = "riesgo-alto-sm";
    }

    const fecha = e.iniciado_en ? tiempoRelativo(e.iniciado_en) : "—";

    return `
      <tr onclick="window.location.href='scanner.html'" title="Ir al scanner">
        <td><span class="dash-ip">${escaparHTML(e.target_ip)}</span></td>
        <td><span class="dash-estado ${estadoClass}">${escaparHTML(estadoLabel)}</span></td>
        <td style="font-variant-numeric:tabular-nums;font-weight:700">
          ${e.puertos_abiertos != null ? Number(e.puertos_abiertos) : "—"}
        </td>
        <td><span class="dash-riesgo ${riesgoClass}">${escaparHTML(riesgoLabel)}</span></td>
        <td><span class="dash-fecha">${escaparHTML(fecha)}</span></td>
      </tr>
    `;
  }).join("");
}

/* ===== TIEMPO RELATIVO ===== */
function tiempoRelativo(fechaStr) {
  try {
    const fecha   = new Date(fechaStr);
    const ahora   = new Date();
    const diffSeg = Math.floor((ahora - fecha) / 1000);

    if (diffSeg < 60)    return "Hace unos segundos";
    if (diffSeg < 3600)  return `Hace ${Math.floor(diffSeg / 60)} min`;
    if (diffSeg < 86400) return `Hace ${Math.floor(diffSeg / 3600)} h`;
    if (diffSeg < 604800)return `Hace ${Math.floor(diffSeg / 86400)} días`;
    return fecha.toLocaleDateString("es-DO", { day: "2-digit", month: "short" });
  } catch {
    return "—";
  }
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

/* ===== INICIAR ===== */
cargarDashboard();