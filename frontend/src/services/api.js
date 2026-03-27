import axios from 'axios';

const API_URL = 'http://localhost:8001/api';

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

// Handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
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

export const registro = (data) =>
  api.post('/auth/registro/', data);

export const getPerfil = () =>
  api.get('/auth/perfil/');

export const actualizarPerfil = (data) =>
  api.put('/auth/perfil/', data);

export const cambiarPassword = (data) =>
  api.post('/auth/cambiar-password/', data);

// Viajes
export const getRutas = () =>
  api.get('/rutas/');

export const buscarViajes = (params) =>
  api.get('/viajes/', { params });

export const getViaje = (id) =>
  api.get(`/viajes/${id}/`);

export const getAsientos = (viajeId) =>
  api.get(`/viajes/${viajeId}/asientos/`);

// Reservas
export const crearReserva = (data) =>
  api.post('/reservas/', data);

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

export const adminGetComprobantes = (estado) =>
  api.get('/admin/comprobantes/', { params: estado ? { estado } : {} });

export const adminValidarComprobante = (comprobanteId, estado, nota = '') =>
  api.patch(`/admin/comprobantes/${comprobanteId}/validar/`, { estado, nota });

// Tickets
export const getTicket = (grupoPago) =>
  api.get(`/ticket/${grupoPago}/`);

export const verificarTicket = (codigoTicket) =>
  api.get(`/verificar/${codigoTicket}/`);

export default api;
