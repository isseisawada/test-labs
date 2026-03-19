// ============================================================
// カスタマイザーメイン画面
// ============================================================

import React, { useState } from 'react';
import { ModulePanel } from './ModulePanel';
import { FloorPlan } from './FloorPlan';
import { EstimatePanel } from './EstimatePanel';
import type { ModuleDefinition } from '../../types';

export const CustomizerView: React.FC = () => {
  const [draggingDef, setDraggingDef] = useState<ModuleDefinition | null>(null);

  return (
    <div className="customizer-layout">
      {/* 左パネル */}
      <aside className="left-panel">
        <ModulePanel onDragStart={(def) => setDraggingDef(def)} />
      </aside>

      {/* 中央：平面図 */}
      <main className="center-panel">
        <div className="center-header">
          <h1 className="center-title">間取り設計エリア</h1>
          <p className="center-hint">
            {draggingDef
              ? `「${draggingDef.label}」を配置する場所をクリックしてください`
              : 'パーツを選択して配置エリアをクリック、またはドラッグ&ドロップで配置できます'}
          </p>
        </div>
        <FloorPlan
          draggingDef={draggingDef}
          onDragEnd={() => setDraggingDef(null)}
        />
        {draggingDef && (
          <div className="placing-indicator">
            <span>{draggingDef.icon} {draggingDef.label} を配置中</span>
            <button onClick={() => setDraggingDef(null)} className="cancel-btn">キャンセル</button>
          </div>
        )}
      </main>

      {/* 右パネル */}
      <aside className="right-panel">
        <EstimatePanel />
      </aside>
    </div>
  );
};
