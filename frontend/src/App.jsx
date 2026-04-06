import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import CedulaAlert from './components/CedulaAlert';
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
import PerfilPage from './pages/PerfilPage';
import TicketPage from './pages/TicketPage';
import VerificarPage from './pages/VerificarPage';
import VerificarEmailPage from './pages/VerificarEmailPage';
import RecuperarPasswordPage from './pages/RecuperarPasswordPage';
import './styles/PerfilPage.css';

const GOOGLE_CLIENT_ID = '941001553573-u64s6mjms1jtlk0v5agsrk5qq6bbvoat.apps.googleusercontent.com';

function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
    <AuthProvider>
      <BrowserRouter>
        <Navbar />
        <CedulaAlert />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/registro" element={<RegisterPage />} />
          <Route path="/verificar-email" element={<VerificarEmailPage />} />
          <Route path="/recuperar-password" element={<RecuperarPasswordPage />} />
          <Route path="/viajes" element={<ViajesPage />} />
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
        </Routes>
        <Footer />
      </BrowserRouter>
    </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
