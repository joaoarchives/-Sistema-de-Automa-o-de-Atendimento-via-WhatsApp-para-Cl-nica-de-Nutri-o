import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import AgendaDia from "./pages/AgendaDia";
import AgendaSemana from "./pages/AgendaSemana";
import Historico from "./pages/Historico";
import Layout from "./components/Layout";

function RotaProtegida({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" replace />;
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
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
