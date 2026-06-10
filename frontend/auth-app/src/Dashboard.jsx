import React, { useState, useMemo, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Search,
  Plus,
  Edit3,
  Eye,
  Trash2,
  CheckCircle2,
  Clock,
  AlertCircle,
  UserPlus,
  FileText,
  AlertTriangle,
  ThumbsUp,
  Hash,
  Upload,
  TestTube,
  BarChart3,
  Home,
  Users,
  ChevronRight,
  Globe,
} from "lucide-react";
import milesLogo from "./img/Miles-car-rental.png";
import viajemosLogo from "./img/logo-viajemos.png";

// Importar hooks personalizados
import {
  useProyectos,
  useCurrentUser,
  useUsers,
  useFilters,
  useSearch,
} from "./hooks/useApi.js";
import apiService from "./services/apiService.js";
import { isAdminUser, canManageUsers, roleLabel } from "./utils/roles";
import { getDominiosPorMarca } from "./data/dominios";

// Logo local por marca (solo las dos marcas activas)
const BRAND_LOGOS = {
  mcr: milesLogo,
  viajemos: viajemosLogo,
};

// Configuración de temas por proyecto
const PROJECT_THEMES = {
  viajemos: {
    name: "Viajemos",
    primary: "#0583FF",
    primaryHover: "#0583FF",
    primaryLight: "#dbeafe",
    secondary: "#0583FF",
    accent: "#60a5fa",
  },
  mcr: {
    name: "Miles Car Rental",
    primary: "#E6484B",
    primaryHover: "#E6484B",
    primaryLight: "#fee2e2",
    secondary: "#E6484B",
    accent: "#f87171",
  },
  outlet: {
    name: "Outlet Rental Cars",
    primary: "#f59e0b",
    primaryHover: "#d97706",
    primaryLight: "#fef3c7",
    secondary: "#b45309",
    accent: "#fbbf24",
  },
  guialegal: {
    name: "Guía Legal",
    primary: "#8b5cf6",
    primaryHover: "#7c3aed",
    primaryLight: "#ede9fe",
    secondary: "#6d28d9",
    accent: "#a78bfa",
  },
  arriendo: {
    name: "Arriendo",
    primary: "#ef4444",
    primaryHover: "#dc2626",
    primaryLight: "#fee2e2",
    secondary: "#b91c1c",
    accent: "#f87171",
  },
  default: {
    name: "Todos los Proyectos",
    primary: "#1e5fd6",
    primaryHover: "#1a52ba",
    primaryLight: "#dde8fb",
    secondary: "#164497",
    accent: "#1e5fd6",
  },
};

const filterFunctions = {
  domain: (proyecto, value) => {
    if (value === "all") return true;
    return proyecto.domain === value;
  },
  status: (proyecto, value) => value === "all" || proyecto.status === value,
  priority: (proyecto, value) => value === "all" || proyecto.priority === value,
  assignee: (proyecto, value) => {
    if (value === "all") return true;
    if (value === "unassigned") return !proyecto.assignedTo;
    return proyecto.assignedTo === value;
  },
  date: (proyecto, value) => {
    if (value === "all") return true;
    const now = new Date();
    const proyectoDate = new Date(proyecto.lastModified);
    const diffTime = now - proyectoDate;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    switch (value) {
      case "today":
        return diffDays <= 1;
      case "week":
        return diffDays <= 7;
      case "month":
        return diffDays <= 30;
      default:
        return true;
    }
  },
};

const SEARCH_FIELDS = ["name", "description"];

function Dashboard() {
  const navigate = useNavigate();
  const { proyecto } = useParams(); // Obtener proyecto de la URL

  // Determinar el tema basado en el proyecto
  const currentTheme = PROJECT_THEMES[proyecto] || PROJECT_THEMES.default;
  const isFilteredByProject = !!proyecto;

  // Estados usando hooks personalizados
  const { user: currentUser, loading: loadingUser } = useCurrentUser();
  const { users } = useUsers(true);
  const {
    proyectos,
    loading: loadingProyectos,
    createProyecto,
    updateProyecto,
    deleteProyecto,
    assignProyecto,
  } = useProyectos();

  // Cargar templates para poder filtrar por proyecto
  const [templates, setTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        setLoadingTemplates(true);
        // Usar endpoint que devuelve todos los templates (activos e inactivos) para filtrar proyectos
        const response = await fetch(
          `${process.env.REACT_APP_API_URL || "http://192.168.1.129:8080"}/templates/public/all-for-analytics`,
        );
        if (response.ok) {
          const templatesData = await response.json();
          setTemplates(templatesData);
        }
      } catch (error) {
        console.error("Error cargando templates:", error);
      } finally {
        setLoadingTemplates(false);
      }
    };

    loadTemplates();
  }, []);

  // Estados locales para modales
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedProyecto, setSelectedProyecto] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingProyecto, setEditingProyecto] = useState(null);

  const getFilteredUsers = () => {
    if (!users || !currentUser) return [];

    if (isAdminUser(currentUser)) {
      return users;
    } else {
      return users.filter((user) => user.id === currentUser.id);
    }
  };

  const canAssignUsers = () => isAdminUser(currentUser);

  const canCreateProjects = () => isAdminUser(currentUser);

  const canDeleteProjects = () => isAdminUser(currentUser);

  const getAllUsers = () => {
    return users || [];
  };

  // Filtrar proyectos por el parámetro de URL si existe
  const proyectosFiltrados = useMemo(() => {
    if (!isFilteredByProject) {
      return proyectos;
    }

    if (loadingTemplates) {
      return [];
    }

    const filtered = proyectos.filter((p) => {
      // Buscar el template asociado al proyecto
      const template = templates.find((t) => t.id === p.templateId);

      if (!template) {
        return false;
      }

      return template.proyecto === proyecto;
    });

    return filtered;
  }, [proyectos, proyecto, isFilteredByProject, templates, loadingTemplates]);

  // Filtros y búsqueda

  const {
    filters,
    filteredData: filteredByFilters,
    updateFilter,
  } = useFilters(proyectosFiltrados, filterFunctions);
  const { searchTerm, setSearchTerm, searchResults } = useSearch(
    filteredByFilters,
    SEARCH_FIELDS,
  );

  const sortByLastModifiedDesc = (list) =>
    [...list].sort((a, b) => {
      const dateA = a.lastModified ? new Date(a.lastModified) : new Date(0);
      const dateB = b.lastModified ? new Date(b.lastModified) : new Date(0);
      return dateB - dateA;
    });

  // Proyectos visibles según permisos del usuario
  const visibleProyectos = useMemo(() => {
    if (!currentUser) {
      return [];
    }

    if (isAdminUser(currentUser)) {
      return sortByLastModifiedDesc(searchResults);
    }

    if (currentUser.role === "editor") {
      return sortByLastModifiedDesc(
        searchResults.filter(
          (proyecto) =>
            proyecto.assignedTo === currentUser.id ||
            proyecto.assignedTo === null ||
            proyecto.createdBy === currentUser.id,
        ),
      );
    }

    return sortByLastModifiedDesc(
      searchResults.filter(
        (proyecto) =>
          proyecto.assignedTo === currentUser.id ||
          proyecto.createdBy === currentUser.id,
      ),
    );
  }, [searchResults, currentUser]);

  // Estadísticas calculadas
  const stats = useMemo(() => {
    const total = visibleProyectos.length;
    const completed = visibleProyectos.filter(
      (p) => p.status === "completed",
    ).length;
    // "En Proceso" = proyectos en redacción activa (status in_progress),
    // no todo lo que aún no está publicado.
    const nonCompleted = visibleProyectos.filter(
      (p) => p.status === "in_progress",
    ).length;
    const unassigned = visibleProyectos.filter((p) => !p.assignedTo).length;

    return { total, completed, nonCompleted, unassigned };
  }, [visibleProyectos]);

  // Funciones auxiliares
  const getStatusColor = (status) => {
    const colors = {
      // Estados existentes
      completed: "#10b981",
      in_progress: "#3b82f6",
      review: "#8b5cf6",
      draft: "#6b7280",
      pen_review: "#f59e0b",
      pen_ajuste: "#ef4444",
      ajuste_aplicado: "#8044ef",
      approved: "#059669",
      rev_kws: "#E3AAAA",
      cargue: "#0ea5e9",
      en_it: "#6366f1",
      test: "#f97316",
    };
    return colors[status] || "#6b7280";
  };

  const getStatusIcon = (status) => {
    const icons = {
      // Estados existentes
      completed: <CheckCircle2 size={16} />,
      in_progress: <Clock size={16} />,
      review: <Eye size={16} />,
      draft: <Edit3 size={16} />,
      pen_review: <FileText size={16} />,
      pen_ajuste: <AlertTriangle size={16} />,
      ajuste_aplicado: <AlertTriangle size={16} />,
      approved: <ThumbsUp size={16} />,
      rev_kws: <Hash size={16} />,
      cargue: <Upload size={16} />,
      en_it: <Clock size={16} />,
      test: <TestTube size={16} />,
    };
    return icons[status] || <Clock size={16} />;
  };

  const getStatusText = (status) => {
    const texts = {
      draft: "Borrador",
      review: "Pendiente de Redacción",
      in_progress: "En Redacción",
      pen_review: "Pendiente de Revisión",
      pen_ajuste: "Pendiente de Ajuste",
      ajuste_aplicado: "Ajuste Aplicado",
      approved: "Aprobado",
      rev_kws: "Pendiente KWS",
      cargue: "Cargue",
      en_it: "En IT",
      test: "Test",
      completed: "Publicado",
    };
    return texts[status] || status;
  };

  const getPriorityColor = (priority) => {
    const colors = {
      high: "#ef4444",
      medium: "#f59e0b",
      low: "#10b981",
    };
    return colors[priority] || "#6b7280";
  };

  const canEdit = (proyecto) => {
    if (isAdminUser(currentUser)) {
      return true;
    }

    return (
      proyecto.assignedTo === currentUser?.id ||
      proyecto.createdBy === currentUser?.id
    );
  };

  const handleCreateProyecto = async (formData) => {
    try {
      await createProyecto(formData);
      setShowCreateModal(false);
    } catch (error) {
      alert("Error al crear el proyecto: " + error.message);
    }
  };

  const handleAssignProyecto = async (proyectoId, userId) => {
    try {
      await assignProyecto(proyectoId, userId);
      setShowAssignModal(false);
    } catch (error) {
      alert("Error al asignar usuario: " + error.message);
    }
  };

  const handleEditProyecto = async (formData) => {
    try {
      await updateProyecto(editingProyecto.id, formData);
      setShowEditModal(false);
      setEditingProyecto(null);
    } catch (error) {
      alert("Error al actualizar el proyecto: " + error.message);
    }
  };

  const handleDeleteProyecto = async (id) => {
    if (
      window.confirm("¿Estás seguro de que quieres eliminar este proyecto?")
    ) {
      try {
        await deleteProyecto(id);
      } catch (error) {
        alert("Error al eliminar el proyecto: " + error.message);
      }
    }
  };

  if (loadingUser || loadingProyectos || loadingTemplates) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#f8fafc",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              border: "4px solid #e2e8f0",
              borderTop: `4px solid ${currentTheme.primary}`,
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              margin: "0 auto 1rem",
            }}
          ></div>
          <p style={{ color: "#64748b" }}>
            {loadingTemplates
              ? "Cargando templates..."
              : "Cargando proyectos..."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100dvh", backgroundColor: "#f8fafc" }}>
      {/* Header */}
      <header
        style={{
          backgroundColor: "white",
          backgroundImage: `radial-gradient(640px 220px at 0% -60%, ${currentTheme.primary}14, transparent 70%)`,
          borderTop: `3px solid ${currentTheme.primary}`,
          borderBottom: "1px solid #e2e8f0",
          padding: "1.15rem 2rem",
          boxShadow: "0 1px 2px rgba(15,23,42,0.04), 0 4px 16px -10px rgba(15,23,42,0.18)",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            maxWidth: "1400px",
            margin: "0 auto",
            gap: "1rem",
            flexWrap: "wrap",
          }}
        >
          <div
            style={{ display: "flex", alignItems: "center", gap: "1.1rem" }}
          >
            {/* Logo de marca */}
            {isFilteredByProject && BRAND_LOGOS[proyecto] && (
              <div
                style={{
                  width: "4rem",
                  height: "4rem",
                  minWidth: "4rem",
                  borderRadius: "1rem",
                  backgroundColor: "white",
                  border: "1px solid #eef2f7",
                  boxShadow: `0 8px 20px -12px ${currentTheme.primary}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "0.7rem",
                }}
              >
                <img
                  src={BRAND_LOGOS[proyecto]}
                  alt={`Logo de ${currentTheme.name}`}
                  style={{
                    maxWidth: "100%",
                    maxHeight: "100%",
                    objectFit: "contain",
                  }}
                />
              </div>
            )}

            <div>
              {/* Breadcrumb — incluye vuelta a Inicio */}
              <nav
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem",
                  fontSize: "0.78rem",
                  color: "#94a3b8",
                  marginBottom: "0.3rem",
                }}
              >
                <span
                  onClick={() => navigate("/home")}
                  style={{
                    cursor: "pointer",
                    fontWeight: "500",
                    transition: "color 0.2s",
                  }}
                  onMouseOver={(e) =>
                    (e.currentTarget.style.color = currentTheme.primary)
                  }
                  onMouseOut={(e) => (e.currentTarget.style.color = "#94a3b8")}
                >
                  Inicio
                </span>
                <ChevronRight size={13} />
                <span style={{ color: "#64748b", fontWeight: "600" }}>
                  Landing Pages
                </span>
              </nav>
              <h1
                style={{
                  margin: 0,
                  fontSize: "1.75rem",
                  fontWeight: "800",
                  letterSpacing: "-0.025em",
                  color: currentTheme.primary,
                  lineHeight: 1.1,
                }}
              >
                {isFilteredByProject
                  ? currentTheme.name
                  : "Dashboard Redactoria"}
              </h1>
              <p
                style={{
                  margin: "0.3rem 0 0 0",
                  color: "#64748b",
                  fontSize: "0.875rem",
                }}
              >
                {isFilteredByProject
                  ? `Gestiona los proyectos de Landing Pages de ${currentTheme.name}`
                  : "Gestiona y supervisa todos los proyectos"}
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            {/* Home Button */}
            <button
              onClick={() => navigate("/home")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.5rem 1rem",
                backgroundColor: "#f1f5f9",
                color: "#64748b",
                border: "none",
                borderRadius: "0.5rem",
                cursor: "pointer",
                fontSize: "0.875rem",
                fontWeight: "500",
                transition: "background-color 0.2s",
              }}
              onMouseOver={(e) =>
                (e.currentTarget.style.backgroundColor = "#e2e8f0")
              }
              onMouseOut={(e) =>
                (e.currentTarget.style.backgroundColor = "#f1f5f9")
              }
            >
              <Home size={18} />
              Home TEST
            </button>

            {/* Analytics Button - Only for Admin */}
            {currentUser && isAdminUser(currentUser) && (
                <button
                  onClick={() => navigate("/analytics")}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    padding: "0.5rem 1rem",
                    backgroundColor: currentTheme.primary,
                    color: "white",
                    border: "none",
                    borderRadius: "0.5rem",
                    cursor: "pointer",
                    fontSize: "0.875rem",
                    fontWeight: "500",
                    transition: "background-color 0.2s",
                  }}
                  onMouseOver={(e) =>
                    (e.currentTarget.style.backgroundColor =
                      currentTheme.primaryHover)
                  }
                  onMouseOut={(e) =>
                    (e.currentTarget.style.backgroundColor =
                      currentTheme.primary)
                  }
                >
                  <BarChart3 size={18} />
                  Analytics
                </button>
              )}

            {currentUser && canManageUsers(currentUser) && (
              <button
                onClick={() => navigate("/usuarios")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  padding: "0.5rem 1rem",
                  backgroundColor: currentTheme.primary,
                  color: "white",
                  border: "none",
                  borderRadius: "0.5rem",
                  cursor: "pointer",
                  fontSize: "0.875rem",
                  fontWeight: "500",
                }}
              >
                <Users size={18} />
                Usuarios
              </button>
            )}

            {currentUser && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  backgroundColor: "#f1f5f9",
                  padding: "0.5rem 1rem",
                  borderRadius: "0.5rem",
                }}
              >
                <div
                  style={{
                    width: "2rem",
                    height: "2rem",
                    backgroundColor: currentTheme.primary,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "white",
                    fontSize: "0.875rem",
                    fontWeight: "600",
                  }}
                >
                  {currentUser.avatar ||
                    (currentUser.first_name || currentUser.last_name
                      ? `${(currentUser.first_name?.[0] || "").toUpperCase()}${(currentUser.last_name?.[0] || "").toUpperCase()}`
                      : (currentUser.email?.[0] || "").toUpperCase())}
                </div>
                <div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "0.875rem",
                      fontWeight: "600",
                      color: "#1e293b",
                    }}
                  >
                    {currentUser.name}
                  </p>
                  <p
                    style={{ margin: 0, fontSize: "0.75rem", color: "#64748b" }}
                  >
                    {roleLabel(currentUser)}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
        {/* Estadísticas rápidas */}
        <div
          className="dashboard-stats-container"
          style={{
            display: "flex",
            flexDirection: "row",
            flexWrap: "nowrap",
            gap: "1rem",
            marginBottom: "2rem",
            overflowX: "auto",
            width: "100%",
          }}
        >
          <StatCard
            icon={<Edit3 size={20} />}
            value={stats.total}
            label="Proyectos Totales"
            color={currentTheme.primary}
            bgColor={currentTheme.primaryLight}
          />
          <StatCard
            icon={<CheckCircle2 size={20} />}
            value={stats.completed}
            label="Publicados"
            color={currentTheme.secondary}
            bgColor={currentTheme.primaryLight}
          />
          <StatCard
            icon={<Clock size={20} />}
            value={stats.nonCompleted}
            label="En Proceso"
            color="#f59e0b"
            bgColor="#fef3c7"
          />
          <StatCard
            icon={<AlertCircle size={20} />}
            value={stats.unassigned}
            label="Sin Asignar"
            color="#ef4444"
            bgColor="#fee2e2"
          />
        </div>

        {/* Filtros y búsqueda */}
        <FilterPanel
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          filters={filters}
          onFilterChange={updateFilter}
          users={users}
          currentUser={currentUser}
          onCreateProject={() => setShowCreateModal(true)}
          canCreateProjects={canCreateProjects}
          isAdminUser={isAdminUser}
          hideDomainFilter={isFilteredByProject}
          theme={currentTheme}
        />

        {/* Tabla de Proyectos */}
        <ProjectsTable
          proyectos={visibleProyectos}
          templates={templates}
          users={getAllUsers()}
          currentUser={currentUser}
          onEdit={canEdit}
          onAssign={(proyecto) => {
            setSelectedProyecto(proyecto);
            setShowAssignModal(true);
          }}
          onDelete={handleDeleteProyecto}
          onEditClick={(proyecto) => {
            setEditingProyecto(proyecto);
            setShowEditModal(true);
          }}
          canAssignUsers={canAssignUsers}
          canDeleteProjects={canDeleteProjects}
          getStatusColor={getStatusColor}
          getStatusIcon={getStatusIcon}
          getStatusText={getStatusText}
          getPriorityColor={getPriorityColor}
        />
      </div>

      {/* Modales */}
      {showCreateModal && (
        <CreateProyectoModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateProyecto}
          proyectoFilter={proyecto}
          theme={currentTheme}
        />
      )}

      {showAssignModal && (
        <AssignModal
          proyecto={selectedProyecto}
          users={getFilteredUsers()}
          onClose={() => setShowAssignModal(false)}
          onAssign={handleAssignProyecto}
        />
      )}

      {showEditModal && editingProyecto && (
        <EditProyectoModal
          proyecto={editingProyecto}
          canEditName={isAdminUser(currentUser)}
          onClose={() => {
            setShowEditModal(false);
            setEditingProyecto(null);
          }}
          onSubmit={handleEditProyecto}
        />
      )}

      {/* CSS para animación de loading */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .dashboard-stats-container {
          display: flex !important;
          flex-direction: row !important;
          flex-wrap: nowrap !important;
          gap: 1rem !important;
          margin-bottom: 2rem !important;
          overflow-x: auto !important;
          width: 100% !important;
        }

        .dashboard-stats-container > div {
          flex: 1 1 0 !important;
          min-width: 250px !important;
          max-width: none !important;
          transition: transform 0.25s cubic-bezier(0.22,1,0.36,1), box-shadow 0.25s cubic-bezier(0.22,1,0.36,1) !important;
        }

        .dashboard-stats-container > div:hover {
          transform: translateY(-4px) !important;
          box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 20px 34px -14px rgba(15,23,42,0.22) !important;
        }

        /* Tabla de proyectos */
        .dashboard-table thead th {
          background: #f8fafc !important;
          padding: 0.95rem 1.25rem !important;
          color: #475569 !important;
          box-shadow: inset 0 -1px 0 #e2e8f0;
        }
        .dashboard-table tbody td {
          padding: 1.1rem 1.25rem !important;
        }
        .dashboard-table tbody tr {
          transition: background-color 0.15s ease;
        }
        .dashboard-table tbody tr:hover {
          background-color: #eef3fd !important;
        }

        /* Botones de acción de la tabla — feedback de hover/press uniforme,
           funciona sobre cualquier color de fondo */
        .dt-act {
          transition: transform 0.15s cubic-bezier(0.22,1,0.36,1),
                      box-shadow 0.15s ease,
                      filter 0.15s ease;
        }
        .dt-act:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 14px -6px rgba(15,23,42,0.4);
          filter: brightness(1.07);
        }
        .dt-act:active {
          transform: translateY(0) scale(0.92);
          box-shadow: none;
        }

        /* Filtros y búsqueda */
        .dashboard-filters input,
        .dashboard-filters select {
          transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        .dashboard-filters input:focus,
        .dashboard-filters select:focus {
          border-color: #1e5fd6 !important;
          box-shadow: 0 0 0 3px rgba(30,95,214,0.15) !important;
          outline: none !important;
        }
        .dashboard-filters select { cursor: pointer; }

        /* ---- Modales de formulario (LP) ----
           Reglas que el estilo inline NO puede definir: foco, hover, animación.
           Se montan sin pelear con los estilos inline de cada modal. */
        @keyframes lpModalFadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes lpModalSlideUp {
          from { opacity: 0; transform: translateY(16px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .lp-modal {
          animation: lpModalFadeIn 0.2s ease-out;
        }
        .lp-modal > div {
          animation: lpModalSlideUp 0.28s cubic-bezier(0.22,1,0.36,1);
        }
        .lp-modal input:focus,
        .lp-modal select:focus,
        .lp-modal textarea:focus {
          border-color: #1e5fd6 !important;
          box-shadow: 0 0 0 3px rgba(30,95,214,0.15) !important;
          outline: none !important;
        }
        .lp-modal input,
        .lp-modal select,
        .lp-modal textarea {
          transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
        }
        .lp-modal button {
          transition: filter 0.15s ease, transform 0.12s ease, box-shadow 0.15s ease;
        }
        .lp-modal button:hover {
          filter: brightness(1.06);
        }
        .lp-modal button:active {
          transform: translateY(1px) scale(0.99);
        }
        /* Scrollbar discreta dentro del modal */
        .lp-modal > div::-webkit-scrollbar { width: 10px; }
        .lp-modal > div::-webkit-scrollbar-thumb {
          background: #cbd5e1; border-radius: 8px; border: 3px solid #fff;
        }
      `}</style>
    </div>
  );
}

// Componente de tarjeta de estadísticas
function StatCard({ icon, value, label, color, bgColor }) {
  return (
    <div
      style={{
        position: "relative",
        backgroundColor: "white",
        padding: "1.5rem 1.5rem 1.5rem 1.75rem",
        borderRadius: "1rem",
        boxShadow: "0 1px 2px rgba(15,23,42,0.04), 0 8px 24px -12px rgba(15,23,42,0.12)",
        border: "1px solid #eef2f7",
        flex: "1",
        minWidth: "250px",
        display: "flex",
        alignItems: "center",
        gap: "1.1rem",
        overflow: "hidden",
      }}
    >
      {/* Barra de acento lateral */}
      <span
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: "5px",
          backgroundColor: color,
        }}
      />
      <div
        style={{
          width: "3.25rem",
          height: "3.25rem",
          minWidth: "3.25rem",
          backgroundColor: color,
          borderRadius: "0.9rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#ffffff",
          boxShadow: `0 8px 18px -8px ${color}`,
        }}
      >
        {icon}
      </div>
      <div>
        <p
          style={{
            margin: 0,
            fontSize: "2.25rem",
            fontWeight: "800",
            letterSpacing: "-0.03em",
            lineHeight: 1,
            color: "#0f172a",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {value}
        </p>
        <p
          style={{
            margin: "0.4rem 0 0 0",
            fontSize: "0.78rem",
            fontWeight: "600",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "#64748b",
          }}
        >
          {label}
        </p>
      </div>
    </div>
  );
}

// Componente del panel de filtros
function FilterPanel({
  searchTerm,
  onSearchChange,
  filters,
  onFilterChange,
  users,
  currentUser,
  onCreateProject,
  canCreateProjects,
  isAdminUser,
  hideDomainFilter = false,
  theme = { primary: "#3b82f6", primaryHover: "#2563eb" },
}) {
  return (
    <div
      className="dashboard-filters"
      style={{
        backgroundColor: "white",
        padding: "1.5rem",
        borderRadius: "1rem",
        boxShadow: "0 1px 2px rgba(15,23,42,0.04), 0 8px 24px -16px rgba(15,23,42,0.12)",
        border: "1px solid #eef2f7",
        marginBottom: "1.5rem",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "0.75rem",
          marginBottom: "1rem",
        }}
      >
        {/* Búsqueda */}
        <div
          style={{
            position: "relative",
            gridColumn: "span 6",
            minWidth: "0",
          }}
        >
          <Search
            size={16}
            style={{
              position: "absolute",
              left: "0.75rem",
              top: "50%",
              transform: "translateY(-50%)",
              color: "#64748b",
            }}
          />
          <input
            type="text"
            placeholder="Buscar proyectos..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            style={{
              padding: "0.5rem 0.75rem 0.5rem 2.5rem",
              border: "1px solid #d1d5db",
              borderRadius: "0.375rem",
              fontSize: "0.875rem",
              width: "100%",
              outline: "none",
              height: "2.25rem",
              boxSizing: "border-box",
            }}
          />
        </div>

        {/* Filtros de dominio - Solo mostrar si no está filtrado por proyecto */}
        {!hideDomainFilter && (
          <select
            value={filters.domain || "all"}
            onChange={(e) => onFilterChange("domain", e.target.value)}
            style={{
              padding: "0.5rem 0.75rem",
              border: "1px solid #d1d5db",
              borderRadius: "0.375rem",
              fontSize: "0.875rem",
              outline: "none",
              height: "2.25rem",
              minWidth: "0",
            }}
          >
            <option value="all">Todos los proyectos</option>
            <option value="viajemos">Viajemos</option>
            <option value="mcr">Miles Car Rental</option>
            <option value="outlet">Outlet Rental Cars</option>
            <option value="guialegal">Guía Legal</option>
            <option value="arriendo">Arriendo</option>
          </select>
        )}

        {/* Filtros de estado */}
        <select
          value={filters.status || "all"}
          onChange={(e) => onFilterChange("status", e.target.value)}
          style={{
            padding: "0.5rem 0.75rem",
            border: "1px solid #d1d5db",
            borderRadius: "0.375rem",
            fontSize: "0.875rem",
            outline: "none",
            height: "2.25rem",
            minWidth: "0",
          }}
        >
          <option value="all">Todos los estados</option>
          <option value="draft">Borrador</option>
          <option value="review">Pendiente de Redacción</option>
          <option value="in_progress">En Redacción</option>
          <option value="pen_review">Pendiente de Revisión</option>
          <option value="pen_ajuste">Pendiente de Ajuste</option>
          <option value="ajuste_aplicado">Ajuste Aplicado</option>
          <option value="approved">Aprobado</option>
          <option value="rev_kws">Pendiente KWS</option>
          <option value="cargue">Cargue</option>
          <option value="en_it">En IT</option>
          <option value="test">Test</option>
          <option value="completed">Publicado</option>
        </select>

        {/* Filtro de prioridad */}
        <select
          value={filters.priority || "all"}
          onChange={(e) => onFilterChange("priority", e.target.value)}
          style={{
            padding: "0.5rem 0.75rem",
            border: "1px solid #d1d5db",
            borderRadius: "0.375rem",
            fontSize: "0.875rem",
            outline: "none",
            height: "2.25rem",
            minWidth: "0",
          }}
        >
          <option value="all">Todas las prioridades</option>
          <option value="high">Alta</option>
          <option value="medium">Media</option>
          <option value="low">Baja</option>
        </select>

        {/* Filtro de fecha */}
        <select
          value={filters.date || "all"}
          onChange={(e) => onFilterChange("date", e.target.value)}
          style={{
            padding: "0.5rem 0.75rem",
            border: "1px solid #d1d5db",
            borderRadius: "0.375rem",
            fontSize: "0.875rem",
            outline: "none",
            height: "2.25rem",
            minWidth: "0",
          }}
        >
          <option value="all">Todas las fechas</option>
          <option value="week">Esta semana</option>
          <option value="month">Este mes</option>
          <option value="year">Este año</option>
        </select>

        {/* Filtro de asignado (solo para admins) */}
        {isAdminUser(currentUser) &&
          users && (
            <select
              value={filters.assignee || "all"}
              onChange={(e) => onFilterChange("assignee", e.target.value)}
              style={{
                padding: "0.5rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                fontSize: "0.875rem",
                outline: "none",
                height: "2.25rem",
                minWidth: "0",
              }}
            >
              <option value="all">Todos los asignados</option>
              <option value="unassigned">Sin asignar</option>
              {users
                .filter((u) => u.role !== "viewer")
                .map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.name}
                  </option>
                ))}
            </select>
          )}
      </div>

      {/* Botón de acción - separado en su propia fila */}
      {canCreateProjects() && (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={onCreateProject}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.5rem 1rem",
              backgroundColor: theme.primary,
              color: "white",
              border: "none",
              borderRadius: "0.375rem",
              fontSize: "0.875rem",
              fontWeight: "500",
              cursor: "pointer",
              height: "2.25rem",
              transition: "background-color 0.2s",
            }}
            onMouseOver={(e) =>
              (e.currentTarget.style.backgroundColor = theme.primaryHover)
            }
            onMouseOut={(e) =>
              (e.currentTarget.style.backgroundColor = theme.primary)
            }
          >
            <Plus size={16} />
            Nuevo Proyecto
          </button>
        </div>
      )}
    </div>
  );
}

// Componente de la tabla de proyectos
function ProjectsTable({
  proyectos,
  templates,
  users,
  currentUser,
  onEdit,
  onAssign,
  onDelete,
  onEditClick,
  canAssignUsers,
  canDeleteProjects,
  getStatusColor,
  getStatusIcon,
  getStatusText,
  getPriorityColor,
}) {
  const openRedactor = async (proyectoId) => {
    try {
      // Verificar que existe la landing page
      const landingPage = await apiService.getLandingPageByProyecto(proyectoId);

      // Abrir redactor con el proyecto_id
      window.open(`/redactor/${proyectoId}`, "_blank");
    } catch (error) {
      console.error(" Error al verificar landing page:", error);
      alert("Error al acceder a la landing page: " + error.message);
    }
  };

  const formatUsageType = (categoria) => {
    const raw = (categoria || "").toString().trim();
    if (!raw) return "Sin tipo";

    const normalized = raw.toLowerCase();
    if (normalized.includes("auto")) return "Autos";
    if (normalized.includes("agenc")) return "Agencias";
    if (normalized.includes("ofert")) return "Ofertas";
    if (normalized.includes("local")) return "Localidad";
    if (normalized.includes("ciudad")) return "Ciudad";

    return raw.charAt(0).toUpperCase() + raw.slice(1);
  };

  return (
    <div
      style={{
        backgroundColor: "white",
        borderRadius: "1rem",
        boxShadow: "0 1px 2px rgba(15,23,42,0.04), 0 8px 24px -16px rgba(15,23,42,0.12)",
        border: "1px solid #eef2f7",
        overflow: "hidden",
      }}
    >
      <div style={{ overflowX: "auto" }}>
        <table
          className="dashboard-table"
          style={{ width: "100%", borderCollapse: "collapse" }}
        >
          <thead style={{ backgroundColor: "#f8fafc" }}>
            <tr>
              <th
                style={{
                  padding: "0.75rem 1rem",
                  textAlign: "left",
                  fontSize: "0.75rem",
                  fontWeight: "600",
                  color: "#374151",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Nombre
              </th>
              <th
                style={{
                  padding: "0.75rem 1rem",
                  textAlign: "left",
                  fontSize: "0.75rem",
                  fontWeight: "600",
                  color: "#374151",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Template usado
              </th>
              <th
                style={{
                  padding: "0.75rem 1rem",
                  textAlign: "left",
                  fontSize: "0.75rem",
                  fontWeight: "600",
                  color: "#374151",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Asignado a
              </th>
              <th
                style={{
                  padding: "0.75rem 1rem",
                  textAlign: "left",
                  fontSize: "0.75rem",
                  fontWeight: "600",
                  color: "#374151",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Estado
              </th>
              <th
                style={{
                  padding: "0.75rem 1rem",
                  textAlign: "left",
                  fontSize: "0.75rem",
                  fontWeight: "600",
                  color: "#374151",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Prioridad
              </th>
              <th
                style={{
                  padding: "0.75rem 1rem",
                  textAlign: "left",
                  fontSize: "0.75rem",
                  fontWeight: "600",
                  color: "#374151",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Fecha Creación
              </th>
              <th
                style={{
                  padding: "0.75rem 1rem",
                  textAlign: "left",
                  fontSize: "0.75rem",
                  fontWeight: "600",
                  color: "#374151",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Última Modificación
              </th>
              <th
                style={{
                  padding: "0.75rem 1rem",
                  textAlign: "right",
                  fontSize: "0.75rem",
                  fontWeight: "600",
                  color: "#374151",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Acciones
              </th>
            </tr>
          </thead>
          <tbody>
            {proyectos.map((proyecto, index) => {
              const assignedUser = users?.find(
                (u) => u.id === proyecto.assignedTo,
              );
              const templateUsed = templates?.find(
                (t) => t.id === proyecto.templateId,
              );
              const brandKey = (templateUsed?.proyecto || "").toLowerCase();
              const brandTheme =
                PROJECT_THEMES[brandKey] || PROJECT_THEMES.default;

              return (
                <tr
                  key={proyecto.id}
                  style={{
                    borderTop: index > 0 ? "1px solid #e2e8f0" : "none",
                  }}
                >
                  <td style={{ padding: "1rem" }}>
                    <div>
                      <p
                        style={{
                          margin: 0,
                          fontWeight: "600",
                          color: "#1e293b",
                        }}
                      >
                        {proyecto.name}
                      </p>
                      {proyecto.dominio && (
                        <p
                          style={{
                            margin: "0.3rem 0 0 0",
                            fontSize: "0.75rem",
                            color: "#64748b",
                            display: "flex",
                            alignItems: "center",
                            gap: "0.3rem",
                          }}
                          title={proyecto.dominioUrl || proyecto.dominio}
                        >
                          <Globe size={12} />
                          {proyecto.dominio}
                          {proyecto.dominioPais
                            ? ` · ${proyecto.dominioPais}`
                            : ""}
                        </p>
                      )}
                    </div>
                  </td>

                  <td style={{ padding: "1rem" }}>
                    {templateUsed ? (
                      <div>
                        <p
                          style={{
                            margin: 0,
                            fontSize: "0.875rem",
                            fontWeight: "600",
                            color: "#1e293b",
                          }}
                        >
                          {templateUsed.name}
                        </p>
                        <div
                          style={{
                            marginTop: "0.375rem",
                            display: "flex",
                            gap: "0.375rem",
                            flexWrap: "wrap",
                          }}
                        >
                          <span
                            style={{
                              fontSize: "0.7rem",
                              fontWeight: "700",
                              color: "#ffffff",
                              backgroundColor: brandTheme.primary,
                              padding: "0.15rem 0.5rem",
                              borderRadius: "9999px",
                            }}
                            title={`Marca: ${brandTheme.name}`}
                          >
                            {templateUsed.proyecto
                              ? brandTheme.name
                              : "-"}
                          </span>
                          <span
                            style={{
                              fontSize: "0.7rem",
                              fontWeight: "600",
                              color: "#065f46",
                              backgroundColor: "#d1fae5",
                              padding: "0.15rem 0.45rem",
                              borderRadius: "9999px",
                            }}
                          >
                            {formatUsageType(templateUsed.categoria)}
                          </span>
                          {templateUsed.dominio && (
                            <span
                              style={{
                                fontSize: "0.7rem",
                                fontWeight: "600",
                                color: "#6b21a8",
                                backgroundColor: "#f3e8ff",
                                padding: "0.15rem 0.45rem",
                                borderRadius: "9999px",
                              }}
                            >
                              {templateUsed.dominio}
                            </span>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div>
                        <p style={{ margin: 0, fontSize: "0.8rem", color: "#9ca3af" }}>
                          Template no disponible
                        </p>
                        {proyecto.templateId && (
                          <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.75rem", color: "#9ca3af" }}>
                            ID: {proyecto.templateId}
                          </p>
                        )}
                      </div>
                    )}
                  </td>

                  <td style={{ padding: "1rem" }}>
                    {assignedUser ? (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.5rem",
                        }}
                      >
                        <div
                          style={{
                            width: "1.5rem",
                            height: "1.5rem",
                            backgroundColor: "#1e5fd6",
                            borderRadius: "50%",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "white",
                            fontSize: "0.75rem",
                            fontWeight: "600",
                          }}
                        >
                          {assignedUser.avatar || assignedUser.name?.charAt(0)}
                        </div>
                        <div>
                          <p
                            style={{
                              margin: 0,
                              fontSize: "0.875rem",
                              fontWeight: "500",
                              color: "#1e293b",
                            }}
                          >
                            {assignedUser.name}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <span style={{ color: "#64748b", fontSize: "0.875rem" }}>
                        Sin asignar
                      </span>
                    )}
                  </td>

                  <td style={{ padding: "1rem" }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        padding: "0.25rem 0.75rem",
                        backgroundColor: `${getStatusColor(proyecto.status)}15`,
                        color: getStatusColor(proyecto.status),
                        borderRadius: "9999px",
                        fontSize: "0.75rem",
                        fontWeight: "500",
                        width: "fit-content",
                      }}
                    >
                      {getStatusIcon(proyecto.status)}
                      {getStatusText(proyecto.status)}
                    </div>
                  </td>

                  <td style={{ padding: "1rem" }}>
                    <span
                      style={{
                        padding: "0.25rem 0.5rem",
                        backgroundColor: `${getPriorityColor(proyecto.priority)}15`,
                        color: getPriorityColor(proyecto.priority),
                        borderRadius: "0.25rem",
                        fontSize: "0.75rem",
                        fontWeight: "500",
                      }}
                    >
                      {proyecto.priority === "high"
                        ? "Alta"
                        : proyecto.priority === "medium"
                          ? "Media"
                          : "Baja"}
                    </span>
                  </td>

                  <td style={{ padding: "1rem" }}>
                    <span style={{ fontSize: "0.875rem", color: "#64748b" }}>
                      {proyecto.createdDate
                        ? new Date(proyecto.createdDate).toLocaleDateString(
                            "es-ES",
                          )
                        : "-"}
                    </span>
                  </td>

                  <td style={{ padding: "1rem" }}>
                    <span style={{ fontSize: "0.875rem", color: "#64748b" }}>
                      {proyecto.lastModifiedAt
                        ? new Date(proyecto.lastModifiedAt).toLocaleString(
                            "es-ES",
                          )
                        : "-"}
                    </span>
                  </td>

                  <td style={{ padding: "1rem", textAlign: "right" }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "flex-end",
                        gap: "0.5rem",
                      }}
                    >
                      <button
                        className="dt-act"
                        onClick={() => openRedactor(proyecto.id)}
                        style={{
                          padding: "0.5rem",
                          backgroundColor: "#f3f4f6",
                          color: "#64748b",
                          border: "none",
                          borderRadius: "0.5rem",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                        title="Ver Proyecto"
                      >
                        <Eye size={14} />
                      </button>

                      {canAssignUsers() && (
                        <button
                          className="dt-act"
                          onClick={() => onAssign(proyecto)}
                          style={{
                            padding: "0.5rem",
                            backgroundColor: "#10b981",
                            color: "white",
                            border: "none",
                            borderRadius: "0.5rem",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                          title="Asignar usuario"
                        >
                          <UserPlus size={14} />
                        </button>
                      )}

                      {onEdit(proyecto) && (
                        <button
                          className="dt-act"
                          onClick={() => onEditClick(proyecto)}
                          style={{
                            padding: "0.5rem",
                            backgroundColor: "#1e5fd6",
                            color: "white",
                            border: "none",
                            borderRadius: "0.5rem",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                          title="Editar proyecto"
                        >
                          <Edit3 size={14} />
                        </button>
                      )}

                      {canAssignUsers() && (
                        <button
                          className="dt-act"
                          onClick={() => onDelete(proyecto.id)}
                          style={{
                            padding: "0.5rem",
                            backgroundColor: "#ef4444",
                            color: "white",
                            border: "none",
                            borderRadius: "0.5rem",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                          title="Eliminar proyecto"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {proyectos.length === 0 && (
        <div
          style={{
            padding: "3rem",
            textAlign: "center",
            color: "#64748b",
          }}
        >
          <AlertCircle
            size={48}
            style={{ margin: "0 auto 1rem", opacity: 0.5 }}
          />
          <p style={{ margin: 0, fontSize: "1.125rem", fontWeight: "500" }}>
            No se encontraron proyectos
          </p>
          <p style={{ margin: "0.5rem 0 0 0", fontSize: "0.875rem" }}>
            Ajusta los filtros o crea un nuevo proyecto
          </p>
        </div>
      )}
    </div>
  );
}

// Modal para crear nuevo proyecto
function CreateProyectoModal({ onClose, onSubmit, proyectoFilter, theme = { primary: "#3b82f6", primaryLight: "#dbeafe" } }) {
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    priority: "",
    template_id: "",
    dominio: "",
    dominio_url: "",
    dominio_pais: "",
    dominio_idiomas: "",
  });
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [templatesGrouped, setTemplatesGrouped] = useState({});

  // Marca efectiva: la del filtro de URL (/dashboard/mcr) o, si no hay,
  // la del template seleccionado. De ella depende el catálogo de dominios.
  const selectedTemplate = templates.find((t) => t.id === formData.template_id);
  const marcaDominios = proyectoFilter || selectedTemplate?.proyecto || "";
  const dominiosDisponibles = getDominiosPorMarca(marcaDominios);

  const handleDominioChange = (value) => {
    const elegido = dominiosDisponibles.find((d) => d.dominio === value);
    setFormData((prev) => ({
      ...prev,
      dominio: elegido ? elegido.dominio : "",
      dominio_url: elegido ? elegido.url : "",
      dominio_pais: elegido ? elegido.pais : "",
      dominio_idiomas: elegido ? elegido.idiomas.join(",") : "",
    }));
  };

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        setTemplatesLoading(true);
        const response = await fetch(
          `${process.env.REACT_APP_API_URL || "http://192.168.1.129:8080"}/templates/public/active`,
        );

        if (response.ok) {
          const templatesData = await response.json();
          setTemplates(templatesData);

          // Agrupar templates por proyecto > dominio > categoria
          const grouped = {};
          templatesData.forEach((template) => {
            const { proyecto, dominio, categoria } = template;

            if (!grouped[proyecto]) {
              grouped[proyecto] = {};
            }
            if (!grouped[proyecto][dominio]) {
              grouped[proyecto][dominio] = {};
            }
            if (!grouped[proyecto][dominio][categoria]) {
              grouped[proyecto][dominio][categoria] = [];
            }

            grouped[proyecto][dominio][categoria].push(template);
          });

          setTemplatesGrouped(grouped);
        } else {
          console.error("Error cargando templates:", response.status);
        }
      } catch (error) {
        console.error("Error cargando templates:", error);
      } finally {
        setTemplatesLoading(false);
      }
    };

    loadTemplates();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.template_id) {
      alert("Por favor selecciona un template");
      return;
    }

    if (dominiosDisponibles.length > 0 && !formData.dominio) {
      alert("Por favor selecciona un dominio destino");
      return;
    }

    if (formData.name.trim()) {
      try {
        setLoading(true);

        await onSubmit(formData);
      } catch (error) {
        console.error("Error in form submission:", error);
      } finally {
        setLoading(false);
      }
    }
  };

  const renderTemplateSelector = () => {
    if (templatesLoading) {
      return (
        <div
          style={{
            padding: "0.75rem 1rem",
            border: "1px solid #e2e8f0",
            borderRadius: "0.375rem",
            backgroundColor: "#f8fafc",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            color: "#64748b",
            fontSize: "0.875rem",
          }}
        >
          <div
            style={{
              width: "14px",
              height: "14px",
              border: "2px solid #cbd5e1",
              borderTop: "2px solid #3b82f6",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              flexShrink: 0,
            }}
          />
          Cargando templates...
        </div>
      );
    }

    if (templates.length === 0) {
      return (
        <div
          style={{
            padding: "0.75rem 1rem",
            border: "1px solid #fecaca",
            borderRadius: "0.375rem",
            backgroundColor: "#fef2f2",
            color: "#dc2626",
            fontSize: "0.875rem",
          }}
        >
          No hay templates disponibles
        </div>
      );
    }

    const visibleGrouped = proyectoFilter
      ? Object.fromEntries(
          Object.entries(templatesGrouped).filter(([key]) => key === proyectoFilter)
        )
      : templatesGrouped;

    return (
      <div
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: "0.5rem",
          maxHeight: "420px",
          overflowY: "auto",
          backgroundColor: "#f8fafc",
          padding: "1rem",
          display: "flex",
          flexDirection: "column",
          gap: "1.25rem",
        }}
      >
        {Object.entries(visibleGrouped).map(([proyecto, dominios]) =>
          Object.entries(dominios).map(([dominio, categorias]) => {
            const allTemplates = Object.values(categorias).flat();
            return (
              <div key={`${proyecto}-${dominio}`}>
                <div
                  style={{
                    fontSize: "0.7rem",
                    fontWeight: "700",
                    color: "#6b7280",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: "0.625rem",
                  }}
                >
                  {dominio}
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "0.5rem",
                  }}
                >
                  {allTemplates.map((template) => {
                    const isSelected = formData.template_id === template.id;
                    return (
                      <button
                        key={template.id}
                        type="button"
                        onClick={() => setFormData({ ...formData, template_id: template.id })}
                        style={{
                          padding: "0.4rem 0.9rem",
                          border: isSelected ? `2px solid ${theme.primary}` : "1px solid #d1d5db",
                          borderRadius: "9999px",
                          backgroundColor: isSelected ? theme.primaryLight : "white",
                          color: isSelected ? theme.primary : "#4b5563",
                          fontSize: "0.8rem",
                          fontWeight: isSelected ? "600" : "400",
                          cursor: "pointer",
                          transition: "all 0.15s",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          boxShadow: isSelected ? `0 0 0 3px ${theme.primary}33` : "none",
                        }}
                      >
                        {template.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })
        )}

        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  };

  return (
    <div
      className="lp-modal"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.55)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
    >
      <div
        style={{
          backgroundColor: "white",
          border: "1px solid #eef2f7",
          borderTop: "3px solid #1e5fd6",
          borderRadius: "1rem",
          boxShadow: "0 24px 60px -15px rgba(15,23,42,0.35)",
          padding: "1.75rem 2rem 2rem",
          minWidth: "500px",
          maxWidth: "600px",
          maxHeight: "90vh",
          overflowY: "auto",
        }}
      >
        <h2
          style={{
            margin: "0 0 1.5rem 0",
            fontSize: "1.4rem",
            fontWeight: "800",
            letterSpacing: "-0.02em",
            color: "#0f172a",
          }}
        >
          Crear Nuevo Proyecto
        </h2>

        <form onSubmit={handleSubmit}>
          {/* Campo Nombre */}
          <div style={{ marginBottom: "1rem" }}>
            <label
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontWeight: "500",
              }}
            >
              Nombre *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                fontSize: "0.875rem",
                outline: "none",
                boxSizing: "border-box",
              }}
              placeholder="Nombre del proyecto"
              required
            />
          </div>

          {/* Campo Descripción */}
          <div style={{ marginBottom: "1rem" }}>
            <label
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontWeight: "500",
              }}
            >
              Descripción
            </label>
            <textarea
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              rows={3}
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                fontSize: "0.875rem",
                outline: "none",
                boxSizing: "border-box",
                resize: "vertical",
              }}
              placeholder="Descripción del proyecto (opcional)"
            />
          </div>

          {/* Selector de Template */}
          <div style={{ marginBottom: "1rem" }}>
            <label
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontWeight: "500",
              }}
            >
              Template *
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "#6b7280",
                  fontWeight: "400",
                  marginLeft: "0.5rem",
                }}
              >
                (Selecciona el template base para tu proyecto)
              </span>
            </label>
            {renderTemplateSelector()}
          </div>

          {/* Selector de Dominio destino (depende de la marca) */}
          {(dominiosDisponibles.length > 0 || !marcaDominios) && (
            <div style={{ marginBottom: "1rem" }}>
              <label
                style={{
                  display: "block",
                  marginBottom: "0.5rem",
                  fontWeight: "500",
                }}
              >
                Dominio destino {dominiosDisponibles.length > 0 ? "*" : ""}
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "#6b7280",
                    fontWeight: "400",
                    marginLeft: "0.5rem",
                  }}
                >
                  (Sitio/país donde se publicará la landing)
                </span>
              </label>

              {dominiosDisponibles.length > 0 ? (
                <>
                  <select
                    value={formData.dominio}
                    onChange={(e) => handleDominioChange(e.target.value)}
                    required
                    style={{
                      width: "100%",
                      padding: "0.5rem 0.75rem",
                      border: "1px solid #d1d5db",
                      borderRadius: "0.375rem",
                      fontSize: "0.875rem",
                      outline: "none",
                      boxSizing: "border-box",
                    }}
                  >
                    <option value="">Selecciona un dominio</option>
                    {dominiosDisponibles.map((d) => (
                      <option key={d.dominio} value={d.dominio}>
                        {d.pais} — {d.dominio} ({d.idiomas.join("/")})
                      </option>
                    ))}
                  </select>
                  {formData.dominio_url && (
                    <p
                      style={{
                        margin: "0.4rem 0 0 0",
                        fontSize: "0.75rem",
                        color: "#64748b",
                      }}
                    >
                      {formData.dominio_url} · Idiomas:{" "}
                      {formData.dominio_idiomas.split(",").join(", ")}
                    </p>
                  )}
                </>
              ) : (
                <div
                  style={{
                    padding: "0.625rem 0.875rem",
                    border: "1px dashed #cbd5e1",
                    borderRadius: "0.375rem",
                    backgroundColor: "#f8fafc",
                    color: "#94a3b8",
                    fontSize: "0.8rem",
                  }}
                >
                  Selecciona un template primero para elegir el dominio.
                </div>
              )}
            </div>
          )}

          {/* Campo Prioridad */}
          <div style={{ marginBottom: "1.5rem" }}>
            <label
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontWeight: "500",
              }}
            >
              Prioridad
            </label>
            <select
              value={formData.priority}
              onChange={(e) =>
                setFormData({ ...formData, priority: e.target.value })
              }
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                fontSize: "0.875rem",
                outline: "none",
                boxSizing: "border-box",
              }}
              required
            >
              <option value="">Selecciona una prioridad</option>
              <option value="low">Baja</option>
              <option value="medium">Media</option>
              <option value="high">Alta</option>
            </select>
          </div>

          {/* Template seleccionado - Info */}
          {formData.template_id && (
            <div
              style={{
                marginBottom: "1.5rem",
                padding: "0.75rem",
                backgroundColor: `${theme.primary}10`,
                border: `1px solid ${theme.primary}50`,
                borderRadius: "0.375rem",
              }}
            >
              <div style={{ fontSize: "0.875rem", color: theme.primary }}>
                <strong>Template seleccionado:</strong>
                {(() => {
                  const selectedTemplate = templates.find(
                    (t) => t.id === formData.template_id,
                  );
                  return selectedTemplate ? (
                    <div style={{ marginTop: "0.25rem" }}>
                      📄 {selectedTemplate.name}
                      <span style={{ color: "#64748b", fontSize: "0.75rem" }}>
                        ({selectedTemplate.proyecto} →{" "}
                        {selectedTemplate.dominio} →{" "}
                        {selectedTemplate.categoria})
                      </span>
                    </div>
                  ) : null;
                })()}
              </div>
            </div>
          )}

          {/* Botones */}
          <div
            style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}
          >
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: "0.5rem 1rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                backgroundColor: "white",
                color: "#374151",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.6 : 1,
              }}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={
                loading || !formData.name.trim() || !formData.template_id
              }
              style={{
                padding: "0.5rem 1rem",
                border: "none",
                borderRadius: "0.375rem",
                backgroundColor:
                  loading || !formData.name.trim() || !formData.template_id
                    ? "#94a3b8"
                    : theme.primary,
                color: "white",
                cursor:
                  loading || !formData.name.trim() || !formData.template_id
                    ? "not-allowed"
                    : "pointer",
              }}
            >
              {loading ? "Creando..." : "Crear Proyecto"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Modal para asignar usuario
function AssignModal({ proyecto, users, onClose, onAssign }) {
  const [selectedUser, setSelectedUser] = useState(proyecto?.assignedTo || "");
  const [loading, setLoading] = useState(false);

  const handleAssign = async () => {
    try {
      setLoading(true);
      await onAssign(proyecto.id, selectedUser || null);
    } catch (error) {
      console.error("Error in assignment:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="lp-modal"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.55)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
    >
      <div
        style={{
          backgroundColor: "white",
          border: "1px solid #eef2f7",
          borderTop: "3px solid #1e5fd6",
          borderRadius: "1rem",
          boxShadow: "0 24px 60px -15px rgba(15,23,42,0.35)",
          padding: "1.75rem 2rem 2rem",
          minWidth: "400px",
          maxWidth: "460px",
          width: "100%",
        }}
      >
        <h2
          style={{
            margin: "0 0 1.25rem 0",
            fontSize: "1.4rem",
            fontWeight: "800",
            letterSpacing: "-0.02em",
            color: "#0f172a",
          }}
        >
          Asignar Usuario
        </h2>

        <p style={{ margin: "0 0 1rem 0", color: "#64748b" }}>
          Proyecto: <strong>{proyecto?.name}</strong>
        </p>

        <div style={{ marginBottom: "1.5rem" }}>
          <label
            style={{
              display: "block",
              marginBottom: "0.5rem",
              fontWeight: "500",
            }}
          >
            Asignar a
          </label>
          <select
            value={selectedUser}
            onChange={(e) => setSelectedUser(e.target.value)}
            style={{
              width: "100%",
              padding: "0.5rem 0.75rem",
              border: "1px solid #d1d5db",
              borderRadius: "0.375rem",
              fontSize: "0.875rem",
              outline: "none",
              boxSizing: "border-box",
            }}
          >
            <option value="">Sin asignar</option>
            {users?.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
          </select>
        </div>

        <div
          style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}
        >
          <button
            onClick={onClose}
            disabled={loading}
            style={{
              padding: "0.5rem 1rem",
              border: "1px solid #d1d5db",
              borderRadius: "0.375rem",
              backgroundColor: "white",
              color: "#374151",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.6 : 1,
            }}
          >
            Cancelar
          </button>
          <button
            onClick={handleAssign}
            disabled={loading}
            style={{
              padding: "0.5rem 1rem",
              border: "none",
              borderRadius: "0.375rem",
              backgroundColor: loading ? "#94a3b8" : "#1e5fd6",
              color: "white",
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Asignando..." : "Asignar"}
          </button>
        </div>
      </div>
    </div>
  );
}

// Modal para editar proyecto
function EditProyectoModal({ proyecto, onClose, onSubmit, canEditName = false }) {
  const [formData, setFormData] = useState({
    name: proyecto.name || "",
    description: proyecto.description || "",
    status: proyecto.status,
    priority: proyecto.priority,
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.name.trim()) {
      try {
        setLoading(true);
        await onSubmit(formData);
      } catch (error) {
        console.error("Error in form submission:", error);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div
      className="lp-modal"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.55)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
    >
      <div
        style={{
          backgroundColor: "white",
          border: "1px solid #eef2f7",
          borderTop: "3px solid #1e5fd6",
          borderRadius: "1rem",
          boxShadow: "0 24px 60px -15px rgba(15,23,42,0.35)",
          padding: "1.75rem 2rem 2rem",
          minWidth: "500px",
          maxWidth: "600px",
          maxHeight: "90vh",
          overflowY: "auto",
        }}
      >
        <h2
          style={{
            margin: "0 0 1.5rem 0",
            fontSize: "1.4rem",
            fontWeight: "800",
            letterSpacing: "-0.02em",
            color: "#0f172a",
          }}
        >
          Editar Proyecto
        </h2>

        <form onSubmit={handleSubmit}>
          {/* Campo Nombre — editable solo para administradores */}
          <div style={{ marginBottom: "1rem" }}>
            <label
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontWeight: "500",
              }}
            >
              Nombre
            </label>
            <input
              type="text"
              value={formData.name}
              readOnly={!canEditName}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                fontSize: "0.875rem",
                outline: "none",
                boxSizing: "border-box",
                backgroundColor: canEditName ? "#ffffff" : "#f9fafb",
                color: canEditName ? "#0f172a" : "#6b7280",
                cursor: canEditName ? "text" : "not-allowed",
              }}
              placeholder="Nombre del proyecto"
              required
            />
            {!canEditName && (
              <p
                style={{
                  margin: "0.4rem 0 0 0",
                  fontSize: "0.75rem",
                  color: "#94a3b8",
                }}
              >
                Solo un administrador puede cambiar el nombre.
              </p>
            )}
          </div>

          {/* Campo Descripción */}
          <div style={{ marginBottom: "1rem" }}>
            <label
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontWeight: "500",
              }}
            >
              Descripción
            </label>
            <textarea
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              rows={3}
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                fontSize: "0.875rem",
                outline: "none",
                boxSizing: "border-box",
                resize: "vertical",
              }}
              placeholder="Descripción del proyecto"
            />
          </div>

          {/* Campo Estado */}
          <div style={{ marginBottom: "1rem" }}>
            <label
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontWeight: "500",
              }}
            >
              Estado
            </label>
            <select
              value={formData.status}
              onChange={(e) =>
                setFormData({ ...formData, status: e.target.value })
              }
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                fontSize: "0.875rem",
                outline: "none",
                boxSizing: "border-box",
              }}
            >
              <option value="all">Todos los estados</option>
              <option value="draft">Borrador</option>
              <option value="review">Pendiente de Redacción</option>
              <option value="in_progress">En Redacción</option>
              <option value="pen_review">Pendiente de Revisión</option>
              <option value="pen_ajuste">Pendiente de Ajuste</option>
              <option value="ajuste_aplicado">Ajuste Aplicado</option>
              <option value="approved">Aprobado</option>
              <option value="rev_kws">Pendiente KWS</option>
              <option value="cargue">Cargue</option>
              <option value="en_it">En IT</option>
              <option value="test">Test</option>
              <option value="completed">Publicado</option>
            </select>
          </div>

          {/* Campo Prioridad */}
          <div style={{ marginBottom: "1.5rem" }}>
            <label
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontWeight: "500",
              }}
            >
              Prioridad
            </label>
            <select
              value={formData.priority}
              onChange={(e) =>
                setFormData({ ...formData, priority: e.target.value })
              }
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                fontSize: "0.875rem",
                outline: "none",
                boxSizing: "border-box",
              }}
            >
              <option value="low">Baja</option>
              <option value="medium">Media</option>
              <option value="high">Alta</option>
            </select>
          </div>

          {/* Botones */}
          <div
            style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}
          >
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: "0.5rem 1rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                backgroundColor: "white",
                color: "#374151",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.6 : 1,
              }}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !formData.name.trim()}
              style={{
                padding: "0.5rem 1rem",
                border: "none",
                borderRadius: "0.375rem",
                backgroundColor:
                  loading || !formData.name.trim() ? "#94a3b8" : "#1e5fd6",
                color: "white",
                cursor:
                  loading || !formData.name.trim() ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Guardando..." : "Guardar Cambios"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Dashboard;
