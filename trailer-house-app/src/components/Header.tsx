// ============================================================
// ヘッダーコンポーネント
// ============================================================

import React from 'react';
import { useAppStore } from '../store/useAppStore';
import type { View } from '../types';

const NAV_ITEMS: { id: View; label: string; step: number }[] = [
  { id: 'customizer', label: '① 間取り設計', step: 1 },
  { id: '3d', label: '② 3Dパース確認', step: 2 },
  { id: 'estimate', label: '③ 見積もり・お問い合わせ', step: 3 },
];

export const Header: React.FC = () => {
  const { currentView, setCurrentView, placedModules } = useAppStore();

  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo">
          <span className="logo-mark">TH</span>
        </div>
        <div>
          <div className="header-title">TrailerHouse Studio</div>
          <div className="header-sub">トレーラーハウス カスタマイザー</div>
        </div>
      </div>

      <nav className="header-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={`nav-step ${currentView === item.id ? 'active' : ''}`}
            onClick={() => setCurrentView(item.id)}
          >
            <span className="step-num">{item.step}</span>
            <span className="step-label">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="header-meta">
        {placedModules.length > 0 && (
          <span className="module-count">{placedModules.length}個配置済み</span>
        )}
      </div>
    </header>
  );
};
