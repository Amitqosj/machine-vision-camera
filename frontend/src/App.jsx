import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ChamberProvider } from "./chamber/state/ChamberContext";
import { MainLayout } from "./chamber/layout/MainLayout";
import DashboardPage from "./pages/DashboardPage";
import CameraDetailPage from "./pages/CameraDetailPage";
import CombinedCamerasPage from "./pages/CombinedCamerasPage";
import RecordingSessionPage from "./pages/RecordingSessionPage";
import HardwareArduinoPage from "./pages/HardwareArduinoPage";
import SystemStatusPage from "./pages/SystemStatusPage";
import SettingsPage from "./pages/SettingsPage";
import LegacyInspectionPage from "./pages/LegacyInspectionPage";

export default function App() {
  return (
    <ChamberProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<MainLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="camera/all" element={<CombinedCamerasPage />} />
            <Route path="camera/:slug" element={<CameraDetailPage />} />
            <Route path="recording" element={<RecordingSessionPage />} />
            <Route path="hardware" element={<HardwareArduinoPage />} />
            <Route path="status" element={<SystemStatusPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="legacy-inspection" element={<LegacyInspectionPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ChamberProvider>
  );
}
