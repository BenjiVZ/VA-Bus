import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import CedulaAlert from './components/CedulaAlert';
import ReservaPendienteAlert from './components/ReservaPendienteAlert';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ViajesPage from './pages/ViajesPage';
import AsientosPage from './pages/AsientosPage';
import ConfirmacionPage from './pages/ConfirmacionPage';
import MisReservasPage from './pages/MisReservasPage';
import PagoPage from './pages/PagoPage';
import AdminPanelPage from './pages/AdminPanelPage';
import AdminViajePage from './pages/AdminViajePage';
import AdminBusesPage from './pages/AdminBusesPage';
import AdminComprobantesPage from './pages/AdminComprobantesPage';
import AdminClientesPage from './pages/AdminClientesPage';
import PerfilPage from './pages/PerfilPage';
import TicketPage from './pages/TicketPage';
import NosotrosPage from './pages/NosotrosPage';
import VerificarPage from './pages/VerificarPage';
import VerificarEmailPage from './pages/VerificarEmailPage';
import RecuperarPasswordPage from './pages/RecuperarPasswordPage';
import './styles/PerfilPage.css';
import ChatBot from './components/ChatBot';
import ScrollToTop from './components/ScrollToTop';
import TickerBar from './components/TickerBar';
import BackendStatusBanner from './components/BackendStatusBanner';

const GOOGLE_CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID || '').trim();

function App() {
  const appContent = (
    <AuthProvider>
      <BrowserRouter>
        <BackendStatusBanner />
        <ScrollToTop />
        <div className="sticky-header">
          <Navbar />
          <CedulaAlert />
          <ReservaPendienteAlert />
        </div>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/registro" element={<RegisterPage />} />
          <Route path="/verificar-email" element={<VerificarEmailPage />} />
          <Route path="/recuperar-password" element={<RecuperarPasswordPage />} />
          <Route path="/viajes" element={<ViajesPage />} />
          <Route path="/nosotros" element={<NosotrosPage />} />
          <Route path="/viajes/:id/asientos" element={<AsientosPage />} />
          <Route path="/pago" element={<PagoPage />} />
          <Route path="/reserva/confirmacion" element={<ConfirmacionPage />} />
          <Route path="/mis-reservas" element={<MisReservasPage />} />
          <Route path="/perfil" element={<PerfilPage />} />
          <Route path="/ticket/:grupoPago" element={<TicketPage />} />
          <Route path="/verificar/:codigoTicket" element={<VerificarPage />} />
          {/* Admin */}
          <Route path="/admin/panel" element={<AdminPanelPage />} />
          <Route path="/admin/viajes/:id" element={<AdminViajePage />} />
          <Route path="/admin/buses" element={<AdminBusesPage />} />
          <Route path="/admin/comprobantes" element={<AdminComprobantesPage />} />
          <Route path="/admin/clientes" element={<AdminClientesPage />} />
        </Routes>
        <ChatBot />
        <TickerBar />
        <Footer />
      </BrowserRouter>
    </AuthProvider>
  );

  if (!GOOGLE_CLIENT_ID) {
    return appContent;
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      {appContent}
    </GoogleOAuthProvider>
  );
}

export default App;
