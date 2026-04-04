import { useState, useEffect, useRef } from "react";
import { getConversas, getMensagensPaciente } from "../api/api";

function formatarHora(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function Conversas() {
  const [conversas,  setConversas]  = useState([]);
  const [ativa,      setAtiva]      = useState(null);
  const [mensagens,  setMensagens]  = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [loadingMsg, setLoadingMsg] = useState(false);
  const [busca,      setBusca]      = useState("");
  const fimRef = useRef(null);

  // Carrega lista de conversas
  useEffect(() => {
    setLoading(true);
    getConversas()
      .then((r) => setConversas(r.data.conversas || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Carrega mensagens da conversa ativa
  useEffect(() => {
    if (!ativa) return;
    setLoadingMsg(true);
    getMensagensPaciente(ativa.telefone)
      .then((r) => setMensagens(r.data.mensagens || []))
      .catch(() => setMensagens([]))
      .finally(() => setLoadingMsg(false));
  }, [ativa]);

  // Scroll para o fim ao abrir conversa
  useEffect(() => {
    if (fimRef.current) {
      fimRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [mensagens]);

  const conversasFiltradas = conversas.filter((c) =>
    c.nome?.toLowerCase().includes(busca.toLowerCase()) ||
    c.telefone?.includes(busca)
  );

  return (
    <div style={styles.wrapper}>
      {/* ── Sidebar: lista de conversas ── */}
      <div style={styles.sidebar}>
        <div style={styles.sideHeader}>
          <h2 style={styles.titulo}>Conversas</h2>
          <input
            style={styles.busca}
            placeholder="Buscar paciente..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>

        {loading && <p style={styles.info}>Carregando...</p>}

        <div style={styles.lista}>
          {conversasFiltradas.map((c) => (
            <div
              key={c.telefone}
              style={{
                ...styles.item,
                ...(ativa?.telefone === c.telefone ? styles.itemAtivo : {}),
              }}
              onClick={() => setAtiva(c)}
            >
              <div style={styles.avatar}>
                {(c.nome?.[0] || "?").toUpperCase()}
              </div>
              <div style={styles.itemInfo}>
                <div style={styles.itemNome}>{c.nome || c.telefone}</div>
                <div style={styles.itemPreview}>
                  {c.direcao === "recebida" ? "👤 " : "🤖 "}
                  {c.preview || "—"}
                </div>
              </div>
              <div style={styles.itemHora}>{formatarHora(c.criado_em)}</div>
            </div>
          ))}
          {!loading && conversasFiltradas.length === 0 && (
            <p style={styles.info}>Nenhuma conversa encontrada.</p>
          )}
        </div>
      </div>

      {/* ── Área de chat ── */}
      <div style={styles.chat}>
        {!ativa ? (
          <div style={styles.vazio}>
            <div style={styles.vazioIcon}>💬</div>
            <p>Selecione uma conversa para ver o histórico.</p>
          </div>
        ) : (
          <>
            {/* Header do chat */}
            <div style={styles.chatHeader}>
              <div style={styles.avatar}>{(ativa.nome?.[0] || "?").toUpperCase()}</div>
              <div>
                <div style={styles.chatNome}>{ativa.nome || ativa.telefone}</div>
                <div style={styles.chatTel}>{ativa.telefone}</div>
              </div>
            </div>

            {/* Mensagens */}
            <div style={styles.mensagens}>
              {loadingMsg && <p style={styles.info}>Carregando mensagens...</p>}
              {mensagens.map((m) => {
                const recebida = m.direcao === "recebida";
                return (
                  <div
                    key={m.id}
                    style={{
                      ...styles.balaoWrap,
                      justifyContent: recebida ? "flex-start" : "flex-end",
                    }}
                  >
                    <div
                      style={{
                        ...styles.balao,
                        ...(recebida ? styles.balaoCliente : styles.balaoBot),
                      }}
                    >
                      {!recebida && (
                        <div style={styles.balaoLabel}>🤖 Sofia</div>
                      )}
                      <div style={styles.balaoTexto}>
                        {m.texto || <em style={{ color: "#8b949e" }}>[mídia]</em>}
                      </div>
                      <div style={styles.balaoHora}>{formatarHora(m.criado_em)}</div>
                    </div>
                  </div>
                );
              })}
              <div ref={fimRef} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    display: "flex",
    height: "calc(100vh - 64px)",
    gap: 0,
    background: "#0d1117",
    borderRadius: 12,
    overflow: "hidden",
    border: "0.5px solid #30363d",
  },

  // Sidebar
  sidebar: {
    width: 300,
    borderRight: "0.5px solid #30363d",
    display: "flex",
    flexDirection: "column",
    background: "#161b22",
    flexShrink: 0,
  },
  sideHeader: {
    padding: "16px 16px 12px",
    borderBottom: "0.5px solid #30363d",
  },
  titulo: { margin: "0 0 10px", fontSize: 16, fontWeight: 600, color: "#e6edf3" },
  busca: {
    width: "100%",
    padding: "7px 10px",
    borderRadius: 8,
    border: "0.5px solid #30363d",
    background: "#0d1117",
    color: "#e6edf3",
    fontSize: 13,
    outline: "none",
    boxSizing: "border-box",
  },
  lista: { flex: 1, overflowY: "auto" },
  item: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 14px",
    cursor: "pointer",
    borderBottom: "0.5px solid #21262d",
    transition: "background 0.15s",
  },
  itemAtivo: { background: "#1c2128" },
  avatar: {
    width: 36, height: 36, borderRadius: "50%",
    background: "#1A56DB", color: "#fff",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 14, fontWeight: 700, flexShrink: 0,
  },
  itemInfo: { flex: 1, minWidth: 0 },
  itemNome: { fontSize: 13, fontWeight: 500, color: "#e6edf3", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  itemPreview: { fontSize: 11, color: "#8b949e", marginTop: 2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  itemHora: { fontSize: 10, color: "#8b949e", flexShrink: 0 },

  // Chat
  chat: { flex: 1, display: "flex", flexDirection: "column", background: "#0d1117" },
  chatHeader: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "14px 20px",
    borderBottom: "0.5px solid #30363d",
    background: "#161b22",
  },
  chatNome: { fontSize: 14, fontWeight: 600, color: "#e6edf3" },
  chatTel:  { fontSize: 12, color: "#8b949e" },
  mensagens: {
    flex: 1, overflowY: "auto",
    padding: "16px 20px",
    display: "flex", flexDirection: "column", gap: 8,
  },
  balaoWrap: { display: "flex" },
  balao: {
    maxWidth: "70%",
    padding: "8px 12px",
    borderRadius: 12,
    fontSize: 13,
  },
  balaoCliente: {
    background: "#1c2128",
    border: "0.5px solid #30363d",
    borderBottomLeftRadius: 4,
  },
  balaoBot: {
    background: "#0c2d4a",
    border: "0.5px solid #1A56DB44",
    borderBottomRightRadius: 4,
  },
  balaoLabel: { fontSize: 10, color: "#58a6ff", marginBottom: 4, fontWeight: 600 },
  balaoTexto: { color: "#e6edf3", lineHeight: 1.5, whiteSpace: "pre-wrap" },
  balaoHora:  { fontSize: 10, color: "#8b949e", marginTop: 4, textAlign: "right" },

  // Estados
  info:  { color: "#8b949e", fontSize: 13, padding: "12px 16px" },
  vazio: {
    flex: 1, display: "flex", flexDirection: "column",
    alignItems: "center", justifyContent: "center",
    color: "#8b949e", fontSize: 14, gap: 8,
  },
  vazioIcon: { fontSize: 40 },
};
