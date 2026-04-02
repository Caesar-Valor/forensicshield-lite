/* =============================================
   ForensicShield Lite — script.js
   Dashboard principal
   Cesar Eduardo Valenzuela Mosquera · ITESPF 2026
   ============================================= */

const API_URL = "http://127.0.0.1:8000";

/* ===== VERIFICAR SESIÓN ===== */
const token    = sessionStorage.getItem("fs_token");
const nombre   = sessionStorage.getItem("fs_nombre");
const apellido = sessionStorage.getItem("fs_apellido");
const rol      = sessionStorage.getItem("fs_rol");

if (!token) {
  window.location.href = "login.html";
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

  /* ===== ANIMACIONES GSAP ===== */
  gsap.from(".sidebar",      { x: -50, opacity: 0, duration: 1.2, ease: "power4.out" });
  gsap.from(".hero-section", { y: 30,  opacity: 0, duration: 1,   delay: 0.2, ease: "power3.out" });
  gsap.from(".metric-card",  { y: 20,  opacity: 0, duration: 0.6, stagger: 0.08, delay: 0.3, ease: "back.out(1.2)" });
  gsap.from(".dash-panel",   { y: 30,  opacity: 0, duration: 0.7, stagger: 0.1,  delay: 0.4, ease: "power3.out" });
  gsap.from(".bento-card",   { y: 40,  opacity: 0, duration: 0.8, stagger: 0.1,  delay: 0.5, ease: "back.out(1.2)" });
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
      headers: { "Authorization": `Bearer ${token}` }
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
        <td><span class="dash-ip">${e.target_ip}</span></td>
        <td><span class="dash-estado ${estadoClass}">${estadoLabel}</span></td>
        <td style="font-variant-numeric:tabular-nums;font-weight:700">
          ${e.puertos_abiertos ?? "—"}
        </td>
        <td><span class="dash-riesgo ${riesgoClass}">${riesgoLabel}</span></td>
        <td><span class="dash-fecha">${fecha}</span></td>
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

/* ===== INICIAR ===== */
cargarDashboard();