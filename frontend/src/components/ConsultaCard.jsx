import { cancelarConsulta, concluirConsulta, confirmarPagamento } from "../api/api";
import useViewport from "../hooks/useViewport";

const STATUS = {
  aguardando_pagamento: { bg: "#2d1f08", cor: "#e3a008", texto: "Ag. Pagamento" },
  confirmado: { bg: "#0c2d4a", cor: "#58a6ff", texto: "Confirmada" },
  pendente: { bg: "#2d2008", cor: "#e3a008", texto: "Pendente" },
  concluido: { bg: "#1d3a2e", cor: "#00b37e", texto: "Concluída" },
  cancelado: { bg: "#2d0f0f", cor: "#f85149", texto: "Cancelada" },
};

const TIPO_LABEL = {
  primeira_consulta: "1ª Consulta",
  retorno: "Retorno",
};

export default function ConsultaCard({ consulta, onAtualizar }) {
  const { isMobile, isSmallMobile } = useViewport();
  const status = STATUS[consulta.status] || STATUS.confirmado;
  const isFinal = consulta.status === "concluido" || consulta.status === "cancelado";
  const aguardandoPagamento = consulta.status === "aguardando_pagamento";

  async function handleCancelar() {
    if (!confirm(`Cancelar consulta de ${consulta.nome}?`)) return;
    try {
      await cancelarConsulta(consulta.id);
      onAtualizar();
    } catch {
      alert("Erro ao cancelar consulta.");
    }
  }

  async function handleConcluir() {
    if (!confirm(`Marcar consulta de ${consulta.nome} como concluída?`)) return;
    try {
      await concluirConsulta(consulta.id);
      onAtualizar();
    } catch {
      alert("Erro ao concluir consulta.");
    }
  }

  async function handleConfirmarPagamento() {
    if (!confirm(`Confirmar pagamento de ${consulta.nome}?`)) return;
    try {
      const resposta = await confirmarPagamento(consulta.id);
      onAtualizar();
      if (resposta?.data?.aviso) {
        alert(resposta.data.aviso);
      }
    } catch {
      alert("Erro ao confirmar pagamento.");
    }
  }

  return (
    <div
      style={{
        ...styles.card,
        ...(isMobile ? styles.cardMobile : {}),
        opacity: consulta.status === "cancelado" ? 0.6 : 1,
        borderLeft: aguardandoPagamento ? "2px solid #e3a008" : "2px solid transparent",
      }}
    >
      <div style={{ ...styles.horario, ...(isMobile ? styles.horarioMobile : {}) }}>{String(consulta.horario).slice(0, 5)}</div>

      <div style={{ ...styles.info, ...(isMobile ? styles.infoMobile : {}) }}>
        <div
          style={{
            ...styles.nome,
            textDecoration: consulta.status === "cancelado" ? "line-through" : "none",
            color: consulta.status === "cancelado" ? "#8b949e" : "#e6edf3",
          }}
        >
          {consulta.nome || "Paciente"}
        </div>
        <div style={{ ...styles.detalhe, ...(isSmallMobile ? styles.detalheMobile : {}) }}>
          {consulta.telefone}
          {" · "}
          {TIPO_LABEL[consulta.tipo_consulta] || consulta.tipo_consulta}
          {consulta.sexo && <>{` · ${consulta.sexo}`}</>}
          {consulta.plano && (
            <>
              {" · "}
              <span style={{ color: "#58a6ff" }}>{consulta.plano}</span>
            </>
          )}
        </div>
      </div>

      <div style={{ ...styles.acoes, ...(isMobile ? styles.acoesMobile : {}) }}>
        <span style={{ ...styles.badge, background: status.bg, color: status.cor }}>{status.texto}</span>

        {aguardandoPagamento && (
          <button style={{ ...styles.btnConfirmar, ...(isMobile ? styles.btnMobile : {}) }} onClick={handleConfirmarPagamento}>
            ✓ Confirmar Pagamento
          </button>
        )}

        {!isFinal && !aguardandoPagamento && (
          <button style={{ ...styles.btnConcluir, ...(isMobile ? styles.btnMobile : {}) }} onClick={handleConcluir}>
            ✓ Concluir
          </button>
        )}

        {!isFinal && (
          <button style={{ ...styles.btnCancelar, ...(isMobile ? styles.btnMobile : {}) }} onClick={handleCancelar}>
            ✕ Cancelar
          </button>
        )}
      </div>
    </div>
  );
}

const styles = {
  card: {
    display: "flex",
    alignItems: "center",
    gap: 16,
    width: "100%",
    maxWidth: "100%",
    minWidth: 0,
    background: "#161b22",
    border: "0.5px solid #30363d",
    borderRadius: 10,
    padding: "14px 20px",
    transition: "border-color 0.15s",
  },
  cardMobile: {
    flexDirection: "column",
    alignItems: "stretch",
    gap: 12,
    padding: "14px 14px 16px",
  },
  horario: {
    fontSize: 18,
    fontWeight: 500,
    color: "#58a6ff",
    minWidth: 54,
    fontVariantNumeric: "tabular-nums",
  },
  horarioMobile: {
    minWidth: 0,
  },
  info: { flex: 1, minWidth: 0 },
  infoMobile: {
    width: "100%",
  },
  nome: { fontWeight: 500, fontSize: 14, transition: "color 0.15s" },
  detalhe: { fontSize: 12, color: "#8b949e", marginTop: 3, wordBreak: "break-word" },
  detalheMobile: {
    lineHeight: 1.5,
  },
  acoes: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" },
  acoesMobile: {
    width: "100%",
    alignItems: "stretch",
    minWidth: 0,
  },
  badge: {
    fontSize: 11,
    fontWeight: 500,
    padding: "4px 10px",
    borderRadius: 20,
  },
  btnConfirmar: {
    padding: "8px 12px",
    background: "#2d1f08",
    color: "#e3a008",
    border: "0.5px solid #e3a00844",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
  },
  btnConcluir: {
    padding: "8px 12px",
    background: "#1d3a2e",
    color: "#00b37e",
    border: "0.5px solid #00b37e44",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
  },
  btnCancelar: {
    padding: "8px 12px",
    background: "#2d0f0f",
    color: "#f85149",
    border: "0.5px solid #f8514933",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
  },
  btnMobile: {
    minHeight: 42,
    flex: "1 1 100%",
    minWidth: 0,
  },
};
