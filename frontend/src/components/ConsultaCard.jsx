import { cancelarConsulta, concluirConsulta, confirmarPagamento } from "../api/api";

const STATUS = {
  aguardando_pagamento: { bg: "#2d1f08", cor: "#e3a008", texto: "Ag. Pagamento" },
  confirmado: { bg: "#0c2d4a", cor: "#58a6ff", texto: "Confirmada" },
  pendente:   { bg: "#2d2008", cor: "#e3a008", texto: "Pendente"   },
  concluido:  { bg: "#1d3a2e", cor: "#00b37e", texto: "Concluída"  },
  cancelado:  { bg: "#2d0f0f", cor: "#f85149", texto: "Cancelada"  },
};

const TIPO_LABEL = {
  primeira_consulta: "1ª Consulta",
  retorno:           "Retorno",
};

export default function ConsultaCard({ consulta, onAtualizar }) {
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
      await confirmarPagamento(consulta.id);
      onAtualizar();
    } catch {
      alert("Erro ao confirmar pagamento.");
    }
  }

  return (
      <div style={{
        ...styles.card,
        opacity: consulta.status === "cancelado" ? 0.6 : 1,
        borderLeft: aguardandoPagamento ? "2px solid #e3a008" : "2px solid transparent",
      }}>
        <div style={styles.horario}>{String(consulta.horario).slice(0, 5)}</div>

        <div style={styles.info}>
          <div style={{
            ...styles.nome,
            textDecoration: consulta.status === "cancelado" ? "line-through" : "none",
            color: consulta.status === "cancelado" ? "#8b949e" : "#e6edf3",
          }}>
            {consulta.nome || "Paciente"}
          </div>
          <div style={styles.detalhe}>
            {consulta.telefone}
            &nbsp;·&nbsp;
            {TIPO_LABEL[consulta.tipo_consulta] || consulta.tipo_consulta}
            {consulta.sexo && <>&nbsp;·&nbsp;{consulta.sexo}</>}
            {consulta.plano && <>&nbsp;·&nbsp;<span style={{color: "#58a6ff"}}>{consulta.plano}</span></>}
          </div>
        </div>

        <div style={styles.acoes}>
        <span style={{ ...styles.badge, background: status.bg, color: status.cor }}>
          {status.texto}
        </span>

          {aguardandoPagamento && (
              <button style={styles.btnConfirmar} onClick={handleConfirmarPagamento}>
                ✓ Confirmar Pagamento
              </button>
          )}

          {!isFinal && !aguardandoPagamento && (
              <>
                <button style={styles.btnConcluir} onClick={handleConcluir}>
                  ✓ Concluir
                </button>
              </>
          )}

          {!isFinal && (
              <button style={styles.btnCancelar} onClick={handleCancelar}>
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
    background: "#161b22",
    border: "0.5px solid #30363d",
    borderRadius: 10,
    padding: "14px 20px",
    transition: "border-color 0.15s",
  },
  horario: {
    fontSize: 18,
    fontWeight: 500,
    color: "#58a6ff",
    minWidth: 50,
    fontVariantNumeric: "tabular-nums",
  },
  info:  { flex: 1 },
  nome:  { fontWeight: 500, fontSize: 14, transition: "color 0.15s" },
  detalhe: { fontSize: 12, color: "#8b949e", marginTop: 3 },
  acoes: { display: "flex", alignItems: "center", gap: 8 },
  badge: {
    fontSize: 11,
    fontWeight: 500,
    padding: "3px 10px",
    borderRadius: 20,
  },
  btnConfirmar: {
    padding: "5px 12px",
    background: "#2d1f08",
    color: "#e3a008",
    border: "0.5px solid #e3a00844",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
  },
  btnConcluir: {
    padding: "5px 12px",
    background: "#1d3a2e",
    color: "#00b37e",
    border: "0.5px solid #00b37e44",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
  },
  btnCancelar: {
    padding: "5px 12px",
    background: "#2d0f0f",
    color: "#f85149",
    border: "0.5px solid #f8514933",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
  },
};
