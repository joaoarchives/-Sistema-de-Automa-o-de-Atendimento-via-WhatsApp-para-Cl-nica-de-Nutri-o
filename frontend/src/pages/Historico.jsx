import { useState, useEffect, useCallback } from "react";
import { getHistorico } from "../api/api";
import ConsultaCard from "../components/ConsultaCard";
import useViewport from "../hooks/useViewport";

export default function Historico() {
  const { isMobile, isSmallMobile } = useViewport();
  const [dados, setDados]     = useState({ consultas: [], total: 0, paginas: 1 });
  const [pagina, setPagina]   = useState(1);
  const [loading, setLoading] = useState(false);
  const [erro, setErro]       = useState("");

  const carregar = useCallback(async () => {
    setLoading(true);
    setErro("");
    try {
      const res = await getHistorico(pagina);
      setDados(res.data);
    } catch {
      setErro("Erro ao carregar histórico.");
    } finally {
      setLoading(false);
    }
  }, [pagina]);

  useEffect(() => { carregar(); }, [carregar]);

  return (
      <div>
        <div style={styles.header}>
          <div>
            <h2 style={styles.titulo}>Histórico de Consultas</h2>
            <p style={styles.sub}>{dados.total ?? 0} consulta(s) no total</p>
          </div>
        </div>

        {loading && <p style={styles.info}>Carregando...</p>}
        {erro    && <p style={styles.erro}>{erro}</p>}

        {!loading && !erro && dados.consultas.length === 0 && (
            <div style={{ ...styles.vazio, ...(isSmallMobile ? styles.vazioMobile : {}) }}>
              <p>Nenhuma consulta encontrada.</p>
            </div>
        )}

        <div style={styles.lista}>
          {dados.consultas.map((c) => (
              <ConsultaCard key={c.id} consulta={c} onAtualizar={carregar} />
          ))}
        </div>

        {dados.paginas > 1 && (
            <div style={{ ...styles.paginacao, ...(isMobile ? styles.paginacaoMobile : {}) }}>
              <button
                  style={{
                    ...styles.btn,
                    ...(isSmallMobile ? styles.btnMobile : {}),
                    opacity: pagina === 1 ? 0.4 : 1,
                    cursor: pagina === 1 ? "not-allowed" : "pointer",
                  }}
                  onClick={() => setPagina((p) => Math.max(1, p - 1))}
                  disabled={pagina === 1}
              >
                ← Anterior
              </button>
              <span style={styles.pagInfo}>
            Página {pagina} de {dados.paginas}
          </span>
              <button
                  style={{
                    ...styles.btn,
                    ...(isSmallMobile ? styles.btnMobile : {}),
                    opacity: pagina === dados.paginas ? 0.4 : 1,
                    cursor: pagina === dados.paginas ? "not-allowed" : "pointer",
                  }}
                  onClick={() => setPagina((p) => Math.min(dados.paginas, p + 1))}
                  disabled={pagina === dados.paginas}
              >
                Próxima →
              </button>
            </div>
        )}
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
  info:      { color: "#8b949e", fontSize: 14 },
  erro:      { color: "#f85149", fontSize: 14 },
  vazio: {
    background: "#161b22",
    border: "0.5px solid #30363d",
    borderRadius: 10,
    padding: "32px 20px",
    textAlign: "center",
    color: "#8b949e",
    fontSize: 14,
  },
  vazioMobile: {
    padding: "24px 16px",
  },
  lista: { display: "flex", flexDirection: "column", gap: 8 },
  paginacao: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    marginTop: 24,
  },
  paginacaoMobile: {
    flexWrap: "wrap",
    justifyContent: "stretch",
    gap: 12,
  },
  btn: {
    padding: "10px 16px",
    borderRadius: 8,
    border: "0.5px solid #30363d",
    background: "#161b22",
    color: "#8b949e",
    fontSize: 13,
    fontWeight: 500,
    transition: "opacity 0.15s",
  },
  btnMobile: {
    flex: "1 1 140px",
    minHeight: 44,
  },
  pagInfo: { fontSize: 13, color: "#8b949e" },
};
