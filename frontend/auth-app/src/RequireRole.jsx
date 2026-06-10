import React from "react";
import { Navigate } from "react-router-dom";
import { useApp } from "./context/AppContext";
import { isAdminUser, isMaster } from "./utils/roles";

// Guard de ruta por rol. Envuelve el elemento de una <Route>.
//   min="auth"   → requiere sesión (cualquier rol)
//   min="admin"  → admin o master
//   min="master" → solo master
// La fuente de verdad del rol es currentUser.role (de /users/me), igual que el backend.
const RequireRole = ({ min = "auth", children }) => {
  const { currentUser, loading } = useApp();

  // Mientras se resuelve la sesión no decidimos nada (evita rebotes en falso).
  if (loading) return null;

  // Sin sesión → al landing público (que tiene el login).
  if (!currentUser) return <Navigate to="/home" replace />;

  const allowed =
    min === "auth" ||
    (min === "admin" && isAdminUser(currentUser)) ||
    (min === "master" && isMaster(currentUser));

  // Autenticado pero sin rol suficiente → a su área principal.
  if (!allowed) return <Navigate to="/dashboard" replace />;

  return children;
};

export default RequireRole;
