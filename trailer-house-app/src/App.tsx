// ============================================================
// メインアプリ
// ============================================================

import { Header } from './components/Header';
import { CustomizerView } from './components/customizer/CustomizerView';
import { ThreeDView } from './components/three/ThreeDView';
import { EstimateView } from './components/estimate/EstimateView';
import { useAppStore } from './store/useAppStore';
import './styles/global.css';

function App() {
  const { currentView } = useAppStore();

  return (
    <div className="app-root">
      <Header />
      <main className="app-main">
        {currentView === 'customizer' && <CustomizerView />}
        {currentView === '3d' && <ThreeDView />}
        {currentView === 'estimate' && <EstimateView />}
      </main>
    </div>
  );
}

export default App;
