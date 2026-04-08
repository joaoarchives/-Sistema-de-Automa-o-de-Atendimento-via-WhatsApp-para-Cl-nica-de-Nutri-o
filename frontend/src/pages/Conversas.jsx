import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MessageCircle, Search, CheckCheck, AlertCircle, ArrowLeft } from "lucide-react";
import api from "../api/api";
import useViewport from "../hooks/useViewport";

function formatarDataLista(iso) {
  if (!iso) return "";
  const data = new Date(iso);
  const dia = data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  const hora = data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${dia}, ${hora}`;
}

function formatarHora(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function resumoTexto(texto, fallback = "") {
  const base = String(texto || fallback || "").replace(/\s+/g, " ").trim();
  if (!base) return "Sem mensagens";
  return base.length > 34 ? `${base.slice(0, 34)}...` : base;
}

function iconeStatus(status) {
  if (status === "enviado") return <CheckCheck size={12} color="#94a3b8" />;
  if (status === "entregue") return <CheckCheck size={12} color="#4ade80" />;
  if (status === "falhou") return <AlertCircle size={12} color="#f87171" />;
  return null;
}

function inicial(contato) {
  const numero = String(contato?.telefone || "").replace(/\D/g, "");
  if (numero) return numero.slice(-1);
  const nome = String(contato?.nome || "?").trim();
  return nome[0]?.toUpperCase() || "?";
}

function normalizarSenderType(mensagem) {
  const senderBruto = String(
    mensagem?.senderType ??
      mensagem?.sender ??
      mensagem?.role ??
      mensagem?.author ??
      mensagem?.from ??
      "",
  )
    .trim()
    .toLowerCase();

  if (["client", "cliente", "user", "patient", "paciente"].includes(senderBruto)) return "client";
  if (["bot", "assistant", "system", "sofia"].includes(senderBruto)) return "bot";

  const direction = String(mensagem?.direction ?? "").trim().toLowerCase();
  if (["incoming", "inbound", "received"].includes(direction)) return "client";
  if (["outgoing", "outbound", "sent"].includes(direction)) return "bot";

  if (mensagem?.fromMe === true) return "bot";
  if (mensagem?.fromMe === false) return "client";
  if (mensagem?.isFromUser === true) return "client";
  if (mensagem?.isFromUser === false) return "bot";

  const status = String(mensagem?.status_envio ?? "").trim().toLowerCase();
  if (status === "recebido") return "client";
  if (["enviado", "sent", "delivered", "entregue", "read", "lido", "erro", "falhou"].includes(status)) return "bot";

  return "bot";
}

function isTextoTecnico(valor) {
  const texto = String(valor || "").trim().toLowerCase();
  return ["interactive", "lista", "list", "text", "texto", "image", "document", "media"].includes(texto);
}

function extrairDisplayDoPayload(payload, fallbackMensagem = {}) {
  if (!payload || typeof payload !== "object") {
    return { displayText: "", displaySubtext: "", messageKind: fallbackMensagem?.tipo_mensagem || "unknown" };
  }

  const tipo = String(payload.type ?? fallbackMensagem?.tipo_mensagem ?? fallbackMensagem?.messageType ?? "")
    .trim()
    .toLowerCase();
  const interactive = payload.interactive || {};
  const listReply = interactive.list_reply || payload.list_reply || {};
  const buttonReply = interactive.button_reply || payload.button_reply || payload.button || {};
  const interactiveBody = interactive.body || {};
  const interactiveAction = interactive.action || {};
  const textNode = payload.text;
  const imageNode = payload.image || {};
  const documentNode = payload.document || {};

  if (listReply.title || listReply.id || listReply.description) {
    return {
      displayText: listReply.title || listReply.id || "",
      displaySubtext: listReply.description || "",
      messageKind: "list_reply",
    };
  }

  if (buttonReply.title || buttonReply.text || buttonReply.id) {
    return {
      displayText: buttonReply.title || buttonReply.text || buttonReply.id || "",
      displaySubtext: "",
      messageKind: "button_reply",
    };
  }

  if (tipo === "interactive" || fallbackMensagem?.tipo_mensagem === "lista") {
    return {
      displayText: interactiveBody.text || payload.body?.text || payload.body || "",
      displaySubtext: interactiveAction.button || "",
      messageKind: interactive.type || "interactive",
    };
  }

  if (typeof textNode === "string") return { displayText: textNode, displaySubtext: "", messageKind: "text" };
  if (textNode?.body) return { displayText: textNode.body, displaySubtext: "", messageKind: "text" };
  if (typeof payload.body === "string") return { displayText: payload.body, displaySubtext: "", messageKind: tipo || "text" };
  if (payload.body?.text) return { displayText: payload.body.text, displaySubtext: "", messageKind: tipo || "text" };
  if (imageNode.caption) return { displayText: imageNode.caption, displaySubtext: "", messageKind: "image" };
  if (documentNode.caption || documentNode.filename) {
    return { displayText: documentNode.caption || documentNode.filename || "", displaySubtext: "", messageKind: "document" };
  }

  return { displayText: "", displaySubtext: "", messageKind: tipo || fallbackMensagem?.tipo_mensagem || "unknown" };
}

function melhorFallbackTexto(mensagem, senderType) {
  if (mensagem?.attachments?.length) return "";

  const bruto = String(mensagem?.texto || "").trim();
  if (bruto && !isTextoTecnico(bruto)) return bruto;
  if (mensagem?.tipo_mensagem === "document") return "Documento enviado";
  if (mensagem?.tipo_mensagem === "image") return "Imagem enviada";
  if (mensagem?.tipo_mensagem === "lista" && senderType === "bot") return "Lista enviada";
  if (mensagem?.tipo_mensagem === "interactive" && senderType === "client") return "Resposta interativa";
  return "";
}

function normalizarMensagem(mensagem) {
  const senderType = normalizarSenderType(mensagem);
  const { displayText, displaySubtext, messageKind } = extrairDisplayDoPayload(mensagem?.payload, mensagem);

  return {
    ...mensagem,
    senderType,
    displayText: displayText || melhorFallbackTexto(mensagem, senderType),
    displaySubtext: displaySubtext || "",
    messageKind,
  };
}

function normalizarConversa(contato) {
  const display = extrairDisplayDoPayload(contato?.ultimo_payload, contato);
  const previewText = display.displayText || (!isTextoTecnico(contato?.ultima_previa) ? contato?.ultima_previa : "");
  const fallback =
    contato?.ultimo_tipo === "document" ? "Documento" : contato?.ultimo_tipo === "image" ? "Imagem" : "Sem mensagens";

  return {
    ...contato,
    previewText: previewText || fallback,
  };
}

function isImagem(attachment) {
  return attachment?.fileType === "image" || attachment?.mimeType?.startsWith("image/");
}

function formatarTamanho(size) {
  if (!size || Number.isNaN(Number(size))) return null;
  const bytes = Number(size);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function extensaoArquivo(attachment) {
  const nome = attachment?.fileName || "";
  const match = nome.match(/\.([a-z0-9]+)$/i);
  return (match?.[1] || attachment?.fileType || "arquivo").toUpperCase();
}

function isUrlProtegida(url) {
  return String(url || "").startsWith("/api/");
}

function temTextoRelevante(mensagem) {
  return Boolean(String(mensagem?.displayText || "").trim() || String(mensagem?.displaySubtext || "").trim());
}

function AnexoImagem({ attachment, onOpen, isMobile }) {
  const [src, setSrc] = useState("");
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let ativo = true;
    let objectUrl = "";

    async function carregar() {
      setLoading(true);
      setErro("");
      try {
        if (!isUrlProtegida(attachment.fileUrl)) {
          if (ativo) setSrc(attachment.fileUrl);
          return;
        }

        const res = await api.get(attachment.fileUrl, { responseType: "blob" });
        objectUrl = URL.createObjectURL(res.data);
        if (ativo) setSrc(objectUrl);
      } catch {
        if (ativo) setErro("Erro ao carregar imagem");
      } finally {
        if (ativo) setLoading(false);
      }
    }

    carregar();
    return () => {
      ativo = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [attachment.fileUrl]);

  if (loading) return <div style={{ ...s.imageLoading, ...(isMobile ? s.imageLoadingMobile : {}) }}>Carregando imagem...</div>;
  if (erro) return <div style={s.attachmentError}>{erro}</div>;

  return (
    <button type="button" onClick={() => onOpen(src, attachment.fileName)} style={s.imageButton}>
      <img src={src} alt={attachment.fileName} style={{ ...s.imagePreview, ...(isMobile ? s.imagePreviewMobile : {}) }} />
    </button>
  );
}

function AnexoArquivo({ attachment, isMobile }) {
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");

  async function abrirOuBaixar(download = false) {
    setLoading(true);
    setErro("");
    try {
      if (!isUrlProtegida(attachment.fileUrl)) {
        if (download) {
          const link = document.createElement("a");
          link.href = attachment.fileUrl;
          link.download = attachment.fileName || "arquivo";
          link.click();
        } else {
          window.open(attachment.fileUrl, "_blank", "noopener,noreferrer");
        }
        return;
      }

      const res = await api.get(attachment.fileUrl, { responseType: "blob" });
      const objectUrl = URL.createObjectURL(res.data);
      if (download) {
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = attachment.fileName || "arquivo";
        link.click();
      } else {
        window.open(objectUrl, "_blank", "noopener,noreferrer");
      }
      setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
    } catch {
      setErro("Erro ao carregar anexo");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ ...s.fileCard, ...(isMobile ? s.fileCardMobile : {}) }}>
      <div style={s.fileBadge}>{extensaoArquivo(attachment)}</div>
      <div style={s.fileBody}>
        <div style={s.fileName}>{attachment.fileName || "Arquivo"}</div>
        <div style={s.fileMeta}>
          {attachment.mimeType || attachment.fileType}
          {formatarTamanho(attachment.size) ? ` - ${formatarTamanho(attachment.size)}` : ""}
        </div>
        <div style={{ ...s.fileActions, ...(isMobile ? s.fileActionsMobile : {}) }}>
          <button type="button" onClick={() => abrirOuBaixar(false)} style={{ ...s.fileActionBtn, ...(isMobile ? s.fileActionBtnMobile : {}) }} disabled={loading}>
            Abrir
          </button>
          <button type="button" onClick={() => abrirOuBaixar(true)} style={{ ...s.fileActionBtn, ...(isMobile ? s.fileActionBtnMobile : {}) }} disabled={loading}>
            Baixar
          </button>
        </div>
        {erro && <div style={s.attachmentError}>{erro}</div>}
      </div>
    </div>
  );
}

export default function Conversas() {
  const { isMobile, isSmallMobile } = useViewport();
  const [conversas, setConversas] = useState([]);
  const [selecionado, setSelecionado] = useState(null);
  const [mensagens, setMensagens] = useState([]);
  const [busca, setBusca] = useState("");
  const [imagemAberta, setImagemAberta] = useState(null);
  const [loadingLista, setLoadingLista] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);
  const [erro, setErro] = useState("");
  const [erroChat, setErroChat] = useState("");
  const [listaAbertaMobile, setListaAbertaMobile] = useState(true);
  const selecionadoRef = useRef(null);

  useEffect(() => {
    if (!isMobile) setListaAbertaMobile(true);
  }, [isMobile]);

  useEffect(() => {
    selecionadoRef.current = selecionado;
  }, [selecionado]);

  const abrirConversa = useCallback(
    async (contato, options = {}) => {
      const { atualizarSelecionado = true } = options;
      if (!contato?.telefone) return;

      if (atualizarSelecionado) setSelecionado(contato);
      setLoadingChat(true);
      setErroChat("");
      try {
        const res = await api.get(`/api/conversas/${encodeURIComponent(contato.telefone)}`);
        setMensagens((res.data.mensagens || []).map(normalizarMensagem));
        if (isMobile) setListaAbertaMobile(false);
      } catch {
        setMensagens([]);
        setErroChat("Não foi possível carregar o histórico desta conversa.");
      } finally {
        setLoadingChat(false);
      }
    },
    [isMobile],
  );

  const carregarLista = useCallback(async () => {
    setLoadingLista(true);
    setErro("");
    try {
      const res = await api.get("/api/conversas");
      const lista = (res.data.conversas || []).map(normalizarConversa);
      setConversas(lista);

      const atual = selecionadoRef.current;
      const selecionadoAtualizado = atual ? lista.find((item) => item.telefone === atual.telefone) || null : null;

      if (selecionadoAtualizado) {
        setSelecionado(selecionadoAtualizado);
      } else if (lista[0]) {
        await abrirConversa(lista[0], { atualizarSelecionado: true });
      } else {
        setSelecionado(null);
        setMensagens([]);
        setErroChat("");
      }
    } catch {
      setErro("Erro ao carregar conversas.");
    } finally {
      setLoadingLista(false);
    }
  }, [abrirConversa]);

  useEffect(() => {
    carregarLista();
  }, [carregarLista]);

  const conversasFiltradas = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return conversas;
    return conversas.filter((c) =>
      [c.nome, c.telefone, c.previewText, c.ultima_previa, c.ultimo_tipo]
        .filter(Boolean)
        .some((valor) => String(valor).toLowerCase().includes(termo)),
    );
  }, [busca, conversas]);

  const mostrarLista = !isMobile || listaAbertaMobile || !selecionado;
  const mostrarChat = !isMobile || (!listaAbertaMobile && !!selecionado);

  return (
    <div
      style={{
        ...s.page,
        ...(isMobile ? s.pageMobile : {}),
      }}
    >
      {mostrarLista && (
        <aside style={{ ...s.sidebar, ...(isMobile ? s.sidebarMobile : {}) }}>
          <div style={s.sidebarHeader}>
            <h1 style={s.title}>Conversas</h1>
            <div style={s.searchBox}>
              <Search size={15} color="#64748b" />
              <input
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar paciente..."
                style={s.searchInput}
              />
            </div>
          </div>

          <div style={s.contactList}>
            {loadingLista && <p style={s.sideInfo}>Carregando...</p>}
            {erro && <p style={s.sideError}>{erro}</p>}
            {!loadingLista && !conversasFiltradas.length && <p style={s.sideInfo}>Nenhuma conversa.</p>}

            {conversasFiltradas.map((contato) => {
              const ativo = selecionado?.telefone === contato.telefone;
              return (
                <button
                  key={contato.telefone}
                  onClick={() => abrirConversa(contato)}
                  style={{ ...s.contactItem, ...(ativo ? s.contactItemActive : {}) }}
                >
                  <div style={s.avatar}>{inicial(contato)}</div>
                  <div style={s.contactMain}>
                    <div style={s.contactTop}>
                      <div style={s.contactName}>{contato.nome || contato.telefone}</div>
                      <div style={s.contactDate}>{formatarDataLista(contato.ultima_mensagem)}</div>
                    </div>
                    <div style={s.contactPreview}>
                      <span style={s.contactPreviewIcon}>🗨️</span>
                      <span style={s.contactPreviewText}>{resumoTexto(contato.previewText, contato.ultimo_tipo)}</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>
      )}

      {mostrarChat && (
        <section style={{ ...s.chat, ...(isMobile ? s.chatMobile : {}) }}>
          {!selecionado ? (
            <div style={s.emptyState}>
              <MessageCircle size={40} color="#314155" />
              <p style={s.emptyText}>Selecione uma conversa</p>
            </div>
          ) : (
            <>
              <header style={{ ...s.chatHeader, ...(isSmallMobile ? s.chatHeaderMobile : {}) }}>
                {isMobile && (
                  <button type="button" style={s.backButton} onClick={() => setListaAbertaMobile(true)} aria-label="Voltar para lista">
                    <ArrowLeft size={18} />
                  </button>
                )}
                <div style={s.avatarLarge}>{inicial(selecionado)}</div>
                <div style={s.headerMain}>
                  <div style={s.headerName}>{selecionado.nome || selecionado.telefone}</div>
                  <div style={s.headerPhone}>{selecionado.telefone}</div>
                </div>
              </header>

              <div style={{ ...s.chatBody, ...(isMobile ? s.chatBodyMobile : {}) }}>
                {loadingChat && <p style={s.sideInfo}>Carregando mensagens...</p>}
                {!loadingChat && erroChat && <p style={s.sideError}>{erroChat}</p>}
                {!loadingChat && !erroChat && !mensagens.length && <p style={s.sideInfo}>Nenhuma mensagem encontrada.</p>}

                {mensagens.map((mensagem) => {
                  const bot = mensagem.senderType === "bot";
                  return (
                    <div
                      key={mensagem.id}
                      style={{
                        ...s.row,
                        justifyContent: bot ? "flex-start" : "flex-end",
                      }}
                    >
                      <div
                        style={{
                          ...s.bubble,
                          ...(bot ? s.bubbleBot : s.bubbleCliente),
                          ...(isMobile ? s.bubbleMobile : {}),
                        }}
                      >
                        {bot && <div style={s.label}>Sofia</div>}
                        {mensagem.attachments?.length > 0 && (
                          <div style={s.attachmentsWrap}>
                            {mensagem.attachments.map((attachment) =>
                              isImagem(attachment) ? (
                                <AnexoImagem
                                  key={attachment.id}
                                  attachment={attachment}
                                  isMobile={isMobile}
                                  onOpen={(src, nome) => setImagemAberta({ src, nome })}
                                />
                              ) : (
                                <AnexoArquivo key={attachment.id} attachment={attachment} isMobile={isMobile} />
                              ),
                            )}
                          </div>
                        )}
                        {temTextoRelevante(mensagem) && (
                          <div>
                            {mensagem.displayText && <div style={s.text}>{mensagem.displayText}</div>}
                            {mensagem.displaySubtext && <div style={s.subtext}>{mensagem.displaySubtext}</div>}
                          </div>
                        )}
                        <div style={s.meta}>
                          <span>{formatarHora(mensagem.timestamp || mensagem.criado_em)}</span>
                          {bot && iconeStatus(mensagem.status_envio)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </section>
      )}

      {imagemAberta && (
        <div style={s.modalOverlay} onClick={() => setImagemAberta(null)}>
          <div style={s.modalCard} onClick={(e) => e.stopPropagation()}>
            <img src={imagemAberta.src} alt={imagemAberta.nome} style={s.modalImage} />
            <div style={{ ...s.modalFooter, ...(isSmallMobile ? s.modalFooterMobile : {}) }}>
              <span style={s.modalName}>{imagemAberta.nome}</span>
              <button type="button" onClick={() => setImagemAberta(null)} style={s.modalClose}>
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const s = {
  page: {
    display: "flex",
    marginTop: -32,
    marginLeft: -32,
    marginRight: -32,
    marginBottom: -32,
    minHeight: "calc(100vh - 64px)",
    background: "#0d131b",
    color: "#e5edf6",
    overflow: "hidden",
  },
  pageMobile: {
    display: "block",
    marginLeft: -16,
    marginRight: -16,
    marginBottom: -16,
    marginTop: 0,
    minHeight: "calc(100dvh - 32px)",
    paddingTop: "max(8px, env(safe-area-inset-top, 0px))",
    overflowX: "hidden",
  },
  sidebar: {
    width: 330,
    minWidth: 330,
    background: "#171d25",
    borderRight: "1px solid #283445",
    display: "flex",
    flexDirection: "column",
  },
  sidebarMobile: {
    width: "100%",
    minWidth: 0,
    minHeight: "calc(100dvh - 32px)",
  },
  sidebarHeader: {
    padding: "22px 18px 14px",
    borderBottom: "1px solid #283445",
  },
  title: {
    margin: 0,
    marginBottom: 14,
    fontSize: 17,
    fontWeight: 700,
  },
  searchBox: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    height: 40,
    padding: "0 12px",
    background: "#0f141b",
    border: "1px solid #2a3443",
    borderRadius: 10,
  },
  searchInput: {
    width: "100%",
    background: "transparent",
    border: "none",
    outline: "none",
    color: "#d8e1eb",
    fontSize: 14,
  },
  contactList: {
    flex: 1,
    overflowY: "auto",
    padding: 10,
  },
  sideInfo: {
    padding: 16,
    color: "#93a4b8",
    fontSize: 13,
  },
  sideError: {
    padding: 16,
    color: "#f87171",
    fontSize: 13,
  },
  contactItem: {
    width: "100%",
    display: "flex",
    gap: 12,
    padding: "12px 10px",
    background: "transparent",
    border: "none",
    borderRadius: 12,
    color: "inherit",
    textAlign: "left",
    cursor: "pointer",
  },
  contactItemActive: {
    background: "#202833",
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 999,
    background: "#2563eb",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 18,
    fontWeight: 700,
    flexShrink: 0,
  },
  avatarLarge: {
    width: 40,
    height: 40,
    borderRadius: 999,
    background: "#2563eb",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 18,
    fontWeight: 700,
    flexShrink: 0,
  },
  contactMain: {
    flex: 1,
    minWidth: 0,
  },
  contactTop: {
    display: "flex",
    gap: 8,
    alignItems: "center",
  },
  contactName: {
    flex: 1,
    fontSize: 13,
    fontWeight: 700,
    color: "#eef4fb",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  contactDate: {
    fontSize: 11,
    color: "#94a3b8",
    flexShrink: 0,
  },
  contactPreview: {
    display: "flex",
    gap: 6,
    alignItems: "center",
    marginTop: 6,
    color: "#94a3b8",
    fontSize: 12,
  },
  contactPreviewIcon: {
    flexShrink: 0,
  },
  contactPreviewText: {
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  chat: {
    flex: 1,
    minWidth: 0,
    display: "flex",
    flexDirection: "column",
    background: "#0c1219",
  },
  chatMobile: {
    width: "100%",
    minHeight: "calc(100dvh - 40px - env(safe-area-inset-top, 0px))",
  },
  chatHeader: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "16px 22px",
    background: "#171d25",
    borderBottom: "1px solid #283445",
  },
  chatHeaderMobile: {
    padding: "18px 16px 14px",
  },
  backButton: {
    width: 38,
    height: 38,
    borderRadius: 10,
    border: "1px solid #2a3443",
    background: "#0f141b",
    color: "#e5edf6",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    flexShrink: 0,
  },
  headerMain: {
    minWidth: 0,
  },
  headerName: {
    fontSize: 15,
    fontWeight: 700,
  },
  headerPhone: {
    marginTop: 2,
    color: "#7e8ea4",
    fontSize: 13,
  },
  chatBody: {
    flex: 1,
    overflowY: "auto",
    padding: "18px 22px 24px",
    display: "flex",
    flexDirection: "column",
    gap: 10,
    backgroundColor: "#0b141a",
    backgroundImage: "radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)",
    backgroundSize: "18px 18px",
  },
  chatBodyMobile: {
    padding: "16px 12px calc(20px + env(safe-area-inset-bottom, 0px))",
  },
  emptyState: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
  },
  emptyText: {
    marginTop: 12,
    color: "#8ea0b5",
    fontSize: 14,
  },
  row: {
    display: "flex",
    width: "100%",
  },
  bubble: {
    width: "fit-content",
    maxWidth: "72%",
    minWidth: 96,
    borderRadius: 16,
    padding: "10px 12px 8px",
    boxShadow: "0 8px 20px rgba(0,0,0,0.18)",
  },
  bubbleMobile: {
    maxWidth: "84%",
    minWidth: 0,
  },
  bubbleBot: {
    background: "#202c33",
    color: "#e9edef",
    borderTopLeftRadius: 6,
  },
  bubbleCliente: {
    background: "#005c4b",
    color: "#e9edef",
    borderTopRightRadius: 6,
  },
  label: {
    marginBottom: 8,
    fontSize: 12,
    fontWeight: 700,
    color: "#8ad1ff",
  },
  text: {
    fontSize: 14,
    lineHeight: 1.45,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  subtext: {
    marginTop: 6,
    fontSize: 12,
    lineHeight: 1.35,
    color: "rgba(233,237,239,0.72)",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  attachmentsWrap: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    marginBottom: 8,
  },
  imageButton: {
    background: "transparent",
    border: "none",
    padding: 0,
    cursor: "pointer",
  },
  imagePreview: {
    display: "block",
    width: "100%",
    maxWidth: 320,
    maxHeight: 240,
    objectFit: "cover",
    borderRadius: 12,
  },
  imagePreviewMobile: {
    maxWidth: "100%",
    maxHeight: 220,
  },
  imageLoading: {
    minWidth: 180,
    minHeight: 120,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "rgba(255,255,255,0.08)",
    borderRadius: 12,
    color: "#cbd5e1",
    fontSize: 12,
  },
  imageLoadingMobile: {
    minWidth: 0,
    width: "100%",
  },
  fileCard: {
    display: "flex",
    gap: 10,
    padding: 10,
    background: "rgba(255,255,255,0.08)",
    borderRadius: 12,
    minWidth: 220,
  },
  fileCardMobile: {
    minWidth: 0,
    width: "100%",
  },
  fileBadge: {
    width: 48,
    height: 48,
    borderRadius: 10,
    background: "rgba(15,23,42,0.35)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    fontWeight: 700,
    color: "#bfdbfe",
    flexShrink: 0,
  },
  fileBody: {
    flex: 1,
    minWidth: 0,
  },
  fileName: {
    fontSize: 13,
    fontWeight: 700,
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  fileMeta: {
    marginTop: 4,
    fontSize: 11,
    color: "rgba(233,237,239,0.72)",
    wordBreak: "break-word",
  },
  fileActions: {
    display: "flex",
    gap: 8,
    marginTop: 8,
  },
  fileActionsMobile: {
    flexWrap: "wrap",
  },
  fileActionBtn: {
    border: "none",
    borderRadius: 8,
    padding: "6px 10px",
    background: "rgba(15,23,42,0.42)",
    color: "#e2e8f0",
    fontSize: 12,
    cursor: "pointer",
  },
  fileActionBtnMobile: {
    minHeight: 40,
    flex: "1 1 90px",
  },
  attachmentError: {
    marginTop: 6,
    fontSize: 11,
    color: "#fecaca",
  },
  meta: {
    marginTop: 8,
    display: "flex",
    justifyContent: "flex-end",
    alignItems: "center",
    gap: 6,
    fontSize: 11,
    color: "rgba(233,237,239,0.72)",
  },
  modalOverlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.75)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    zIndex: 50,
  },
  modalCard: {
    maxWidth: "min(92vw, 1000px)",
    maxHeight: "90vh",
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  modalImage: {
    maxWidth: "100%",
    maxHeight: "calc(90vh - 56px)",
    objectFit: "contain",
    borderRadius: 14,
  },
  modalFooter: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    color: "#e5edf6",
  },
  modalFooterMobile: {
    flexDirection: "column",
    alignItems: "stretch",
  },
  modalName: {
    fontSize: 13,
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  modalClose: {
    border: "none",
    borderRadius: 8,
    padding: "10px 12px",
    background: "#1f2937",
    color: "#fff",
    cursor: "pointer",
  },
};
