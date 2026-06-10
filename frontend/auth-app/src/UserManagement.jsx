import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  Pencil,
  Key,
  Ban,
  UserCheck,
  Users,
  ChevronRight,
  ShieldCheck,
  AlertCircle,
  RotateCcw,
} from "lucide-react";
import apiService from "./services/apiService";
import { useApp } from "./context/AppContext";
import { isMaster, roleLabel } from "./utils/roles";

// El master no puede crear otros masters desde la UI (único master del sistema).
const ASSIGNABLE_ROLES = [
  { value: "redactor", label: "Redactor" },
  { value: "editor", label: "Editor" },
  { value: "admin", label: "Administrador" },
];

const EMPTY_CREATE = {
  email: "",
  first_name: "",
  last_name: "",
  password: "",
  role: "redactor",
};

// Estilo de la píldora de rol: monocromo azul/slate, master destacado.
const ROLE_BADGE = {
  master: { background: "#1e5fd6", color: "#ffffff" },
  admin: { background: "var(--accent-50)", color: "var(--accent-700)" },
  editor: { background: "#eef1f5", color: "#475569" },
  redactor: { background: "#f1f5f9", color: "#64748b" },
};

const overlay = {
  position: "fixed",
  inset: 0,
  background: "rgba(15,23,42,0.55)",
  backdropFilter: "blur(6px)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  padding: "20px",
};
const modalBox = {
  background: "#fff",
  border: "1px solid #eef2f7",
  borderTop: "3px solid #1e5fd6",
  borderRadius: "1rem",
  padding: "1.75rem",
  width: "440px",
  maxWidth: "90vw",
  boxShadow: "0 24px 60px -15px rgba(15,23,42,0.35)",
};
const inputStyle = {
  width: "100%",
  padding: "0.6rem 0.8rem",
  border: "1px solid #cbd5e1",
  borderRadius: "0.5rem",
  marginTop: "0.3rem",
  fontSize: "0.9rem",
  boxSizing: "border-box",
  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
};
const labelStyle = {
  fontSize: "0.8rem",
  fontWeight: 600,
  color: "#475569",
  marginTop: "0.85rem",
  display: "block",
};
const btnPrimary = {
  background: "#1e5fd6",
  color: "#fff",
  border: "none",
  borderRadius: "0.6rem",
  padding: "0.6rem 1.1rem",
  cursor: "pointer",
  fontWeight: 600,
  boxShadow: "0 6px 14px -6px rgba(30,95,214,0.6)",
};
const btnGhost = {
  background: "#f1f5f9",
  color: "#475569",
  border: "1px solid #e2e8f0",
  borderRadius: "0.6rem",
  padding: "0.6rem 1.1rem",
  cursor: "pointer",
  fontWeight: 600,
};

function Field({ label, children }) {
  return (
    <label style={labelStyle}>
      {label}
      {children}
    </label>
  );
}

function RoleBadge({ user }) {
  const s = ROLE_BADGE[user.role] || ROLE_BADGE.redactor;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.35rem",
        padding: "0.2rem 0.6rem",
        borderRadius: "999px",
        fontSize: "0.74rem",
        fontWeight: 700,
        letterSpacing: "0.01em",
        background: s.background,
        color: s.color,
      }}
    >
      {user.role === "master" && <ShieldCheck size={13} />}
      {roleLabel(user)}
    </span>
  );
}

function initialsOf(u) {
  const fi = (u.first_name?.[0] || "").toUpperCase();
  const li = (u.last_name?.[0] || "").toUpperCase();
  return fi + li || (u.email?.[0] || "?").toUpperCase();
}

function UserManagement() {
  const navigate = useNavigate();
  const { currentUser, loading: userLoading } = useApp();

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [createForm, setCreateForm] = useState(null); // objeto = modal abierto
  const [editForm, setEditForm] = useState(null); // {id, ...campos}
  const [resetTarget, setResetTarget] = useState(null); // {id, name}
  const [newPassword, setNewPassword] = useState("");
  const [saving, setSaving] = useState(false);

  // Guard de acceso: solo master.
  useEffect(() => {
    if (userLoading) return;
    if (!currentUser) {
      navigate("/login");
      return;
    }
    if (!isMaster(currentUser)) {
      navigate("/dashboard");
    }
  }, [currentUser, userLoading, navigate]);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getUsersRaw();
      setUsers(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message || "Error cargando usuarios");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (currentUser && isMaster(currentUser)) {
      fetchUsers();
    }
  }, [currentUser, fetchUsers]);

  const handleCreate = async () => {
    setSaving(true);
    try {
      await apiService.createUser(createForm);
      setCreateForm(null);
      await fetchUsers();
    } catch (e) {
      alert("No se pudo crear: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    setSaving(true);
    try {
      const { id, ...payload } = editForm;
      await apiService.updateUser(id, payload);
      setEditForm(null);
      await fetchUsers();
    } catch (e) {
      alert("No se pudo actualizar: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!newPassword || newPassword.length < 6) {
      alert("La contraseña debe tener al menos 6 caracteres.");
      return;
    }
    setSaving(true);
    try {
      await apiService.resetUserPassword(resetTarget.id, newPassword);
      setResetTarget(null);
      setNewPassword("");
      alert("Contraseña actualizada.");
    } catch (e) {
      alert("No se pudo resetear: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (user) => {
    const deactivating = user.is_active;
    if (
      deactivating &&
      !window.confirm(
        `¿Desactivar a ${user.first_name} ${user.last_name}? No podrá iniciar sesión, pero conserva su contenido. Podrás reactivarlo cuando quieras.`,
      )
    )
      return;
    try {
      await apiService.setUserActive(user.id, !user.is_active);
      await fetchUsers();
    } catch (e) {
      alert("No se pudo actualizar el estado: " + e.message);
    }
  };

  if (userLoading || !currentUser || !isMaster(currentUser)) {
    return null;
  }

  // Resumen por rol para la cabecera de la tabla.
  const counts = users.reduce(
    (acc, u) => {
      acc.total += 1;
      acc[u.role] = (acc[u.role] || 0) + 1;
      return acc;
    },
    { total: 0, admin: 0, editor: 0, redactor: 0, master: 0 },
  );

  const summary = [
    { label: "Usuarios", value: counts.total, color: "var(--accent)" },
    { label: "Administradores", value: counts.admin + counts.master, color: "#164497" },
    { label: "Editores", value: counts.editor, color: "#0f766e" },
    { label: "Redactores", value: counts.redactor, color: "#475569" },
  ];

  return (
    <div className="um-page" style={{ minHeight: "100dvh", background: "#f5f7fa" }}>
      {/* Header con identidad — igual que LP / Blogs */}
      <header
        style={{
          backgroundColor: "#ffffff",
          backgroundImage:
            "radial-gradient(640px 220px at 0% -60%, rgba(30,95,214,0.08), transparent 70%)",
          borderTop: "3px solid #1e5fd6",
          borderBottom: "1px solid #e2e8f0",
          boxShadow:
            "0 1px 2px rgba(15,23,42,0.04), 0 4px 16px -10px rgba(15,23,42,0.18)",
          padding: "0.9rem 2rem",
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
            gap: "1rem",
            flexWrap: "wrap",
            maxWidth: "1100px",
            margin: "0 auto",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "1.1rem" }}>
            <div
              style={{
                width: "3.4rem",
                height: "3.4rem",
                minWidth: "3.4rem",
                borderRadius: "1rem",
                backgroundColor: "#1e5fd6",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                boxShadow: "0 10px 22px -10px rgba(30,95,214,0.8)",
              }}
            >
              <Users size={26} strokeWidth={1.9} />
            </div>
            <div>
              <nav
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem",
                  fontSize: "0.78rem",
                  color: "#94a3b8",
                  marginBottom: "0.25rem",
                }}
              >
                <span
                  onClick={() => navigate("/home")}
                  style={{ cursor: "pointer", fontWeight: 500, transition: "color 0.2s" }}
                  onMouseOver={(e) => (e.currentTarget.style.color = "#1e5fd6")}
                  onMouseOut={(e) => (e.currentTarget.style.color = "#94a3b8")}
                >
                  Inicio
                </span>
                <ChevronRight size={13} />
                <span style={{ color: "#64748b", fontWeight: 600 }}>Usuarios</span>
              </nav>
              <h1
                style={{
                  margin: 0,
                  fontSize: "1.7rem",
                  fontWeight: 800,
                  letterSpacing: "-0.025em",
                  color: "#0f172a",
                  lineHeight: 1.1,
                }}
              >
                Gestión de usuarios
              </h1>
              <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.9rem", color: "#64748b" }}>
                Crea, edita roles y administra el acceso del equipo
              </p>
            </div>
          </div>

          <button
            className="um-cta"
            onClick={() => setCreateForm({ ...EMPTY_CREATE })}
            style={{ ...btnPrimary, display: "flex", alignItems: "center", gap: "0.5rem" }}
          >
            <Plus size={18} /> Nuevo usuario
          </button>
        </div>
      </header>

      <main style={{ maxWidth: "1100px", margin: "0 auto", padding: "2rem" }}>
        {/* Resumen por rol */}
        <div className="um-summary">
          {summary.map((s) => (
            <div key={s.label} className="um-stat">
              <span className="um-stat-bar" style={{ background: s.color }} />
              <div>
                <div
                  className="um-stat-value"
                  style={{ color: loading ? "transparent" : "#0f172a" }}
                >
                  {loading ? "0" : s.value}
                </div>
                <div className="um-stat-label">{s.label}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Error con reintento */}
        {error && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              background: "#fef2f2",
              border: "1px solid #fecaca",
              color: "#b91c1c",
              padding: "0.85rem 1rem",
              borderRadius: "0.75rem",
              marginBottom: "1rem",
            }}
          >
            <AlertCircle size={18} />
            <span style={{ flex: 1, fontSize: "0.9rem" }}>{error}</span>
            <button
              onClick={fetchUsers}
              style={{
                ...btnGhost,
                padding: "0.4rem 0.8rem",
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
              }}
            >
              <RotateCcw size={15} /> Reintentar
            </button>
          </div>
        )}

        {/* Tabla */}
        <div
          style={{
            background: "#fff",
            borderRadius: "1rem",
            overflow: "hidden",
            border: "1px solid #eef2f7",
            boxShadow:
              "0 1px 2px rgba(15,23,42,0.04), 0 8px 24px -16px rgba(15,23,42,0.12)",
          }}
        >
          <table className="um-table" style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ padding: "0.85rem 1.25rem", textAlign: "left" }}>Usuario</th>
                <th style={{ padding: "0.85rem 1.25rem", textAlign: "left" }}>Email</th>
                <th style={{ padding: "0.85rem 1.25rem", textAlign: "left" }}>Rol</th>
                <th style={{ padding: "0.85rem 1.25rem", textAlign: "right" }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={`sk-${i}`}>
                    <td style={{ padding: "0.9rem 1.25rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                        <span className="um-skel" style={{ width: 36, height: 36, borderRadius: "50%" }} />
                        <span className="um-skel" style={{ width: 140, height: 12 }} />
                      </div>
                    </td>
                    <td style={{ padding: "0.9rem 1.25rem" }}>
                      <span className="um-skel" style={{ width: 180, height: 12 }} />
                    </td>
                    <td style={{ padding: "0.9rem 1.25rem" }}>
                      <span className="um-skel" style={{ width: 80, height: 20, borderRadius: 999 }} />
                    </td>
                    <td style={{ padding: "0.9rem 1.25rem" }}>
                      <span className="um-skel" style={{ width: 96, height: 28, marginLeft: "auto", display: "block" }} />
                    </td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={4}>
                    <div
                      style={{
                        padding: "3rem 1rem",
                        textAlign: "center",
                        color: "#64748b",
                      }}
                    >
                      <Users size={42} style={{ opacity: 0.4, marginBottom: "0.75rem" }} />
                      <p style={{ margin: 0, fontSize: "1.05rem", fontWeight: 600, color: "#334155" }}>
                        Aún no hay usuarios
                      </p>
                      <p style={{ margin: "0.35rem 0 1.25rem", fontSize: "0.9rem" }}>
                        Crea el primer usuario para darle acceso a la plataforma.
                      </p>
                      <button
                        className="um-cta"
                        onClick={() => setCreateForm({ ...EMPTY_CREATE })}
                        style={{
                          ...btnPrimary,
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "0.5rem",
                        }}
                      >
                        <Plus size={18} /> Nuevo usuario
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                users.map((u) => {
                  const targetIsMaster = u.role === "master";
                  const isSelf = u.id === currentUser.id;
                  return (
                    <tr key={u.id} style={u.is_active ? undefined : { background: "#fafbfc" }}>
                      <td style={{ padding: "0.9rem 1.25rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                          <span
                            style={{
                              width: 36,
                              height: 36,
                              minWidth: 36,
                              borderRadius: "50%",
                              background: u.is_active ? "var(--accent)" : "#94a3b8",
                              color: "#fff",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: "0.78rem",
                              fontWeight: 700,
                            }}
                          >
                            {initialsOf(u)}
                          </span>
                          <span style={{ fontWeight: 600, color: u.is_active ? "#1e293b" : "#64748b" }}>
                            {u.first_name} {u.last_name}
                            {isSelf && (
                              <span
                                style={{
                                  marginLeft: "0.5rem",
                                  fontSize: "0.7rem",
                                  fontWeight: 600,
                                  color: "var(--accent-700)",
                                  background: "var(--accent-50)",
                                  padding: "0.1rem 0.45rem",
                                  borderRadius: "999px",
                                }}
                              >
                                Tú
                              </span>
                            )}
                            {!u.is_active && (
                              <span
                                style={{
                                  marginLeft: "0.5rem",
                                  fontSize: "0.7rem",
                                  fontWeight: 600,
                                  color: "#92400e",
                                  background: "#fef3c7",
                                  padding: "0.1rem 0.45rem",
                                  borderRadius: "999px",
                                }}
                              >
                                Inactivo
                              </span>
                            )}
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: "0.9rem 1.25rem", color: "#475569", fontSize: "0.9rem" }}>
                        {u.email}
                      </td>
                      <td style={{ padding: "0.9rem 1.25rem" }}>
                        <RoleBadge user={u} />
                      </td>
                      <td style={{ padding: "0.9rem 1.25rem", textAlign: "right", whiteSpace: "nowrap" }}>
                        <button
                          className="um-act um-act-edit"
                          title="Editar"
                          onClick={() =>
                            setEditForm({
                              id: u.id,
                              first_name: u.first_name,
                              last_name: u.last_name,
                              email: u.email,
                              role: u.role,
                            })
                          }
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="um-act um-act-key"
                          title="Resetear contraseña"
                          onClick={() =>
                            setResetTarget({ id: u.id, name: `${u.first_name} ${u.last_name}` })
                          }
                        >
                          <Key size={16} />
                        </button>
                        <button
                          className={`um-act ${u.is_active ? "um-act-off" : "um-act-on"}`}
                          title={
                            u.is_active
                              ? targetIsMaster
                                ? "No se puede desactivar al master"
                                : isSelf
                                  ? "No puedes desactivar tu cuenta"
                                  : "Desactivar"
                              : "Activar"
                          }
                          disabled={u.is_active && (targetIsMaster || isSelf)}
                          onClick={() => handleToggleActive(u)}
                        >
                          {u.is_active ? <Ban size={16} /> : <UserCheck size={16} />}
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </main>

      {/* Modal crear */}
      {createForm && (
        <div style={overlay} onClick={() => !saving && setCreateForm(null)}>
          <div style={modalBox} onClick={(e) => e.stopPropagation()}>
            <h2 style={{ margin: "0 0 0.25rem", fontSize: "1.25rem", fontWeight: 800, letterSpacing: "-0.02em", color: "#0f172a" }}>
              Nuevo usuario
            </h2>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b" }}>
              Define los datos y el rol de acceso.
            </p>
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <Field label="Nombre">
                <input style={inputStyle} value={createForm.first_name} onChange={(e) => setCreateForm({ ...createForm, first_name: e.target.value })} />
              </Field>
              <Field label="Apellido">
                <input style={inputStyle} value={createForm.last_name} onChange={(e) => setCreateForm({ ...createForm, last_name: e.target.value })} />
              </Field>
            </div>
            <Field label="Email">
              <input style={inputStyle} type="email" value={createForm.email} onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} />
            </Field>
            <Field label="Contraseña inicial">
              <input style={inputStyle} type="text" value={createForm.password} onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })} />
            </Field>
            <Field label="Rol">
              <select style={inputStyle} value={createForm.role} onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}>
                {ASSIGNABLE_ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </Field>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.6rem", marginTop: "1.5rem" }}>
              <button className="um-cta" style={btnGhost} disabled={saving} onClick={() => setCreateForm(null)}>Cancelar</button>
              <button className="um-cta" style={btnPrimary} disabled={saving} onClick={handleCreate}>{saving ? "Creando..." : "Crear usuario"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal editar */}
      {editForm && (
        <div style={overlay} onClick={() => !saving && setEditForm(null)}>
          <div style={modalBox} onClick={(e) => e.stopPropagation()}>
            <h2 style={{ margin: "0 0 0.25rem", fontSize: "1.25rem", fontWeight: 800, letterSpacing: "-0.02em", color: "#0f172a" }}>
              Editar usuario
            </h2>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b" }}>
              Actualiza los datos o el rol de acceso.
            </p>
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <Field label="Nombre">
                <input style={inputStyle} value={editForm.first_name || ""} onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })} />
              </Field>
              <Field label="Apellido">
                <input style={inputStyle} value={editForm.last_name || ""} onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })} />
              </Field>
            </div>
            <Field label="Email">
              <input style={inputStyle} type="email" value={editForm.email || ""} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} />
            </Field>
            <Field label="Rol">
              {editForm.role === "master" ? (
                <input style={{ ...inputStyle, background: "#f3f4f6", color: "#64748b" }} value="Master (no editable)" disabled />
              ) : (
                <select style={inputStyle} value={editForm.role} onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}>
                  {ASSIGNABLE_ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              )}
            </Field>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.6rem", marginTop: "1.5rem" }}>
              <button className="um-cta" style={btnGhost} disabled={saving} onClick={() => setEditForm(null)}>Cancelar</button>
              <button className="um-cta" style={btnPrimary} disabled={saving} onClick={handleUpdate}>{saving ? "Guardando..." : "Guardar cambios"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal reset password */}
      {resetTarget && (
        <div style={overlay} onClick={() => !saving && setResetTarget(null)}>
          <div style={modalBox} onClick={(e) => e.stopPropagation()}>
            <h2 style={{ margin: "0 0 0.25rem", fontSize: "1.25rem", fontWeight: 800, letterSpacing: "-0.02em", color: "#0f172a" }}>
              Resetear contraseña
            </h2>
            <p style={{ margin: 0, color: "#475569", fontSize: "0.9rem" }}>
              Usuario: <strong>{resetTarget.name}</strong>
            </p>
            <Field label="Nueva contraseña">
              <input style={inputStyle} type="text" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Mínimo 6 caracteres" />
            </Field>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.6rem", marginTop: "1.5rem" }}>
              <button className="um-cta" style={btnGhost} disabled={saving} onClick={() => { setResetTarget(null); setNewPassword(""); }}>Cancelar</button>
              <button className="um-cta" style={btnPrimary} disabled={saving} onClick={handleReset}>{saving ? "Guardando..." : "Resetear"}</button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .um-summary {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 1rem;
          margin-bottom: 1.5rem;
        }
        @media (max-width: 720px) {
          .um-summary { grid-template-columns: repeat(2, 1fr); }
        }
        .um-stat {
          position: relative;
          display: flex;
          align-items: center;
          gap: 0.9rem;
          background: #fff;
          border: 1px solid #eef2f7;
          border-radius: 0.9rem;
          padding: 1rem 1.1rem 1rem 1.25rem;
          overflow: hidden;
          box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 8px 24px -16px rgba(15,23,42,0.12);
        }
        .um-stat-bar { position: absolute; left: 0; top: 0; bottom: 0; width: 4px; }
        .um-stat-value {
          font-size: 1.7rem; font-weight: 800; line-height: 1;
          letter-spacing: -0.03em; font-variant-numeric: tabular-nums;
        }
        .um-stat-label {
          margin-top: 0.3rem; font-size: 0.72rem; font-weight: 600;
          text-transform: uppercase; letter-spacing: 0.05em; color: #64748b;
        }

        .um-table thead th {
          background: #f8fafc;
          font-size: 0.72rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: #64748b;
          box-shadow: inset 0 -1px 0 #e2e8f0;
        }
        .um-table tbody tr { transition: background-color 0.15s ease; }
        .um-table tbody tr:not(:first-child) td { border-top: 1px solid #eef2f7; }
        .um-table tbody tr:hover { background-color: #eef3fd; }

        /* Botones de acción de la tabla */
        .um-act {
          width: 34px; height: 34px;
          display: inline-flex; align-items: center; justify-content: center;
          margin-left: 0.4rem;
          background: #f1f5f9;
          color: #64748b;
          border: 1px solid #e2e8f0;
          border-radius: 0.5rem;
          cursor: pointer;
          transition: transform 0.12s ease, background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
        }
        .um-act:hover { transform: translateY(-2px); }
        .um-act:active:not(:disabled) { transform: translateY(0) scale(0.94); }
        .um-act-edit:hover { background: var(--accent-50); color: var(--accent-700); border-color: var(--accent-100); }
        .um-act-key:hover  { background: var(--accent-50); color: var(--accent-700); border-color: var(--accent-100); }
        /* Desactivar = ámbar (reversible, no destructivo). Activar = acento. */
        .um-act-off:hover:not(:disabled) { background: #fef3c7; color: #b45309; border-color: #fde68a; }
        .um-act-on:hover:not(:disabled)  { background: var(--accent-50); color: var(--accent-700); border-color: var(--accent-100); }
        .um-act:disabled { opacity: 0.4; cursor: not-allowed; }

        /* Botones generales: hover/press */
        .um-cta { transition: filter 0.15s ease, transform 0.12s ease, box-shadow 0.15s ease; }
        .um-cta:hover:not(:disabled) { filter: brightness(1.05); }
        .um-cta:active:not(:disabled) { transform: translateY(1px) scale(0.99); }
        .um-cta:disabled { opacity: 0.6; cursor: not-allowed; }

        /* Foco accesible en formularios */
        .um-page input:focus,
        .um-page select:focus {
          outline: none;
          border-color: #1e5fd6 !important;
          box-shadow: 0 0 0 3px rgba(30,95,214,0.15);
        }

        /* Skeleton shimmer */
        .um-skel {
          display: inline-block;
          background: linear-gradient(90deg, #eef2f7 25%, #e2e8f0 37%, #eef2f7 63%);
          background-size: 400% 100%;
          border-radius: 6px;
          animation: umShimmer 1.4s ease infinite;
        }
        @keyframes umShimmer {
          0% { background-position: 100% 50%; }
          100% { background-position: 0 50%; }
        }
        @media (prefers-reduced-motion: reduce) {
          .um-skel { animation: none; }
        }
      `}</style>
    </div>
  );
}

export default UserManagement;
