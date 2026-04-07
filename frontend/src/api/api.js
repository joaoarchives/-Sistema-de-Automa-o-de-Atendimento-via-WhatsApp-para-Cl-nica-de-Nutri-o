import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "";

const api = axios.create({ baseURL: BASE_URL });

function tokenValido(token) {
    if (!token) return false;

    try {
        const [, payloadBase64] = token.split(".");
        if (!payloadBase64) return false;

        const payloadJson = atob(payloadBase64.replace(/-/g, "+").replace(/_/g, "/"));
        const payload = JSON.parse(payloadJson);

        if (!payload?.exp) return true;
        return Number(payload.exp) * 1000 > Date.now();
    } catch {
        return false;
    }
}

// Injeta o token em toda requisição automaticamente
api.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");
    if (!tokenValido(token)) {
        localStorage.removeItem("token");
        return config;
    }

    config.headers.Authorization = `Bearer ${token}`;
    return config;
});

// Se o token expirou, manda pro login
api.interceptors.response.use(
    (res) => res,
    (err) => {
        if (err.response?.status === 401) {
            localStorage.removeItem("token");
            window.location.href = "/login";
        }
        return Promise.reject(err);
    }
);

export const login = (usuario, senha) =>
    api.post("/api/auth/login", { usuario, senha });

export const getAgendaDia = (data) =>
    api.get("/api/consultas/hoje", { params: { data } });

export const getAgendaSemana = (inicio) =>
    api.get("/api/consultas/semana", { params: { inicio } });

export const getHistorico = (pagina = 1, por_pagina = 20) =>
    api.get("/api/consultas/historico", { params: { pagina, por_pagina } });

export const confirmarPagamento = (id) =>
    api.patch(`/api/consultas/${id}/confirmar-pagamento`, {}, {
        headers: { 'Content-Type': 'application/json' }
    });

export const cancelarConsulta = (id) =>
    api.patch(`/api/consultas/${id}/cancelar`, {}, {
        headers: { 'Content-Type': 'application/json' }
    });

export const concluirConsulta = (id) =>
    api.patch(`/api/consultas/${id}/concluir`, {}, {
        headers: { 'Content-Type': 'application/json' }
    });

export const getConversas = () =>
    api.get("/api/conversas");

export const getMensagensContato = (telefone) =>
    api.get(`/api/conversas/${encodeURIComponent(telefone)}`);

export default api;
