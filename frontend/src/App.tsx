import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import SearchPage from "./pages/SearchPage";
import LawyerDetailPage from "./pages/LawyerDetailPage";
import FirmDetailPage from "./pages/FirmDetailPage";
import LoginPage from "./pages/LoginPage";
import RegisterChoicePage from "./pages/RegisterChoicePage";
import RegisterClientPage from "./pages/RegisterClientPage";
import RegisterLawyerPage from "./pages/RegisterLawyerPage";
import RegisterFirmPage from "./pages/RegisterFirmPage";
import DashboardStub from "./pages/DashboardStub";

export default function App() {
  return (
    <>
      <Navbar />
      <main>
        <Routes>
          {/* Client view — the focus of this milestone */}
          <Route path="/" element={<SearchPage />} />
          <Route path="/advogados/:id" element={<LawyerDetailPage />} />
          <Route path="/escritorios/:id" element={<FirmDetailPage />} />

          {/* Auth & registration */}
          <Route path="/entrar" element={<LoginPage />} />
          <Route path="/cadastro" element={<RegisterChoicePage />} />
          <Route path="/cadastro/cliente" element={<RegisterClientPage />} />
          <Route path="/cadastro/advogado" element={<RegisterLawyerPage />} />
          <Route path="/cadastro/escritorio" element={<RegisterFirmPage />} />

          {/* Lawyer/firm dashboards: not implemented yet */}
          <Route path="/painel" element={<DashboardStub />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
