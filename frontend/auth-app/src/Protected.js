import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";

function ProtectedPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const verifyAccess = async () => {
      const token = localStorage.getItem("token");
      const API_BASE =
        process.env.REACT_APP_API_URL || "http://192.168.1.129:8080";

      try {
        // Obtenemos el usuario actual (incluye su rol) para decidir el acceso.
        const response = await fetch(`${API_BASE}/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          throw new Error("Token verification failed");
        }

        const user = await response.json();

        // El dashboard protegido es solo para administradores.
        if (user.role !== "admin") {
          navigate("/Redactor");
        }
      } catch (error) {
        // Si hay error con el token (inválido/expirado), va al login
        localStorage.removeItem("token");
        navigate("/login");
      }
    };

    verifyAccess();
  }, [navigate]);

  // Dashboard para usuarios autorizados (temporal)
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Dashboard</h1>
        <p className="text-gray-600">
          Bienvenido al dashboard. Solo usuarios autorizados pueden ver esto.
        </p>
        <p className="text-sm text-gray-500 mt-4">
          Próximamente: funcionalidades del dashboard...
        </p>
      </div>
    </div>
  );
}

export default ProtectedPage;
