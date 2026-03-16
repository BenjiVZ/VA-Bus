import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
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

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Navbar />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/registro" element={<RegisterPage />} />
          <Route path="/viajes" element={<ViajesPage />} />
          <Route path="/viajes/:id/asientos" element={<AsientosPage />} />
          <Route path="/pago" element={<PagoPage />} />
          <Route path="/reserva/confirmacion" element={<ConfirmacionPage />} />
          <Route path="/mis-reservas" element={<MisReservasPage />} />
          {/* Admin */}
          <Route path="/admin/panel" element={<AdminPanelPage />} />
          <Route path="/admin/viajes/:id" element={<AdminViajePage />} />
          <Route path="/admin/buses" element={<AdminBusesPage />} />
          <Route path="/admin/comprobantes" element={<AdminComprobantesPage />} />
        </Routes>
        <Footer />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
