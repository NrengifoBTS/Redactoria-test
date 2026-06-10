// Helpers de rol. La fuente de verdad es `user.role` que viene de /users/me.
// Roles posibles: "master" | "admin" | "editor" | "redactor".
// Jerarquía: master > admin > editor > redactor.
//
// IMPORTANTE: estas funciones reciben el OBJETO usuario (currentUser), no el id.

export const ROLES = {
  MASTER: "master",
  ADMIN: "admin",
  EDITOR: "editor",
  REDACTOR: "redactor",
};

export const getRole = (user) => user?.role || ROLES.REDACTOR;

export const isMaster = (user) => getRole(user) === ROLES.MASTER;

// admin o master (master hereda todas las capacidades de admin).
export const isAdminUser = (user) =>
  getRole(user) === ROLES.ADMIN || isMaster(user);

export const isEditorUser = (user) => getRole(user) === ROLES.EDITOR;

// Supervisor = editor, admin o master (pueden ver/editar contenido de otros y crear blogs).
export const isSupervisor = (user) => isAdminUser(user) || isEditorUser(user);

// Capacidades nombradas (espejan la matriz de permisos del backend).
export const canCreateLandingPage = (user) => isAdminUser(user);
export const canCreateBlog = (user) => isSupervisor(user);
export const canViewAnalytics = (user) => isAdminUser(user);
// Solo master gestiona usuarios.
export const canManageUsers = (user) => isMaster(user);

// Etiqueta legible del rol para mostrar en la UI.
export const roleLabel = (user) => {
  switch (getRole(user)) {
    case ROLES.MASTER:
      return "Master";
    case ROLES.ADMIN:
      return "Administrador";
    case ROLES.EDITOR:
      return "Editor";
    default:
      return "Redactor";
  }
};
