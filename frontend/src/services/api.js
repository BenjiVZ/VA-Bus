import axios from 'axios';

// Resuelve la URL del backend según dónde se sirva el frontend.
// Prioridad:
//   1. VITE_API_URL (override explícito en .env)
//   2. Dominio masterslogic: 5001.masterslogic.com  ->  https://5002.masterslogic.com/api
//   3. Local / IP de red:    localhost:5001          ->  http://<host>:5002/api
// El backend (Django/daphne) corre en el puerto 5002 (ver ejecutar.bat).
function resolveBackendUrl() {
  const fromEnv = import.meta.env.VITE_API_URL;
  if (fromEnv) return fromEnv.replace(/\/+$/, '');

  if (typeof window !== 'undefined' && window.location) {
    const { protocol, hostname } = window.location;
    if (hostname.endsWith('.masterslogic.com')) {
      return `${protocol}//5002.masterslogic.com/api`;
    }
    return `http://${hostname}:5002/api`;
  }
  return 'http://localhost:5002/api';
}

export const API_URL = resolveBackendUrl();
const API_ORIGIN = API_URL.endsWith('/api') ? API_URL.slice(0, -4) : API_URL;

export const resolveApiFileUrl = (path = '') => {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_ORIGIN}${normalizedPath}`;
};

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Avisar al resto de la app si el backend está accesible o no.
const emitBackendStatus = (online) => {
  window.dispatchEvent(new CustomEvent('backend-status', { detail: { online } }));
};

// Handle token refresh
api.interceptors.response.use(
  (response) => {
    // Hubo respuesta del servidor => está en línea.
    emitBackendStatus(true);
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Sin `error.response` = no se pudo contactar al backend
    // (servidor caído, sin red, CORS, DNS...). No aplica a peticiones canceladas.
    const peticionCancelada = error.code === 'ERR_CANCELED' || error.name === 'CanceledError';
    if (!error.response && !peticionCancelada) {
      emitBackendStatus(false);
    } else if (error.response) {
      // El servidor respondió (aunque sea un 4xx/5xx): sigue en línea.
      emitBackendStatus(true);
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/auth/refresh/`, {
            refresh: refreshToken,
          });
          const { access } = response.data;
          localStorage.setItem('access_token', access);
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const login = (username, password) =>
  api.post('/auth/login/', { username, password });

export const googleLogin = (credential) =>
  api.post('/auth/google-login/', { credential });

export const registro = (data) =>
  api.post('/auth/registro/', data);

export const getPerfil = () =>
  api.get('/auth/perfil/');

export const actualizarPerfil = (data) =>
  api.put('/auth/perfil/', data);

export const cambiarPassword = (data) =>
  api.post('/auth/cambiar-password/', data);

// Verificación de email
export const verificarEmail = (email, codigo) =>
  api.post('/auth/verificar-email/', { email, codigo });

export const reenviarCodigo = (email) =>
  api.post('/auth/reenviar-codigo/', { email });

// Recuperar contraseña
export const solicitarResetPassword = (email) =>
  api.post('/auth/recuperar-password/', { email });

export const resetPassword = (email, codigo, new_password, new_password2) =>
  api.post('/auth/reset-password/', { email, codigo, new_password, new_password2 });

// Viajes
export const getRutas = () =>
  api.get('/rutas/');

export const getOficinas = () =>
  api.get('/oficinas/');

// ── Aerorutas (consulta en vivo del sistema de control) ──
export const getAerorutasOficinas = () =>
  api.get('/aerorutas/oficinas/');

export const getAerorutasRutas = (inicio, fin, fecha) =>
  api.get('/aerorutas/rutas/', { params: { inicio, fin, fecha } });

export const getAerorutasPuestos = (codofi, codrut, fecha) =>
  api.get('/aerorutas/puestos/', { params: { codofi, codrut, fecha } });

export const getStats = () =>
  api.get('/stats/');

// Búsqueda y asientos ahora salen del adaptador de Aerorutas (data en vivo,
// transformada por el backend al mismo formato que /viajes/).
export const buscarViajes = (params) =>
  api.get('/aerorutas/viajes/', { params });

export const getViaje = (id) =>
  api.get(`/viajes/${id}/`);

export const getAsientos = (viajeId) =>
  api.get(`/aerorutas/viajes/${viajeId}/asientos/`);

// Reservas
export const crearReserva = (data) =>
  api.post('/reservas/', data);

export const subirDocumentosMenor = (reservaId, formData) =>
  api.post(`/reservas/${reservaId}/documentos-menor/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const subirDocVacunacion = (reservaId, formData) =>
  api.post(`/reservas/${reservaId}/doc-vacunacion/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const subirDocDiscapacidad = (reservaId, formData) =>
  api.post(`/reservas/${reservaId}/doc-discapacidad/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const bloquearAsiento = (viajeId, numeroAsiento, pisoAsiento = 1) =>
  api.post('/reservas/bloquear-asiento/', {
    viaje_id: viajeId,
    numero_asiento: numeroAsiento,
    piso_asiento: pisoAsiento,
  });

export const liberarAsiento = (viajeId, numeroAsiento, pisoAsiento = 1) =>
  api.post('/reservas/liberar-asiento/', {
    viaje_id: viajeId,
    numero_asiento: numeroAsiento,
    piso_asiento: pisoAsiento,
  });

export const getMisReservas = () =>
  api.get('/mis-reservas/');

// Config
export const getTasaCambio = () =>
  api.get('/tasa-cambio/');

export const getConfiguracion = () =>
  api.get('/configuracion/');

// Admin
export const adminGetViajes = () =>
  api.get('/admin/viajes/');

export const adminGetReservas = (viajeId) =>
  api.get(`/admin/viajes/${viajeId}/reservas/`);

export const adminCambiarEstado = (reservaId, estado) =>
  api.patch(`/admin/reservas/${reservaId}/estado/`, { estado });

export const adminCambiarAsiento = (reservaId, numero_asiento, piso_asiento) =>
  api.patch(`/admin/reservas/${reservaId}/asiento/`, { numero_asiento, piso_asiento });

export const adminGetBuses = () =>
  api.get('/admin/buses/');

// Pagos
export const getMetodosPago = () =>
  api.get('/metodos-pago/');

export const crearComprobante = (formData) =>
  api.post('/comprobantes/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const getEstadoComprobante = (grupoPago) =>
  api.get(`/comprobantes/${grupoPago}/`);

// ── R4 Conecta — Cobro Inmediato (Débito con OTP) ──
// Lista centralizada de bancos (fuente única backend).
export const getBancos = () =>
  api.get('/r4/bancos/');

// Paso 1: el banco envía un OTP al teléfono del cliente.
export const r4GenerarOtp = (data) =>
  api.post('/r4/debito/generar-otp/', data);

// Paso 2: confirmar con el OTP (+ comprobante opcional vía FormData).
export const r4ConfirmarDebito = (formData) =>
  api.post('/r4/debito/confirmar/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

// Estado de la operación (para polling mientras queda "en espera").
export const r4EstadoOperacion = (operacionId) =>
  api.get(`/r4/debito/${operacionId}/`);

export const adminGetComprobantes = (estado) =>
  api.get('/admin/comprobantes/', { params: estado ? { estado } : {} });

export const adminValidarComprobante = (comprobanteId, estado, nota = '') =>
  api.patch(`/admin/comprobantes/${comprobanteId}/validar/`, { estado, nota });

// Tickets
export const getTicket = (grupoPago) =>
  api.get(`/ticket/${grupoPago}/`);

export const verificarTicket = (codigoTicket) =>
  api.get(`/verificar/${codigoTicket}/`);

// Admin — Clientes
export const adminGetClientesDashboard = () =>
  api.get('/auth/admin/clientes/dashboard/');

export const adminGetClientes = (query = '') =>
  api.get('/auth/admin/clientes/', { params: query ? { q: query } : {} });

export const adminToggleVip = (userId, data) =>
  api.patch(`/auth/admin/clientes/${userId}/vip/`, data);

export default api;
