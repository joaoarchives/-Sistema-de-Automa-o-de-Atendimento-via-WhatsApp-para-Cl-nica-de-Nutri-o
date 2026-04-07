import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/api";

export default function Login() {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setErro("");
    setLoading(true);
    try {
      const res = await login(usuario, senha);
      localStorage.setItem("token", res.data.token);
      navigate("/agenda/dia");
    } catch (error) {
      setErro(error?.response?.data?.erro || "Usuário ou senha incorretos.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.wrapper}>
      <form style={styles.card} onSubmit={handleSubmit}>
        <div style={styles.logoWrap}>
          <img src="/brand-mark.png" alt="Paulo Jordão" style={styles.logoMark} />
        </div>
        <h1 style={styles.titulo}>Paulo Jordão</h1>
        <div style={styles.fieldGroup}>
          <label style={styles.label}>Usuário</label>
          <input
            type="text"
            placeholder="drpaulo"
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
            style={styles.input}
            autoFocus
            required
          />
        </div>

        <div style={styles.fieldGroup}>
          <label style={styles.label}>Senha</label>
          <input
            type="password"
            placeholder="••••••••"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            style={styles.input}
            required
          />
        </div>

        {erro && <p style={styles.erro}>{erro}</p>}

        <button type="submit" style={styles.btn} disabled={loading}>
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}

const styles = {
  wrapper: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#0d1117",
    fontFamily: "system-ui, sans-serif",
  },
  card: {
    background: "#161b22",
    border: "0.5px solid #30363d",
    borderRadius: 14,
    padding: "40px 36px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 12,
    width: 320,
  },
  logoWrap: {
    width: 44,
    height: 44,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  logoMark: {
    width: 44,
    height: 44,
    borderRadius: 12,
    objectFit: "cover",
    boxShadow: "0 10px 22px rgba(0,0,0,0.28)",
  },
  logoDot: {
    width: 14,
    height: 14,
    borderRadius: "50%",
    background: "#00b37e",
  },
  titulo: { margin: 0, fontSize: 20, fontWeight: 600, color: "#e6edf3" },
  sub: { margin: 0, fontSize: 13, color: "#8b949e" },
  fieldGroup: { width: "100%", display: "flex", flexDirection: "column", gap: 6 },
  label: { fontSize: 13, color: "#8b949e", textAlign: "left" },
  input: {
    width: "100%",
    padding: "10px 14px",
    borderRadius: 8,
    border: "0.5px solid #30363d",
    background: "#0d1117",
    color: "#e6edf3",
    fontSize: 14,
    boxSizing: "border-box",
    outline: "none",
  },
  erro: { color: "#f85149", fontSize: 13, margin: 0 },
  btn: {
    width: "100%",
    padding: "11px 0",
    background: "#00b37e",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    marginTop: 4,
  },
};
