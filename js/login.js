/* =============================================
   ForensicShield Lite — login.js
   Cesar Eduardo Valenzuela Mosquera · ITESPF 2026
   ============================================= */

/* ===== URL DEL BACKEND ===== */
// En desarrollo apunta a FastAPI local
// En producción cambia por tu dominio real
const API_URL = "http://127.0.0.1:8000";

/* ===== FONDO ANIMADO THREE.JS ===== */
const canvas   = document.getElementById("canvas-bg");
const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const scene  = new THREE.Scene();
const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

const uniforms = {
  u_time:  { value: 0 },
  u_res:   { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
  u_theme: { value: 0.0 }
};

const material = new THREE.ShaderMaterial({
  uniforms,
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform float u_time;
    uniform vec2  u_res;
    uniform float u_theme;
    varying vec2  vUv;

    float random(in vec2 _st) {
      return fract(sin(dot(_st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
    }
    float noise(in vec2 _st) {
      vec2 i = floor(_st);
      vec2 f = fract(_st);
      float a = random(i);
      float b = random(i + vec2(1.0, 0.0));
      float c = random(i + vec2(0.0, 1.0));
      float d = random(i + vec2(1.0, 1.0));
      vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
    }
    float fbm(in vec2 _st) {
      float v = 0.0;
      float a = 0.5;
      vec2  shift = vec2(100.0);
      mat2  rot   = mat2(cos(0.5), sin(0.5), -sin(0.5), cos(0.5));
      for (int i = 0; i < 5; ++i) {
        v  += a * noise(_st);
        _st = rot * _st * 2.0 + shift;
        a  *= 0.5;
      }
      return v;
    }
    void main() {
      vec2 st = gl_FragCoord.xy / u_res.xy;
      st.x *= u_res.x / u_res.y;

      vec2 q = vec2(0.);
      q.x = fbm(st + 0.00 * u_time);
      q.y = fbm(st + vec2(1.0));

      vec2 r = vec2(0.);
      r.x = fbm(st + 1.0 * q + vec2(1.7,  9.2) + 0.150 * u_time);
      r.y = fbm(st + 1.0 * q + vec2(8.3,  2.8) + 0.126 * u_time);

      vec3 dark1      = vec3(0.02, 0.02, 0.06);
      vec3 dark2      = vec3(0.08, 0.04, 0.18);
      vec3 darkAccent = vec3(0.43, 0.36, 0.99);
      vec3 light1     = vec3(0.95, 0.95, 0.98);
      vec3 light2     = vec3(0.90, 0.92, 1.00);
      vec3 lightAccent= vec3(0.40, 0.60, 1.00);

      vec3 c1      = mix(dark1,      light1,      u_theme);
      vec3 c2      = mix(dark2,      light2,      u_theme);
      vec3 cAccent = mix(darkAccent, lightAccent, u_theme);

      vec3 color = mix(c1, c2, length(q));
      color      = mix(color, cAccent, length(r) * 0.4);

      gl_FragColor = vec4(color, 1.0);
    }
  `
});

const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
scene.add(plane);

function resize() {
  const w = window.innerWidth;
  const h = window.innerHeight;
  renderer.setSize(w, h);
  uniforms.u_res.value.set(w, h);
}
window.addEventListener("resize", resize);
resize();

function animate(t) {
  requestAnimationFrame(animate);
  uniforms.u_time.value = t * 0.001;
  renderer.render(scene, camera);
}
animate(0);

/* ===== ANIMACIONES DE ENTRADA (GSAP) ===== */
gsap.from(".login-brand", {
  x: -50, opacity: 0, duration: 1.2, ease: "power4.out"
});
gsap.from(".login-card", {
  y: 40, opacity: 0, duration: 1, delay: 0.2, ease: "power3.out"
});
gsap.from(".brand-feature", {
  x: -20, opacity: 0, duration: 0.6, stagger: 0.12, delay: 0.5, ease: "power2.out"
});

/* ===== MOSTRAR / OCULTAR CONTRASEÑA ===== */
const togglePassword = document.getElementById("togglePassword");
const passwordInput  = document.getElementById("password");
const eyeShow        = togglePassword.querySelector(".eye-show");
const eyeHide        = togglePassword.querySelector(".eye-hide");

togglePassword.addEventListener("click", () => {
  const isHidden = passwordInput.type === "password";
  passwordInput.type         = isHidden ? "text" : "password";
  togglePassword.ariaPressed = isHidden ? "true" : "false";
  togglePassword.ariaLabel   = isHidden ? "Ocultar contraseña" : "Mostrar contraseña";
  eyeShow.hidden = isHidden;
  eyeHide.hidden = !isHidden;
});

/* ===== VALIDACIÓN EN TIEMPO REAL ===== */
const emailInput    = document.getElementById("email");
const emailError    = document.getElementById("email-error");
const passwordError = document.getElementById("password-error");

emailInput.addEventListener("blur", () => {
  const val = emailInput.value.trim();
  if (!val) {
    showFieldError(emailInput, emailError, "El correo es obligatorio.");
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
    showFieldError(emailInput, emailError, "Ingresa un correo válido.");
  } else {
    clearFieldError(emailInput, emailError);
  }
});

passwordInput.addEventListener("blur", () => {
  const val = passwordInput.value;
  if (!val) {
    showFieldError(passwordInput, passwordError, "La contraseña es obligatoria.");
  } else if (val.length < 8) {
    showFieldError(passwordInput, passwordError, "Mínimo 8 caracteres.");
  } else {
    clearFieldError(passwordInput, passwordError);
  }
});

emailInput.addEventListener("input",    () => clearFieldError(emailInput,    emailError));
passwordInput.addEventListener("input", () => clearFieldError(passwordInput, passwordError));

function showFieldError(input, errorEl, msg) {
  input.style.borderColor = "rgba(239, 68, 68, 0.6)";
  errorEl.textContent     = msg;
}
function clearFieldError(input, errorEl) {
  input.style.borderColor = "";
  errorEl.textContent     = "";
}

/* ===== SUBMIT DEL FORMULARIO ===== */
const loginForm  = document.getElementById("loginForm");
const btnLogin   = document.getElementById("btnLogin");
const btnText    = btnLogin.querySelector(".btn-text");
const btnLoader  = btnLogin.querySelector(".btn-loader");
const loginAlert = document.getElementById("loginAlert");
const alertMsg   = document.getElementById("loginAlertMsg");

let intentosFallidos = 0;
const MAX_INTENTOS   = 5;

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const email    = emailInput.value.trim();
  const password = passwordInput.value;

  // ── Validación frontend ──────────────────────────────────────────
  let valido = true;
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showFieldError(emailInput, emailError, "Ingresa un correo válido.");
    valido = false;
  }
  if (!password || password.length < 8) {
    showFieldError(passwordInput, passwordError, "Mínimo 8 caracteres.");
    valido = false;
  }
  if (!valido) return;

  if (intentosFallidos >= MAX_INTENTOS) {
    mostrarAlerta("Demasiados intentos fallidos. Espera unos minutos e intenta de nuevo.");
    return;
  }

  setLoading(true);
  ocultarAlerta();

  try {
    // ── Llamada al backend FastAPI ───────────────────────────────────
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method:      "POST",
      headers:     { "Content-Type": "application/json" },
      credentials: "include",
      body:        JSON.stringify({ email, password })
    });

    // ── Error 429 — demasiados intentos (slowapi / bloqueo por IP) ──
    if (response.status === 429) {
      mostrarAlerta("Demasiados intentos. Espera unos minutos e intenta de nuevo.");
      setLoading(false);
      return;
    }

    const data = await response.json();

    if (response.ok && data.nombre) {
      // ── Login exitoso ─────────────────────────────────────────────
      // El JWT viaja en HttpOnly cookie (no accesible desde JS)
      // Solo guardamos datos no sensibles para la UI
      intentosFallidos = 0;

      sessionStorage.setItem("fs_rol",      data.rol);
      sessionStorage.setItem("fs_nombre",   data.nombre);
      sessionStorage.setItem("fs_apellido", data.apellido);

      // Animación de salida y redirección al index (dashboard futuro)
      gsap.to(".login-card", {
        y: -20,
        opacity: 0,
        duration: 0.4,
        ease: "power2.in",
        onComplete: () => {
          // ⚠️ Cambia "/index.html" por "/dashboard" cuando tengas el dashboard
          window.location.href = "/index.html";
        }
      });

    } else {
      // ── Login fallido ─────────────────────────────────────────────
      intentosFallidos++;
      const restantes = MAX_INTENTOS - intentosFallidos;

      if (intentosFallidos >= MAX_INTENTOS) {
        mostrarAlerta("Demasiados intentos fallidos. Espera unos minutos e intenta de nuevo.");
      } else {
        const msg = data.detail || "Credenciales incorrectas.";
        mostrarAlerta(`${msg} Te quedan ${restantes} intento${restantes !== 1 ? "s" : ""}.`);
      }

      // Animación de sacudida
      gsap.fromTo(".login-card",
        { x: -8 },
        { x: 0, duration: 0.4, ease: "elastic.out(1, 0.3)" }
      );
    }

  } catch (err) {
    mostrarAlerta("No se pudo conectar con el servidor. Verifica que el backend esté corriendo.");
    console.error("Error de red:", err);

  } finally {
    setLoading(false);
  }
});

/* ===== UTILIDADES ===== */
function setLoading(estado) {
  btnLogin.disabled = estado;
  btnText.hidden    = estado;
  btnLoader.hidden  = !estado;
}

function mostrarAlerta(msg) {
  alertMsg.textContent = msg;
  loginAlert.hidden    = false;
  loginAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function ocultarAlerta() {
  loginAlert.hidden = true;
}