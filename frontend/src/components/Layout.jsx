import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { CalendarDays, CalendarRange, ClipboardList, MessageCircle, LogOut, Menu, X } from "lucide-react";
import useViewport from "../hooks/useViewport";

const links = [
  { to: "/agenda/dia", label: "Agenda do Dia", Icon: CalendarDays },
  { to: "/agenda/semana", label: "Agenda da Semana", Icon: CalendarRange },
  { to: "/historico", label: "Histórico", Icon: ClipboardList },
  { to: "/conversas", label: "Conversas", Icon: MessageCircle },
];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isMobile } = useViewport();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname, isMobile]);

  function sair() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  const paginaAtual = useMemo(
    () => links.find((item) => location.pathname.startsWith(item.to))?.label || "Paulo Jordão",
    [location.pathname],
  );

  return (
    <div style={styles.wrapper}>
      {isMobile && menuOpen && <button type="button" style={styles.overlay} onClick={() => setMenuOpen(false)} aria-label="Fechar menu" />}

      <aside
        style={{
          ...styles.sidebar,
          ...(isMobile ? styles.sidebarMobile : {}),
          ...(isMobile && menuOpen ? styles.sidebarMobileOpen : {}),
        }}
      >
        <div style={styles.logoWrap}>
          <img src="/brand-mark.png" alt="Paulo Jordão" style={styles.logoMark} />
          <div style={styles.logoTextWrap}>
            <div style={styles.logoTitle}>Paulo Jordão</div>
            <div style={styles.logoSub}>Nutrição & Performance</div>
          </div>
          {isMobile && (
            <button type="button" style={styles.iconButton} onClick={() => setMenuOpen(false)} aria-label="Fechar menu">
              <X size={18} />
            </button>
          )}
        </div>

        <nav style={styles.nav}>
          {links.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => isMobile && setMenuOpen(false)}
              style={({ isActive }) => ({
                ...styles.link,
                ...(isActive ? styles.linkAtivo : {}),
              })}
            >
              <Icon size={16} strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </nav>

        <button style={styles.sair} onClick={sair}>
          <LogOut size={14} strokeWidth={1.8} />
          Sair
        </button>
      </aside>

      <main style={styles.main}>
        {isMobile && (
          <header style={styles.mobileHeader}>
            <button type="button" style={styles.iconButton} onClick={() => setMenuOpen(true)} aria-label="Abrir menu">
              <Menu size={20} />
            </button>
            <div style={styles.mobileHeaderText}>
              <div style={styles.mobileBrand}>Paulo Jordão</div>
              <div style={styles.mobilePage}>{paginaAtual}</div>
            </div>
          </header>
        )}

        <div style={{ ...styles.content, ...(isMobile ? styles.contentMobile : {}) }}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}

const styles = {
  wrapper: {
    display: "flex",
    minHeight: "100vh",
    width: "100%",
    maxWidth: "100%",
    background: "#0d1117",
    color: "#e6edf3",
    position: "relative",
    overflow: "hidden",
  },
  overlay: {
    position: "fixed",
    inset: 0,
    border: "none",
    background: "rgba(3, 7, 12, 0.62)",
    zIndex: 30,
  },
  sidebar: {
    width: 220,
    flexShrink: 0,
    background: "#161b22",
    borderRight: "0.5px solid #30363d",
    color: "#e6edf3",
    display: "flex",
    flexDirection: "column",
    padding: "20px 0",
    position: "sticky",
    top: 0,
    height: "100vh",
    zIndex: 40,
  },
  sidebarMobile: {
    position: "fixed",
    left: 0,
    top: 0,
    bottom: 0,
    width: "min(84vw, 320px)",
    maxWidth: 320,
    transform: "translateX(-104%)",
    transition: "transform 0.24s ease",
    boxShadow: "0 18px 42px rgba(0,0,0,0.36)",
    paddingTop: "calc(18px + env(safe-area-inset-top, 0px))",
  },
  sidebarMobileOpen: {
    transform: "translateX(0)",
  },
  logoWrap: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "0 20px 20px",
    borderBottom: "0.5px solid #30363d",
    marginBottom: 8,
  },
  logoTextWrap: {
    flex: 1,
    minWidth: 0,
  },
  logoMark: {
    width: 42,
    height: 42,
    borderRadius: 12,
    objectFit: "cover",
    flexShrink: 0,
    boxShadow: "0 8px 18px rgba(0,0,0,0.28)",
  },
  logoTitle: { fontSize: 14, fontWeight: 600, color: "#e6edf3" },
  logoSub: { fontSize: 11, color: "#8b949e", marginTop: 1 },
  nav: {
    display: "flex",
    flexDirection: "column",
    flex: 1,
    gap: 2,
    padding: "8px 0",
  },
  link: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "12px 20px",
    color: "#8b949e",
    textDecoration: "none",
    fontSize: 13,
    transition: "background 0.15s, color 0.15s",
    borderLeft: "2px solid transparent",
  },
  linkAtivo: {
    background: "#1c2128",
    color: "#e6edf3",
    borderLeft: "2px solid #00b37e",
  },
  sair: {
    margin: "0 16px",
    padding: "10px 12px",
    background: "transparent",
    border: "0.5px solid #30363d",
    color: "#8b949e",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 13,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  main: {
    flex: 1,
    minWidth: 0,
    width: "100%",
    maxWidth: "100%",
    display: "flex",
    flexDirection: "column",
    background: "#0d1117",
    overflow: "hidden",
  },
  mobileHeader: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "calc(12px + env(safe-area-inset-top, 0px)) 16px 12px",
    borderBottom: "0.5px solid #30363d",
    background: "rgba(13, 17, 23, 0.96)",
    backdropFilter: "blur(12px)",
    position: "sticky",
    top: 0,
    zIndex: 20,
  },
  iconButton: {
    width: 38,
    height: 38,
    borderRadius: 10,
    border: "0.5px solid #30363d",
    background: "#161b22",
    color: "#e6edf3",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    flexShrink: 0,
  },
  mobileHeaderText: {
    minWidth: 0,
  },
  mobileBrand: {
    fontSize: 14,
    fontWeight: 700,
    color: "#e6edf3",
  },
  mobilePage: {
    marginTop: 2,
    fontSize: 12,
    color: "#8b949e",
  },
  content: {
    flex: 1,
    width: "100%",
    maxWidth: "100%",
    minWidth: 0,
    overflowY: "auto",
    overflowX: "hidden",
    padding: 32,
  },
  contentMobile: {
    padding: 16,
    paddingBottom: "calc(20px + env(safe-area-inset-bottom, 0px))",
  },
};
