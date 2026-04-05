/* =============================================
   ForensicShield Lite — scanner.js
   Cesar Eduardo Valenzuela Mosquera · ITESPF 2026

    Este archivo contiene la lógica principal del escáner de puertos, así como la gestión de la red local y el control de acceso al firewall. Incluye:  
    - Verificación de sesión y manejo de tokens
    - Animación de fondo con Three.js
    - Interacción con el backend para iniciar escaneos y obtener resultados
    - Renderizado dinámico de resultados y recomendaciones
    
============================================= */

const API_URL = "http://127.0.0.1:8000";

/* ===== VERIFICAR SESION ===== */
// El token JWT viaja en HttpOnly cookie — no accesible desde JS
const nombre   = sessionStorage.getItem("fs_nombre");
const apellido = sessionStorage.getItem("fs_apellido");
const rol      = sessionStorage.getItem("fs_rol");

if (!nombre) {
  window.location.href = "login.html";
}

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
  if (typeof window.uniforms !== "undefined") {
    window.uniforms.u_theme.value = root.getAttribute("data-theme") === "light" ? 1.0 : 0.0;
  }
});

/* ===== FONDO ANIMADO THREE.JS ===== */
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
    vertexShader: `
      varying vec2 vUv;
      void main() { vUv = uv; gl_Position = vec4(position, 1.0); }
    `,
    fragmentShader: `
      uniform float u_time; uniform vec2 u_res; uniform float u_theme;
      varying vec2 vUv;
      float random(in vec2 _st) { return fract(sin(dot(_st.xy,vec2(12.9898,78.233)))*43758.5453123); }
      float noise(in vec2 _st) {
        vec2 i=floor(_st); vec2 f=fract(_st);
        float a=random(i),b=random(i+vec2(1.,0.)),c=random(i+vec2(0.,1.)),d=random(i+vec2(1.,1.));
        vec2 u=f*f*(3.-2.*f);
        return mix(a,b,u.x)+(c-a)*u.y*(1.-u.x)+(d-b)*u.x*u.y;
      }
      float fbm(in vec2 _st) {
        float v=0.,a=0.5; vec2 shift=vec2(100.);
        mat2 rot=mat2(cos(0.5),sin(0.5),-sin(0.5),cos(0.5));
        for(int i=0;i<5;++i){v+=a*noise(_st);_st=rot*_st*2.+shift;a*=0.5;}
        return v;
      }
      void main() {
        vec2 st=gl_FragCoord.xy/u_res.xy; st.x*=u_res.x/u_res.y;
        vec2 q=vec2(fbm(st+0.*u_time),fbm(st+vec2(1.)));
        vec2 r=vec2(fbm(st+q+vec2(1.7,9.2)+.15*u_time),fbm(st+q+vec2(8.3,2.8)+.126*u_time));
        vec3 c1=mix(vec3(.02,.02,.06),vec3(.95,.95,.98),u_theme);
        vec3 c2=mix(vec3(.08,.04,.18),vec3(.90,.92,1.0),u_theme);
        vec3 ca=mix(vec3(.43,.36,.99),vec3(.40,.60,1.0),u_theme);
        vec3 color=mix(c1,c2,length(q));
        color=mix(color,ca,length(r)*.4);
        gl_FragColor=vec4(color,1.);
      }
    `
  });

  const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
  scene.add(plane);

  function resize() {
    const w = window.innerWidth, h = window.innerHeight;
    renderer.setSize(w, h);
    window.uniforms.u_res.value.set(w, h);
  }
  window.addEventListener("resize", resize);
  resize();

  (function animate(t) {
    requestAnimationFrame(animate);
    window.uniforms.u_time.value = t * 0.001;
    renderer.render(scene, camera);
  })(0);

  gsap.from(".sidebar",        { x: -50, opacity: 0, duration: 1.2, ease: "power4.out" });
  gsap.from(".scanner-header", { y: 30,  opacity: 0, duration: 1,   delay: 0.2, ease: "power3.out" });
  gsap.from(".control-panel",  { y: 30,  opacity: 0, duration: 0.8, delay: 0.3, ease: "power3.out" });
  gsap.from(".counter-card",   { y: 20,  opacity: 0, duration: 0.6, stagger: 0.1, delay: 0.4, ease: "back.out(1.2)" });
});

/* ===== SELECTOR DE MODO ===== */
let modoActual = "rapido";

document.querySelectorAll(".mode-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".mode-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    modoActual = tab.dataset.mode;
  });
});

/* ===== REFERENCIAS AL DOM ===== */
const btnScan       = document.getElementById("btnScan");
const btnText       = document.getElementById("btnText");
const btnIcon       = document.getElementById("btnIcon");
const targetIpInput = document.getElementById("targetIp");
const scanAlert     = document.getElementById("scanAlert");
const scanAlertMsg  = document.getElementById("scanAlertMsg");

const cEstado   = document.getElementById("cEstado");
const cTarget   = document.getElementById("cTarget");
const cOpen     = document.getElementById("cOpen");
const cClosed   = document.getElementById("cClosed");
const cDuracion = document.getElementById("cDuracion");
const cModo     = document.getElementById("cModo");

const progressSection = document.getElementById("progressSection");
const progressLabel   = document.getElementById("progressLabel");
const progressStatus  = document.getElementById("progressStatus");
const progressFill    = document.getElementById("progressFill");

const resultsSection   = document.getElementById("resultsSection");
const resultsTableBody = document.getElementById("resultsTableBody");
const resultsMeta      = document.getElementById("resultsMeta");

/* ===== ESTADO GLOBAL ===== */
let escaneoActual   = null;
let pollingTimer    = null;
let timerInterval   = null;
let segundosTransc  = 0;
let todosLosPuertos = [];
let progresoAnim    = null;

/* ===== BOTON ESCANEAR ===== */
btnScan.addEventListener("click", async () => {
  const ip = targetIpInput.value.trim();

  if (!ip) {
    mostrarAlerta("Ingresa una direccion IP antes de escanear.");
    return;
  }

  const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$|^[a-zA-Z0-9.-]+$/;
  if (!ipRegex.test(ip)) {
    mostrarAlerta("Formato de IP invalido. Ejemplo: 192.168.1.1");
    return;
  }

  ocultarAlerta();
  iniciarUI(ip);

  try {
    const response = await fetch(`${API_URL}/api/scanner/iniciar`, {
      method:      "POST",
      headers:     { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        target_ip:     ip,
        target_nombre: ip,
        modo:          modoActual
      })
    });

    if (response.status === 401) {
      sessionStorage.clear();  // limpiar datos de UI
      window.location.href = "login.html";
      return;
    }

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Error al iniciar el escaneo.");
    }

    escaneoActual = data.escaneo_id;
    iniciarPolling(data.escaneo_id);

  } catch (err) {
    finalizarUI();
    mostrarAlerta(err.message || "No se pudo conectar con el backend.");
  }
});

/* ===== POLLING ===== */
function iniciarPolling(escaneoId) {
  if (pollingTimer) clearInterval(pollingTimer);

  pollingTimer = setInterval(async () => {
    try {
      const response = await fetch(
        `${API_URL}/api/scanner/resultado/${escaneoId}`,
        { credentials: "include" }
      );

      if (!response.ok) return;

      const data = await response.json();

      if (data.estado === "completado") {
        clearInterval(pollingTimer);
        clearInterval(timerInterval);
        mostrarResultados(data);
        finalizarUI();

      } else if (data.estado === "fallido") {
        clearInterval(pollingTimer);
        clearInterval(timerInterval);
        finalizarUI();
        mostrarAlerta("El escaneo fallo. " + (data.notas || "Verifica la IP ingresada."));
        cEstado.textContent = "Fallido";
      }

    } catch (err) {
      console.error("Error en polling:", err);
    }
  }, 3000);
}

/* ===== UI ===== */
function iniciarUI(ip) {
  btnScan.disabled    = true;
  btnText.textContent = "Escaneando...";
  btnIcon.innerHTML   = `<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>`;
  btnIcon.classList.add("spin");

  cEstado.textContent = "En progreso";
  cTarget.textContent = ip;
  cOpen.textContent   = "—";
  cClosed.textContent = "—";
  cModo.textContent   = `Modo: ${modoActual}`;

  segundosTransc        = 0;
  cDuracion.textContent = "0s";
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    segundosTransc++;
    cDuracion.textContent = `${segundosTransc}s`;
  }, 1000);

  progressSection.hidden     = false;
  progressLabel.textContent  = `Escaneando ${ip} en modo ${modoActual}...`;
  progressStatus.textContent = "En progreso";
  animarProgreso();

  resultsSection.hidden = true;
}

function finalizarUI() {
  btnScan.disabled    = false;
  btnText.textContent = "Escanear";
  btnIcon.innerHTML   = `<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>`;
  btnIcon.classList.remove("spin");
  progressSection.hidden   = true;
  progressFill.style.width = "0%";
  if (progresoAnim) clearInterval(progresoAnim);
}

function animarProgreso() {
  if (progresoAnim) clearInterval(progresoAnim);
  let ancho    = 0;
  let subiendo = true;

  progresoAnim = setInterval(() => {
    if (progressSection.hidden) { clearInterval(progresoAnim); return; }
    if (subiendo) {
      ancho += 1.2;
      if (ancho >= 85) subiendo = false;
    } else {
      ancho -= 0.4;
      if (ancho <= 20) subiendo = true;
    }
    progressFill.style.width = ancho + "%";
  }, 80);
}

/* ===== MOSTRAR RESULTADOS ===== */
function mostrarResultados(data) {
  todosLosPuertos = data.puertos || [];

  cEstado.textContent   = "Completado";
  cOpen.textContent     = data.puertos_abiertos ?? 0;
  cClosed.textContent   = data.puertos_cerrados ?? 0;
  cDuracion.textContent = `${data.duracion_seg ?? 0}s`;

  resultsMeta.textContent = `${todosLosPuertos.length} puertos · ${data.target_ip} · ${data.duracion_seg}s`;

  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
  document.querySelector('[data-filter="todos"]').classList.add("active");

  renderizarTabla(todosLosPuertos);

  resultsSection.hidden = false;
  if (typeof gsap !== "undefined") {
    gsap.from(".results-section", { y: 20, opacity: 0, duration: 0.6, ease: "power3.out" });
  }

  cargarRecomendaciones(escaneoActual);
}

/* ===== RENDERIZAR TABLA DE PUERTOS ===== */
function renderizarTabla(puertos) {
  if (!puertos || puertos.length === 0) {
    resultsTableBody.innerHTML = `
      <tr>
        <td colspan="5">
          <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <p>No se encontraron puertos con ese filtro.</p>
          </div>
        </td>
      </tr>`;
    return;
  }

  resultsTableBody.innerHTML = puertos.map(p => `
    <tr>
      <td>
        <span class="puerto-num">${Number(p.puerto)}</span>
        <span class="protocolo-badge">${escHtml(p.protocolo || "TCP")}</span>
      </td>
      <td>
        <span class="badge-estado badge-${escHtml(p.estado)}">
          ${p.estado === "open" ? "Abierto" : p.estado === "closed" ? "Cerrado" : "Filtrado"}
        </span>
      </td>
      <td><span class="servicio-name">${escHtml(p.servicio || "—")}</span></td>
      <td>
        ${p.version
          ? `<span class="version-text">${escHtml(p.version)}</span>`
          : `<span style="color:var(--text-muted);font-size:13px">—</span>`}
      </td>
      <td>
        <span class="badge-riesgo riesgo-${escHtml(p.riesgo || "ninguno")}">
          ${capitalizar(escHtml(p.riesgo || "ninguno"))}
        </span>
      </td>
    </tr>
  `).join("");
}

/* ===== FILTROS ===== */
document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    const filtro = btn.dataset.filter;
    let filtrados = todosLosPuertos;

    if (filtro === "open") {
      filtrados = todosLosPuertos.filter(p => p.estado === "open");
    } else if (filtro !== "todos") {
      filtrados = todosLosPuertos.filter(p => p.riesgo === filtro);
    }

    renderizarTabla(filtrados);
  });
});

/* ===== UTILIDADES SCANNER ===== */
function mostrarAlerta(msg) {
  scanAlertMsg.textContent = msg;
  scanAlert.hidden         = false;
}

function ocultarAlerta() {
  scanAlert.hidden = true;
}

function capitalizar(str) {
  if (!str) return "—";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

targetIpInput.addEventListener("input", ocultarAlerta);

/* =============================================
   RED LOCAL
   ============================================= */

const btnDiscover     = document.getElementById("btnDiscover");
const btnDiscoverText = document.getElementById("btnDiscoverText");
const netAlert        = document.getElementById("netAlert");
const netAlertMsg     = document.getElementById("netAlertMsg");
const netEmpty        = document.getElementById("netEmpty");
const netTable        = document.getElementById("netTable");
const netTableBody    = document.getElementById("netTableBody");

const modalNombre      = document.getElementById("modalNombre");
const modalIpLabel     = document.getElementById("modalIpLabel");
const modalNombreInput = document.getElementById("modalNombreInput");
const modalNotasInput  = document.getElementById("modalNotasInput");
const modalCancelar    = document.getElementById("modalCancelar");
const modalGuardar     = document.getElementById("modalGuardar");

let modalIpActual  = null;
let modalMacActual = null;

/* ===== DESCUBRIR RED ===== */
btnDiscover.addEventListener("click", async () => {
  btnDiscover.disabled = true;
  btnDiscover.classList.add("loading");
  btnDiscoverText.textContent = "Escaneando...";
  ocultarNetAlert();

  try {
    const res = await fetch(`${API_URL}/api/network/hosts`, {
      credentials: "include"
    });

    if (res.status === 401) {
      sessionStorage.clear();  // limpiar datos de UI
      window.location.href = "login.html";
      return;
    }

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al escanear la red.");

    renderizarTablaRed(data.hosts, data.subred, data.ip_servidor);

  } catch (err) {
    mostrarNetAlert(err.message || "No se pudo conectar al backend.");
  } finally {
    btnDiscover.disabled = false;
    btnDiscover.classList.remove("loading");
    btnDiscoverText.textContent = "Descubrir Red";
  }
});

/* ===== RENDERIZAR TABLA DE RED ===== */
function renderizarTablaRed(hosts, subred, ipServidor) {
  if (!hosts || hosts.length === 0) {
    netEmpty.hidden = false;
    netTable.hidden = true;
    netEmpty.querySelector("p").innerHTML =
      "No se encontraron dispositivos en la subred <strong>" + subred + "</strong>.";
    return;
  }

  netEmpty.hidden = true;
  netTable.hidden = false;

  netTableBody.innerHTML = hosts.map(h => {
    const esServidor = h.es_servidor;

    let nombreHTML;
    if (h.nombre_personalizado) {
      nombreHTML = `<span class="net-nombre-custom">${escHtml(h.nombre_personalizado)}</span>`;
    } else if (h.nombre) {
      nombreHTML = `<span class="net-nombre-dns">${escHtml(h.nombre)}</span>`;
    } else {
      nombreHTML = `<span class="net-nombre-vacio">Sin nombre</span>`;
    }

    let macHTML = '<span class="net-nombre-vacio">—</span>';
    if (h.mac) {
      macHTML = `<div class="net-mac">${escHtml(h.mac)}</div>`;
      if (h.fabricante) {
        macHTML += `<div class="net-vendor">${escHtml(h.fabricante)}</div>`;
      }
    }

    /* BUG #2 CORREGIDO: se eliminó mac del botón Bloquear.
       El backend /api/network/bloquear solo acepta el parámetro ip. */
    const btnBloquear = (!esServidor)
      ? `<button class="btn-net-bloquear"
           onclick="bloquearDispositivo('${escHtml(h.ip)}')"
           title="Bloquear acceso a la red">
           Bloquear
         </button>`
      : "";

    return `
      <tr class="${esServidor ? "es-servidor" : ""}">
        <td><div class="net-dot-wrap"><span class="net-dot" title="En linea"></span></div></td>
        <td>
          <span class="net-ip">${escHtml(h.ip)}</span>
          ${esServidor ? '<span class="badge-servidor">Este servidor</span>' : ""}
        </td>
        <td>${nombreHTML}</td>
        <td>${macHTML}</td>
        <td>
          <div class="net-actions">
            <button class="btn-net-rapido"
              onclick="seleccionarYEscanear('${escHtml(h.ip)}','rapido')">
              Rapido
            </button>
            <button class="btn-net-completo"
              onclick="seleccionarYEscanear('${escHtml(h.ip)}','completo')">
              Completo
            </button>
            <button class="btn-net-nombre"
              onclick="abrirModal('${escHtml(h.ip)}','${escHtml(h.mac || '')}','${escHtml(h.nombre_personalizado || '')}')">
              Nombrar
            </button>
            ${btnBloquear}
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

/* ===== SELECCIONAR IP Y ESCANEAR ===== */
function seleccionarYEscanear(ip, modo) {
  document.getElementById("targetIp").value = ip;
  document.querySelectorAll(".mode-tab").forEach(t => t.classList.remove("active"));
  const tabModo = document.querySelector(`.mode-tab[data-mode="${modo}"]`);
  if (tabModo) { tabModo.classList.add("active"); modoActual = modo; }
  document.querySelector(".control-panel").scrollIntoView({ behavior: "smooth", block: "center" });
  setTimeout(() => { document.getElementById("btnScan").click(); }, 600);
}

/* ===== MODAL NOMBRE ===== */
function abrirModal(ip, mac, nombreActual) {
  modalIpActual            = ip;
  modalMacActual           = mac || null;
  modalIpLabel.textContent = `IP: ${ip}`;
  modalNombreInput.value   = nombreActual || "";
  modalNotasInput.value    = "";
  modalNombre.hidden       = false;
  modalNombreInput.focus();
}

modalCancelar.addEventListener("click", () => {
  modalNombre.hidden = true;
  modalIpActual      = null;
  modalMacActual     = null;
});

modalNombre.addEventListener("click", (e) => {
  if (e.target === modalNombre) modalNombre.hidden = true;
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modalNombre.hidden) modalNombre.hidden = true;
});

modalGuardar.addEventListener("click", async () => {
  const nombre = modalNombreInput.value.trim();
  const notas  = modalNotasInput.value.trim();

  if (!nombre) {
    modalNombreInput.style.borderColor = "rgba(239,68,68,0.6)";
    modalNombreInput.focus();
    return;
  }
  modalNombreInput.style.borderColor = "";
  modalGuardar.textContent           = "Guardando...";
  modalGuardar.disabled              = true;

  try {
    const res = await fetch(`${API_URL}/api/network/nombre`, {
      method:      "POST",
      headers:     { "Content-Type": "application/json" },
      credentials: "include",
      body:    JSON.stringify({
        ip:     modalIpActual,
        mac:    modalMacActual || null,
        nombre,
        notas:  notas || null
      })
    });
    const data = await res.json();
    if (res.ok) { modalNombre.hidden = true; btnDiscover.click(); }
    else { alert("Error: " + (data.detail || "No se pudo guardar.")); }
  } catch (err) {
    alert("Error de conexion al guardar el nombre.");
  } finally {
    modalGuardar.textContent = "Guardar";
    modalGuardar.disabled    = false;
  }
});

/* ===== BLOQUEAR DISPOSITIVO =====
   BUG #2 CORREGIDO: se eliminó el parámetro mac de la URL.
   El endpoint solo necesita ip. */
async function bloquearDispositivo(ip) {
  if (!confirm(`¿Deseas bloquear ${ip} en el firewall?`)) return;
  try {
    const res = await fetch(
      `${API_URL}/api/network/bloquear?ip=${encodeURIComponent(ip)}`,
      { method: "POST", credentials: "include" }
    );
    const data = await res.json();
    if (res.ok) { alert(data.mensaje); }
    else        { alert(data.detail || "No se pudo bloquear."); }
  } catch (err) {
    alert("Error de conexion.");
  }
}

/* ===== UTILIDADES RED ===== */
function mostrarNetAlert(msg) { netAlertMsg.textContent = msg; netAlert.hidden = false; }
function ocultarNetAlert()    { netAlert.hidden = true; }

function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g,  "&amp;")
    .replace(/</g,  "&lt;")
    .replace(/>/g,  "&gt;")
    .replace(/"/g,  "&quot;")
    .replace(/'/g,  "&#39;");
}

/* =============================================
   CONTROL DE ACCESO — FIREWALL
   ============================================= */

document.querySelectorAll(".access-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".access-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    const tabName = tab.dataset.tab;
    document.getElementById("tabIp").hidden      = tabName !== "ip";
    document.getElementById("tabDominio").hidden = tabName !== "dominio";
    ocultarAccessResult();
  });
});

document.getElementById("btnBloquearIp").addEventListener("click", async () => {
  const ip = document.getElementById("firewallIp").value.trim();
  if (!ip) { mostrarAccessResult("Ingresa una IP.", false); return; }
  await ejecutarAcceso(
    `${API_URL}/api/network/bloquear?ip=${encodeURIComponent(ip)}`,
    `¿Bloquear IP ${ip} en el firewall de Windows?`
  );
});

document.getElementById("btnDesbloquearIp").addEventListener("click", async () => {
  const ip = document.getElementById("firewallIp").value.trim();
  if (!ip) { mostrarAccessResult("Ingresa una IP.", false); return; }
  await ejecutarAcceso(
    `${API_URL}/api/network/desbloquear?ip=${encodeURIComponent(ip)}`,
    `¿Desbloquear IP ${ip} del firewall?`
  );
});

document.getElementById("btnBloquearDominio").addEventListener("click", async () => {
  const dominio = document.getElementById("firewallDominio").value.trim();
  if (!dominio) { mostrarAccessResult("Ingresa un dominio.", false); return; }
  await ejecutarAcceso(
    `${API_URL}/api/network/bloquear-dominio?dominio=${encodeURIComponent(dominio)}`,
    `¿Bloquear ${dominio} en el firewall?`
  );
});

document.getElementById("btnDesbloquearDominio").addEventListener("click", async () => {
  const dominio = document.getElementById("firewallDominio").value.trim();
  if (!dominio) { mostrarAccessResult("Ingresa un dominio.", false); return; }
  await ejecutarAcceso(
    `${API_URL}/api/network/desbloquear-dominio?dominio=${encodeURIComponent(dominio)}`,
    `¿Desbloquear ${dominio} del firewall?`
  );
});

async function ejecutarAcceso(url, confirmMsg) {
  if (!confirm(confirmMsg)) return;
  const btns = document.querySelectorAll(".btn-bloquear-fw, .btn-desbloquear-fw");
  btns.forEach(b => b.disabled = true);
  ocultarAccessResult();

  try {
    const res  = await fetch(url, {
      method:      "POST",
      credentials: "include"
    });
    const data = await res.json();

    if (res.ok) {
      const msg = data.mensaje ||
        (data.ips_bloqueadas
          ? `${data.dominio} bloqueado — ${data.ips_bloqueadas.length} IPs bloqueadas.`
          : "Operacion exitosa.");
      mostrarAccessResult(msg, true);
    } else {
      mostrarAccessResult(data.detail || "Error al procesar la solicitud.", false);
    }
  } catch (err) {
    mostrarAccessResult("Error de conexion. ¿Esta uvicorn corriendo como administrador?", false);
  } finally {
    btns.forEach(b => b.disabled = false);
  }
}

function mostrarAccessResult(msg, exito) {
  const el = document.getElementById("accessResult");
  el.querySelector("#accessResultMsg").textContent = msg;
  el.className  = "access-result " + (exito ? "success" : "error");
  el.hidden     = false;
  setTimeout(() => { el.hidden = true; }, 6000);
}

function ocultarAccessResult() {
  document.getElementById("accessResult").hidden = true;
}

/* =============================================
   RECOMENDACIONES DE SEGURIDAD
   ============================================= */

async function cargarRecomendaciones(escaneoId) {
  try {
    const res  = await fetch(`${API_URL}/api/scanner/recomendaciones/${escaneoId}`, {
      credentials: "include"
    });
    const data = await res.json();
    if (res.ok) renderizarRecomendaciones(data);
  } catch (err) {
    console.error("Error cargando recomendaciones:", err);
  }
}

/* =============================================
   PUERTOS DEL SISTEMA OPERATIVO
   Estos puertos NO pueden cerrarse con el firewall
   de Windows cuando se escanea desde localhost,
   porque el tráfico local nunca pasa por el firewall.
   Requieren deshabilitar el servicio manualmente.
   ============================================= */
const PUERTOS_SISTEMA_OS = {
  135: {
    servicio: "RPC (Remote Procedure Call)",
    razon:    "Es un servicio del núcleo de Windows. El firewall no lo oculta a escaneos locales.",
    pasos:    [
      "Abre Servicios (services.msc)",
      "Busca 'Llamada a procedimiento remoto (RPC)'",
      "Nota: este servicio NO se puede deshabilitar — Windows depende de él.",
      "La solución correcta es restringir el acceso externo desde el router/perimeter firewall."
    ]
  },
  139: {
    servicio: "NetBIOS Session Service",
    razon:    "Cerrar este puerto rompe la resolución de nombres NetBIOS que usa el scanner de red.",
    pasos:    [
      "Panel de Control → Centro de redes → Adaptador → Propiedades",
      "Selecciona 'Protocolo de Internet versión 4 (TCP/IPv4)' → Propiedades → Avanzadas",
      "Pestaña WINS → Selecciona 'Deshabilitar NetBIOS sobre TCP/IP'",
      "⚠️ Esto deshabilitará también la resolución de nombres de red en el scanner."
    ]
  },
  445: {
    servicio: "SMB (Server Message Block)",
    razon:    "Es un servicio central de Windows para compartir archivos e impresoras.",
    pasos:    [
      "Para deshabilitar SMBv1 (el más peligroso):",
      "PowerShell como Admin: Set-SmbServerConfiguration -EnableSMB1Protocol $false",
      "Para bloquear SMB externamente: configura el router para bloquear el puerto 445 desde internet.",
      "No deshabilites SMB completamente si usas carpetas compartidas en red local."
    ]
  },
  137: {
    servicio: "NetBIOS Name Service",
    razon:    "Servicio de nombres NetBIOS del sistema operativo Windows.",
    pasos:    [
      "Panel de Control → Adaptador de red → Propiedades",
      "TCP/IPv4 → Propiedades → Avanzadas → WINS",
      "Selecciona 'Deshabilitar NetBIOS sobre TCP/IP'"
    ]
  },
  138: {
    servicio: "NetBIOS Datagram Service",
    razon:    "Servicio de datagramas NetBIOS del sistema operativo Windows.",
    pasos:    [
      "Mismo procedimiento que el puerto 137.",
      "Deshabilitar NetBIOS sobre TCP/IP desde las propiedades del adaptador de red."
    ]
  }
};

function renderizarRecomendaciones(data) {
  const { recomendaciones, resumen } = data;

  const anterior = document.getElementById("recSection");
  if (anterior) anterior.remove();

  if (!recomendaciones || recomendaciones.length === 0) return;

  const colores = {
    inmediata: { bg: "rgba(239,68,68,0.1)",  borde: "rgba(239,68,68,0.3)",  texto: "#f87171", label: "Inmediata" },
    alta:      { bg: "rgba(249,115,22,0.1)", borde: "rgba(249,115,22,0.3)", texto: "#fb923c", label: "Alta"      },
    media:     { bg: "rgba(234,179,8,0.1)",  borde: "rgba(234,179,8,0.3)",  texto: "#facc15", label: "Media"     },
    baja:      { bg: "rgba(34,197,94,0.1)",  borde: "rgba(34,197,94,0.3)",  texto: "#4ade80", label: "Baja"      },
  };

  const tarjetas = recomendaciones.map(r => {
    const c          = colores[r.urgencia] || colores.media;
    const esSistema  = PUERTOS_SISTEMA_OS.hasOwnProperty(r.puerto);
    const infoSistema = esSistema ? PUERTOS_SISTEMA_OS[r.puerto] : null;

    const cmdHtml = r.comando
      ? `<div class="rec-cmd">
           <span class="rec-cmd-label">Comando a ejecutar en la máquina afectada:</span>
           <code id="cmd-${r.puerto}">${escHtml(r.comando)}</code>
           <button class="btn-copiar-cmd" onclick="copiarComando(${r.puerto})" title="Copiar comando">
             <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
               <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
             </svg>
             Copiar
           </button>
         </div>`
      : "";

    /* Advertencia especial para puertos del sistema OS */
    const advertenciaSistemaHtml = esSistema ? `
      <div class="rec-aviso-sistema">
        <div class="rec-aviso-sistema-header">
          <span class="rec-aviso-sistema-icono">⚠️</span>
          <span class="rec-aviso-sistema-titulo">Servicio del sistema — no se puede cerrar con el firewall</span>
        </div>
        <p class="rec-aviso-sistema-razon">${escHtml(infoSistema.razon)}</p>
        <div class="rec-aviso-sistema-pasos">
          <span class="rec-aviso-sistema-pasos-label">Pasos manuales requeridos:</span>
          <ol class="rec-aviso-pasos-lista">
            ${infoSistema.pasos.map(p => `<li>${escHtml(p)}</li>`).join("")}
          </ol>
        </div>
      </div>
    ` : "";

    /* Panel de verificación — aparece después de aplicar corrección */
    const verificacionHtml = `
      <div class="rec-verificacion" id="verif-${r.puerto}" hidden>
        <div class="rec-verif-header">
          <span class="rec-verif-icono">⏳</span>
          <span class="rec-verif-texto" id="verif-texto-${r.puerto}">Verificando si el puerto se cerró...</span>
        </div>
        <div class="rec-verif-barra-bg">
          <div class="rec-verif-barra-fill" id="verif-barra-${r.puerto}"></div>
        </div>
        <div class="rec-verif-resultado" id="verif-resultado-${r.puerto}" hidden></div>
      </div>
    `;

    /* Registro forense — aparece después de aplicar */
    const registroHtml = `
      <div class="rec-registro" id="registro-${r.puerto}" hidden>
        <span class="rec-registro-icono">🛡️</span>
        <div class="rec-registro-info">
          <span class="rec-registro-titulo">Corrección registrada</span>
          <span class="rec-registro-meta" id="registro-meta-${r.puerto}"></span>
        </div>
      </div>
    `;

    /* Botón — deshabilitado con explicación para puertos del sistema */
    const btnCorreccion = esSistema
      ? `<div class="rec-actions">
           <button class="btn-aplicar-correccion btn-sistema-deshabilitado" disabled
             title="Este puerto pertenece al sistema operativo y no puede cerrarse con el firewall desde localhost">
             🔒 Requiere intervención manual — ver pasos arriba
           </button>
         </div>`
      : `<div class="rec-actions">
           <button
             class="btn-aplicar-correccion"
             onclick="aplicarCorreccion(${r.puerto}, '${r.protocolo}', this)"
             data-puerto="${r.puerto}"
             data-protocolo="${r.protocolo}"
             data-aplicado="false">
             ⚡ Aplicar Corrección
           </button>
         </div>`;

    return `
      <div class="rec-card ${esSistema ? "rec-card-sistema" : ""}" id="rec-card-${r.puerto}" style="border-color:${c.borde}">
        <div class="rec-card-header">
          <div class="rec-card-left">
            <span class="rec-puerto">Puerto ${r.puerto}/${r.protocolo}</span>
            <span class="rec-servicio">${escHtml(r.servicio)}</span>
            ${esSistema ? '<span class="badge-sistema-os">Servicio OS</span>' : ""}
          </div>
          <span class="rec-urgencia" style="background:${c.bg};color:${c.texto};border-color:${c.borde}">
            ${c.label}
          </span>
        </div>
        <h4 class="rec-titulo">${escHtml(r.titulo)}</h4>
        <p class="rec-problema"><strong>Problema:</strong> ${escHtml(r.problema)}</p>
        <p class="rec-accion"><strong>Acción:</strong> ${escHtml(r.accion)}</p>
        ${cmdHtml}
        ${advertenciaSistemaHtml}
        ${registroHtml}
        ${verificacionHtml}
        ${btnCorreccion}
        <div class="rec-footer">
          <span class="rec-ref">${escHtml(r.referencia)}</span>
        </div>
      </div>
    `;
  }).join("");

  const badgeResumen = [
    resumen.inmediata > 0
      ? `<span class="rec-badge" style="background:rgba(239,68,68,0.15);color:#f87171;border-color:rgba(239,68,68,0.3)">
           ${resumen.inmediata} Inmediata${resumen.inmediata > 1 ? "s" : ""}
         </span>` : "",
    resumen.alta > 0
      ? `<span class="rec-badge" style="background:rgba(249,115,22,0.15);color:#fb923c;border-color:rgba(249,115,22,0.3)">
           ${resumen.alta} Alta${resumen.alta > 1 ? "s" : ""}
         </span>` : "",
    resumen.media > 0
      ? `<span class="rec-badge" style="background:rgba(234,179,8,0.15);color:#facc15;border-color:rgba(234,179,8,0.3)">
           ${resumen.media} Media${resumen.media > 1 ? "s" : ""}
         </span>` : "",
    resumen.baja > 0
      ? `<span class="rec-badge" style="background:rgba(34,197,94,0.15);color:#4ade80;border-color:rgba(34,197,94,0.3)">
           ${resumen.baja} Baja${resumen.baja > 1 ? "s" : ""}
         </span>` : "",
  ].join("");

  const html = `
    <section class="rec-section" id="recSection" aria-labelledby="rec-title">
      <div class="rec-header">
        <div>
          <h2 class="results-title" id="rec-title">Plan de Acción de Seguridad</h2>
          <p class="rec-subtitulo">Basado en los puertos abiertos detectados en este escaneo.</p>
        </div>
        <div class="rec-resumen">${badgeResumen}</div>
      </div>
      <div class="rec-grid">${tarjetas}</div>
    </section>
  `;

  document.getElementById("resultsSection").insertAdjacentHTML("afterend", html);

  if (typeof gsap !== "undefined") {
    gsap.from(".rec-card", { y: 20, opacity: 0, duration: 0.5, stagger: 0.08, ease: "power3.out" });
  }
}

/* =============================================
   COPIAR COMANDO AL PORTAPAPELES
   ============================================= */

function copiarComando(puerto) {
  const codigo = document.getElementById(`cmd-${puerto}`);
  if (!codigo) return;
  navigator.clipboard.writeText(codigo.textContent.trim()).then(() => {
    const btn = codigo.parentElement.querySelector(".btn-copiar-cmd");
    const textoOriginal = btn.innerHTML;
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Copiado`;
    btn.style.color = "#4ade80";
    setTimeout(() => {
      btn.innerHTML = textoOriginal;
      btn.style.color = "";
    }, 2000);
  });
}

/* =============================================
   APLICAR CORRECCIÓN — con registro forense
   y re-escaneo de verificación
   ============================================= */

async function aplicarCorreccion(puerto, protocolo, btn) {
  const yaAplicado = btn.dataset.aplicado === "true";

  /* ── REVERTIR corrección ya aplicada ── */
  if (yaAplicado) {
    if (!confirm(`¿Eliminar la regla de bloqueo del puerto ${puerto}/${protocolo}?`)) return;

    btn.disabled    = true;
    btn.textContent = "Procesando...";

    try {
      const res  = await fetch(
        `${API_URL}/api/scanner/abrir-puerto?puerto=${puerto}&protocolo=${protocolo}`,
        { method: "POST", credentials: "include" }
      );
      const data = await res.json();

      if (res.ok) {
        btn.innerHTML     = "⚡ Aplicar Corrección";
        btn.dataset.aplicado = "false";
        btn.classList.remove("btn-aplicar-correccion-ok");
        btn.classList.add("btn-aplicar-correccion");
        btn.disabled = false;

        /* Ocultar registro y verificación al revertir */
        const reg   = document.getElementById(`registro-${puerto}`);
        const verif = document.getElementById(`verif-${puerto}`);
        if (reg)   reg.hidden   = true;
        if (verif) verif.hidden = true;

        /* Quitar borde verde de la card */
        const card = document.getElementById(`rec-card-${puerto}`);
        if (card) card.classList.remove("rec-card-resuelta");

      } else {
        alert(data.detail || "Error al revertir.");
        btn.disabled = false;
        btn.innerHTML = "⚡ Aplicar Corrección";
      }
    } catch {
      alert("Error de conexión.");
      btn.disabled  = false;
      btn.innerHTML = "⚡ Aplicar Corrección";
    }
    return;
  }

  /* ── APLICAR corrección nueva ── */
  if (!confirm(
    `¿Bloquear el puerto ${puerto}/${protocolo} en el firewall de Windows?\n\n` +
    `Importante: esto bloquea el puerto en ESTA máquina.\n` +
    `Si el objetivo es otro equipo, ejecuta el comando mostrado manualmente en él.`
  )) return;

  btn.disabled  = true;
  btn.innerHTML = `<svg style="width:14px;height:14px;animation:spin 0.8s linear infinite" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/></svg> Aplicando...`;

  try {
    const res  = await fetch(
      `${API_URL}/api/scanner/cerrar-puerto?puerto=${puerto}&protocolo=${protocolo}`,
      { method: "POST", credentials: "include" }
    );
    const data = await res.json();

    if (!res.ok) {
      alert(data.detail || "Error al aplicar corrección.");
      btn.disabled  = false;
      btn.innerHTML = "⚡ Aplicar Corrección";
      return;
    }

    /* ── 1. Cambiar estado del botón ── */
    btn.innerHTML     = "✅ Corrección Aplicada — Revertir";
    btn.dataset.aplicado = "true";
    btn.classList.remove("btn-aplicar-correccion");
    btn.classList.add("btn-aplicar-correccion-ok");
    btn.disabled = false;

    /* ── 2. Registro forense con timestamp ── */
    const ahora     = new Date();
    const timestamp = ahora.toLocaleString("es-DO", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit", second: "2-digit"
    });
    const reg  = document.getElementById(`registro-${puerto}`);
    const meta = document.getElementById(`registro-meta-${puerto}`);
    if (reg && meta) {
      meta.textContent = `${timestamp} · Usuario: ${nombre} ${apellido || ""}`.trim();
      reg.hidden = false;
      if (typeof gsap !== "undefined") {
        gsap.from(reg, { y: -6, opacity: 0, duration: 0.4, ease: "power2.out" });
      }
    }

    /* Marcar card visualmente como resuelta */
    const card = document.getElementById(`rec-card-${puerto}`);
    if (card) card.classList.add("rec-card-resuelta");

    /* ── 3. Re-escaneo de verificación (5 segundos después) ── */
    iniciarVerificacion(puerto, protocolo);

  } catch {
    alert("Error de conexión. ¿Está uvicorn corriendo como Administrador?");
    btn.disabled  = false;
    btn.innerHTML = "⚡ Aplicar Corrección";
  }
}

/* =============================================
   VERIFICACIÓN — re-escanea el puerto para
   confirmar si realmente se cerró
   ============================================= */

function iniciarVerificacion(puerto, protocolo) {
  const verif   = document.getElementById(`verif-${puerto}`);
  const texto   = document.getElementById(`verif-texto-${puerto}`);
  const barra   = document.getElementById(`verif-barra-${puerto}`);
  const result  = document.getElementById(`verif-resultado-${puerto}`);
  if (!verif) return;

  const ESPERA_SEG = 8;

  verif.hidden   = false;
  result.hidden  = true;
  texto.textContent = `Verificando en ${ESPERA_SEG}s si el puerto ${puerto} se cerró...`;
  barra.style.width = "0%";
  barra.style.background = "var(--accent)";

  if (typeof gsap !== "undefined") {
    gsap.from(verif, { y: -6, opacity: 0, duration: 0.4, ease: "power2.out" });
  }

  /* Animación de la barra de cuenta regresiva */
  let elapsed = 0;
  const intervalo = setInterval(() => {
    elapsed++;
    const pct = Math.min((elapsed / ESPERA_SEG) * 100, 100);
    barra.style.width = pct + "%";
    const restante = ESPERA_SEG - elapsed;
    if (restante > 0) {
      texto.textContent = `Verificando en ${restante}s si el puerto ${puerto} se cerró...`;
    } else {
      texto.textContent = `Escaneando puerto ${puerto}...`;
      clearInterval(intervalo);
    }
  }, 1000);

  /* Lanzar el escaneo después de la espera */
  setTimeout(async () => {
    try {
      /* Inicia un escaneo rápido solo sobre ese puerto */
      const ipActual = document.getElementById("targetIp").value.trim()
                    || cTarget.textContent.trim();

      if (!ipActual || ipActual === "Ningún escaneo activo") {
        mostrarResultadoVerificacion(result, barra, "pendiente",
          "No se pudo determinar la IP objetivo. Verifica manualmente.");
        return;
      }

      const resInicio = await fetch(`${API_URL}/api/scanner/iniciar`, {
        method:      "POST",
        headers:     { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          target_ip:      ipActual,
          target_nombre:  ipActual,
          modo:           "rapido",
          puertos_custom: String(puerto)
        })
      });

      if (!resInicio.ok) {
        mostrarResultadoVerificacion(result, barra, "pendiente",
          "No se pudo lanzar el escaneo de verificación.");
        return;
      }

      const dataInicio = await resInicio.json();
      const idVerif    = dataInicio.escaneo_id;

      /* Polling hasta que termine */
      let intentos = 0;
      const poll = setInterval(async () => {
        intentos++;
        if (intentos > 20) {
          clearInterval(poll);
          mostrarResultadoVerificacion(result, barra, "pendiente",
            "Tiempo agotado. Verifica manualmente.");
          return;
        }

        const resResult = await fetch(
          `${API_URL}/api/scanner/resultado/${idVerif}`,
          { credentials: "include" }
        );
        const dataResult = await resResult.json();

        if (dataResult.estado === "completado") {
          clearInterval(poll);
          const portResult = (dataResult.puertos || []).find(p => p.puerto === puerto);
          const estadoFinal = portResult ? portResult.estado : "closed";

          if (estadoFinal === "open") {
            mostrarResultadoVerificacion(result, barra, "abierto",
              `⚠️ Puerto ${puerto} sigue abierto. La regla de firewall se aplicó en esta máquina, pero el servicio aún está activo. Detén el servicio manualmente.`);
          } else {
            mostrarResultadoVerificacion(result, barra, "cerrado",
              `✅ Puerto ${puerto} verificado como ${estadoFinal === "filtered" ? "filtrado" : "cerrado"}. Corrección exitosa.`);
          }
        } else if (dataResult.estado === "fallido") {
          clearInterval(poll);
          mostrarResultadoVerificacion(result, barra, "pendiente",
            "El escaneo de verificación falló. Verifica manualmente.");
        }
      }, 3000);

    } catch (err) {
      mostrarResultadoVerificacion(result, barra, "pendiente",
        "Error al verificar. Comprueba la conexión con el backend.");
    }
  }, ESPERA_SEG * 1000);
}

function mostrarResultadoVerificacion(el, barra, estado, mensaje) {
  el.hidden = false;
  el.textContent = mensaje;

  if (estado === "cerrado") {
    el.className   = "rec-verif-resultado verif-ok";
    barra.style.background = "#22c55e";
    barra.style.width = "100%";
    document.getElementById(el.id.replace("resultado", "icono")) &&
      (document.getElementById(el.id.replace("resultado", "icono")).textContent = "✅");
  } else if (estado === "abierto") {
    el.className   = "rec-verif-resultado verif-warn";
    barra.style.background = "#f97316";
    barra.style.width = "100%";
  } else {
    el.className   = "rec-verif-resultado verif-info";
    barra.style.width = "100%";
  }

  const textoEl = barra.closest(".rec-verificacion").querySelector(".rec-verif-texto");
  if (textoEl) textoEl.textContent = "Verificación completada";

  if (typeof gsap !== "undefined") {
    gsap.from(el, { y: -4, opacity: 0, duration: 0.4, ease: "power2.out" });
  }
}

/* =============================================
   REPORTES PDF
   ============================================= */

const btnGenerarPdf       = document.getElementById("btnGenerarPdf");
const btnPdfText          = document.getElementById("btnPdfText");
const btnRefrescarReportes = document.getElementById("btnRefrescarReportes");
const reportesSection     = document.getElementById("reportesSection");
const reportesEmpty       = document.getElementById("reportesEmpty");
const reportesTableWrap   = document.getElementById("reportesTableWrap");
const reportesTableBody   = document.getElementById("reportesTableBody");

const RIESGO_COLORS = {
  critico: "#ef4444",
  alto:    "#f97316",
  medio:   "#eab308",
  bajo:    "#22c55e",
  ninguno: "#64748b",
};

/* ── Generar reporte del escaneo actual ─────────────────────────── */
btnGenerarPdf.addEventListener("click", async () => {
  if (!escaneoActual) return;

  btnGenerarPdf.disabled = true;
  btnPdfText.textContent = "Generando...";

  try {
    const res  = await fetch(`${API_URL}/api/reportes/generar/${escaneoActual}`, {
      method:      "POST",
      credentials: "include"
    });
    const data = await res.json();

    if (!res.ok) {
      alert(data.detail || "Error al generar el reporte.");
      return;
    }

    mostrarNotificacion(`✅ Reporte ${data.numero_reporte} generado. Descargando...`);
    await descargarReporte(data.reporte_id, data.numero_reporte);
    await cargarReportes();

  } catch (err) {
    alert("Error de conexión al generar el reporte.");
    console.error(err);
  } finally {
    btnGenerarPdf.disabled = false;
    btnPdfText.textContent = "Generar Reporte PDF";
  }
});

/* ── Descargar PDF por ID ────────────────────────────────────────── */
async function descargarReporte(reporteId, numeroReporte) {
  try {
    const res = await fetch(`${API_URL}/api/reportes/descargar/${reporteId}`, {
      credentials: "include"
    });
    if (!res.ok) { alert("No se pudo descargar el reporte."); return; }

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
    alert("Error al descargar el PDF.");
    console.error(err);
  }
}

/* ── Cargar historial de reportes ───────────────────────────────── */
async function cargarReportes() {
  try {
    const res  = await fetch(`${API_URL}/api/reportes/lista`, { credentials: "include" });
    if (!res.ok) return;
    const data = await res.json();

    if (!data.reportes || data.reportes.length === 0) {
      reportesEmpty.hidden     = false;
      reportesTableWrap.hidden = true;
      return;
    }

    reportesEmpty.hidden     = true;
    reportesTableWrap.hidden = false;

    reportesTableBody.innerHTML = data.reportes.map(r => {
      const riesgoColor = RIESGO_COLORS[r.riesgo_maximo] || RIESGO_COLORS.ninguno;
      return `
        <tr>
          <td>
            <span class="rep-numero">${escHtml(r.numero_reporte)}</span>
          </td>
          <td><span class="rep-ip">${escHtml(r.target_ip)}</span></td>
          <td>
            <span class="rep-riesgo" style="background:${riesgoColor}">
              ${escHtml(r.riesgo_maximo)}
            </span>
          </td>
          <td style="text-align:center;font-weight:700">${Number(r.hallazgos)}</td>
          <td class="rep-fecha">${escHtml(r.generado_en)}</td>
          <td>
            <button
              class="btn-descargar-rep"
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

    if (typeof gsap !== "undefined") {
      gsap.from("#reportesSection", { y: 16, opacity: 0, duration: 0.5, ease: "power3.out" });
    }
  } catch (err) {
    console.error("Error cargando reportes:", err);
  }
}

/* ── Notificación temporal ──────────────────────────────────────── */
function mostrarNotificacion(msg) {
  let notif = document.getElementById("pdfNotif");
  if (!notif) {
    notif = document.createElement("div");
    notif.id = "pdfNotif";
    document.body.appendChild(notif);
  }
  notif.textContent = msg;
  notif.className   = "pdf-notif visible";
  setTimeout(() => { notif.className = "pdf-notif"; }, 4000);
}

btnRefrescarReportes.addEventListener("click", cargarReportes);

/* Cargar reportes al iniciar */
cargarReportes();

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