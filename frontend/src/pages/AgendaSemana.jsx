import { useState, useEffect, useCallback } from "react";
import { getAgendaSemana } from "../api/api";
import ConsultaCard from "../components/ConsultaCard";

function hojeISO() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth()+1).padStart(2,'0');
  const day = String(d.getDate()).padStart(2,'0');
  return `${y}-${m}-${day}`;
}
function toISO(val) {
  if (!val) return "";
  if (val instanceof Date) {
    const y = val.getFullYear();
    const m = String(val.getMonth()+1).padStart(2,'0');
    const d = String(val.getDate()).padStart(2,'0');
    return `${y}-${m}-${d}`;
  }
  return String(val).slice(0, 10);
}

function formatarDataBR(val) {
  const iso = toISO(val);
  if (!iso || iso.includes('N')) return "";
  const [ano, mes, dia] = iso.split("-");
  const d = new Date(`${ano}-${mes}-${dia}T12:00:00`);
  const dias = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"];
  return `${dias[d.getDay()]}, ${dia}/${mes}/${ano}`;
}

function adicionarDias(val, dias) {
  const iso = toISO(val);
  const d = new Date(iso + "T12:00:00");
  d.setDate(d.getDate() + dias);
  return toISO(d);
}

function agruparPorData(consultas) {
  return consultas.reduce((acc, c) => {
    const key = toISO(c.data);
    if (!key) return acc;
    acc[key] = acc[key] || [];
    acc[key].push(c);
    return acc;
  }, {});
}

export default function AgendaSemana() {
  const [inicio, setInicio]       = useState(hojeISO());
  const [consultas, setConsultas] = useState([]);
  const [loading, setLoading]     = useState(false);
  const [erro, setErro]           = useState("");

  const carregar = useCallback(async () => {
    setLoading(true);
    setErro("");
    try {
      const res = await getAgendaSemana(inicio);
      const todas = res.data.semana?.flatMap(d => d.consultas) ?? [];
      setConsultas(todas);
    } catch {
      setErro("Erro ao carregar agenda da semana.");
    } finally {
      setLoading(false);
    }
  }, [inicio]);

  useEffect(() => { carregar(); }, [carregar]);

  const fim      = adicionarDias(inicio, 6);
  const agrupado = agruparPorData(consultas);

  return (
      <div>
        <div style={styles.header}>
          <div>
            <h2 style={styles.titulo}>Agenda da Semana</h2>
            <p style={styles.sub}>
              {formatarDataBR(inicio)} → {formatarDataBR(fim)}
            </p>
          </div>
          <div style={styles.navSemana}>
            <button style={styles.btn} onClick={() => setInicio(adicionarDias(inicio, -7))}>
              ← Anterior
            </button>
            <button style={{ ...styles.btn, ...styles.btnHoje }} onClick={() => setInicio(hojeISO())}>
              Hoje
            </button>
            <button style={styles.btn} onClick={() => setInicio(adicionarDias(inicio, 7))}>
              Próxima →
            </button>
          </div>
        </div>

        {loading && <p style={styles.info}>Carregando...</p>}
        {erro    && <p style={styles.erro}>{erro}</p>}

        {!loading && !erro && consultas.length === 0 && (
            <div style={styles.vazio}>
              <p>Nenhuma consulta para esta semana.</p>
            </div>
        )}

        {Object.keys(agrupado).sort().map((data) => (
            <div key={data} style={styles.grupo}>
              <div style={styles.dataHeader}>
                <span style={styles.dataLabel}>{formatarDataBR(data)}</span>
                <span style={styles.dataBadge}>{agrupado[data].length} consulta(s)</span>
              </div>
              <div style={styles.lista}>
                {agrupado[data].map((c) => (
                    <ConsultaCard key={c.id} consulta={c} onAtualizar={carregar} />
                ))}
              </div>
            </div>
        ))}
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
  titulo:    { margin: 0, fontSize: 20, fontWeight: 600, color: "#e6edf3" },
  sub:       { margin: "4px 0 0", fontSize: 13, color: "#8b949e" },
  navSemana: { display: "flex", gap: 8 },
  btn: {
    padding: "8px 14px",
    borderRadius: 8,
    border: "0.5px solid #30363d",
    background: "#161b22",
    color: "#8b949e",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 500,
  },
  btnHoje: { color: "#00b37e", borderColor: "#00b37e44" },
  grupo:      { marginBottom: 28 },
  dataHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 10,
    paddingBottom: 10,
    borderBottom: "0.5px solid #30363d",
  },
  dataLabel: { fontSize: 14, fontWeight: 500, color: "#58a6ff" },
  dataBadge: {
    fontSize: 11,
    color: "#8b949e",
    background: "#1c2128",
    padding: "2px 8px",
    borderRadius: 20,
  },
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