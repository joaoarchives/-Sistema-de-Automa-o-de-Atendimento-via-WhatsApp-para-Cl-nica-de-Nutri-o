import { useState, useEffect, useCallback } from "react";
import { MessageCircle, ChevronLeft, Clock, CheckCheck, AlertCircle } from "lucide-react";
import api from "../api/api";

function formatarData(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = Date.now() - d;
  if (diff < 60_000) return "agora";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}min`;
  if (diff < 86_400_000) return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

function formatarHora(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function iconeStatus(status) {
  if (status === "enviado")  return <CheckCheck size={12} color="#8b949e" />;
  if (status === "entregue") return <CheckCheck size={12} color="#00b37e" />;
  if (status === "falhou")   return <AlertCircle size={12} color="#f85149" />;
  return null;
}

function etiquetaTipo(tipo) {
  const mapa = {
    confirmacao:           "confirmação",
    lembrete_24h:          "lembrete 24h",
    lembrete_1h:           "lembrete 1h",
    agendamento_pendente:  "pend. pagamento",
    cancelamento:          "cancelamento",
    confirmacao_pagamento: "pagto confirmado",
  };
  return mapa[tipo] || tipo;
}

export default function Conversas() {
  const [conversas,    setConversas]    = useState([]);
  const [selecionado,  setSelecionado]  = useState(null);
  const [mensagens,    setMensagens]    = useState([]);
  const [loadingLista, setLoadingLista] = useState(false);
  const [loadingChat,  setLoadingChat]  = useState(false);
  const [erro,         setErro]         = useState("");

  const carregarLista = useCallback(async () => {
    setLoadingLista(true);
    setErro("");
    try {
      const res = await api.get("/api/conversas");
      setConversas(res.data.conversas || []);
    } catch {
      setErro("Erro ao carregar conversas.");
    } finally {
      setLoadingLista(false);
    }
  }, []);

  useEffect(() => { carregarLista(); }, [carregarLista]);

  async function abrirConversa(contato) {
    setSelecionado(contato);
    setLoadingChat(true);
    setMensagens([]);
    try {
      const res = await api.get(`/api/conversas/${encodeURIComponent(contato.telefone)}`);
      setMensagens(res.data.mensagens || []);
    } catch {
      setMensagens([]);
    } finally {
      setLoadingChat(false);
    }
  }

  // Layout sem tricks: painel lateral fixo + chat scrollável
  return (
    <div style={s.wrap}>
      {/* lista */}
      <div style={s.painel}>
        <div style={s.painelHeader}>
          <h2 style={s.titulo}>Conversas</h2>
          <p style={s.sub}>{conversas.length} contato(s)</p>
        </div>
        {loadingLista && <p style={s.info}>Carregando...</p>}
        {erro         && <p style={s.erroTxt}>{erro}</p>}
        {!loadingLista && conversas.length === 0 && (
          <div style={s.vazio}>
            <MessageCircle size={28} color="#30363d" />
            <p>Nenhuma conversa ainda.</p>
          </div>
        )}
        <div style={s.lista}>
          {conversas.map((c) => {
            const ativo = selecionado?.telefone === c.telefone;
            return (
              <button key={c.telefone} onClick={() => abrirConversa(c)}
                style={{ ...s.item, ...(ativo ? s.itemAtivo : {}) }}>
                <div style={s.avatar}>{(c.nome?.[0] || "?").toUpperCase()}</div>
                <div style={s.itemInfo}>
                  <div style={s.itemNome}>{c.nome}</div>
                  <div style={s.itemTel}>{c.telefone}</div>
                  <div style={s.itemUltimo}>{etiquetaTipo(c.ultimo_tipo)}</div>
                </div>
                <div style={s.itemMeta}>
                  <span style={s.itemHora}>{formatarData(c.ultima_mensagem)}</span>
                  <span style={s.itemBadge}>{c.total_mensagens}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* chat */}
      <div style={s.chat}>
        {!selecionado ? (
          <div style={s.chatVazio}>
            <MessageCircle size={40} color="#30363d" />
            <p style={{ color: "#8b949e", fontSize: 14, marginTop: 12 }}>Selecione uma conversa</p>
          </div>
        ) : (
          <div style={s.chatInner}>
            <div style={s.chatHeader}>
              <button style={s.voltarBtn} onClick={() => setSelecionado(null)}>
                <ChevronLeft size={16} />
              </button>
              <div style={s.avatar}>{(selecionado.nome?.[0] || "?").toUpperCase()}</div>
              <div>
                <div style={s.chatNome}>{selecionado.nome}</div>
                <div style={s.chatTel}>{selecionado.telefone}</div>
              </div>
            </div>
            <div style={s.mensagensWrap}>
              {loadingChat && <p style={s.info}>Carregando mensagens...</p>}
              {!loadingChat && mensagens.length === 0 && <p style={s.info}>Nenhuma mensagem encontrada.</p>}
              {mensagens.map((m) => (
                <div key={m.id} style={s.bolha}>
                  <div style={s.bolhaHeader}>
                    <span style={s.bolhaTipo}>{etiquetaTipo(m.tipo_mensagem)}</span>
                    <span style={s.bolhaHora}>
                      <Clock size={10} style={{ marginRight: 3 }} />
                      {formatarHora(m.criado_em)}
                    </span>
                  </div>
                  <p style={s.bolhaTexto}>{typeof m.texto === 'string' ? m.texto : JSON.stringify(m.texto)}</p>
                  <div style={s.bolhaFooter}>
                    {iconeStatus(m.status_envio)}
                    <span style={s.statusTxt}>{m.status_envio}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const s = {
  wrap: {
    display: "flex",
    marginTop: -32,
    marginLeft: -32,
    marginRight: -32,
    marginBottom: -32,
    height: "calc(100vh - 0px)",
    background: "#0d1117",
    overflow: "hidden",
  },
  painel: {
    width: 280,
    minWidth: 280,
    borderRight: "0.5px solid #30363d",
    display: "flex",
    flexDirection: "column",
    height: "100%",
    overflow: "hidden",
  },
  painelHeader: { padding: "24px 20px 16px", borderBottom: "0.5px solid #30363d", flexShrink: 0 },
  titulo:  { margin: 0, fontSize: 18, fontWeight: 600, color: "#e6edf3" },
  sub:     { margin: "4px 0 0", fontSize: 12, color: "#8b949e" },
  info:    { color: "#8b949e", fontSize: 13, padding: "16px 20px" },
  erroTxt: { color: "#f85149", fontSize: 13, padding: "16px 20px" },
  vazio: {
    display: "flex", flexDirection: "column", alignItems: "center",
    justifyContent: "center", flex: 1, color: "#8b949e", fontSize: 13, gap: 8,
  },
  lista: { flex: 1, overflowY: "auto" },
  item: {
    width: "100%", display: "flex", alignItems: "flex-start", gap: 10,
    padding: "12px 16px", background: "transparent", border: "none",
    borderBottom: "0.5px solid #21262d", cursor: "pointer", textAlign: "left",
  },
  itemAtivo: { background: "#1c2128" },
  avatar: {
    width: 36, height: 36, borderRadius: "50%", background: "#00b37e22", color: "#00b37e",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 14, fontWeight: 700, flexShrink: 0,
  },
  itemInfo:   { flex: 1, minWidth: 0 },
  itemNome:   { fontSize: 13, fontWeight: 500, color: "#e6edf3", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  itemTel:    { fontSize: 11, color: "#8b949e", marginTop: 1 },
  itemUltimo: { fontSize: 11, color: "#58a6ff", marginTop: 3, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  itemMeta:   { display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 },
  itemHora:   { fontSize: 11, color: "#8b949e" },
  itemBadge:  { background: "#00b37e22", color: "#00b37e", borderRadius: 10, fontSize: 10, padding: "1px 6px", fontWeight: 600 },
  chat: { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", height: "100%" },
  chatVazio: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" },
  chatInner: { display: "flex", flexDirection: "column", height: "100%" },
  chatHeader: {
    display: "flex", alignItems: "center", gap: 12, padding: "16px 20px",
    borderBottom: "0.5px solid #30363d", flexShrink: 0,
  },
  voltarBtn: { display: "none", background: "transparent", border: "none", color: "#8b949e", cursor: "pointer" },
  chatNome: { fontSize: 14, fontWeight: 600, color: "#e6edf3" },
  chatTel:  { fontSize: 12, color: "#8b949e" },
  mensagensWrap: {
    flex: 1, overflowY: "auto", padding: 20,
    display: "flex", flexDirection: "column", gap: 10,
  },
  bolha: { background: "#161b22", border: "0.5px solid #30363d", borderRadius: 10, padding: "10px 14px", maxWidth: 520 },
  bolhaHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  bolhaTipo:   { fontSize: 11, fontWeight: 600, color: "#58a6ff", background: "#58a6ff15", borderRadius: 4, padding: "2px 6px" },
  bolhaHora:   { display: "flex", alignItems: "center", fontSize: 11, color: "#8b949e" },
  bolhaTexto:  { margin: 0, fontSize: 13, color: "#e6edf3", lineHeight: 1.55, whiteSpace: "pre-wrap" },
  bolhaFooter: { display: "flex", alignItems: "center", gap: 4, marginTop: 6 },
  statusTxt:   { fontSize: 11, color: "#8b949e" },
};