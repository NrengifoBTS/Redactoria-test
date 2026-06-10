import React, { useState } from "react";
import { useApp } from "./context/AppContext";
import { Mail, Lock, Eye, EyeOff, AlertTriangle, ShieldAlert, X, ArrowRight } from "lucide-react";
import "./Loginmodal.css";

function LoginModal({ isOpen, onClose }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [errorKind, setErrorKind] = useState("error"); // 'error' | 'warning'
  const [loading, setLoading] = useState(false);

  const { login } = useApp();

  if (!isOpen) return null;

  const fail = (message, kind = "error") => {
    setError(message);
    setErrorKind(kind);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!email || !password) {
      fail("Ingresa tu correo y contraseña.");
      return;
    }

    setLoading(true);
    try {
      const result = await login({ username: email, password });
      setLoading(false);

      if (result.success) {
        setEmail("");
        setPassword("");
        setError("");
        onClose();
      } else {
        // 403 = cuenta desactivada → aviso (ámbar). Resto → error (rojo).
        fail(
          result.error || "No se pudo iniciar sesión.",
          result.status === 403 ? "warning" : "error",
        );
      }
    } catch (err) {
      setLoading(false);
      fail("Ocurrió un error. Intenta de nuevo.");
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-contentlp">
        <button className="modal-close" onClick={onClose} aria-label="Cerrar">
          <X size={18} />
        </button>

        <div className="login-modal-card">
          <div className="login-modal-header">
            <div className="login-modal-avatar">
              <Lock strokeWidth={1.75} />
            </div>
            <h1 className="login-modal-title">Iniciar sesión</h1>
            <p className="login-modal-subtitle">Accede a tu cuenta para continuar</p>
          </div>

          <form onSubmit={handleSubmit} className="login-modal-form" noValidate>
            {/* Correo */}
            <div className="modal-form-group">
              <label className="modal-form-label" htmlFor="login-email">
                Correo electrónico
              </label>
              <div className="modal-input-wrapper">
                <span className="modal-input-icon">
                  <Mail />
                </span>
                <input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="modal-form-input"
                  placeholder="tucorreo@ejemplo.com"
                />
              </div>
            </div>

            {/* Contraseña */}
            <div className="modal-form-group">
              <label className="modal-form-label" htmlFor="login-password">
                Contraseña
              </label>
              <div className="modal-input-wrapper">
                <span className="modal-input-icon">
                  <Lock />
                </span>
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="modal-form-input has-toggle"
                  placeholder="Tu contraseña"
                />
                <button
                  type="button"
                  className="modal-input-toggle"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Mensaje de error / aviso */}
            {error && (
              <div
                className={`modal-error-message ${errorKind === "warning" ? "is-warning" : "is-error"}`}
                role="alert"
              >
                <span className="modal-error-icon">
                  {errorKind === "warning" ? <ShieldAlert /> : <AlertTriangle />}
                </span>
                <p className="modal-error-text">{error}</p>
              </div>
            )}

            {/* Botón */}
            <button type="submit" disabled={loading} className="login-modal-button">
              {loading ? (
                <span className="modal-loading-spinner">
                  <span className="modal-spinner" />
                  Ingresando...
                </span>
              ) : (
                <span className="login-modal-button-label">
                  Iniciar sesión
                  <ArrowRight size={18} />
                </span>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default LoginModal;
