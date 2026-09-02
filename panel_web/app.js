/**
 * ==========================================================================
 *  PORTAL DE CONTROL DE LICENCIAS - CLIENTE & GESTIÓN EN TIEMPO REAL
 *  Lógica Frontend: Conexión con Firebase Realtime Database
 * ==========================================================================
 */

// Configuración de la Base de Datos en la Nube
const FIREBASE_DB_URL = "https://bot-invima-licencias-default-rtdb.firebaseio.com";
const MASTER_ACCESS_PIN = "Febas0407"; // Clave maestra para la administradora

// Estado Global de la Aplicación
let licenciasData = {};
let filtroActual = "todos";
let terminoBusqueda = "";
let licenciaEnAccion = null; // Para modales de confirmación

// Elementos del DOM
const loginSection = document.getElementById("loginSection");
const dashboardSection = document.getElementById("dashboardSection");
const loginForm = document.getElementById("loginForm");
const adminPinInput = document.getElementById("adminPin");
const loginError = document.getElementById("loginError");
const togglePinVisibility = document.getElementById("togglePinVisibility");
const btnLogout = document.getElementById("btnLogout");
const btnRefresh = document.getElementById("btnRefresh");

const statTotal = document.getElementById("statTotal");
const statLibres = document.getElementById("statLibres");
const statOcupados = document.getElementById("statOcupados");

const searchInput = document.getElementById("searchInput");
const btnClearSearch = document.getElementById("btnClearSearch");
const filterTabs = document.querySelectorAll(".filter-tab");
const badgeCountTodos = document.getElementById("badgeCountTodos");
const badgeCountLibres = document.getElementById("badgeCountLibres");
const badgeCountOcupados = document.getElementById("badgeCountOcupados");

const loadingIndicator = document.getElementById("loadingIndicator");
const licensesContainer = document.getElementById("licensesContainer");
const emptyState = document.getElementById("emptyState");

// Modales
const modalRegenerar = document.getElementById("modalRegenerar");
const modalPcName = document.getElementById("modalPcName");
const modalOldKey = document.getElementById("modalOldKey");
const btnConfirmarRegenerar = document.getElementById("btnConfirmarRegenerar");

const modalDesvincular = document.getElementById("modalDesvincular");
const modalDesvincularKey = document.getElementById("modalDesvincularKey");
const modalDesvincularPc = document.getElementById("modalDesvincularPc");
const btnConfirmarDesvincular = document.getElementById("btnConfirmarDesvincular");

const toastContainer = document.getElementById("toastContainer");


// --------------------------------------------------------------------------
// 1. INICIALIZACIÓN & AUTENTICACIÓN
// --------------------------------------------------------------------------
const CURRENT_AUTH_TOKEN = "AUTH_FEBAS_0407_V2";

document.addEventListener("DOMContentLoaded", () => {
  // Limpiar cualquier sesión anterior que use el token antiguo
  if (sessionStorage.getItem("invima_admin_auth") === "true") {
    sessionStorage.removeItem("invima_admin_auth");
  }

  // Verificar si la sesión actual con la nueva contraseña es válida
  const tokenGuardado = sessionStorage.getItem("invima_admin_token");
  if (tokenGuardado === CURRENT_AUTH_TOKEN) {
    mostrarDashboard();
  } else {
    mostrarLogin();
  }

  configurarEventos();
});

function configurarEventos() {
  // Formulario Login
  loginForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const pinIngresado = adminPinInput.value.trim();
    if (pinIngresado === MASTER_ACCESS_PIN) {
      sessionStorage.setItem("invima_admin_token", CURRENT_AUTH_TOKEN);
      loginError.classList.add("hidden");
      mostrarDashboard();
      mostrarToast("¡Bienvenida al Panel de Control!", "success");
    } else {
      loginError.classList.remove("hidden");
      adminPinInput.value = "";
      adminPinInput.focus();
    }
  });

  // Mostrar / Ocultar PIN
  togglePinVisibility.addEventListener("click", () => {
    const isPass = adminPinInput.type === "password";
    adminPinInput.type = isPass ? "text" : "password";
  });

  // Cerrar Sesión
  btnLogout.addEventListener("click", () => {
    sessionStorage.removeItem("invima_admin_token");
    sessionStorage.removeItem("invima_admin_auth");
    adminPinInput.value = "";
    mostrarLogin();
    mostrarToast("Sesión cerrada correctamente.", "info");
  });

  // Botón Actualizar
  btnRefresh.addEventListener("click", () => {
    const icon = btnRefresh.querySelector(".icon-refresh");
    if (icon) icon.classList.add("spinning");
    cargarLicencias(() => {
      if (icon) icon.classList.remove("spinning");
      mostrarToast("Licencias actualizadas en tiempo real.", "success");
    });
  });

  // Búsqueda en vivo
  searchInput.addEventListener("input", (e) => {
    terminoBusqueda = e.target.value.trim().toLowerCase();
    btnClearSearch.classList.toggle("hidden", terminoBusqueda === "");
    renderizarLicencias();
  });

  btnClearSearch.addEventListener("click", () => {
    searchInput.value = "";
    terminoBusqueda = "";
    btnClearSearch.classList.add("hidden");
    renderizarLicencias();
  });

  // Pestañas de Filtro
  filterTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      filterTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      filtroActual = tab.dataset.filter;
      renderizarLicencias();
    });
  });

  // Botones de cerrar modales
  document.querySelectorAll(".btnCloseModal").forEach((btn) => {
    btn.addEventListener("click", cerrarTodosLosModales);
  });

  // Confirmar Regeneración de Clave
  btnConfirmarRegenerar.addEventListener("click", ejecutarRegeneracionClave);

  // Confirmar Desvinculación de PC
  btnConfirmarDesvincular.addEventListener("click", ejecutarDesvinculacionPC);

  // Auto-refresco en segundo plano cada 20 segundos
  setInterval(() => {
    if (sessionStorage.getItem("invima_admin_auth") === "true") {
      cargarLicencias(null, true);
    }
  }, 20000);
}

function mostrarLogin() {
  loginSection.classList.remove("hidden");
  dashboardSection.classList.add("hidden");
  adminPinInput.focus();
}

function mostrarDashboard() {
  loginSection.classList.add("hidden");
  dashboardSection.classList.remove("hidden");
  cargarLicencias();
}


// --------------------------------------------------------------------------
// 2. COMUNICACIÓN CON FIREBASE REALTIME DATABASE
// --------------------------------------------------------------------------
async function cargarLicencias(callback = null, silencioso = false) {
  if (!silencioso) {
    loadingIndicator.classList.remove("hidden");
    licensesContainer.classList.add("hidden");
    emptyState.classList.add("hidden");
  }

  try {
    const res = await fetch(`${FIREBASE_DB_URL}/licencias.json`, {
      method: "GET",
      headers: { "Content-Type": "application/json" }
    });

    if (!res.ok) {
      if (res.status === 401) {
        throw new Error("Permiso denegado (401). Activa las reglas en Firebase Console -> Realtime Database -> Reglas.");
      } else if (res.status === 404) {
        throw new Error("Base de datos no encontrada (404). Verifica la URL del proyecto Firebase.");
      }
      throw new Error(`Error en el servidor (${res.status})`);
    }

    const data = await res.json();
    licenciasData = data || {};

    if (Object.keys(licenciasData).length === 0) {
      console.warn("El nodo licencias está vacío en Firebase.");
    }

    actualizarMetricas();
    renderizarLicencias();

    if (callback) callback();
  } catch (error) {
    console.error("Error al cargar licencias:", error);
    if (!silencioso) {
      mostrarToast(`${error.message}`, "error");
    }
  } finally {
    if (!silencioso) {
      loadingIndicator.classList.add("hidden");
    }
  }
}


// --------------------------------------------------------------------------
// 3. RENDERIZADO Y MÉTRICAS
// --------------------------------------------------------------------------
function obtenerListaLicenciasProcesada() {
  const lista = [];

  for (const [clave, obj] of Object.entries(licenciasData)) {
    if (!obj || typeof obj !== "object") continue;

    const equipos = obj.equipos || {};
    // Filtrar equipos activos
    const equiposActivos = Object.entries(equipos).filter(
      ([_, val]) => val !== false && String(val).toLowerCase() !== "false"
    );

    const estaOcupada = equiposActivos.length > 0;
    const primerEquipo = estaOcupada ? equiposActivos[0] : null;

    lista.push({
      clave: clave,
      empresa: obj.empresa || "Cliente INVIMA",
      vencimiento: obj.vencimiento || "2026-12-31",
      max_equipos: parseInt(obj.max_equipos || 1),
      activa: obj.activa !== false,
      estaOcupada: estaOcupada,
      pcNombre: primerEquipo ? primerEquipo[1] : null,
      hwid: primerEquipo ? primerEquipo[0] : null,
      equiposTotal: equiposActivos.length
    });
  }

  return lista;
}

function actualizarMetricas() {
  const lista = obtenerListaLicenciasProcesada();
  const total = lista.length;
  const ocupadas = lista.filter((l) => l.estaOcupada).length;
  const libres = total - ocupadas;

  statTotal.textContent = total;
  statLibres.textContent = libres;
  statOcupados.textContent = ocupadas;

  badgeCountTodos.textContent = total;
  badgeCountLibres.textContent = libres;
  badgeCountOcupados.textContent = ocupadas;
}

function renderizarLicencias() {
  const lista = obtenerListaLicenciasProcesada();
  licensesContainer.innerHTML = "";

  // Aplicar Filtro de Pestaña
  let filtradas = lista.filter((lic) => {
    if (filtroActual === "libres") return !lic.estaOcupada;
    if (filtroActual === "ocupados") return lic.estaOcupada;
    return true;
  });

  // Aplicar Búsqueda por Texto
  if (terminoBusqueda) {
    filtradas = filtradas.filter((lic) => {
      const matchClave = lic.clave.toLowerCase().includes(terminoBusqueda);
      const matchPc = lic.pcNombre ? String(lic.pcNombre).toLowerCase().includes(terminoBusqueda) : false;
      const matchEmpresa = lic.empresa.toLowerCase().includes(terminoBusqueda);
      return matchClave || matchPc || matchEmpresa;
    });
  }

  if (filtradas.length === 0) {
    licensesContainer.classList.add("hidden");
    emptyState.classList.remove("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  licensesContainer.classList.remove("hidden");

  filtradas.forEach((lic, idx) => {
    const card = document.createElement("div");
    card.className = `license-card glass-panel ${lic.estaOcupada ? "status-used" : "status-free"}`;

    const estadoHtml = lic.estaOcupada
      ? `<span class="status-badge badge-used"><span class="status-dot" style="background:#F59E0B"></span> En Uso</span>`
      : `<span class="status-badge badge-free"><span class="status-dot" style="background:#10B981"></span> Disponible</span>`;

    const detalleEquipoHtml = lic.estaOcupada
      ? `
        <div class="device-details">
          <div class="device-row">
            <span class="device-label">🖥️ Computador:</span>
            <span class="device-value highlight-text">${escapeHtml(String(lic.pcNombre))}</span>
          </div>
          <div class="device-row">
            <span class="device-label">🔑 ID de Hardware:</span>
            <span class="device-value mono" style="font-size:0.75rem;">${escapeHtml(String(lic.hwid))}</span>
          </div>
        </div>
      `
      : `
        <div class="device-details" style="text-align:center; color: var(--emerald); padding: 14px;">
          <span>✅ Cupo libre &bull; Listo para asignarse</span>
        </div>
      `;

    const botonesAccionHtml = lic.estaOcupada
      ? `
        <button class="btn-action btn-regenerate" onclick="abrirModalRegenerar('${lic.clave}', '${escapeHtml(String(lic.pcNombre || 'PC'))}')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
          <span>Expulsar y Cambiar Clave</span>
        </button>
        <button class="btn-action btn-unlink" onclick="abrirModalDesvincular('${lic.clave}', '${escapeHtml(String(lic.pcNombre || 'PC'))}')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/></svg>
          <span>Solo Desvincular</span>
        </button>
      `
      : `
        <button class="btn-action btn-regenerate" style="opacity:0.85;" onclick="abrirModalRegenerar('${lic.clave}', 'Ninguno (Libre)')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
          <span>Regenerar Clave Limpia</span>
        </button>
      `;

    card.innerHTML = `
      <div class="card-top">
        <span class="card-index">PUESTO #${idx + 1}</span>
        ${estadoHtml}
      </div>

      <div class="key-container">
        <span class="key-text">${lic.clave}</span>
        <button class="btn-copy" onclick="copiarAlPortapapeles('${lic.clave}', this)" title="Copiar Clave">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          <span>Copiar</span>
        </button>
      </div>

      ${detalleEquipoHtml}

      <div class="device-row" style="margin-bottom:12px; font-size:0.8rem;">
        <span class="device-label">📅 Vencimiento:</span>
        <span class="device-value">${lic.vencimiento}</span>
      </div>

      <div class="card-actions">
        ${botonesAccionHtml}
      </div>
    `;

    licensesContainer.appendChild(card);
  });
}


// --------------------------------------------------------------------------
// 4. ACCIONES: EXPULSAR / REGENERAR Y DESVINCULAR
// --------------------------------------------------------------------------
function generarNuevaClaveAleatoria() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // Sin 0, O, 1, I
  let b1 = "", b2 = "";
  for (let i = 0; i < 4; i++) b1 += chars.charAt(Math.floor(Math.random() * chars.length));
  for (let i = 0; i < 4; i++) b2 += chars.charAt(Math.floor(Math.random() * chars.length));
  return `INVIMA-2026-${b1}-${b2}`;
}

window.abrirModalRegenerar = function (clave, pcNombre) {
  licenciaEnAccion = clave;
  modalOldKey.textContent = clave;
  modalPcName.textContent = pcNombre;
  modalRegenerar.classList.remove("hidden");
};

window.abrirModalDesvincular = function (clave, pcNombre) {
  licenciaEnAccion = clave;
  modalDesvincularKey.textContent = clave;
  modalDesvincularPc.textContent = pcNombre;
  modalDesvincular.classList.remove("hidden");
};

function cerrarTodosLosModales() {
  modalRegenerar.classList.add("hidden");
  modalDesvincular.classList.add("hidden");
  licenciaEnAccion = null;
}

// 🔄 Ejecutar Regeneración 1 a 1 (Eliminar clave vieja -> Crear clave nueva limpia)
async function ejecutarRegeneracionClave() {
  if (!licenciaEnAccion || !licenciasData[licenciaEnAccion]) return;

  const claveAntigua = licenciaEnAccion;
  const datosAntiguos = licenciasData[claveAntigua];
  const claveNueva = generarNuevaClaveAleatoria();

  btnConfirmarRegenerar.disabled = true;
  btnConfirmarRegenerar.textContent = "Cambiando código...";

  try {
    // 1. Crear nueva clave limpia en Firebase (con 0 equipos y max_equipos = 1)
    const nuevoObjeto = {
      activa: true,
      empresa: datosAntiguos.empresa || "Cliente INVIMA",
      max_equipos: 1,
      vencimiento: datosAntiguos.vencimiento || "2026-12-31",
      equipos: {}
    };

    const resPut = await fetch(`${FIREBASE_DB_URL}/licencias/${claveNueva}.json`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(nuevoObjeto)
    });

    if (!resPut.ok) throw new Error("No se pudo crear la nueva clave en la nube.");

    // 2. Destruir la clave antigua en Firebase
    const resDel = await fetch(`${FIREBASE_DB_URL}/licencias/${claveAntigua}.json`, {
      method: "DELETE"
    });

    if (!resDel.ok) throw new Error("No se pudo eliminar la clave anterior.");

    cerrarTodosLosModales();
    mostrarToast(`¡Código cambiado exitosamente! Nueva Clave: ${claveNueva}`, "success");
    cargarLicencias();
  } catch (error) {
    mostrarToast(`Error al regenerar: ${error.message}`, "error");
  } finally {
    btnConfirmarRegenerar.disabled = false;
    btnConfirmarRegenerar.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
      <span>Confirmar y Cambiar Clave</span>
    `;
  }
}

// 🔌 Solo Desvincular PC (Mantiene la misma clave)
async function ejecutarDesvinculacionPC() {
  if (!licenciaEnAccion) return;

  const clave = licenciaEnAccion;
  btnConfirmarDesvincular.disabled = true;
  btnConfirmarDesvincular.textContent = "Desvinculando...";

  try {
    const res = await fetch(`${FIREBASE_DB_URL}/licencias/${clave}/equipos.json`, {
      method: "DELETE"
    });

    if (!res.ok) throw new Error("Error al desvincular el equipo en Firebase.");

    cerrarTodosLosModales();
    mostrarToast(`Equipo desvinculado. La clave ${clave} quedó libre.`, "success");
    cargarLicencias();
  } catch (error) {
    mostrarToast(`Error al desvincular: ${error.message}`, "error");
  } finally {
    btnConfirmarDesvincular.disabled = false;
    btnConfirmarDesvincular.textContent = "Desvincular Equipo";
  }
}


// --------------------------------------------------------------------------
// 5. UTILIDADES & NOTIFICACIONES (TOASTS)
// --------------------------------------------------------------------------
window.copiarAlPortapapeles = function (texto, btnElement) {
  navigator.clipboard.writeText(texto).then(() => {
    const spanOriginal = btnElement.querySelector("span");
    const textoOriginal = spanOriginal ? spanOriginal.textContent : "";
    if (spanOriginal) spanOriginal.textContent = "¡Copiada!";
    btnElement.style.background = "#10B981";
    btnElement.style.borderColor = "#10B981";
    btnElement.style.color = "#FFF";

    mostrarToast(`Clave ${texto} copiada al portapapeles.`, "success");

    setTimeout(() => {
      if (spanOriginal) spanOriginal.textContent = textoOriginal;
      btnElement.style.background = "";
      btnElement.style.borderColor = "";
      btnElement.style.color = "";
    }, 1800);
  }).catch(() => {
    mostrarToast("No se pudo copiar automáticamente.", "error");
  });
};

function mostrarToast(mensaje, tipo = "info") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${tipo}`;

  const iconSvg = tipo === "success"
    ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>`
    : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

  toast.innerHTML = `${iconSvg}<span>${escapeHtml(mensaje)}</span>`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.25s ease-out";
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
