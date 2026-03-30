import { useState, useEffect, useCallback } from "react";
import { getAgendaDia } from "../api/api";
import ConsultaCard from "../components/ConsultaCard";

function hojeISO() {
  return new Date().toISOString().slice(0, 10);
}

function formatarDataBR(iso) {
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}

export default function AgendaDia() {
  const [data, setData]           = useState(hojeISO());
  const [consultas, setConsultas] = useState([]);
  const [loading, setLoading]     = useState(false);
  const [erro, setErro]           = useState("");

  const carregar = useCallback(async () => {
    setLoading(true);
    setErro("");
    try {
      const res = await getAgendaDia(data);
      setConsultas(res.data.consultas);
    } catch {
      setErro("Erro ao carregar agenda.");
    } finally {
      setLoading(false);
    }
  }, [data]);

  useEffect(() => { carregar(); }, [carregar]);

  const confirmadas = consultas.filter((c) => c.status === "confirmado").length;
  const concluidas  = consultas.filter((c) => c.status === "concluido").length;
  const canceladas  = consultas.filter((c) => c.status === "cancelado").length;

  return (
      <div>
        <div style={styles.header}>
          <div>
            <h2 style={styles.titulo}>Agenda do Dia</h2>
            <p style={styles.sub}>{formatarDataBR(data)}</p>
          </div>
          <input
              type="date"
              value={data}
              onChange={(e) => setData(e.target.value)}
              style={styles.datePicker}
          />
        </div>

        {consultas.length > 0 && (
            <div style={styles.statsRow}>
              <div style={styles.statCard}>
                <div style={styles.statLabel}>Total</div>
                <div style={styles.statValue}>{consultas.length}</div>
              </div>
              <div style={styles.statCard}>
                <div style={styles.statLabel}>Confirmadas</div>
                <div style={{ ...styles.statValue, color: "#58a6ff" }}>{confirmadas}</div>
              </div>
              <div style={styles.statCard}>
                <div style={styles.statLabel}>Concluídas</div>
                <div style={{ ...styles.statValue, color: "#00b37e" }}>{concluidas}</div>
              </div>
              <div style={styles.statCard}>
                <div style={styles.statLabel}>Canceladas</div>
                <div style={{ ...styles.statValue, color: "#f85149" }}>{canceladas}</div>
              </div>
            </div>
        )}

        {loading && <p style={styles.info}>Carregando...</p>}
        {erro    && <p style={styles.erro}>{erro}</p>}

        {!loading && !erro && consultas.length === 0 && (
            <div style={styles.vazio}>
              <p>Nenhuma consulta para este dia.</p>
            </div>
        )}

        <div style={styles.lista}>
          {consultas.map((c) => (
              <ConsultaCard key={c.id} consulta={c} onAtualizar={carregar} />
          ))}
        </div>
      </div>
  );
}

const styles = {
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 24,
  },
  titulo:     { margin: 0, fontSize: 20, fontWeight: 600, color: "#e6edf3" },
  sub:        { margin: "4px 0 0", fontSize: 13, color: "#8b949e" },
  datePicker: {
    padding: "8px 12px",
    borderRadius: 8,
    border: "0.5px solid #30363d",
    background: "#161b22",
    color: "#e6edf3",
    fontSize: 13,
    cursor: "pointer",
    outline: "none",
  },
  statsRow: {
    display: "grid",
    gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    background: "#161b22",
    border: "0.5px solid #30363d",
    borderRadius: 10,
    padding: "12px 16px",
  },
  statLabel: { fontSize: 11, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 6 },
  statValue: { fontSize: 24, fontWeight: 500, color: "#e6edf3" },
  info:  { color: "#8b949e", fontSize: 14 },
  erro:  { color: "#f85149", fontSize: 14 },
  vazio: {
    background: "#161b22",
    border: "0.5px solid #30363d",
    borderRadius: 10,
    padding: "32px 20px",
    textAlign: "center",
    color: "#8b949e",
    fontSize: 14,
  },
  lista: { display: "flex", flexDirection: "column", gap: 8 },
};