//redactoria/fronted/auth-app/src/app.js
import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import Login from "./Login";
import ProtectedPage from "./Protected";
import Redactor from "./Redactor";
import Dashboard from "./Dashboard";
import Home from "./Home";
import { AppProvider } from "./context/AppContext";
import BlogGeneracion from "./Blog_Generacion";
import Dashboard_Blog from "./Dashboard_Blog";
import BlogMetrics from "./BlogMetrics";
import Analytics from "./Analytics";
import UserManagement from "./UserManagement";
import RequireRole from "./RequireRole";

function App() {
  return (
    <AppProvider>
      <Router>
        <Routes>
          {/* Públicas */}
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/protected" element={<ProtectedPage />} />

          {/* Requieren sesión (cualquier rol; el backend escopa el contenido) */}
          <Route
            path="/redactor/:lpId"
            element={
              <RequireRole min="auth">
                <Redactor />
              </RequireRole>
            }
          />
          <Route
            path="/dashboard"
            element={
              <RequireRole min="auth">
                <Dashboard />
              </RequireRole>
            }
          />
          <Route
            path="/dashboard/:proyecto"
            element={
              <RequireRole min="auth">
                <Dashboard />
              </RequireRole>
            }
          />
          <Route
            path="/dashboard_blog"
            element={
              <RequireRole min="auth">
                <Dashboard_Blog />
              </RequireRole>
            }
          />
          <Route
            path="/blog/edit/:blogId"
            element={
              <RequireRole min="auth">
                <BlogGeneracion />
              </RequireRole>
            }
          />
          <Route
            path="/blog_metrics"
            element={
              <RequireRole min="auth">
                <BlogMetrics />
              </RequireRole>
            }
          />

          {/* Solo admin/master */}
          <Route
            path="/analytics"
            element={
              <RequireRole min="admin">
                <Analytics />
              </RequireRole>
            }
          />

          {/* Solo master */}
          <Route
            path="/usuarios"
            element={
              <RequireRole min="master">
                <UserManagement />
              </RequireRole>
            }
          />

          <Route path="*" element={<div>404 Not Found</div>} />
        </Routes>
      </Router>
    </AppProvider>
  );
}

export default App;
