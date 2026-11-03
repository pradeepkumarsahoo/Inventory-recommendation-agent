import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from './layouts/AppLayout';
import ExecutiveDashboard from './pages/ExecutiveDashboard';
import ProductIntelligence from './pages/ProductIntelligence';
import InventoryOptimization from './pages/InventoryOptimization';
import PricingIntelligence from './pages/PricingIntelligence';
import AgentDecisionCenter from './pages/AgentDecisionCenter';
import DailyGamePlan from './pages/DailyGamePlan';
import Architecture from './pages/Architecture';
import { StoreProvider } from './state/StoreContext';

export default function App() {
  return (
    <StoreProvider>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<ExecutiveDashboard />} />
          <Route path="products" element={<ProductIntelligence />} />
          <Route path="inventory" element={<InventoryOptimization />} />
          <Route path="pricing" element={<PricingIntelligence />} />
          <Route path="agents" element={<AgentDecisionCenter />} />
          <Route path="game-plan" element={<DailyGamePlan />} />
          <Route path="architecture" element={<Architecture />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </StoreProvider>
  );
}
