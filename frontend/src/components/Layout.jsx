import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { CalendarDays, CalendarRange, ClipboardList, MessageCircle, LogOut } from "lucide-react";

const links = [
  { to: "/agenda/dia",    label: "Agenda do Dia",    Icon: CalendarDays },
  { to: "/agenda/semana", label: "Agenda da Semana", Icon: CalendarRange },
  { to: "/historico",     label: "Histórico",        Icon: ClipboardList },
  { to: "/conversas",     label: "Conversas",        Icon: MessageCircle },
];

export default function Layout() {
  const navigate = useNavigate();

  function sair() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  return (
      <div style={styles.wrapper}>
        <aside style={styles.sidebar}>
          <div style={styles.logoWrap}>
            <div style={styles.logoDot} />
            <div>
              <div style={styles.logoTitle}>Paulo Jordão</div>
              <div style={styles.logoSub}>Nutrição & Performance</div>
            </div>
          </div>

          <nav style={styles.nav}>
            {links.map(({ to, label, Icon }) => (
                <NavLink
                    key={to}
                    to={to}
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
          <Outlet />
        </main>
      </div>
  );
}

const styles = {
  wrapper: {
    display: "flex",
    minHeight: "100vh",
    fontFamily: "system-ui, sans-serif",
    background: "#0d1117",
  },
  sidebar: {
    width: 220,
    background: "#161b22",
    borderRight: "0.5px solid #30363d",
    color: "#e6edf3",
    display: "flex",
    flexDirection: "column",
    padding: "20px 0",
    position: "sticky",
    top: 0,
    height: "100vh",
  },
  logoWrap: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "0 20px 20px",
    borderBottom: "0.5px solid #30363d",
    marginBottom: 8,
  },
  logoDot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    background: "#00b37e",
    flexShrink: 0,
  },
  logoTitle: { fontSize: 14, fontWeight: 600, color: "#e6edf3" },
  logoSub:   { fontSize: 11, color: "#8b949e", marginTop: 1 },
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
    padding: "9px 20px",
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
    padding: "8px 12px",
    background: "transparent",
    border: "0.5px solid #30363d",
    color: "#8b949e",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 13,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  main: {
    flex: 1,
    padding: 32,
    overflowY: "auto",
    background: "#0d1117",
  },
};