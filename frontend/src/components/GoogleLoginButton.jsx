import { GoogleLogin } from '@react-oauth/google';
import { googleLogin } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';

const GOOGLE_CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID || '').trim();

export default function GoogleLoginButton() {
  const { loginUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');

  if (!GOOGLE_CLIENT_ID) {
    return null;
  }

  const handleSuccess = async (credentialResponse) => {
    setError('');
    try {
      const res = await googleLogin(credentialResponse.credential);
      const { tokens, usuario } = res.data;

      localStorage.setItem('access_token', tokens.access);
      localStorage.setItem('refresh_token', tokens.refresh);
      loginUser(tokens, usuario);
      navigate('/');
    } catch (err) {
      setError(
        err.response?.data?.error || 'Error al iniciar sesión con Google.'
      );
    }
  };

  return (
    <div style={{ width: '100%' }}>
      {error && (
        <div className="alert alert-error" style={{ marginBottom: '0.75rem', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <GoogleLogin
          onSuccess={handleSuccess}
          onError={() => setError(
            'No se pudo conectar con Google. Tu proveedor de internet puede estar ' +
            'bloqueándolo. Probá con tu usuario y contraseña más abajo, o activá un VPN.'
          )}
          text="signin_with"
          shape="rectangular"
          width="300"
          locale="es"
        />
      </div>
    </div>
  );
}
