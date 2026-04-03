/* =============================================
   ForensicShield Lite — reportes.js
   Módulo Report Generator
   Cesar Eduardo Valenzuela Mosquera · ITESPF 2026
   ============================================= */

const API_URL = "http://127.0.0.1:8000";

/* ===== VERIFICAR SESIÓN ===== */
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
  if (typeof window.uniforms !== "undefined")
    window.uniforms.u_theme.value = root.getAttribute("data-theme") === "light" ? 1.0 : 0.0;
});

/* ===== FONDO THREE.JS ===== */
window.addEventListener("load", () => {
  if (typeof THREE === "undefined" || typeof gsap === "undefined") return;
  const canvas   = document.getElementById("canvas-bg");
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  const scene  = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  window.uniforms = {
    u_time:  { value: 0 },
    u_res:   { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
    u_theme: { value: 0.0 }
  };
  const material = new THREE.ShaderMaterial({
    uniforms: window.uniforms,
    vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position,1.0); }`,
    fragmentShader: `
      uniform float u_time; uniform vec2 u_res; uniform float u_theme; varying vec2 vUv;
      float r(vec2 s){return fract(sin(dot(s.xy,vec2(12.9898,78.233)))*43758.5453123);}
      float n(vec2 s){vec2 i=floor(s),f=fract(s);float a=r(i),b=r(i+vec2(1,0)),c=r(i+vec2(0,1)),d=r(i+vec2(1,1));vec2 u=f*f*(3.-2.*f);return mix(a,b,u.x)+(c-a)*u.y*(1.-u.x)+(d-b)*u.x*u.y;}
      float fbm(vec2 s){float v=0.,a=.5;mat2 m=mat2(cos(.5),sin(.5),-sin(.5),cos(.5));for(int i=0;i<5;i++){v+=a*n(s);s=m*s*2.+vec2(100.);a*=.5;}return v;}
      void main(){vec2 st=gl_FragCoord.xy/u_res.xy;st.x*=u_res.x/u_res.y;
        vec2 q=vec2(fbm(st+.0*u_time),fbm(st+vec2(1)));
        vec2 rr=vec2(fbm(st+q+vec2(1.7,9.2)+.15*u_time),fbm(st+q+vec2(8.3,2.8)+.126*u_time));
        vec3 c1=mix(vec3(.02,.02,.06),vec3(.95,.95,.98),u_theme);
        vec3 c2=mix(vec3(.08,.04,.18),vec3(.90,.92,1.),u_theme);
        vec3 ca=mix(vec3(.43,.36,.99),vec3(.40,.60,1.),u_theme);
        vec3 color=mix(c1,c2,length(q)); color=mix(color,ca,length(rr)*.4);
        gl_FragColor=vec4(color,1.);}
    `
  });
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
  scene.add(plane);
  function resize() {
    const w = window.innerWidth, h = window.innerHeight;
    renderer.setSize(w, h); window.uniforms.u_res.value.set(w, h);
  }
  window.addEventListener("resize", resize); resize();
  (function animate(t) {
    requestAnimationFrame(animate);
    window.uniforms.u_time.value = t * 0.001;
    renderer.render(scene, camera);
  })(0);
  gsap.from(".sidebar",    { x: -50, opacity: 0, duration: 1.2, ease: "power4.out" });
  gsap.from(".rep-header", { y: 30,  opacity: 0, duration: 1,   delay: 0.2, ease: "power3.out" });
  gsap.from(".rep-metric-card", { y: 20, opacity: 0, duration: 0.6, stagger: 0.08, delay: 0.3, ease: "back.out(1.2)" });
  gsap.from(".rep-panel",  { y: 24,  opacity: 0, duration: 0.7, stagger: 0.1, delay: 0.4, ease: "power3.out" });
});

/* ===== UTILIDAD — ESCAPE HTML ===== */
function escHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/* ===== COLORES DE RIESGO ===== */
const RIESGO_COLOR = {
  critico: "#ef4444",
  alto:    "#f97316",
  medio:   "#eab308",
  bajo:    "#22c55e",
  ninguno: "#4b5563",
};

/* ===== REFERENCIAS DOM ===== */
const selectEscaneo  = document.getElementById("selectEscaneo");
const btnGenerar     = document.getElementById("btnGenerar");
const btnGenerarText = document.getElementById("btnGenerarText");
const btnRefresh     = document.getElementById("btnRefresh");
const genAlert       = document.getElementById("genAlert");
const histEmpty      = document.getElementById("histEmpty");
const histTableWrap  = document.getElementById("histTableWrap");
const histTableBody  = document.getElementById("histTableBody");
const repNotif       = document.getElementById("repNotif");

/* ===== CARGAR ESCANEOS COMPLETADOS ===== */
async function cargarEscaneos() {
  try {
    const res  = await fetch(`${API_URL}/api/scanner/historial`, { credentials: "include" });
    if (res.status === 401) { sessionStorage.clear(); window.location.href = "login.html"; return; }
    if (!res.ok) return;

    const data     = await res.json();
    const escaneos = (data.escaneos || []).filter(e => e.estado === "completado");

    selectEscaneo.innerHTML = escaneos.length
      ? `<option value="">— Selecciona un escaneo —</option>` +
        escaneos.map(e => {
          const fecha = e.iniciado_en ? new Date(e.iniciado_en).toLocaleDateString("es-DO", {
            day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit"
          }) : "";
          return `<option value="${e.id}">${escHtml(e.target_ip)} · ${e.puertos_abiertos ?? 0} abiertos · ${fecha}</option>`;
        }).join("")
      : `<option value="">— No hay escaneos completados aún —</option>`;

  } catch (err) {
    selectEscaneo.innerHTML = `<option value="">— Error cargando escaneos —</option>`;
    console.error("Error cargando escaneos:", err);
  }
}

selectEscaneo.addEventListener("change", () => {
  btnGenerar.disabled = !selectEscaneo.value;
  ocultarAlert();
});

/* ===== GENERAR REPORTE ===== */
btnGenerar.addEventListener("click", async () => {
  const escaneoId = selectEscaneo.value;
  if (!escaneoId) return;

  btnGenerar.disabled   = true;
  btnGenerarText.textContent = "Generando PDF...";
  ocultarAlert();

  try {
    const res  = await fetch(`${API_URL}/api/reportes/generar/${escaneoId}`, {
      method: "POST", credentials: "include"
    });
    const data = await res.json();

    if (!res.ok) {
      mostrarAlert(data.detail || "Error al generar el reporte.", "error");
      return;
    }

    mostrarAlert(`Reporte ${data.numero_reporte} generado correctamente. Descargando...`, "ok");
    mostrarNotif(`Reporte ${data.numero_reporte} listo.`);
    await descargarReporte(data.reporte_id, data.numero_reporte);
    await cargarReportes();

  } catch (err) {
    mostrarAlert("No se pudo conectar con el servidor.", "error");
    console.error(err);
  } finally {
    btnGenerar.disabled        = !selectEscaneo.value;
    btnGenerarText.textContent = "Generar PDF";
  }
});

/* ===== DESCARGAR REPORTE ===== */
async function descargarReporte(reporteId, numeroReporte) {
  try {
    const res = await fetch(`${API_URL}/api/reportes/descargar/${reporteId}`, { credentials: "include" });
    if (!res.ok) { mostrarAlert("No se pudo descargar el PDF.", "error"); return; }

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `${numeroReporte}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    mostrarAlert("Error al descargar el PDF.", "error");
    console.error(err);
  }
}

/* ===== CARGAR HISTORIAL DE REPORTES ===== */
async function cargarReportes() {
  try {
    const res  = await fetch(`${API_URL}/api/reportes/lista`, { credentials: "include" });
    if (!res.ok) return;
    const data = await res.json();

    actualizarMetricas(data.reportes || []);

    if (!data.reportes || data.reportes.length === 0) {
      histEmpty.hidden     = false;
      histTableWrap.hidden = true;
      return;
    }

    histEmpty.hidden     = true;
    histTableWrap.hidden = false;

    histTableBody.innerHTML = data.reportes.map(r => {
      const color = RIESGO_COLOR[r.riesgo_maximo] || RIESGO_COLOR.ninguno;
      return `
        <tr>
          <td><span class="rep-numero">${escHtml(r.numero_reporte)}</span></td>
          <td><span class="rep-ip">${escHtml(r.target_ip)}</span></td>
          <td>
            <span class="rep-badge" style="background:${color}">
              ${escHtml(r.riesgo_maximo)}
            </span>
          </td>
          <td style="text-align:center;font-weight:700;font-variant-numeric:tabular-nums">
            ${Number(r.hallazgos)}
          </td>
          <td class="rep-fecha">${escHtml(r.generado_en)}</td>
          <td>
            <button class="btn-dl-rep"
              onclick="descargarReporte(${r.reporte_id}, '${escHtml(r.numero_reporte)}')"
              title="Descargar PDF">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              Descargar
            </button>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.error("Error cargando reportes:", err);
  }
}

/* ===== MÉTRICAS ===== */
function actualizarMetricas(reportes) {
  document.getElementById("mTotal").textContent     = reportes.length;
  document.getElementById("mCriticos").textContent  = reportes.filter(r => r.riesgo_maximo === "critico").length;
  document.getElementById("mHallazgos").textContent = reportes.reduce((s, r) => s + (r.hallazgos || 0), 0);

  if (reportes.length > 0) {
    document.getElementById("mUltimo").textContent = reportes[0].generado_en || "—";
  } else {
    document.getElementById("mUltimo").textContent = "Ninguno";
  }
}

/* ===== UTILIDADES ===== */
function mostrarAlert(msg, tipo) {
  genAlert.textContent = msg;
  genAlert.className   = `rep-alert ${tipo}`;
  genAlert.hidden      = false;
}
function ocultarAlert() { genAlert.hidden = true; }

function mostrarNotif(msg) {
  repNotif.textContent = msg;
  repNotif.classList.add("visible");
  setTimeout(() => repNotif.classList.remove("visible"), 4000);
}

/* ===== EVENTOS ===== */
btnRefresh.addEventListener("click", () => {
  cargarReportes();
  cargarEscaneos();
});

/* ===== INICIAR ===== */
cargarEscaneos();
cargarReportes();
