// ============================================================
// 左パネル：モジュール一覧
// ============================================================

import React, { useState } from 'react';
import { MODULE_DEFINITIONS } from '../../data/definitions';
import type { ModuleCategory, ModuleDefinition } from '../../types';
import { formatPrice } from '../../utils/estimate';

interface ModulePanelProps {
  onDragStart: (def: ModuleDefinition) => void;
}

const CATEGORIES: ModuleCategory[] = ['水回り', '家具', '収納', '寝室'];

export const ModulePanel: React.FC<ModulePanelProps> = ({ onDragStart }) => {
  const [activeCategory, setActiveCategory] = useState<ModuleCategory | 'すべて'>('すべて');

  const filtered = activeCategory === 'すべて'
    ? MODULE_DEFINITIONS
    : MODULE_DEFINITIONS.filter((m) => m.category === activeCategory);

  return (
    <div className="module-panel">
      <div className="panel-header">
        <h2 className="panel-title">パーツ選択</h2>
        <p className="panel-hint">クリックして配置エリアに追加</p>
      </div>

      <div className="category-tabs">
        <button
          className={`cat-tab ${activeCategory === 'すべて' ? 'active' : ''}`}
          onClick={() => setActiveCategory('すべて')}
        >
          すべて
        </button>
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            className={`cat-tab ${activeCategory === cat ? 'active' : ''}`}
            onClick={() => setActiveCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="module-list">
        {filtered.map((def) => (
          <div
            key={def.type}
            className="module-card"
            draggable
            onDragStart={() => onDragStart(def)}
          >
            <div className="module-card-icon" style={{ backgroundColor: def.color }}>
              <span>{def.icon}</span>
            </div>
            <div className="module-card-info">
              <div className="module-card-name">{def.label}</div>
              <div className="module-card-price">{formatPrice(def.price)}</div>
              <div className="module-card-desc">{def.description}</div>
              {def.isWater && (
                <span className="badge badge-water">給排水</span>
              )}
              {def.hasHeightConstraint && (
                <span className="badge badge-height">高さ制約</span>
              )}
            </div>
            <button
              className="module-add-btn"
              onClick={() => onDragStart(def)}
              title="クリックして追加"
            >
              ＋
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
