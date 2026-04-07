import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import AgendaDia from "./pages/AgendaDia";
import AgendaSemana from "./pages/AgendaSemana";
import Historico from "./pages/Historico";
import Conversas from "./pages/Conversas";
import Layout from "./components/Layout";

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

function RotaProtegida({ children }) {
  const token = localStorage.getItem("token");
  if (!tokenValido(token)) {
    localStorage.removeItem("token");
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RotaProtegida>
              <Layout />
            </RotaProtegida>
          }
        >
          <Route index element={<Navigate to="/agenda/dia" replace />} />
          <Route path="agenda/dia" element={<AgendaDia />} />
          <Route path="agenda/semana" element={<AgendaSemana />} />
          <Route path="historico" element={<Historico />} />
          <Route path="conversas" element={<Conversas />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
