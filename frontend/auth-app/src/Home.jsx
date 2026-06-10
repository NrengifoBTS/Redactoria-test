import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useApp } from "./context/AppContext";
import LoginModal from "./Loginmodal";
import { Cpu, Sparkles, Target, LayoutTemplate, Newspaper, ArrowUpRight } from "lucide-react";
import "./Home.css";
import milesLogo from "./img/Miles-car-rental.png";
import viajemosLogo from "./img/logo-viajemos.png";

const Home = () => {
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const { currentUser, logout } = useApp();
  const handleLogout = () => {
    logout();
  };

  // Cada destino: si hay sesión navega; si no, abre el login.
  const handleDestino = (url) => {
    if (currentUser) {
      window.location.href = url;
    } else {
      setIsLoginModalOpen(true);
    }
  };

  const getAvatarText = () => {
    if (!currentUser) return "";
    if (currentUser.avatar) return currentUser.avatar;
    if (currentUser.first_name || currentUser.last_name) {
      return `${(currentUser.first_name?.[0] || "").toUpperCase()}${(currentUser.last_name?.[0] || "").toUpperCase()}`;
    }
    return (currentUser.email?.[0] || "").toUpperCase();
  };

  const getDisplayName = () => {
    if (!currentUser) return "";
    if (currentUser.name) return currentUser.name;
    if (currentUser.first_name || currentUser.last_name) {
      return `${currentUser.first_name || ""} ${currentUser.last_name || ""}`.trim();
    }
    return currentUser.email || "";
  };
  // Solo trabajamos dos marcas; cada una con dos destinos: Landing Pages y Blogs.
  const marcas = [
    {
      id: "miles",
      nombre: "Miles Car Rental",
      etiqueta: "Alquiler de vehículos",
      logo: milesLogo,
      sitio: "https://www.milescarrental.com",
      descripcion:
        "Redacción y gestión de contenido con IA para las landing pages y el blog de Miles Car Rental.",
      destinos: [
        {
          tipo: "Landing Pages",
          url: "/dashboard/mcr",
          descripcion: "Genera y publica landing pages de MCR",
          icon: LayoutTemplate,
        },
        {
          tipo: "Blogs",
          url: "/dashboard_blog",
          descripcion: "Escribe y administra artículos del blog",
          icon: Newspaper,
        },
      ],
    },
    {
      id: "viajemos",
      nombre: "Viajemos",
      etiqueta: "Agencia de viajes",
      logo: viajemosLogo,
      sitio: "https://www.viajemos.com",
      descripcion:
        "Generación optimizada de artículos y landing pages para el ecosistema de contenido de Viajemos.",
      destinos: [
        {
          tipo: "Landing Pages",
          url: "/dashboard/viajemos",
          descripcion: "Genera y publica landing pages de Viajemos",
          icon: LayoutTemplate,
        },
        {
          tipo: "Blogs",
          url: "/dashboard_blog",
          descripcion: "Escribe y administra artículos del blog",
          icon: Newspaper,
        },
      ],
    },
  ];

  // Logos de empresas con sus redes sociales
  const empresasClientes = [
    {
      nombre: "MCR",
      logo: milesLogo,
      url: "https://www.milescarrental.com",
      redes: [
        {
          nombre: "Facebook",
          url: "https://web.facebook.com/MilesCarRental.ES",
          icon: "M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z",
        },
        {
          nombre: "TikTok",
          url: "https://www.tiktok.com/@milescarrental",
          icon: "M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z",
        },
        {
          nombre: "Instagram",
          url: "https://www.instagram.com/milescarrental.com_/",
          icon: "M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z",
        },
      ],
    },
    {
      nombre: "VJS",
      logo: viajemosLogo,
      url: "https://www.viajemos.com",
      redes: [
        {
          nombre: "Facebook",
          url: "https://www.facebook.com/Viajemoscom-106478295647370",
          icon: "M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z",
        },
        {
          nombre: "TikTok",
          url: "https://www.tiktok.com/@viajemos.com_",
          icon: "M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z",
        },
        {
          nombre: "Instagram",
          url: "https://www.instagram.com/viajemos.com_/",
          icon: "M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z",
        },
      ],
    },
  ];

  return (
    <div className="home-container">
      {/* Header con Logo */}
      <header className="main-header">
        <div className="header-content">
          <Link to="/home" className="logo-link">
            <div className="logo">
              <img
                src="https://browsertravelsolutions.com/wp-content/uploads/2022/02/Logo-1.png"
                alt="Logo BTS"
                className="logo-image"
              />
              <span className="logo-text">Presents Omina test </span>
            </div>
          </Link>
          <nav className="header-nav">
            {currentUser ? (
              <div className="user-menu">
                <div className="user-avatar">{getAvatarText()}</div>
                <span className="user-name">{getDisplayName()}</span>

                <button onClick={handleLogout} className="logout-button">
                  Cerrar Sesión
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsLoginModalOpen(true)}
                className="nav-link nav-link-primary"
                style={{ border: "none", cursor: "pointer" }}
              >
                Iniciar Sesión
              </button>
            )}
          </nav>
        </div>
      </header>

      <div className="hero-section">
        <div className="hero-content">
          <div className="hero-badge">
            <span>Redacción con IA</span>
          </div>
          <h1 className="hero-title">Omina</h1>
          <p className="hero-subtitle">
            La plataforma de contenido para Miles Car Rental y Viajemos. Genera
            landing pages y artículos de blog optimizados, en un solo lugar.
          </p>
        </div>
      </div>

      {/* Sección de Marcas — solo Miles y Viajemos, cada una con LPs y Blogs */}
      <div className="marcas-section">
        <div className="section-header">
          <h2 className="section-title">Elige dónde quieres trabajar</h2>
          <p className="section-subtitle">
            Dos marcas, dos tipos de contenido. Entra directo al panel que
            necesitas.
          </p>
        </div>

        <div className="marcas-grid">
          {marcas.map((marca) => (
            <article key={marca.id} className="marca-card">
              <div className="marca-head">
                <div className="marca-logo-box">
                  <img
                    src={marca.logo}
                    alt={`Logo de ${marca.nombre}`}
                    className="marca-logo"
                  />
                </div>
                <div className="marca-meta">
                  <span className="marca-etiqueta">{marca.etiqueta}</span>
                  <h3 className="marca-nombre">{marca.nombre}</h3>
                </div>
              </div>

              <p className="marca-descripcion">{marca.descripcion}</p>

              <div className="marca-destinos">
                {marca.destinos.map((destino) => {
                  const Icon = destino.icon;
                  return (
                    <button
                      key={destino.tipo}
                      type="button"
                      className="destino-btn"
                      onClick={() => handleDestino(destino.url)}
                    >
                      <span className="destino-icon">
                        <Icon strokeWidth={1.75} />
                      </span>
                      <span className="destino-texto">
                        <span className="destino-tipo">{destino.tipo}</span>
                        <span className="destino-desc">
                          {destino.descripcion}
                        </span>
                      </span>
                      <ArrowUpRight className="destino-flecha" strokeWidth={2} />
                    </button>
                  );
                })}
              </div>

              {!currentUser && (
                <p className="marca-nota">
                  Inicia sesión para abrir cualquiera de los paneles.
                </p>
              )}
            </article>
          ))}
        </div>
      </div>

      {/* Sección About */}
      <div className="about-section">
        <div className="about-content">
          <div className="about-text">
            <h2 className="about-title">Sobre Nuestra Área</h2>
            <p className="about-paragraph">
              Somos un equipo dedicado al desarrollo de soluciones tecnológicas
              innovadoras que transforman la manera en que las empresas operan y
              crecen en la era digital.
            </p>
            <p className="about-paragraph">
              Nuestro ecosistema integrado de herramientas está diseñado para
              maximizar la eficiencia, mejorar la colaboración y potenciar la
              toma de decisiones basada en datos.
            </p>
            {/* Dashboard general solo accesible por URL directa - no mostrar link */}
          </div>

          <div className="about-features">
            <div className="feature-box">
              <div className="feature-item">
                <div className="feature-icon">
                  <Cpu strokeWidth={1.75} />
                </div>
                <div className="feature-content">
                  <h4 className="feature-title">Tecnología de Vanguardia</h4>
                  <p className="feature-text">Stack moderno y escalable</p>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon">
                  <Sparkles strokeWidth={1.75} />
                </div>
                <div className="feature-content">
                  <h4 className="feature-title">IA Integrada</h4>
                  <p className="feature-text">Automatización inteligente</p>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon">
                  <Target strokeWidth={1.75} />
                </div>
                <div className="feature-content">
                  <h4 className="feature-title">Enfoque en Resultados</h4>
                  <p className="feature-text">Soluciones que generan valor</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="footer">
        {/* Logos de Empresas Clientes */}
        <div className="empresas-section">
          <p className="empresas-title">Empresas con las que trabajamos</p>
          <div className="empresas-grid">
            {empresasClientes.map((empresa, index) => (
              <div key={index} className="empresa-card">
                <a
                  href={empresa.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="empresa-logo-link"
                >
                  <div className="empresa-logo-card">
                    <img
                      src={empresa.logo}
                      alt={empresa.nombre}
                      className="empresa-logo"
                    />
                  </div>
                </a>

                {/* Redes sociales de cada empresa */}
                <div className="empresa-redes">
                  {empresa.redes.map((red, redIndex) => (
                    <a
                      key={redIndex}
                      href={red.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="empresa-social-link"
                      title={red.nombre}
                    >
                      <svg
                        className="empresa-social-icon"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d={red.icon} />
                      </svg>
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="footer-copyright">
          <p>© 2025 Browser Travel SOLUTIONS. Todos los derechos reservados.</p>
        </div>
      </footer>
      {/* Modal de Login */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />
    </div>
  );
};

export default Home;
